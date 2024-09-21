"""Display of raster datasets (.tif, .vrt, .nc, and all other formats managed by the GDAL library)"""
# Author(s): Davide.De-Marchi@ec.europa.eu
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



#####################################################################################################################################################
# Class rasterlayer to create server-side VectorLayer instances for raster display without using inter client library
#####################################################################################################################################################
class rasterlayer:
    """
    Raster datasets visualization. Class to display any type of raster dataset format managed by the GDAL library.

    An instance of this class can be created using one of these class methods:
    
    - :py:meth:`~rasterlayer.single`
    - :py:meth:`~rasterlayer.rgb`
    
    For Sentinel-2 products, these class methods can be used:
    
    - :py:meth:`~rasterlayer.sentinel2single`
    - :py:meth:`~rasterlayer.sentinel2rgb`
    - :py:meth:`~rasterlayer.sentinel2index`
    
    To define the visual appearance of rasters, these methods can be used:
    
    - :py:meth:`~rasterlayer.symbolizer`
    - :py:meth:`~rasterlayer.colorizer`
    - :py:meth:`~rasterlayer.color`
    - :py:meth:`~rasterlayer.colorlist`
    - :py:meth:`~rasterlayer.colormap`

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
        pass

    

    #####################################################################################################################################################
    # Initialization for displaying a single band from a file (any of the formats managed by GDAL). Also files stored in redis, by using "redis:"+key
    #####################################################################################################################################################
    @classmethod
    def single(cls,
               filepath,
               band=1,
               epsg=4326,
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
            EPSG code of the coordinate system to use (default is 4326, the geographical coordinates).
        proj : str, optional
            Proj4 string of the coordinate system to use (default is the empty string). If a non-empty string is passed, the proj parameter has prevalence over the epsg code.
        nodata : float, optional
            Value to be cosidered as absence of data (default is 999999.0).
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
            from geolayer import rasterlayer

            # Create a single rasterlayer istance to display the first band of a VRT file
            ly = rasterlayer.single('.../Copernicus/Services/Land/Pan-European/SmallWoodyFeatures/SWF2018/VER1-0/Data/VRT/SWF_2018_005m_03035_V1_0.vrt', 
                                    band=1, epsg=3035, nodata=0.0)
                                    
            # Display all pixels having value 1 with a pale green color (see ... for a complete description)
            ly.color(value=1.0, color="#cefc20", mode="exact")

            # Create a Map
            m = Map.Map(zoom=14, basemapindex=1)
            
            # Add the layer to the map
            m.addLayer(ly)
            
            # Set the identify operation
            m.onclick = ly.onclick
            
            # Display the map
            display(m)
        """
        pass

    
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
        """
        RGB composition of three bands of a raster dataset. 
        
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
            EPSG code of the coordinate system to use (default is 4326, the geographical coordinates).
        nodata : float, optional
            Value to be cosidered as absence of data (default is 999999.0).
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
            from geolayer import rasterlayer

            # Create a RGB composition istance to display bands 3,2,1 of a VRT file
            ly = rasterlayer.rgb('.../GLOBAL/UMD/GFC/VER1-7/Data/VRT/last/Hansen_GFC-2019-v1.7_last.vrt',
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
        """
        
    
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
        """
        Display a single band Sentinel-2 product.
        """
        pass
    

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
        """
        Display an RGB 3 bands composition of a Sentinel-2 product.
        """
        pass
            

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
        """
        Display an index calculated from 2 bands (b1 - b2)/(b1 + b2) of a Sentinel-2 product.
        """
        pass
    
    
    # Query Sentinel2 BDAP STAC item if input is a string (i.e. 'S2A_MSIL2A_20230910T100601_N0509_R022_T32TQP_20230910T161500')
    @staticmethod
    def sentinel2item(stacitem):
        """
        Static method to retrieve a STAC item from BDAP.
        """
        pass
    
            
    #####################################################################################################################################################
    # Print
    #####################################################################################################################################################
            
    # Representation
    def __repr__(self):
        pass
        
        
    # Print info on instance    
    def print(self):
        """
        Print class description.
        """
        pass
        
    #####################################################################################################################################################
    # Symbology management
    #####################################################################################################################################################
        
    # Create a symbolizer: see https://github.com/mapnik/mapnik/wiki/RasterSymbolizer
    def symbolizer(self,
                   scaling="near",
                   opacity=1.0,
                   composition=""):
        """
        Create a symbolizer: see https://github.com/mapnik/mapnik/wiki/RasterSymbolizer
        """
        pass
        
        
    # Create a colorizer: see https://github.com/mapnik/mapnik/wiki/RasterColorizer
    def colorizer(self,
                  default_mode="linear",
                  default_color="transparent",
                  epsilon=1.5e-07):
        """
        Create a colorizer: see https://github.com/mapnik/mapnik/wiki/RasterColorizer
        """
        pass

    
    # Add a colorizer step: see https://github.com/mapnik/mapnik/wiki/RasterColorizer#example-xml
    def color(self,
              value,            # Numerical value
              color="red",      # name of color or "#rrggbb"
              mode="linear"):   # "discrete", "linear" or "exact"
        """
        Add a colorizer step: see https://github.com/mapnik/mapnik/wiki/RasterColorizer#example-xml
        """
        pass

    
    # Add a colorlist linearly scaled from a min to a max value
    def colorlist(self, scalemin, scalemax, colorlist):
        """
        Add a colorlist linearly scaled from a min to a max value
        """
        pass

    
    # Add a dictionary having key: raster values, value: colors
    def colormap(self, values2colors, mode='linear'):
        """
        Add a dictionary having key: raster values, value: colors
        """
        pass

    
    #####################################################################################################################################################
    # Identify methods
    #####################################################################################################################################################
    
    # Identify: returns a scalar float/int/string or a list of scalars
    def identify(self, lon, lat, zoom):
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
        pass

    
    # onclick called by a Map.Map instance
    def onclick(self, m, lon, lat, zoom):
        pass

    
    #####################################################################################################################################################
    # Properties
    #####################################################################################################################################################

    @property
    def identify_dict(self):
        pass
        
    @identify_dict.setter
    def identify_dict(self, d):
        pass

        
    @property
    def identify_integer(self):
        pass
        
    @identify_integer.setter
    def identify_integer(self, flag):
        pass

        
    @property
    def identify_digits(self):
        pass
        
    @identify_digits.setter
    def identify_digits(self, n):
        pass

        
    @property
    def identify_label(self):
        pass
        
    @identify_label.setter
    def identify_label(self, s):
        pass
        
        

    #####################################################################################################################################################
    # Create an ipyleaflet.TileLayer
    #####################################################################################################################################################

    # Returns an instance of ipyleaflet.TileLayer
    def tileLayer(self, max_zoom=22):
        """
        Creates an ipyleaflet.TileLayer object from an instance of rasterlayer, to be added to a Map for display.
        
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
            from geolayer import rasterlayer

            # Create a rasterlayer instance
            rlayer = rasterlayer.file(...)
            
            # Create an ipyleaflet Map
            m = ipyleaflet.Map()
            
            # Add the layer to the map
            m.add(rlayer.tileLayer())
            
            # Display the map
            display(m)
        """
        pass

        
    