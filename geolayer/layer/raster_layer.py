"""Geospatial Raster layer"""
# Author(s): Davide.De-Marchi@ec.europa.eu, Edoardo.Ramalli@ec.europa.eu
# Copyright © European Union 2022-2024
# 
# Licensed under the EUPL, Version 1.2 or as soon they will be approved by 
# the European Commission subsequent versions of the EUPL (the "Licence");
# 
# You may not use this work except in compliance with the Licence.
# 
# You may obtain a copy of the Licence at:
# https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

# Unless required by applicable law or agreed to in writing, software
# distributed under the Licence is distributed on an "AS IS"
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied.
# 
# See the Licence for the specific language governing permissions and
# limitations under the Licence.

# Python imports
import ipyleaflet
from io import StringIO, BytesIO
import sys
import json
import requests
import numpy as np

# vois import
from vois import colors
from vois.vuetify import textlist

# geolayer import
from geolayer.api import rasterAPI


#####################################################################################################################################################
# Utility functions
#####################################################################################################################################################
        
# Convert a range [scalemin,scalemax] into ratio and offset to be used to scale an image inside a VRT
def scaleminmax2ratiooffset(scalemin, scalemax):
    ratio  = 255.0 / (scalemax - scalemin)
    offset = -scalemin * ratio
    return ratio,offset

# Convert a ratio,offset int a range [scalemin,scalemax]
def ratiooffset2scaleminmax(ratio, offset):
    scalemin = -offset/ratio
    scalemax = scalemin + 255.0 / ratio
    return scalemin,scalemax

# Convert an original value to a scaled value using ratio and offset
def scaled(value, ratio, offset):
    return value*ratio + offset

# Convert a scaled value back to its original space
def unscaled(scaledvalue, ratio, offset):
    return (scaledvalue - offset) / ratio



# Red display range from band information statistics. Returns minvalue and maxvalue
def minmaxrange(stac_band_dict, scalemin=None, scalemax=None):
    if isinstance(scalemin, float) or isinstance(scalemin, int):
        minvalue = float(scalemin)
    else:
        if 'statistics' in stac_band_dict and 'mean' in stac_band_dict['statistics']:
            minvalue = float(stac_band_dict['statistics']['mean']) - 2.0 * float(stac_band_dict['statistics']['stddev'])
        else:
            minvalue = None

    if isinstance(scalemax, float) or isinstance(scalemax, int):
        maxvalue = float(scalemax)
    else:
        if 'statistics' in stac_band_dict and 'mean' in stac_band_dict['statistics'] and 'stddev' in stac_band_dict['statistics']:
            maxvalue = float(stac_band_dict['statistics']['mean']) + 2.0 * float(stac_band_dict['statistics']['stddev'])
        else:
            maxvalue = None

    # Calculate stats using the rasterAPI
    if minvalue is None or maxvalue is None:

        jinfo = rasterAPI.rasterInfo(filepath, request_stats=True, detailed_stats=False)
        if 'bands' in jinfo and str(band) in jinfo['bands'] and 'statistics' in jinfo['bands'][str(band)]:
            vmin,vmax,vavg,vstddev = jinfo['bands'][str(band)]['statistics']

            if minvalue is None:
                minvalue = max(vmin, vavg - 2.0*vstddev)

            if maxvalue is None:
                maxvalue = min(vmax, vavg + 2.0*vstddev)

    return minvalue,maxvalue



