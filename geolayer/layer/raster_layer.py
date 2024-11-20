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
from io import StringIO
import sys
import json
import requests
import numpy as np
import hashlib

# vois import
from vois import colors
from vois.vuetify import textlist

# geolayer import
from geolayer import settings
from geolayer.api import rasterAPI, redisAPI, vrtAPI
from geolayer.utility import templates


#####################################################################################################################################################
# Python user-defined exceptions
#####################################################################################################################################################

# Customizable exception
class CustomException(Exception):

    def __init__(self, message, data=''):
        self.message = message
        if len(data) > 0:
            self.message += '\nData: ' + str(data)
        super().__init__(self.message)    

        
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



#####################################################################################################################################################
# Class RasterLayer to create server-side raster display
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

        self.md5 = None
        
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
        self.scaling = 'near'    # near, fast, bilinear, bicubic, spline16, spline36, hanning, hamming, hermite, kaiser, quadric, catrom, gaussian, 
                                 # bessel, mitchell, sinc, lanczos, blackman  see http://mapnik.org/mapnik-reference/#3.0.22/raster-scaling
        self.opacity = 1.0

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
        
        # Files to query on identify
        self.identify_filepaths = []
        self.identify_bands     = []
    

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
        
        instance.identify_filepaths = [filepath]
        instance.identify_bands     = [band]
        
        return instance

    
    #####################################################################################################################################################
    # Display an RGB 3 bands composition from a single raster file
    #####################################################################################################################################################
    @classmethod
    def rgb(cls,
            filepath,        # Full path of the raster file
            bandR=1,
            bandG=2,
            bandB=3,
            epsg=None,       # Forced epsg that has prevalence over the epsg read from the raster file
            proj='',         # To be used for projections that do not have an EPSG code (if not empty it is used instead of the passed epsg)
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
            if 'epsg' in info or 'proj4' in info:
                if epsg is None and 'epsg' in info:
                    epsg = info['epsg']
                if len(proj) == 0 and 'proj4' in info:
                    proj = info['proj4']
                
                bands = info['bands']
                if str(bandR) in bands and str(bandG) in bands and str(bandB) in bands:
                    
                    # Band R
                    bR = bands[str(bandR)]
                    wR = bR['x_size']
                    hR = bR['y_size']
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
                    wG = bG['x_size']
                    hG = bG['y_size']
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


                    # Band G
                    bB = bands[str(bandB)]
                    wB = bB['x_size']
                    hB = bB['y_size']
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
                   
                    instance = cls(filepath=dataset + strR + '\n' + strG + '\n' + strB + '\n</VRTDataset>\n',
                                   band=0,
                                   epsg=epsg,
                                   proj=proj,
                                   identify_integer=True)

                    instance.symbolizer(scaling=scaling, opacity=opacity)
                    instance.colorizer()
                    
                    instance.identify_filepaths = [filepath, filepath, filepath]
                    instance.identify_bands     = [bandR, bandG, bandB]

                    return instance
                else:
                    raise CustomException("Not all input bands %s, %s and %s are present in input file"%(str(bandR),str(bandG),str(bandB)))
            else:
                raise CustomException("epsg not found in filepath")
        else:
            raise rasterAPI.InvalidBDAPAnswerException(url=url)

            
            
    #####################################################################################################################################################
    # Display an RGB 3 bands composition from multiple files (having the same number of pixels and data type!)
    #####################################################################################################################################################
    @classmethod
    def rgb_multiple(cls,
                     filepathR,       # Full path of the raster file for band R
                     filepathG,       # Full path of the raster file for band G
                     filepathB,       # Full path of the raster file for band B
                     bandR=1,
                     bandG=1,
                     bandB=1,
                     epsg=None,       # Forced epsg that has prevalence over the epsg read from the raster files
                     proj='',         # To be used for projections that do not have an EPSG code (if not empty it is used instead of the passed epsg)
                     nodata=None,     # Forced nodata that has prevalence over nodata read from the raster files
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

        
        # Query a file and return a VRTRasterBand XML descriptor
        def queryFile(filepath, band, index=0, ColorInterp='Red', epsg=None, proj='', nodata=None, returnDimensions=False):
       
            info = rasterAPI.rasterInfo(filepath, False)
        
            if 'geotransform' in info and 'bands' in info:
                geotransform = info['geotransform']
                if 'epsg' in info or 'proj4' in info:
                    if epsg is None and 'epsg' in info:
                        epsg = info['epsg']
                    if len(proj) == 0 and 'proj4' in info:
                        proj = info['proj4']

                    bands = info['bands']
                    if str(band) in bands:

                        b = bands[str(band)]
                        w = b['x_size']
                        h = b['y_size']
                        datatype = b['type']
                        if nodata is None: nodata = b['nodata']
                        else:              nodata = nodata
                        strnodata = ''
                        if isinstance(nodata, float) or isinstance(nodata, int):
                            strnodata = '\n    <NoDataValue>%.20G</NoDataValue>'%float(nodata)

                        smin = 0.0
                        smax = 255.0
                        if isinstance(scalemin, float) or isinstance(scalemin, int): smin = scalemin
                        elif isinstance(scalemin, list) or isinstance(scalemin, tuple) and len(scalemin) > 0: smin = scalemin[index]
                        if isinstance(scalemax, float) or isinstance(scalemax, int): smax = scalemax
                        elif isinstance(scalemax, list) or isinstance(scalemax, tuple) and len(scalemax) > 0: smax = scalemax[index]
                        ratio,offset = scaleminmax2ratiooffset(smin, smax)
                        
                        vrtband = 1
                        if ColorInterp == 'Green':  vrtband = 2
                        elif ColorInterp == 'Blue': vrtband = 3
                            
                        xml = formatBand(filepath,datatype,w,h, vrtband, band, ColorInterp, strnodata, ratio,offset)
                        if returnDimensions:
                            return xml, w, h, geotransform, epsg, proj
                        else:
                            return xml
                    
            if returnDimensions:
                return '', 0, 0, '', 4326, ''
            else:
                return ''
                    
                   
        strR, w,  h,  geotransform, epsg, proj = queryFile(filepathR, bandR, index=0, ColorInterp='Red',   epsg=epsg, proj=proj, nodata=nodata, returnDimensions=True)
        strG                                   = queryFile(filepathG, bandG, index=1, ColorInterp='Green', epsg=epsg, proj=proj, nodata=nodata, returnDimensions=False)
        strB                                   = queryFile(filepathB, bandB, index=2, ColorInterp='Blue',  epsg=epsg, proj=proj, nodata=nodata, returnDimensions=False)

        if len(strR) > 0 and len(strG) > 0 and len(strB) > 0:
            dataset = 'vrt:<VRTDataset rasterXSize="%d" rasterYSize="%d">\n  <GeoTransform>%s</GeoTransform>\n'%(w,h,geotransform)

            instance = cls(filepath=dataset + strR + '\n' + strG + '\n' + strB + '\n</VRTDataset>\n',
                           band=0,
                           epsg=epsg,
                           proj=proj,
                           identify_integer=True)

            instance.symbolizer(scaling=scaling, opacity=opacity)
            instance.colorizer()
            
            instance.identify_filepaths = [filepathR, filepathG, filepathB]
            instance.identify_bands     = [bandR, bandG, bandB]
            
            return instance
        else:
            raise CustomException("Not all input bands %s, %s and %s are present in input file(s)"%(str(bandR),str(bandG),str(bandB)))

            
            
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
        print("TILEGEO raster layer instance:")
        print("   procid:         %s"%str(self.procid))
        print("   filepath:       %s"%self.filepath)
        print("   band:           %d"%self.band)
        if self.epsg is None: print("   epsg:           None")
        else:                 print("   epsg:           %d"%self.epsg)
        print("   proj:           %s"%self.proj)
        print("   scaling:        %s"%self.scaling)
        print("   opacity:        %-10.6lf"%self.opacity);
        print("   default_mode:   %s"%self.default_mode)
        print("   default_color:  %s"%self.default_color)
        print("   epsilon:        %-20.16lf"%self.epsilon)
        if len(self.values) == 0:
            print("   colorizer:      no")
        else:
            print("   colorizer:");
            for v,c,m in zip(self.values, self.colors, self.modes):
                print("       %-16.10lf   %-10s   %s"%(v,c,m))
    
    
    # Return MD5 of the layer
    def MD5(self):
        return hashlib.md5(self.__repr__().encode()).hexdigest()
        
        
    #####################################################################################################################################################
    # Symbology management
    #####################################################################################################################################################
        
    # Create a symbolizer: see https://github.com/mapnik/mapnik/wiki/RasterSymbolizer
    def symbolizer(self,
                   scaling="near",
                   opacity=1.0):

        self.scaling = scaling
        self.opacity = opacity
        
        
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
    def identify(self, lon, lat, zoom=0):
        while lon < -180.0: lon += 360.0
        while lon >  180.0: lon -= 360.0
        
        values = []
        for filepath, band in zip(self.identify_filepaths, self.identify_bands):
            res = rasterAPI.rasterIdentify(filepath, band=band, lon=lon, lat=lat)
            if 'value' in res:
                values.append(res['value'])
        
        # Convert numbers and None into string
        def value2str(v):
            if v is None:
                return 'nodata'
            else:
                if self._identify_integer:
                    return str(int(v))
                else:
                    return str(round(float(v), self._identify_digits))
                    
                
        return ','.join([value2str(x) for x in values])
        

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
    # Storage of XML Map in Redis and tileUrl calculation
    #####################################################################################################################################################
    
    # Returns the url to display the layer
    def tileUrl(self, file_format='png', cache=False):
        procid = self.toLayer()
        if not procid is None:
            if cache:
                return '%s%s/{z}/{x}/{y}.%s'%(settings.TILE_CACHE_ENDPOINT, procid, file_format)
            else:
                return '%s%s/{z}/{x}/{y}.%s'%(settings.TILE_ENDPOINT, procid, file_format)

    
    # Save the layer in Redis and returns the procid
    def toLayer(self):
        xml = self.xml()
        self.procid = redisAPI.redisStore(xml)
        return self.procid
    
    
    #####################################################################################################################################################
    # Generation of the XML Map
    #####################################################################################################################################################
    
    # Return the full XML in Mapnik syntax
    def xml(self, compositing='src-over'):
        
        self.md5 = self.MD5()
        
        prefix = templates.MAP_PREFIX
        
        styles = self.xml_styles(compositing=compositing)
        
        layer = self.xml_layer()
        
        end = templates.MAP_END
        
        return prefix + '\n' + styles + '\n' + layer + '\n' + end

    
    
    # Return the XML of the Styles
    def xml_styles(self, compositing='src-over'):

        if self.md5 is None:
            self.md5 = self.MD5()
        
        style_name = '%s_0'%self.md5
        
        colorizer = ''
        if len(self.values) > 0:
            steps = ''
            for v,c,m in zip(self.values, self.colors, self.modes):
                temp = '                    <stop color="%s" value="%.10f" mode="%s" />\n'%(c,v,m)
                steps += temp

            colorizer  = '                <RasterColorizer default-mode="%s" default-color="%s" epsilon="%.18G">\n%s'%(self.default_mode, self.default_color, self.epsilon, steps)
            colorizer += '                </RasterColorizer>\n'

        stropacity = ''
        if self.opacity < 1.0 and self.opacity >= 0.0:
            stropacity = ' opacity="%.8G" '%self.opacity

        style  = '    <Style name="%s" comp-op="%s">\n'%(style_name,compositing)
        style += '        <Rule>\n'
        style += '            <RasterSymbolizer scaling="%s" %s>\n'%(self.scaling, stropacity)
        style += colorizer
        style += '            </RasterSymbolizer>\n'
        style += '        </Rule>\n'
        style += '    </Style>'
            
        return style
    
    
    
    # Return the XML of the Layer
    def xml_layer(self):
        
        if self.md5 is None:
            self.md5 = self.MD5()
            
        style_name = '%s_0'%self.md5
        
        # Store VRT file server-side
        if self.filepath[:4] == "vrt:":
            vrt_string = self.filepath[4:]
            res = vrtAPI.vrtStore(vrt_string)
            if 'file_path' in res:
                filepath = res['file_path']
        else:
            filepath = self.filepath
        
        
        if len(self.proj) == 0 or self.proj is None:
            srs = 'epsg:%d'%self.epsg
        else:
            srs = self.proj
            
        band = ''
        if self.band > 0:
            band = '<Parameter name="band">%d</Parameter>'%self.band

        layer  = '\n    <Layer name="%s" srs="%s">'%(self.md5, srs)
        layer += '\n       <StyleName>%s</StyleName>'%style_name
        layer += '\n       <Datasource>'
        layer += '\n          <Parameter name="type">gdal</Parameter>'
        layer += '\n          <Parameter name="file">%s</Parameter>'%filepath
        layer += '\n          %s'%band
        layer += '\n       </Datasource>'
        layer += '\n    </Layer>'

        return layer
