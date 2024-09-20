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
    Raster datasets visualization
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

    

    # Query Sentinel2 BDAP STAC item if input is a string (i.e. 'S2A_MSIL2A_20230910T100601_N0509_R022_T32TQP_20230910T161500')
    @staticmethod
    def sentinel2item(stacitem):
        """
        Static method to retrieve a STAC item from BDAP
        """
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
            Band number to display form 1 to n (default is 1).
        epsg : int, optional
            EPSG code of the coordinate system to use (default is 4326, the geographical coordinates).
        proj : str, optional
            Proj4 string of the coordinate system to use (default is the empty string). If a non-empty string is passes, this parameter has prevalence over the epsg code.
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
        Print class description
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
        pass
        
        
    # Create a colorizer: see https://github.com/mapnik/mapnik/wiki/RasterColorizer
    def colorizer(self,
                  default_mode="linear",
                  default_color="transparent",
                  epsilon=1.5e-07):
        pass

    # Add a colorizer step: see https://github.com/mapnik/mapnik/wiki/RasterColorizer#example-xml
    def color(self,
              value,            # Numerical value
              color="red",      # name of color or "#rrggbb"
              mode="linear"):   # "discrete", "linear" or "exact"
        pass
        
    # Add a colorlist linearly scaled from a min to a max value
    def colorlist(self, scalemin, scalemax, colorlist):
        pass

    # Add a dictionary having key: raster values, value: colors
    def colormap(self, values2colors, mode='linear'):
        pass
            
    #####################################################################################################################################################
    # Identify methods
    #####################################################################################################################################################
    
    # Identify: returns a scalar float/int/string or a list of scalars
    def identify(self, lon, lat, zoom):
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
        pass

        
    