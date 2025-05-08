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
    """
    Raster datasets visualization. Class to display any type of raster dataset format managed by the GDAL library.

    An instance of this class can be created using one of these class methods:
    
    - :py:meth:`~RasterLayer.single`
    - :py:meth:`~RasterLayer.rgb`
    - :py:meth:`~RasterLayer.rgb_multiple`
    - :py:meth:`~RasterLayer.index`
    
    To define the visual appearance of rasters, these methods can be used:
    
    - :py:meth:`~RasterLayer.symbolizer`
    - :py:meth:`~RasterLayer.colorizer`
    - :py:meth:`~RasterLayer.color`
    - :py:meth:`~RasterLayer.colorlist`
    - :py:meth:`~RasterLayer.colormap`

    """
    
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
    # Initialization for displaying a single band from a file (any of the formats managed by GDAL)
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
        """
        Single layer raster display. 
        
        Parameters
        ----------
        filepath : str
            File path of the raster to display.
        band : int, optional
            Band number (from 1 to n) to display (default is 1).
        epsg : int, optional
            EPSG code of the coordinate system to use (default is None which causes the reading of the info from the input file).
        proj : str, optional
            Proj4 string of the coordinate system to use (default is the empty string). If a non-empty string is passed, the proj parameter has prevalence over the epsg code.
        nodata : float, optional
            Value to be considered as absence of data (default is None, which causes the reading of the info from the input file).
        identify_dict : dict, optional
            Dictionary to convert integer pixel values to strings (e.g. classes names). Default is None.
        identify_integer : bool, optional
            True if the identify operation should convert pixels values to integer (default is False).
        identify_digits : int, optional
            Number of digits for the identify of float values (default is 6).
        identify_label : str, optional
            Label for identify operation (default is 'Value')
            
        Example
        -------
        Display of a single band from a VRT file::
        
            # Import libraries
            from IPython.display import display
            from vois.geo import Map
            from geolayer.layer.raster_layer import RasterLayer

            # Create a single RasterLayer istance to display the first band of a VRT file
            ly = RasterLayer.single('/data/SWF_2018_005m_03035_V1_0.vrt', 
                                    band=1, epsg=3035, nodata=0.0)
                                    
            # Display all pixels having value 1 with a pale green color
            # (see colorizer() and color() for a complete description)
            ly.color(value=1.0, color="#cefc20", mode="exact")

            # Create a Map
            m = Map.Map(zoom=14, basemapindex=1)
            
            # Add the layer to the map
            m.addLayer(ly)
            
            # Set the identify operation
            m.onclick = ly.onclick
            
            # Display the map
            display(m)
            
        .. image:: figures/single.png
        """
    
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
        """
        RGB composition of three bands of a single raster file dataset. 
        
        Parameters
        ----------
        filepath : str
            File path of the raster to display.
        bandR : int, optional
            Band number (from 1 to n) to display in the Red channel (default is 1).
        bandG : int, optional
            Band number (from 1 to n) to display in the Green channel (default is 2).
        bandB : int, optional
            Band number (from 1 to n) to display in the Blue channel (default is 3).
        epsg : int, optional
            EPSG code of the coordinate system to use (default is None which causes the reading of the info from the input file).
        proj : str, optional
            Proj4 string of the coordinate system to use (default is the empty string). If a non-empty string is passed, the proj parameter has prevalence over the epsg code.
        nodata : float, optional
            Value to be considered as absence of data: forced nodata that has prevalence over nodata read from the raster file (default is None).
        scaling : str, optional
            Scaling mode (one of 'near', 'fast', 'bilinear', 'bicubic', 'spline16', 'spline36', 'hanning', 'hamming', 'hermite', 'kaiser', 'quadric', 'catrom', 'gaussian', 'bessel', 'mitchell', 'sinc', 'lanczos', 'blackman'). Default is 'near'.
        scalemin : float or list of 3 floats, optional
            Minimum scaling value to convert from raster values to the interval [0,255] (default is None)
        scalemax : float or list of 3 floats, optional
            Maximum scaling value to convert from raster values to the interval [0,255] (default is None)
        opacity : float, optional
            Opacity value (from 0.0 to 1.0) to display the RGB composition with partial transparency (default is 1.0, fully opaque)
            
        Example
        -------
        Display of a RGB composition from a VRT file::
        
            # Import libraries
            from IPython.display import display
            from vois.geo import Map
            from geolayer.layer.raster_layer import RasterLayer

            # Create a RGB composition istance to display bands 3,2,1 of a VRT file
            ly = RasterLayer.rgb('/data/Hansen_GFC-2019-v1.7_last.vrt',
                                 nodata=0.0,
                                 bandR=3,
                                 bandG=2,
                                 bandB=1,
                                 scalemin=[0.0, 0.0, 0.0],
                                 scalemax=[120.0, 100.0, 105.0],
                                 scaling='bilinear')

            # Create a Map
            m = Map.Map()
            
            # Add the layer to the map
            m.addLayer(ly)
            
            # Set the identify operation
            m.onclick = ly.onclick
            
            # Display the map
            display(m)
        
            
        .. image:: figures/rgb.png
        """
        
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
            raise rasterAPI.InvalidBDAPAnswerException(url=filepath)


            
            
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
        """
        RGB composition of three bands of multiple raster files. 
        
        Parameters
        ----------
        filepathR : str
            Full path of the raster file for red band.
        filepathG : str
            Full path of the raster file for green band.
        filepathB : str
            Full path of the raster file for blue band.
        bandR : int, optional
            Band number (from 1 to n) of the filepathR to display in the Red channel (default is 1).
        bandG : int, optional
            Band number (from 1 to n) of the filepathG to display in the Green channel (default is 2).
        bandB : int, optional
            Band number (from 1 to n) of the filepathB to display in the Blue channel (default is 3).
        epsg : int, optional
            EPSG code of the coordinate system to use (default is None which causes the reading of the info from the input file).
        proj : str, optional
            Proj4 string of the coordinate system to use (default is the empty string). If a non-empty string is passed, the proj parameter has prevalence over the epsg code.
        nodata : float, optional
            Value to be considered as absence of data: forced nodata that has prevalence over nodata read from the raster input files (default is None).
        scaling : str, optional
            Scaling mode (one of 'near', 'fast', 'bilinear', 'bicubic', 'spline16', 'spline36', 'hanning', 'hamming', 'hermite', 'kaiser', 'quadric', 'catrom', 'gaussian', 'bessel', 'mitchell', 'sinc', 'lanczos', 'blackman'). Default is 'near'.
        scalemin : float or list of 3 floats, optional
            Minimum scaling value to convert from raster values to the interval [0,255] (default is None)
        scalemax : float or list of 3 floats, optional
            Maximum scaling value to convert from raster values to the interval [0,255] (default is None)
        opacity : float, optional
            Opacity value (from 0.0 to 1.0) to display the RGB composition with partial transparency (default is 1.0, fully opaque)
            
        Example
        -------
        Display of a RGB composition from a VRT file::
        
            # Import libraries
            from IPython.display import display
            from vois.geo import Map
            from geolayer.layer.raster_layer import RasterLayer

            # Create a RGB composition istance to display bands 3,2,1 of a TIFF file
            ly = RasterLayer.rgb_multiple(filepathR='/data/Hansen_GFC-2019-v1.7_last_20N_060W.tif',
                                          filepathG='/data/Hansen_GFC-2019-v1.7_last_20N_060W.tif',
                                          filepathB='/data/Hansen_GFC-2019-v1.7_last_20N_060W.tif',
                                          nodata=0.0,
                                          bandR=3,
                                          bandG=2,
                                          bandB=1,
                                          scalemin=[1.0, 0.0, 0.0],
                                          scalemax=[120.0, 100.0, 105.0],
                                          scaling='near')

            # Create a Map
            m = Map.Map()
            
            # Add the layer to the map
            m.addLayer(ly)
            
            # Set the identify operation
            m.onclick = ly.onclick
            
            # Display the map
            display(m)
        
            
        .. image:: figures/rgb_multiple.png
        """
        
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
    # Display an index calculated from 2 bands (b1 - b2)/(b1 + b2)
    #####################################################################################################################################################
    @classmethod
    def index(cls,
              filepath1,       # Full path of the raster file 1
              filepath2,       # Full path of the raster file 2
              band1=1,
              band2=1,
              epsg=None,       # Forced epsg that has prevalence over the epsg read from the raster files
              proj='',         # To be used for projections that do not have an EPSG code (if not empty it is used instead of the passed epsg)
              scalemin=0,
              scalemax=0.75,
              colorlist=['#784519', '#ffb24a', '#ffeda6', '#ade85e', '#87b540', '#039c00', '#016400', '#015000'],  # Standard NDVI palette
              scaling='near',
              opacity=1.0):
        """
        On-th-fly visualization of an index (i.e. NDVI) calculated from two raster bands (b1 and b2) using the formula (b1 - b2)/(b1 + b2).
        
        Parameters
        ----------
        filepath1 : str
            Full path of the raster file for the first band.
        filepath2 : str
            Full path of the raster file for the second band.
        band1 : int, optional
            Band number (from 1 to n) of the filepath1 to display as the b1 band in the index calculation (default is 1).
        band2 : int, optional
            Band number (from 1 to n) of the filepath2 to display as the b2 band in the index calculation (default is 1).
        epsg : int, optional
            EPSG code of the coordinate system to use (default is 4326, the geographical coordinates).
        proj : str, optional
            Proj4 string of the coordinate system to use (default is the empty string). If a non-empty string is passed, the proj parameter has prevalence over the epsg code.
        scaling : str, optional
            Scaling mode (one of 'near', 'fast', 'bilinear', 'bicubic', 'spline16', 'spline36', 'hanning', 'hamming', 'hermite', 'kaiser', 'quadric', 'catrom', 'gaussian', 'bessel', 'mitchell', 'sinc', 'lanczos', 'blackman'). Default is 'near'.
        scalemin : float, optional
            Minimum scaling value to convert from index values to the interval [0,255] (default is 0.0)
        scalemax : float or list of 3 floats, optional
            Maximum scaling value to convert from index values to the interval [0,255] (default is 0.75)
        opacity : float, optional
            Opacity value (from 0.0 to 1.0) to display the index (default is 1.0, fully opaque)
            
        Example
        -------
        Display of NDVI index from a Sentinel-2 product::
        
            # Import libraries
            from IPython.display import display
            from vois.geo import Map
            from geolayer.layer.raster_layer import RasterLayer

            # Display NDVI index calculated from bands B08 and B04 of a Sentinel-2 product
            ly = RasterLayer.index(filepath1='/data/S2A_MSIL2A_.../R10m/T33TUJ_20230910T100601_B08_10m.jp2',
                                   filepath2='/data/S2A_MSIL2A_.../R10m/T33TUJ_20230910T100601_B04_10m.jp2',
                                   band1=1,
                                   band2=1,
                                   scaling='near')

            # Create a Map
            m = Map.Map()
            
            # Add the layer to the map
            m.addLayer(ly)
            
            # Set the identify operation
            m.onclick = ly.onclick
            
            # Display the map
            display(m)
        
            
        .. image:: figures/rgb.png
        """
        
        info1 = rasterAPI.rasterInfo(filepath1, False)
        info2 = rasterAPI.rasterInfo(filepath2, False)
        
        if 'geotransform' in info1 and 'bands' in info1:
            geotransform = info1['geotransform']
            if 'epsg' in info1 or 'proj4' in info1:
                if epsg is None and 'epsg' in info1:
                    epsg = info1['epsg']
                if len(proj) == 0 and 'proj4' in info1:
                    proj = info1['proj4']

            bands = info1['bands']
            if str(band1) in bands:
                b1 = bands[str(band1)]
                w = w1 = b1['x_size']
                h = h1 = b1['y_size']
                datatype1 = b1['type']
                    
                if 'bands' in info2:
                    bands = info2['bands']
                    if str(band2) in bands:
                        b2 = bands[str(band2)]
                        w2 = b2['x_size']
                        h2 = b2['y_size']
                        datatype2 = b2['type']
                            
                        filepath = '''vrt:<VRTDataset rasterXSize="%d" rasterYSize="%d">
  <GeoTransform>%s</GeoTransform>
  <VRTRasterBand dataType="Float32" band="1" subClass="VRTDerivedRasterBand">
    <SimpleSource>
      <SourceFilename relativeToVRT="0">%s</SourceFilename>
      <SourceBand>1</SourceBand>
      <SourceProperties RasterXSize="%d" RasterYSize="%d" DataType="%s" />
      <SrcRect xOff="0" yOff="0" xSize="%d" ySize="%d" />
      <DstRect xOff="0" yOff="0" xSize="%d" ySize="%d" />
    </SimpleSource>
    <SimpleSource>
      <SourceFilename relativeToVRT="0">%s</SourceFilename>
      <SourceBand>1</SourceBand>
      <SourceProperties RasterXSize="%d" RasterYSize="%d" DataType="%s" />
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
</VRTDataset>''' % (w1,h1, geotransform, filepath1, w1,h1,datatype1,w1,h1,w1,h1, filepath2, w2,h2,datatype1,w2,h2,w1,h1)
                        
                        instance = cls(filepath=filepath, band=1, epsg=epsg, proj=proj, identify_integer=False, identify_digits=4)
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
                        raise CustomException("Band %s not found in filepath2: %s"%(band2,filepath2))
            else:
                raise CustomException("Band %s not found in filepath1: %s"%(band1,filepath1))
        else:
            raise CustomException("Geotransform not present in filepath1: %s"%filepath1)
            
            
    #####################################################################################################################################################
    # Static methods to get info on a raster file
    #####################################################################################################################################################

    # Returns info dictionary on a raster file
    @staticmethod
    def info(filepath):
        """
        Static method to return a dict containing info on a raster file.
        
        Parameters
        ----------
        filepath : str
            Full path of the raster file.
        
        Example
        -------
        Request info on a VRT raster file::
        
            # Import libraries
            from IPython.display import display
            from geolayer.layer.raster_layer import RasterLayer
    
            info = RasterLayer.info('/data/2018_ESACCI_BIOMASS-L4-AGB.vrt')
            display(info)
            
        .. figure:: figures/rasterlayer_info.png
           :scale: 100 %
           :alt: Dictionary returned by the call to info method
            
        """
        
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
        """
        Prints a textual description of the class instance.
        """
        
        print("TILEGEO raster layer instance:")
        #print("   procid:         %s"%str(self.procid))
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
        """
        Initialize the raster rendering by providing settings for single-band display. The geolayer library uses Mapnik to render a raster dataset. See the  see `Raster Symbolizer description <https://github.com/mapnik/mapnik/wiki/RasterSymbolizer>`_ for info.
        
        After a RasterLayer instance is created, this method must be called only if a non-default setting is needed. In other words, if the created RasterLayer instance is going to be displayed using near-neighbour interpolation and fully opaque, the call to simbolizer() method can be avoided.
        
        Parameters
        ----------
        scaling : str, optional
            Scaling mode (one of 'near', 'fast', 'bilinear', 'bicubic', 'spline16', 'spline36', 'hanning', 'hamming', 'hermite', 'kaiser', 'quadric', 'catrom', 'gaussian', 'bessel', 'mitchell', 'sinc', 'lanczos', 'blackman'). Default is 'near'.
        opacity : float, optional
            Opacity value (from 0.0 to 1.0) to display raster with partial transparency (default is 1.0, fully opaque).
        """

        self.scaling = scaling
        self.opacity = opacity
        
        
    # Create a colorizer: see https://github.com/mapnik/mapnik/wiki/RasterColorizer
    def colorizer(self,
                  default_mode="linear",
                  default_color="transparent",
                  epsilon=1.5e-07):
        """
        Create a colorizer descriptor to define how the values of a single-band raster are transformed into colors. See the `Raster Colorizer help page <https://github.com/mapnik/mapnik/wiki/RasterColorizer>`_ for more details.
        
        The colorizer works in the following way:

        - It has an ordered list of *stops* that describe how to translate an input value to an output color.
        - A stop has a value, which marks the stop as being applied to input values from its value, up until the next stops value.
        - A stop has a mode, which says how the input value will be converted to a colour.
        - A stop has a color
        - The colorizer also has default color, which input values will be converted to if they don't match any stops.
        - The colorizer also has a default mode, which can be inherited by the stops.
        - The colorizer also has an epsilon value, which is used in the exact mode.
        
        **Modes**
        
        The available modes are *inherit*, *discrete*, *linear*, and *exact*.
        
        **inherit** is only valid for stops, and not the default colorizer mode. It means that the stop will inherit the mode of the containing colorizer.

        **discrete** causes all input values from the stops value, up until the next stops value (or forever if this is the last stop) to be translated to the stops color.

        **linear** causes all input values from the stops value, up until the next stops value to be translated to a color which is linearly interpolated between the two stops colors. If there is no next stop, then the discrete mode will be used.

        **exact** causes an input value which matches the stops value to be translated to the stops color. The colorizers epsilon value can be used to make the match a bit fuzzy (in the 'greater than' direction).

        The colorizer method sets the initial parameters of the Colorizer. To add one or more stops to the colorizer the following methods can be called:
        
        - :py:meth:`~RasterLayer.color`
        - :py:meth:`~RasterLayer.colorlist`
        - :py:meth:`~RasterLayer.colormap`
        
        After a rasterlayer instance is created, this method must be called only if a non-default setting is needed. In other words, if the created rasterlayer instance is going to be displayed using the "linear" mode and the "transparent" default color, the call to the colorizer() method can be avoided.
        
        Parameters
        ----------
        default_mode : str, optional
            Default colorizer mode that can be inherited by all subsequent stops in case the *inherit* mode is selected. Default is 'linear'.
        default_color : str, optional
            Starting color of the first step of the colorizer. Default is 'transparent'.
        epsilon : float, optional
            Error threshold used in the exact mode to decide if a pixel value matches a stop value. Default is 1.5e-07.

        Examples
        --------
        To visualize a raster mask band by assigning a color to the "valid" pixels::
        
            ly = RasterLayer.single('...', band=1, epsg=3035, nodata=0.0)
            ly.color(value=1.0, color="#cefc20", mode="exact")
            
        To visualize a raster band by assigning a palette of colors to a range of pixel values::
            
            ly = RasterLayer.single('...', band=1, epsg=3035, nodata=0.0)
            ly.colorlist(0.0, 100.0, ['#ff0000', '#0000ff'])

        To visualize a raster band by using a mapping of pixel values to specific colors::
            
            ly = RasterLayer.single('...', band=1, epsg=3035, nodata=0.0)
            ly.colormap({1.0: 'red', 
                         2.0: '#ffff00',
                         3.0: '#00ffff',
                         4.0: '#0000ff',
                         5.0: '#aaffaa'})
        """

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
        """
        Add a colorizer stop. Read the description of the method :py:meth:`~RasterLayer.colorizer` or open the `Raster Colorizer help page <https://github.com/mapnik/mapnik/wiki/RasterColorizer>`_ for more details.
        
        Parameters
        ----------
        value : float
            Numerical value of the raster pixel at which the stop begins to be applied.
        color : str, optional
            Color assigned to the stop. If not specified, the colorizers default_color will be used. A name of color or its exadecimal representation '#rrggbb' can be used. Default is 'red'.
        mode : str, optional
            Stop mode: defines how the assignment of colors is implemented. Possible modes are 'discrete', 'exact' or 'linear' (default).
        """
        
        self.values.append(value)
        self.colors.append(color)
        self.modes.append(mode)

        
    # Add a colorlist linearly scaled from a min to a max value
    def colorlist(self, scalemin, scalemax, colorlist):
        """
        Add a series of colorizer stops, one for each item of a list of colors, so that the pixel values inside a range [scalemin, scalemax] are linearly assigned to the colors of the list. Read the description of the method :py:meth:`~RasterLayer.colorizer` for an example.

        Parameters
        ----------
        scalemin : float
            Minimum pixel value to define the range of pixel values assigned to the list or colors.
        scalemin : float
            Maximum pixel value to define the range of pixel values assigned to the list or colors.
        colorlist : list of str
            List of strings defining the colors. Common names of colors can be used (i.e 'red') or their exadecimal RGB representation '#rrggbb'.
        """
        
        ci = colors.colorInterpolator(colorlist)
        num_classes = len(colorlist)
        values = np.linspace(scalemin, scalemax, num_classes)
        cols = ci.GetColors(num_classes)
        for v,c in zip(values,cols):
            self.color(v, c, "linear")


    # Add a dictionary having key: raster values, value: colors
    def colormap(self, values2colors, mode='linear'):
        """
        Add a series of colorizer stops from a dictionary that maps some pixel values to specific colors. Read the description of the method :py:meth:`~RasterLayer.colorizer` for an example.

        Parameters
        ----------
        values2colors : dict
            Dict with pixel values as keys and colors as values.
        mode : str, optional
            Stop mode: defines how the assignment of colors is implemented. Possible modes are 'discrete', 'exact' or 'linear' (default).
        """
        
        sortedkv = list(sorted(values2colors.items()))
        for value, color in sortedkv:
            self.color(value, color, mode)

            
    #####################################################################################################################################################
    # Identify methods
    #####################################################################################################################################################
    
    # Identify: returns a scalar float/int/string or a list of scalars
    def identify(self, lon, lat, zoom=0):
        """
        Given in input a geographic coordinate  and a zoom level, returns a scalar float/int/string or a list of scalars containing info on the pixel under the (lat,lon) position.
        
        Parameters
        ----------
        lon : float
            Longitude coordinate of the point for which to perform the identify operation.
        lat : float
            Latitude coordinate of the point for which to perform the identify operation.
        zoom : int
            Zoom level in the range [0,20] to use for the identify operation.
        
        Returns
        --------
        res : float/int/string or list of float/int/string
            A scalar float/int/string or a list of scalars
        """
        
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
        """
        Callback onclick called by a Map.Map instance when the user clicks on the map.
        
        Parameters
        ----------
        m : instance of vois Map.Map class
            Map widget instance on which the click event occurs.
        lon : float
            Longitude coordinate of the point for which to perform the identify operation.
        lat : float
            Latitude coordinate of the point for which to perform the identify operation.
        zoom : int
            Zoom level in the range [0,20] to use for the identify operation.

        Example
        -------
        Display of a single band from a VRT file with identify operation on click event::
        
            # Import libraries
            from IPython.display import display
            from vois.geo import Map
            from geolayer.layer.raster_layer import RasterLayer

            # Create a single RasterLayer istance to display the first band of a VRT file
            ly = RasterLayer.single('/data/SWF_2018_005m_03035_V1_0.vrt', 
                                    band=1, epsg=3035, nodata=0.0)
                                    
            # Display all pixels having value 1 with a pale green color
            # (see colorizer() and color() for a complete description)
            ly.color(value=1.0, color="#cefc20", mode="exact")

            # Create a Map
            m = Map.Map(zoom=14, basemapindex=1)
            
            # Add the layer to the map
            m.addLayer(ly)
            
            # Set the identify operation
            m.onclick = ly.onclick
            
            # Display the map
            display(m)
            
        The default implementation of the RasterLayer.onclick method calls the RasterLayer.identify method and displays a popup on the map showing the textual content returned by the identify method.
        """
        
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
        """
        Get/Set the dictionary to be used in the identify operation (click on a pixel) to convert a numerical pixel value into a string description. It can be useful to display class names instead of numerical values when querying categorical raster bands (datasets where each integer value represents a class or category)
        
        Returns
        --------
        d : dict
            Dictionary that assigns a string to each pixel value.

        Example
        -------
        Programmatically change the identify dictionary::
            
            ly.identify_dict = {1: 'wheat', 2: 'maize'}
            print(ly.identify_dict)
        """
        return self._identify_dict
        
    @identify_dict.setter
    def identify_dict(self, d):
        self._identify_dict = d

        
    @property
    def identify_integer(self):
        """
        Get/Set the flag that requests the identify operation (click on a pixel) to return an integer value.
        
        Returns
        --------
        flag : bool
            True if the identify operation must return an integer value.

        Example
        -------
        Programmatically change the identify integer flag::
            
            ly.identify_integer = True
            print(ly.identify_integer)
        """
        return self._identify_integer
        
    @identify_integer.setter
    def identify_integer(self, flag):
        self._identify_integer = flag

        
    @property
    def identify_digits(self):
        """
        Get/Set the flag number of digits to use for the display of floating point values in an identify operation (click on a pixel).
        
        Returns
        --------
        n : int
            Number of decimal digits to use for the display of floating point pixel values.

        Example
        -------
        Programmatically change the identify_digits value::
            
            ly.identify_digits = 2
            print(ly.identify_digits)
        """
        return self._identify_digits
        
    @identify_digits.setter
    def identify_digits(self, n):
        self._identify_digits = int(n)

        
    @property
    def identify_label(self):
        """
        Get/Set the string to use in the display of an identify operation (click on a pixel).
        
        Returns
        --------
        label : str
            Label to prepend to the pixel values displayed in an identify operation.

        Example
        -------
        Programmatically change the identify_label value::
            
            ly.identify_label = 'Intensity value'
            print(ly.identify_label)
        """
        return self._identify_label
        
    @identify_label.setter
    def identify_label(self, s):
        self._identify_label = s
        
        

    #####################################################################################################################################################
    # Create an ipyleaflet.TileLayer
    #####################################################################################################################################################

    # Returns an instance of ipyleaflet.TileLayer
    def tileLayer(self, max_zoom=22, file_format='png', cache=False):
        """
        Creates an ipyleaflet.TileLayer object from an instance of RasterLayer, to be added to a Map for display.
        
        Parameters
        ----------
        max_zoom : int, optional
            Maximum zoom level to define for the layer (default is 22)
        file_format : str, optional
            Format of the tiles generated by the tilego server to serve the raster dataset in WMTS (default is 'png')
        cache : bool, optional
            Flag that enables the server-side caching of the tiles (default is False)
        
        Returns
        --------
        tlayer : ipyleaflet.TileLayer
            Instance of ipyleaflet.TileLayer to be added to a Map

        Example
        -------
        Create an ipyleaflet.TileLayer instance::
        
            # Import libraries
            from IPython.display import display
            import ipyleaflet
            from geolayer.layer.raster_layer import RasterLayer

            # Create a RasterLayer instance
            rlayer = RasterLayer.single(...)
            
            # Create an ipyleaflet Map
            m = ipyleaflet.Map()
            
            # Add the layer to the map
            m.add(rlayer.tileLayer())
            
            # Display the map
            display(m)
        """
        
        url = self.tileUrl(file_format=file_format, cache=cache)
        if not url is None:
            return ipyleaflet.TileLayer(url=url, max_zoom=max_zoom, max_native_zoom=max_zoom)

        
    #####################################################################################################################################################
    # Storage of XML Map in Redis and tileUrl calculation
    #####################################################################################################################################################
    
    # Returns the url to display the layer
    def tileUrl(self, file_format='png', cache=False):
        """
        Returns the url string that can be used to display the layer.
        
        Parameters
        ----------
        file_format : str, optional
            Format of the tiles generated by the tilego server to serve the raster dataset in WMTS (default is 'png')
        cache : bool, optional
            Flag that enables the server-side caching of the tiles (default is False)
            
        Returns
        --------
        url : str
            URL to be used to display the RasterLayer in a WMTS client, for instance ipyleaflet.Map widget, by creating a ipyleaflet.TileLayer instance from the returned URL string.
        """
        procid = self.toLayer()
        if not procid is None:
            if cache:
                return '%s%s/{z}/{x}/{y}.%s'%(settings.TILE_CACHE_ENDPOINT, procid, file_format)
            else:
                return '%s%s/{z}/{x}/{y}.%s'%(settings.TILE_ENDPOINT, procid, file_format)

    
    # Save the layer in Redis and returns the procid
    def toLayer(self):
        """
        Saves the layer in Redis and returns the procid.
        """
        xml = self.xml()
        self.procid = redisAPI.redisStore(xml)
        return self.procid
    
    
    #####################################################################################################################################################
    # Generation of the XML Map
    #####################################################################################################################################################
    
    # Return the full XML in Mapnik syntax
    def xml(self, compositing='src-over'):
        """
        Returns the full XML in Mapnik syntax.
        """
        
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