#####################################################################################################################################################
# Class rasterlayer to create server-side VectorLayer instances for raster display without using inter client library
#####################################################################################################################################################
class RasterLayer:
    
    # Initialization
    def __init__(self,
                 filepath='',
                 band=1,
                 epsg=4326,
                 proj='',                      # To be used for projections that do not have an EPSG code (if not the empty string it is used instead of the passed epsg)
                 nodata=999999.0,
                 identify_dict=None,           # Dictionary to convert integer pixel values to strings (e.g. classes names)
                 identify_integer=False,       # True if the identify operation should convert pixels values to integer
                 identify_digits=6,            # Number of digits for identify of float values
                 identify_label='Value'):      # Label for identify operation

        self.filepath = filepath
        self.band     = band
        self.epsg     = epsg
        self.proj     = proj
        self.nodata   = nodata
        self._identify_dict    = identify_dict
        self._identify_integer = identify_integer
        self._identify_digits  = identify_digits
        self._identify_label   = identify_label
        

        # RasterSymbolizer info
        self.scaling     = 'near'    # near, fast, bilinear, bicubic, spline16, spline36, hanning, hamming, hermite, kaiser, quadric, catrom, gaussian, bessel, mitchell, sinc, lanczos, blackman  see http://mapnik.org/mapnik-reference/#3.0.22/raster-scaling
        self.opacity     = 1.0
        self.composition = ''

        # RasterColorizer info
        self.default_mode  = 'linear'
        self.default_color = 'transparent'
        self.epsilon       = 1.5e-07

        # RasterColorizer arrays
        self.values = []
        self.colors = []
        self.modes  = []
        
        # Store the procid (after a call to self.toLayer())
        self.procid = None
        
        # ratio and offsets of the bands (used in RGB composition to give correct values on identify)
        self.ratios  = []
        self.offsets = []

    

    # Query Sentinel2 BDAP STAC item if input is a string (i.e. 'S2A_MSIL2A_20230910T100601_N0509_R022_T32TQP_20230910T161500')
    @staticmethod
    def sentinel2item(stacitem):
        if isinstance(stacitem, str):
            url = 'http://stac-api.cidsn.jrc.it:20008/services/stac-api/collections/EO.Copernicus.S2.L2A/items/' + stacitem
            response = requests.get(url)
            stacitem = json.loads(response.text)
        return stacitem

    
    #####################################################################################################################################################
    # Initialization for displaying a single band from a file (any of the formats managed by GDAL). Also files stored in redis, by using "redis:"+key
    #####################################################################################################################################################
    @classmethod
    def single(cls,
               filepath,
               band=1,
               epsg=None,
               proj='',                      # To be used for projections that do not have an EPSG code (if not empty it is used instead of the passed epsg)
               nodata=999999.0,
               identify_dict=None,           # Dictionary to convert integer pixel values to strings (e.g. classes names)
               identify_integer=False,       # True if the identify operation should convert pixels values to integer
               identify_digits=6,            # Number of digits for identify of float values
               identify_label='Value'):      # Label for identify operation
    
        if epsg is None and len(proj) == 0:
            info = RasterLayer.info(filepath)
            if 'epsg' in info:
                epsg = info['epsg']
            if 'proj4' in info:
                proj = info['proj4']
                
        instance = cls(filepath=filepath, band=band, epsg=epsg, proj=proj, nodata=nodata,
                       identify_dict=identify_dict, identify_integer=identify_integer, identify_digits=identify_digits, identify_label=identify_label)
        return instance


    #####################################################################################################################################################
    # Display a single band Sentinel-2 product
    #####################################################################################################################################################
    @classmethod
    def sentinel2single(cls,
                        stacitem,
                        band='B04',
                        scalemin=None,
                        scalemax=None,
                        colorlist=['#000000','#ffffff'],
                        scaling='near',
                        opacity=1.0):
        
        stacitem = rasterlayer.sentinel2item(stacitem)
        
        if 'collection' in stacitem and 'EO.Copernicus.S2' in stacitem['collection'] and 'assets' in stacitem and 'properties' in stacitem:
            properties = stacitem['properties']
            if 'proj:epsg' in properties:
                epsg = int(properties['proj:epsg'])
                if band in stacitem['assets']:
                    b = stacitem['assets'][band]
                    filepath = b['href'].replace('file://','')
                    if 'nodata' in b:
                        nodata = b['nodata']
                    else:
                        nodata = 0.0
                    
                    instance = cls(filepath=filepath, band=1, epsg=epsg, nodata=nodata, identify_integer=True)
                    instance.symbolizer(scaling=scaling, opacity=opacity)
                    instance.colorizer()

                    instance.minvalue, instance.maxvalue = minmaxrange(b,scalemin,scalemax)
                    instance.colorlist(instance.minvalue, instance.maxvalue, colorlist)
                    return instance
                else:
                    raise CustomException("Band %s not present in STAC item"%str(band), data=stacitem)
            else:
                raise CustomException("proj:epsg not present in in STAC item properties", data=stacitem)
        else:
            raise InvalidSTACitemException(stacitem)
    
    

    #####################################################################################################################################################
    # Display an RGB 3 bands composition of a Sentinel-2 product
    #####################################################################################################################################################
    @classmethod
    def sentinel2rgb(cls,
                     stacitem,        # STAC item containing info on the Sentinel-2 product
                     bandR='B04',
                     bandG='B03',
                     bandB='B02',
                     scalemin=None,   # Single float or array of 3 floats
                     scalemax=None,   # Single float or array of 3 floats
                     scaling='near',
                     opacity=1.0):
        
        stacitem = rasterlayer.sentinel2item(stacitem)
        
        
        # Format a band inside the VRT (NOT USED AT THE MOMENT!!!)
        def formatBandClip(filepath, wall, hall, w, h, band_number=1, color_interp='Red', nodata=0.0, ratio=1.0, offset=0.0, resampling='nearest'):
            return '''
  <VRTRasterBand dataType="Float32" band="%d" subClass="VRTDerivedRasterBand">
    <ColorInterp>%s</ColorInterp>
    <NoDataValue>%.20G</NoDataValue>
    <ComplexSource resampling="%s">
      <SourceFilename relativeToVRT="0">%s</SourceFilename>
      <SourceBand>1</SourceBand>
      <NoDataValue>0</NoDataValue>
      <SourceProperties RasterXSize="%d" RasterYSize="%d" DataType="UInt16" />
      <SrcRect xOff="0" yOff="0" xSize="%d" ySize="%d" />
      <DstRect xOff="0" yOff="0" xSize="%d" ySize="%d" />
      <ScaleRatio>%.20G</ScaleRatio>
      <ScaleOffset>%.20G</ScaleOffset>
    </ComplexSource>
    <PixelFunctionLanguage>Python</PixelFunctionLanguage>
    <PixelFunctionType>clip</PixelFunctionType>
    <PixelFunctionCode>
<![CDATA[
import numpy as np
def clip(in_ar, out_ar, xoff, yoff, xsize, ysize, raster_xsize, raster_ysize, buf_radius, gt, **kwargs):
    out_ar[:] = np.clip(in_ar, 0, 255)
]]>
    </PixelFunctionCode>
  </VRTRasterBand>''' % (band_number, color_interp, nodata, resampling, filepath, w,h, w,h, wall,hall, ratio, offset)

        
        
        # Format a band inside the VRT
        def formatBand(filepath, wall, hall, w, h, band_number=1, color_interp='Red', nodata=0.0, ratio=1.0, offset=0.0, resampling='nearest'):
            return '''
  <VRTRasterBand dataType="Byte" band="%d">
    <ColorInterp>%s</ColorInterp>
    <NoDataValue>%.20G</NoDataValue>
    <ComplexSource resampling="%s">
      <SourceFilename relativeToVRT="0">%s</SourceFilename>
      <SourceBand>1</SourceBand>
      <SourceProperties RasterXSize="%d" RasterYSize="%d" DataType="UInt16" />
      <SrcRect xOff="0" yOff="0" xSize="%d" ySize="%d" />
      <DstRect xOff="0" yOff="0" xSize="%d" ySize="%d" />
      <ScaleRatio>%.20G</ScaleRatio>
      <ScaleOffset>%.20G</ScaleOffset>
    </ComplexSource>
  </VRTRasterBand>''' % (band_number, color_interp, nodata, resampling, filepath, w,h, w,h, wall,hall, ratio, offset)
        
        
        if 'collection' in stacitem and 'EO.Copernicus.S2' in stacitem['collection'] and 'assets' in stacitem and 'properties' in stacitem:
            properties = stacitem['properties']
            if 'proj:bbox' in properties and 'proj:epsg' in properties:
                bbox = properties['proj:bbox']
                epsg = int(properties['proj:epsg'])
                
                if bandR in stacitem['assets'] and bandG in stacitem['assets'] and bandB in stacitem['assets']:
                    
                    minvalue = []
                    maxvalue = []
                    
                    if   scaling == 'near':     resampling = 'nearest'
                    elif scaling == 'bilinear': resampling = 'bilinear'
                    else:                       resampling = 'bicubic'

                    # Read info from stacitem
                    bR = stacitem['assets'][bandR]
                    filepathR = bR['href'].replace('file://','')
                    if 'nodata' in bR: nodataR = bR['nodata']
                    else:              nodataR = 0.0
                    wR,hR = bR['proj:shape']
                    gsdR = bR['gsd']
                    
                    bG = stacitem['assets'][bandG]
                    filepathG = bG['href'].replace('file://','')
                    if 'nodata' in bG: nodataG = bG['nodata']
                    else:              nodataG = 0.0
                    wG,hG = bG['proj:shape']
                    gsdG = bG['gsd']
                    
                    
                    bB = stacitem['assets'][bandB]
                    filepathB = bB['href'].replace('file://','')
                    if 'nodata' in bB: nodataB = bB['nodata']
                    else:              nodataB = 0.0
                    wB,hB = bB['proj:shape']
                    gsdB = bB['gsd']
                    
                    wall = max(wR,wG,wB)
                    hall = max(hR,hG,hB)
                    gsd  = min(gsdR,gsdB,gsdB)
                    
                    
                    
                    # Band R
                    if 'statistics' in bR:
                        mean   = bR['statistics']['mean']
                        stddev = bR['statistics']['stddev']
                        smin = mean - 2.0*stddev
                        if smin > 1000.0: smin = 1000.0
                        smax = mean + 2.0*stddev
                    else:
                        smin = 1000.0
                        smax = 3000.0
                    if isinstance(scalemin, float) or isinstance(scalemin, int): smin = scalemin
                    elif isinstance(scalemin, list) or isinstance(scalemin, tuple) and len(scalemin) > 0: smin = scalemin[0]
                    if isinstance(scalemax, float) or isinstance(scalemax, int): smax = scalemax
                    elif isinstance(scalemax, list) or isinstance(scalemax, tuple) and len(scalemax) > 0: smax = scalemax[0]
                    ratioR,offsetR = scaleminmax2ratiooffset(smin, smax)
                    minvalue.append(smin)
                    maxvalue.append(smax)
                    #print('R', ratioR, offsetR)
                    strR = formatBand(filepathR, wall,hall, wR,hR, 1, 'Red', nodataR, ratioR, offsetR, resampling)
                    
                    
                    # Band G
                    if 'statistics' in bG:
                        mean   = bG['statistics']['mean']
                        stddev = bG['statistics']['stddev']
                        smin = mean - 2.0*stddev
                        if smin > 1000.0: smin = 1000.0
                        smax = mean + 2.0*stddev
                    else:
                        smin = 1000.0
                        smax = 3000.0
                    if isinstance(scalemin, float) or isinstance(scalemin, int): smin = scalemin
                    elif isinstance(scalemin, list) or isinstance(scalemin, tuple) and len(scalemin) > 1: smin = scalemin[1]
                    if isinstance(scalemax, float) or isinstance(scalemax, int): smax = scalemax
                    elif isinstance(scalemax, list) or isinstance(scalemax, tuple) and len(scalemax) > 1: smax = scalemax[1]
                    ratioG,offsetG = scaleminmax2ratiooffset(smin, smax)
                    minvalue.append(smin)
                    maxvalue.append(smax)
                    #print('G', ratioG, offsetG)
                    strG = formatBand(filepathG, wall,hall ,wG,hG, 2, 'Green', nodataG, ratioG, offsetG, resampling)


                    # Band B
                    if 'statistics' in bB:
                        mean   = bB['statistics']['mean']
                        stddev = bB['statistics']['stddev']
                        smin = mean - 2.0*stddev
                        if smin > 1000.0: smin = 1000.0
                        smax = mean + 2.0*stddev
                    else:
                        smin = 1000.0
                        smax = 3000.0
                    if isinstance(scalemin, float) or isinstance(scalemin, int): smin = scalemin
                    elif isinstance(scalemin, list) or isinstance(scalemin, tuple) and len(scalemin) > 2: smin = scalemin[2]
                    if isinstance(scalemax, float) or isinstance(scalemax, int): smax = scalemax
                    elif isinstance(scalemax, list) or isinstance(scalemax, tuple) and len(scalemax) > 2: smax = scalemax[2]
                    ratioB,offsetB = scaleminmax2ratiooffset(smin, smax)
                    minvalue.append(smin)
                    maxvalue.append(smax)
                    #print('B', ratioB, offsetB)
                    strB = formatBand(filepathB, wall,hall ,wB,hB, 3, 'Blue', nodataB, ratioB, offsetB, resampling)
                    

                    dataset = 'vrt:<VRTDataset rasterXSize="%d" rasterYSize="%d">\n  <GeoTransform>%.10G, %.10G, 0.0, %.10G, 0.0, -%.10G</GeoTransform>'%(wall,hall,bbox[0],gsd,bbox[3],gsd)
                    
                    
                    # Test with mask!!! 
                    mask = '''
<MaskBand>
  <VRTRasterBand dataType="UInt16">
    <NoDataValue>0</NoDataValue>
    <SimpleSource>
      <SourceProperties RasterXSize="%d" RasterYSize="%d" DataType="UInt16" />
      <NoDataValue>0</NoDataValue>
      <SourceFilename relativeToVRT="0">%s</SourceFilename>
      <SourceBand>mask,1</SourceBand>
      <SrcRect xOff="0" yOff="0" xSize="%d" ySize="%d" />
      <DstRect xOff="0" yOff="0" xSize="%d" ySize="%d" />
    </SimpleSource>
  </VRTRasterBand>
</MaskBand>
'''%(wR,hR, filepathR, wR,hR, wall, hall)
                    
                    mask = ''

                    instance = cls(filepath=dataset + mask + strR + strG + strB + '\n</VRTDataset>',
                                   band=0,
                                   epsg=epsg,
                                   nodata=min([nodataR,nodataB,nodataG]),
                                   identify_integer=True)

                    instance.ratios.append(ratioR)
                    instance.offsets.append(offsetR)
                    instance.ratios.append(ratioG)
                    instance.offsets.append(offsetG)
                    instance.ratios.append(ratioB)
                    instance.offsets.append(offsetB)
                    
                    instance.minvalue = minvalue
                    instance.maxvalue = maxvalue
                    
                    instance.symbolizer(scaling=scaling, opacity=opacity)
                    instance.colorizer()
                    instance.color(0.0, '#ffffff00', 'exact')
                    return instance
                else:
                    raise CustomException("Not all input bands %s, %s and %s are present in STAC item"%(str(bandR),str(bandG),str(bandB)), data=stacitem)
            else:
                raise CustomException("proj:box or proj:epsg not present in in STAC item properties", data=stacitem)
        else:
            raise InvalidSTACitemException(stacitem)

            

    #####################################################################################################################################################
    # Display an index calculated from 2 bands (b1 - b2)/(b1 + b2) of a Sentinel-2 product
    #####################################################################################################################################################
    @classmethod
    def sentinel2index(cls,
                       stacitem,        # STAC item containing info on the Sentinel-2 product
                       band1='B08',
                       band2='B04',
                       scalemin=0,
                       scalemax=0.75,
                       colorlist=['#784519', '#ffb24a', '#ffeda6', '#ade85e', '#87b540', '#039c00', '#016400', '#015000'],  # BDAP standard NDVI palette
                       scaling='near',
                       opacity=1.0):
        
        stacitem = rasterlayer.sentinel2item(stacitem)
        
        if 'collection' in stacitem and 'EO.Copernicus.S2' in stacitem['collection'] and 'assets' in stacitem and 'properties' in stacitem:
            properties = stacitem['properties']
            if 'proj:bbox' in properties and 'proj:epsg' in properties:
                bbox = properties['proj:bbox']
                epsg = int(properties['proj:epsg'])
                
                if band1 in stacitem['assets'] and band2 in stacitem['assets']:
                    
                    b1 = stacitem['assets'][band1]
                    b2 = stacitem['assets'][band2]
                    
                    w1,h1 = b1['proj:shape']
                    w2,h2 = b2['proj:shape']
                    wall = max(w1,w2)
                    hall = max(h1,h2)
                    
                    gsd1 = b1['gsd']
                    gsd2 = b2['gsd']
                    gsd = min(gsd1,gsd2)
                    
                    filepath1 = b1['href'].replace('file://','')
                    filepath2 = b2['href'].replace('file://','')
                    
                    filepath = '''vrt:<VRTDataset rasterXSize="%d" rasterYSize="%d">
  <GeoTransform>%.10G, %.10G, 0.0, %.10G, 0.0, -%.10G</GeoTransform>
  <VRTRasterBand dataType="Float32" band="1" subClass="VRTDerivedRasterBand">
    <SimpleSource>
      <SourceFilename relativeToVRT="0">%s</SourceFilename>
      <SourceBand>1</SourceBand>
      <SourceProperties RasterXSize="%d" RasterYSize="%d" DataType="UInt16" />
      <SrcRect xOff="0" yOff="0" xSize="%d" ySize="%d" />
      <DstRect xOff="0" yOff="0" xSize="%d" ySize="%d" />
    </SimpleSource>
    <SimpleSource>
      <SourceFilename relativeToVRT="0">%s</SourceFilename>
      <SourceBand>1</SourceBand>
      <SourceProperties RasterXSize="%d" RasterYSize="%d" DataType="UInt16" />
      <SrcRect xOff="0" yOff="0" xSize="%d" ySize="%d" />
      <DstRect xOff="0" yOff="0" xSize="%d" ySize="%d" />
    </SimpleSource>
    <PixelFunctionLanguage>Python</PixelFunctionLanguage>
    <PixelFunctionType>norm_diff</PixelFunctionType>
    <PixelFunctionCode>
<![CDATA[
import numpy as np
def norm_diff(in_ar, out_ar, xoff, yoff, xsize, ysize, raster_xsize, raster_ysize, buf_radius, gt, **kwargs):
    out_ar[:] = np.nan_to_num(np.divide( np.subtract(in_ar[0],in_ar[1]), np.sum(in_ar,axis=0)), nan=-99999.0)
]]>
    </PixelFunctionCode>
  </VRTRasterBand>
</VRTDataset>''' % (wall,hall, bbox[0], gsd, bbox[3], gsd, filepath1, w1,h1,w1,h1,wall,hall, filepath2, w2,h2,w2,h2,wall,hall)

                    instance = cls(filepath=filepath, band=1, epsg=epsg, identify_integer=False, identify_digits=4)
                    instance.symbolizer(scaling=scaling, opacity=opacity)
                    instance.colorizer()
                    if scalemin is None: scalemin = 0.0
                    if scalemax is None: scalemax = 0.75
                    d = scalemax - scalemin
                    instance.color(scalemin - 10*d, colorlist[0])
                    instance.colorlist(scalemin, scalemax, colorlist)
                    instance.color(scalemax + 10*d, colorlist[-1])
                    
                    instance.minvalue = scalemin
                    instance.maxvalue = scalemax
                    
                    return instance
                else:
                    raise CustomException("Not all input bands %s and %s are present in STAC item"%(str(band1),str(band2)), data=stacitem)
            else:
                raise CustomException("proj:box or proj:epsg not present in in STAC item properties", data=stacitem)
        else:
            raise InvalidSTACitemException(stacitem)

    
    
    
    #####################################################################################################################################################
    # Display an RGB 3 bands composition of a single generic raster file
    #####################################################################################################################################################
    @classmethod
    def rgb(cls,
            filepath,        # Full path of the raster file
            bandR=1,
            bandG=2,
            bandB=3,
            epsg=None,       # Forced epsg that has prevalence over the epsg read from the raster file
            nodata=None,     # Forced nodata that has prevalence over nodata read from the raster file
            scalemin=None,   # Single float or array of 3 floats
            scalemax=None,   # Single float or array of 3 floats
            scaling='near',
            opacity=1.0):
        
        # Format a band inside the VRT
        def formatBand(filepath, DataType, w, h, band_number=1, source_band_number=1, color_interp='Red', nodatastr='', ratio=1.0, offset=0.0):
            return '''  <VRTRasterBand dataType="Byte" band="%d">
    <ColorInterp>%s</ColorInterp>%s
    <ComplexSource>
      <SourceFilename relativeToVRT="0">%s</SourceFilename>
      <SourceBand>%d</SourceBand>%s
      <SourceProperties RasterXSize="%d" RasterYSize="%d" DataType="%s" />
      <SrcRect xOff="0" yOff="0" xSize="%d" ySize="%d" />
      <DstRect xOff="0" yOff="0" xSize="%d" ySize="%d" />
      <ScaleRatio>%.20G</ScaleRatio>
      <ScaleOffset>%.20G</ScaleOffset>
    </ComplexSource>
  </VRTRasterBand>''' % (band_number, color_interp, nodatastr, filepath, source_band_number, nodatastr, w,h, DataType, w,h, w,h, ratio, offset)

        
        # Query info on raster using the RasterAPI
        info = rasterAPI.rasterInfo(filepath, False)
            
        if 'geotransform' in info and 'bands' in info:
            geotransform = info['geotransform']
            if 'epsg' in info or not epsg is None:
                if epsg is None:
                    epsg = info['epsg']
                
                bands = info['bands']
                if str(bandR) in bands and str(bandG) in bands and str(bandB) in bands:
                    
                    # Band R
                    bR = bands[str(bandR)]
                    wR = bR['xsize']
                    hR = bR['ysize']
                    datatype = bR['type']
                    if nodata is None: nodataR = bR['nodata']
                    else:              nodataR = nodata
                    strnodata = ''
                    if isinstance(nodataR, float) or isinstance(nodataR, int):
                        strnodata = '\n    <NoDataValue>%.20G</NoDataValue>'%float(nodataR)
                    
                    smin = 0.0
                    smax = 255.0
                    if isinstance(scalemin, float) or isinstance(scalemin, int): smin = scalemin
                    elif isinstance(scalemin, list) or isinstance(scalemin, tuple) and len(scalemin) > 0: smin = scalemin[0]
                    if isinstance(scalemax, float) or isinstance(scalemax, int): smax = scalemax
                    elif isinstance(scalemax, list) or isinstance(scalemax, tuple) and len(scalemax) > 0: smax = scalemax[0]
                    ratioR,offsetR = scaleminmax2ratiooffset(smin, smax)
                    strR = formatBand(filepath,datatype,wR,hR, 1, bandR, 'Red', strnodata, ratioR,offsetR)
                    
                    
                    # Band R
                    bG = bands[str(bandG)]
                    wG = bG['xsize']
                    hG = bG['ysize']
                    datatype = bG['type']
                    if nodata is None: nodataG = bG['nodata']
                    else:              nodataG = nodata
                    strnodata = ''
                    if isinstance(nodataG, float) or isinstance(nodataG, int):
                        strnodata = '\n    <NoDataValue>%.20G</NoDataValue>'%float(nodataG)
                    
                    smin = 0.0
                    smax = 255.0
                    if isinstance(scalemin, float) or isinstance(scalemin, int): smin = scalemin
                    elif isinstance(scalemin, list) or isinstance(scalemin, tuple) and len(scalemin) > 1: smin = scalemin[1]
                    if isinstance(scalemax, float) or isinstance(scalemax, int): smax = scalemax
                    elif isinstance(scalemax, list) or isinstance(scalemax, tuple) and len(scalemax) > 1: smax = scalemax[1]
                    ratioG,offsetG = scaleminmax2ratiooffset(smin, smax)
                    strG = formatBand(filepath,datatype,wG,hG, 2, bandG, 'Green', strnodata, ratioG,offsetG)


                    # Band B
                    bB = bands[str(bandB)]
                    wB = bB['xsize']
                    hB = bB['ysize']
                    datatype = bB['type']
                    if nodata is None: nodataB = bB['nodata']
                    else:              nodataB = nodata
                    strnodata = ''
                    if isinstance(nodataB, float) or isinstance(nodataB, int):
                        strnodata = '\n    <NoDataValue>%.20G</NoDataValue>'%float(nodataB)
                    
                    smin = 0.0
                    smax = 255.0
                    if isinstance(scalemin, float) or isinstance(scalemin, int): smin = scalemin
                    elif isinstance(scalemin, list) or isinstance(scalemin, tuple) and len(scalemin) > 2: smin = scalemin[2]
                    if isinstance(scalemax, float) or isinstance(scalemax, int): smax = scalemax
                    elif isinstance(scalemax, list) or isinstance(scalemax, tuple) and len(scalemax) > 2: smax = scalemax[2]
                    ratioB,offsetB = scaleminmax2ratiooffset(smin, smax)
                    strB = formatBand(filepath,datatype,wB,hB, 3, bandB, 'Blue', strnodata, ratioB,offsetB)
                    

                    dataset = 'vrt:<VRTDataset rasterXSize="%d" rasterYSize="%d">\n  <GeoTransform>%s</GeoTransform>\n'%(wR,hR,geotransform)
                   
                    instance = cls(filepath=dataset + strR + strG + strB + '\n</VRTDataset>',
                                   band=0,
                                   epsg=epsg,
                                   identify_integer=True)

                    instance.ratios.append(ratioR)
                    instance.offsets.append(offsetR)
                    instance.ratios.append(ratioG)
                    instance.offsets.append(offsetG)
                    instance.ratios.append(ratioB)
                    instance.offsets.append(offsetB)
                    
                    instance.symbolizer(scaling=scaling, opacity=opacity)
                    instance.colorizer()
                    return instance
                else:
                    raise CustomException("Not all input bands %s, %s and %s are present in input file"%(str(bandR),str(bandG),str(bandB)))
            else:
                raise CustomException("epsg not found in filepath")
        else:
            raise rasterAPI.InvalidBDAPAnswerException(url=url)

            
            
    #####################################################################################################################################################
    # Static methods to get info on a raster file
    #####################################################################################################################################################

    # Returns info dictionary on a raster file
    @staticmethod
    def info(filepath):
        return rasterAPI.rasterInfo(filepath, request_stats=True, detailed_stats=False)
    
            
    #####################################################################################################################################################
    # Print
    #####################################################################################################################################################
            
    # Representation
    def __repr__(self):
        old_stdout = sys.stdout
        sys.stdout = mystdout = StringIO()
        self.print()
        sys.stdout = old_stdout
        return mystdout.getvalue()
        
        
    # Print info on instance    
    def print(self):
        print("BDAP raster layer instance:")
        print("   procid:         %s"%str(self.procid))
        print("   filepath:       %s"%self.filepath)
        print("   band:           %d"%self.band)
        if self.epsg is None:
            print("   epsg:           None")
        else:
            print("   epsg:           %d"%self.epsg)
        print("   proj:           %s"%self.proj)
        print("   scaling:        %s"%self.scaling)
        print("   opacity:        %-10.6lf"%self.opacity);
        print("   composition:    %s"%self.composition)
        print("   default_mode:   %s"%self.default_mode)
        print("   default_color:  %s"%self.default_color)
        print("   epsilon:        %-20.16lf"%self.epsilon)
        if len(self.values) == 0:
            print("   colorizer:      no")
        else:
            print("   colorizer:");
            for v,c,m in zip(self.values, self.colors, self.modes):
                print("       %-16.10lf   %-10s   %s"%(v,c,m))
        
        
    #####################################################################################################################################################
    # Symbology management
    #####################################################################################################################################################
        
    # Create a symbolizer: see https://github.com/mapnik/mapnik/wiki/RasterSymbolizer
    def symbolizer(self,
                   scaling="near",
                   opacity=1.0,
                   composition=""):

        self.scaling = scaling
        self.opacity = opacity
        self.composition = composition
        
        
    # Create a colorizer: see https://github.com/mapnik/mapnik/wiki/RasterColorizer
    def colorizer(self,
                  default_mode="linear",
                  default_color="transparent",
                  epsilon=1.5e-07):

        self.default_mode  = default_mode
        self.default_color = default_color
        self.epsilon       = epsilon

        self.values = []
        self.colors = []
        self.modes  = []
        

    # Add a colorizer step: see https://github.com/mapnik/mapnik/wiki/RasterColorizer#example-xml
    def color(self,
              value,            # Numerical value
              color="red",      # name of color or "#rrggbb"
              mode="linear"):   # "discrete", "linear" or "exact"
        
        self.values.append(value)
        self.colors.append(color)
        self.modes.append(mode)

        
    # Add a colorlist linearly scaled from a min to a max value
    def colorlist(self, scalemin, scalemax, colorlist):
        ci = colors.colorInterpolator(colorlist)
        num_classes = len(colorlist)
        values = np.linspace(scalemin, scalemax, num_classes)
        cols = ci.GetColors(num_classes)
        for v,c in zip(values,cols):
            self.color(v, c, "linear")


    # Add a dictionary having key: raster values, value: colors
    def colormap(self, values2colors, mode='linear'):
        sortedkv = list(sorted(values2colors.items()))
        for value, color in sortedkv:
            self.color(value, color, mode)

            
    #####################################################################################################################################################
    # Identify methods
    #####################################################################################################################################################
    
    # Identify: returns a scalar float/int/string or a list of scalars
    def identify(self, lon, lat, zoom):
        while lon < -180.0: lon += 360.0
        while lon >  180.0: lon -= 360.0
        url = 'https://jeodpp.jrc.ec.europa.eu/jiplib-view/?IDENTIFYEX=1&vl=%s&x=%f&y=%f&epsg=%d&zoom=%d' % (self.toLayer(), lon, lat, 4326, int(zoom))
        #print(url)
        response = requests.get(url)
        bio = BytesIO(response.content)
        s = bio.read()
        svalue = s.decode("utf-8").replace('Values = ','').replace('Value = ','')
        if len(svalue) > 0:
            if ',' in svalue:
                vvv = svalue.split(',')
                if len(vvv) <= len(self.ratios):
                    if self._identify_integer:
                        return [int(round(unscaled(float(x),r,o))) for x,r,o in zip(vvv,self.ratios,self.offsets)]
                    else:
                        return [unscaled(float(x),r,o) for x,r,o in zip(vvv,self.ratios,self.offsets)]
                else:
                    if self._identify_integer:
                        return [int(x) for x in vvv]
                    else:
                        return [str(round(float(x), self._identify_digits)) for x in vvv]
            else:
                if len(self.ratios) >= 1 and len(self.offsets) >= 1:
                    if self._identify_integer:
                        return unscaled(float(svalue),self.ratios[0],self.offsets[0])
                    else:
                        return int(round(unscaled(float(svalue),self.ratios[0],self.offsets[0])))
                else:
                    if self._identify_integer:
                        ivalue = int(svalue)
                        if not self._identify_dict is None and ivalue in self._identify_dict:
                            return self._identify_dict[ivalue]
                        return ivalue
                    else:
                        return str(round(float(svalue), self._identify_digits))
        

    # onclick called by a Map.Map instance
    def onclick(self, m, lon, lat, zoom):
        res = self.identify(lon, lat, zoom)
        if not res is None:
            descriptions = [self._identify_label]
            values       = [res]

            t = textlist.textlist(descriptions, values,
                                  titlefontsize=10,
                                  textfontsize=11,
                                  titlecolumn=4,
                                  textcolumn=8,
                                  titlecolor='#000000',
                                  textcolor='#000000',
                                  lineheightfactor=1.1)

            t.card.width = '180px'
            popup = ipyleaflet.Popup(location=[lat,lon], child=t.draw(), auto_pan=False, close_button=True, auto_close=True, close_on_escape_key=True)
            m.add_layer(popup)
        

    #####################################################################################################################################################
    # Properties
    #####################################################################################################################################################

    @property
    def identify_dict(self):
        return self._identify_dict
        
    @identify_dict.setter
    def identify_dict(self, d):
        self._identify_dict = d

        
    @property
    def identify_integer(self):
        return self._identify_integer
        
    @identify_integer.setter
    def identify_integer(self, flag):
        self._identify_integer = flag

        
    @property
    def identify_digits(self):
        return self._identify_digits
        
    @identify_digits.setter
    def identify_digits(self, n):
        self._identify_digits = int(n)

        
    @property
    def identify_label(self):
        return self._identify_label
        
    @identify_label.setter
    def identify_label(self, s):
        self._identify_label = s
        
        

    #####################################################################################################################################################
    # Create an ipyleaflet.TileLayer
    #####################################################################################################################################################

    # Returns an instance of ipyleaflet.TileLayer
    def tileLayer(self, max_zoom=22):
        url = self.tileUrl()
        if not url is None:
            return ipyleaflet.TileLayer(url=url, max_zoom=max_zoom, max_native_zoom=max_zoom)

        
    #####################################################################################################################################################
    # Internal functions
    #####################################################################################################################################################
    
    # Returns the url to display the layer
    def tileUrl(self):
        procid = self.toLayer()
        if not procid is None:
            tileBaseUrl = 'https://jeodpp.jrc.ec.europa.eu/jiplib-view'
            return tileBaseUrl + "?x={x}&y={y}&z={z}&procid=%s" % procid

    
    # Save the layer in Redis and returns the procid
    def toLayer(self):
        j = self.toJson()
        strjson = json.dumps(j)
        self.procid = rasterAPI.saveLayer(strjson)
        return self.procid

    
    # Return the JSON representation of the raster layer
    def toJson(self):
        j = {'AbsolutePath': '',
             'Collection': 1002,
             'CustomXML': '',
             'Description': '',
             'HeatmapMode': 0,
             'HeatmapQuery': '',
             'HeatmapRadius': 0,
             'HeatmapWeightField': '',
             'HeatmapWeightMax': 1000000,
             'HeatmapWeightMin': -1000000,
             'IdentifyAll': 0,
             'IdentifyDigits': -1,
             'IdentifyField': '',
             'IdentifyFilter': '',
             'IdentifySeparator': '#',
             'IdentifySortField': '',
             'Name': 'wkt',
             'POSTGIS_dbname': '',
             'POSTGIS_epsg': 4326,
             'POSTGIS_proj': '',
             'POSTGIS_extents': '',
             'POSTGIS_geomtype': 'Polygon',
             'POSTGIS_host': '',
             'POSTGIS_password': '',
             'POSTGIS_port': 0,
             'POSTGIS_query': '',
             'POSTGIS_user': '',
             'Raster_XML': self.xml(),
             'Raster_band': self.band,
             'Raster_colors': '#000000,#ffffff',
             'Raster_epsgcode': self.epsg,
             'Raster_proj': self.proj,
             'Raster_file': self.filepath,
             'Raster_interpolate': 'near',
             'Raster_nodata': self.nodata,
             'Raster_scalemax': 255,
             'Raster_scalemin': 0,
             'ScaleResolution': 1,
             'filelinklayer': '',
             'filelinkpath': '',
             'filelinkproj': '',
             'joins': None,
             'modify': None,
             'opacity': 255,
             'properties': None,
             'wkt': None}
        
        return j

    
    # Return the XML string containing the Mapnik map for raster display
    def xml(self):
        RASTER_XML = '''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE Map[]>
<Map srs="+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0.0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs +over"
     background-color="#ffffff00" maximum-extent="-20037508.34,-20037508.34,20037508.34,20037508.34"  buffer-size="50">

<Parameters>
  <Parameter name="bounds">-180,-85.05112877980659,180,85.05112877980659</Parameter>
  <Parameter name="center">0,0,2</Parameter>
  <Parameter name="format">png</Parameter>
  <Parameter name="minzoom">0</Parameter>
  <Parameter name="maxzoom">22</Parameter>
  <Parameter name="description">Raster image displayed by Mapnik</Parameter>
</Parameters>

<Layer name="raster" srs="%s">
  <StyleName>raster</StyleName>
  <Datasource>
     <Parameter name="type">gdal</Parameter>
     <Parameter name="file">DYNAMIC_FILENAME</Parameter>
%s
  </Datasource>
</Layer>

<Style name="raster">
  <Rule>
    <RasterSymbolizer scaling="%s" %s %s>
%s    </RasterSymbolizer>
  </Rule>
</Style>

</Map>'''

        RASTER_BAND =  '     <Parameter name="band">%d</Parameter>'

        RASTER_COLORIZER = '''      <RasterColorizer default-mode="%s" default-color="%s" epsilon="%.18G">
%s      </RasterColorizer>
'''        
    
        band = ''
        if self.band > 0:
            band = RASTER_BAND %self.band

        colorizer = ''
        if len(self.values) > 0:
            steps = ''
            for v,c,m in zip(self.values, self.colors, self.modes):
                temp = '        <stop color="%s" value="%.10f" mode="%s" />\n'%(c,v,m)
                steps += temp

            colorizer = RASTER_COLORIZER%(self.default_mode, self.default_color, self.epsilon, steps)

            
        stropacity = ''
        if self.opacity < 1.0 and self.opacity >= 0.0:
            stropacity = ' opacity="%.8G" '%self.opacity


        strmode = ''
        if len(self.composition) > 0:
            strmode = ' comp-op="%s" '%self.composition
            
        if len(self.proj) == 0 or self.proj is None:
            srs = 'epsg:%d'%self.epsg
        else:
            srs = self.proj

        return RASTER_XML % (srs, band, self.scaling, stropacity, strmode, colorizer)
    