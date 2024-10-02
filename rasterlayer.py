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
    
    For Sentinel-2 L2A products, these class methods can be used:
    
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
            ly = rasterlayer.single('.../SWF2018/VER1-0/Data/VRT/SWF_2018_005m_03035_V1_0.vrt', 
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
        """
        Display a single band of a Sentinel-2 L2A product. The input product can be selected by passing its Product ID string (i.e: 'S2A_MSIL2A_20230910T100601_N0509_R022_T32TQP_20230910T161500') or the dict returned by a call to the :py:meth:`~rasterlayer.sentinel2item` method.
        
        The assignment of a list of colors to the pixel values is done by linearly mapping the range of pixel values [scalemin, scalemax] to the color palette. If None is passed as parameters scalemin and scalemax, the statistics of the input band are used to calculate the scaling parameters as [avg - 2*stddev, avg + 2*stddev].
        
        Parameters
        ----------
        stacitem : str or dict, optional
            Product ID string of the Sentinel-2 L2A product or the dict returned by a call to the :py:meth:`~rasterlayer.sentinel2item` method containing the product metadata.
        band : str, optional
            Band name of the band to display (default is 'B04').
        scalemin : float, optional
            Minimum pixel value to define the range of pixel values assigned to the list or colors. The default value is None.
        scalemin : float, optional
            Maximum pixel value to define the range of pixel values assigned to the list or colors. The default value is None.
        colorlist : list of str, optional
            List of strings defining the colors. Common names of colors can be used (i.e 'red') or their exadecimal RGB representation '#rrggbb'. The default colorlist is ['#000000','#ffffff'] which defines a shades of gray color ramp.
        scaling : str, optional
            Scaling mode (one of 'near', 'fast', 'bilinear', 'bicubic', 'spline16', 'spline36', 'hanning', 'hamming', 'hermite', 'kaiser', 'quadric', 'catrom', 'gaussian', 'bessel', 'mitchell', 'sinc', 'lanczos', 'blackman'). Default is 'near'.
        opacity : float, optional
            Opacity value (from 0.0 to 1.0) to display raster with partial transparency (default is 1.0, fully opaque).
            
        Example
        -------
        Display of band B04 of a Sentinel-2 L2A product (using one of the `Plotly continuous color scales <https://plotly.com/python/builtin-colorscales/>`_)::
        
            # Import libraries
            from IPython.display import display
            from vois.geo import Map
            from geolayer import rasterlayer
            import plotly.express as px

            # Create a rasterlayer istance to display a single Sentinel-2 band
            ly = rasterlayer.sentinel2single('S2A_MSIL2A_20230910T100601_N0509_R022_T32TQP_20230910T161500',
                                             band='B04',
                                             scaling='near',
                                             scalemin=800,
                                             scalemax=2800,
                                             colorlist=px.colors.sequential.Viridis)

            # Create a Map
            m = Map.Map(center=[43.696, 12.1179], zoom=9)
            
            # Add the layer to the map
            m.addLayer(ly)
            
            # Set the identify operation
            m.onclick = ly.onclick
            
            # Display the map
            display(m)
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
        Display an RGB three bands composition of a Sentinel-2 L2A product. The input product can be selected by passing its Product ID string (i.e: 'S2A_MSIL2A_20230910T100601_N0509_R022_T32TQP_20230910T161500') or the dict returned by a call to the :py:meth:`~rasterlayer.sentinel2item` method.
        
        The assignment of colors to the pixel values is done by linearly mapping the range of pixel values [scalemin, scalemax] to the [0, 255] interval. If None is passed as parameters scalemin and scalemax, the statistics of the input bands are used to calculate the scaling parameters as [avg - 2*stddev, avg + 2*stddev] for each of the three input bands.
        
        Parameters
        ----------
        stacitem : str or dict, optional
            Product ID string of the Sentinel-2 L2A product or the dict returned by a call to the :py:meth:`~rasterlayer.sentinel2item` method containing the product metadata.
        bandR : str, optional
            Band name of the band to display in the Red channel (default is 'B04').
        bandG : str, optional
            Band name of the band to display in the Green channel (default is 'B03').
        bandB : str, optional
            Band name of the band to display in the Blue channel (default is 'B02').
        scalemin : float or list of 3 floats, optional
            Minimum pixel value to define the range of pixel values mapped to the [0, 255] visualization range. If a single float values is passes, the same scalemin value is used for all the three input bands. As an alternative a list of three floats can be passed to specify distinct values for each of the bands. The default value is None, allowing for automatic calculation of input range from the three bands statistics.
        scalemin : float or list of 3 floats, optional
            Maximum pixel value to define the range of pixel values mapped to the [0, 255] visualization range.  If a single float values is passes, the same scalemax value is used for all the three input bands. As an alternative a list of three floats can be passed to specify distinct values for each of the bands. The default value is None, allowing for automatic calculation of input range from the three bands statistics.
        scaling : str, optional
            Scaling mode (one of 'near', 'fast', 'bilinear', 'bicubic', 'spline16', 'spline36', 'hanning', 'hamming', 'hermite', 'kaiser', 'quadric', 'catrom', 'gaussian', 'bessel', 'mitchell', 'sinc', 'lanczos', 'blackman'). Default is 'near'.
        opacity : float, optional
            Opacity value (from 0.0 to 1.0) to display raster with partial transparency (default is 1.0, fully opaque).
            
        Example
        -------
        Display of a True Color RGB composition (B04/B03/B02) of a Sentinel-2 L2A product (using the bands statistics to calculate the optimal scaling ranges)::
        
            # Import libraries
            from IPython.display import display
            from vois.geo import Map
            from geolayer import rasterlayer

            # Create a rasterlayer istance to display a RGB composition of a Sentinel-2 L2A product
            ly = rasterlayer.sentinel2rgb('S2A_MSIL2A_20230910T100601_N0509_R022_T32TQP_20230910T161500')

            # Create a Map
            m = Map.Map(center=[43.696, 12.1179], zoom=9)
            
            # Add the layer to the map
            m.addLayer(ly)
            
            # Set the identify operation
            m.onclick = ly.onclick
            
            # Display the map
            display(m)
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
        Display an index calculated from 2 bands (b1 - b2)/(b1 + b2) of a Sentinel-2 L2A product. The input product can be selected by passing its Product ID string (i.e: 'S2A_MSIL2A_20230910T100601_N0509_R022_T32TQP_20230910T161500') or the dict returned by a call to the :py:meth:`~rasterlayer.sentinel2item` method. The index calculation returns pixel values in the range [-1, 1].
        
        The assignment of colors to the pixel values is done by linearly mapping the range of pixel values [scalemin, scalemax] to the color ramp.
        
        Parameters
        ----------
        stacitem : str or dict, optional
            Product ID string of the Sentinel-2 L2A product or the dict returned by a call to the :py:meth:`~rasterlayer.sentinel2item` method containing the product metadata.
        band1 : str, optional
            Band name of the first band to use for the index calculation (default is 'B08').
        band2 : str, optional
            Band name of the second band to use for the index calculation (default is 'B04').
        scalemin : float, optional
            Minimum pixel value to define the range of pixel values mapped to the colorlist colors. Default is 0.0.
        scalemin : float, optional
            Maximum pixel value to define the range of pixel values mapped to the colorlist colors. Default is 0.75.
        colorlist : list of str, optional
            List of strings defining the colors. Common names of colors can be used (i.e 'red') or their exadecimal RGB representation '#rrggbb'. The default colorlist is a brown-to-green color ramp.
        scaling : str, optional
            Scaling mode (one of 'near', 'fast', 'bilinear', 'bicubic', 'spline16', 'spline36', 'hanning', 'hamming', 'hermite', 'kaiser', 'quadric', 'catrom', 'gaussian', 'bessel', 'mitchell', 'sinc', 'lanczos', 'blackman'). Default is 'near'.
        opacity : float, optional
            Opacity value (from 0.0 to 1.0) to display raster with partial transparency (default is 1.0, fully opaque).
            
        Example
        -------
        Display of an NDVI index (B08 - B04)/(B08 + B04) of a Sentinel-2 L2A product::
        
            # Import libraries
            from IPython.display import display
            from vois.geo import Map
            from geolayer import rasterlayer

            # Create a rasterlayer istance to display the NDVI index on a Sentinel-2 product
            ly = rasterlayer.sentinel2index('S2A_MSIL2A_20230910T100601_N0509_R022_T32TQP_20230910T161500',
                                            band1='B08',
                                            band2='B04',
                                            scaling='near',
                                            scalemin=0.0,
                                            scalemax=0.6)

            # Create a Map
            m = Map.Map(center=[43.696, 12.1179], zoom=9)
            
            # Add the layer to the map
            m.addLayer(ly)
            
            # Set the identify operation
            m.onclick = ly.onclick
            
            # Display the map
            display(m)
        """
        pass
    
    
    # Query Sentinel2 BDAP STAC item if input is a string (i.e. 'S2A_MSIL2A_20230910T100601_N0509_R022_T32TQP_20230910T161500')
    @staticmethod
    def sentinel2item(S2_L2A_Product_ID):
        """
        Given in input a string containing the Product ID of a Sentinel-2 L2A producs (i.e: 'S2A_MSIL2A_20230910T100601_N0509_R022_T32TQP_20230910T161500'), this static method of the rasterlayer class returns the full stacitem of the product (a dict containing all the metadata information of the product).
        
        Parameters
        ----------
        S2_L2A_Product_ID : str
            Product ID of a Sentinel-2 L2A product.
        
        Returns
        --------
        stacitem : dict
            Dictionary containing all the metadata information on the Sentinel-2 product (bands, statistics, etc.).
        """
        pass
    
            
    #####################################################################################################################################################
    # Static methods to get info on a raster file
    #####################################################################################################################################################

    # Returns info dictionary on a raster file
    @staticmethod
    def info(filepath):
        """
        Returns a dict containing info on a raster file.
        
        Parameters
        ----------
        filepath : str
            Full path of the raster file.
        
        Example
        -------
        Request info on a VRT raster file::
        
            # Import libraries
            from IPython.display import display
            from geolayer import rasterlayer
    
            info = rasterlayer.info('/eos/jeodpp/data/base/Energy/EUROPE/ESA/Biomass_cci/VER3-0/Data/VRT/2018/2018_ESACCI_BIOMASS-L4-AGB.vrt')
            display(info)
            
        .. figure:: figures/rasterlayer_info.png
           :scale: 100 %
           :alt: Dictionary returned by the call to info method
            
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
        Prints a textual description of the class instance.
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
        Initialize the raster rendering by providing settings for single-band display. The geolayer library uses Mapnik to render a raster dataset. See the  see `Raster Symbolizer description <https://github.com/mapnik/mapnik/wiki/RasterSymbolizer>`_ for info.
        
        After a rasterlayer instance is created, this method must be called only if a non-default setting is needed. In other words, if the created rasterlayer instance is going to be displayed using near-neighbour interpolation and fully opaque, the call to simbolizer() method can be avoided.
        
        Parameters
        ----------
        scaling : str, optional
            Scaling mode (one of 'near', 'fast', 'bilinear', 'bicubic', 'spline16', 'spline36', 'hanning', 'hamming', 'hermite', 'kaiser', 'quadric', 'catrom', 'gaussian', 'bessel', 'mitchell', 'sinc', 'lanczos', 'blackman'). Default is 'near'.
        opacity : float, optional
            Opacity value (from 0.0 to 1.0) to display raster with partial transparency (default is 1.0, fully opaque).
        composition : str, optional
            Compositing/Merging effects with image below raster level. Possible values are: grain_merge, grain_merge2, multiply, multiply2, divide, divide2, screen, hard_light. Default is ''.
        """
        pass
        
        
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
        
        - :py:meth:`~rasterlayer.color`
        - :py:meth:`~rasterlayer.colorlist`
        - :py:meth:`~rasterlayer.colormap`
        
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
        
            ly = rasterlayer.single('...', band=1, epsg=3035, nodata=0.0)
            ly.color(value=1.0, color="#cefc20", mode="exact")
            
        To visualize a raster band by assigning a palette of colors to a range of pixel values::
            
            ly = rasterlayer.single('...', band=1, epsg=3035, nodata=0.0)
            ly.colorlist(0.0, 100.0, ['#ff0000', '#0000ff'])

        To visualize a raster band by using a mapping of pixel values to specific colors::
            
            ly = rasterlayer.single('...', band=1, epsg=3035, nodata=0.0)
            ly.colormap({1.0: 'red', 
                         2.0: '#ffff00',
                         3.0: '#00ffff',
                         4.0: '#0000ff',
                         5.0: '#aaffaa'})
        """
        pass

    
    # Add a colorizer stop: see https://github.com/mapnik/mapnik/wiki/RasterColorizer#example-xml
    def color(self,
              value,            # Numerical value
              color="red",      # name of color or "#rrggbb"
              mode="linear"):   # "discrete", "linear" or "exact"
        """
        Add a colorizer stop. Read the description of the method :py:meth:`~rasterlayer.colorizer` or open the `Raster Colorizer help page <https://github.com/mapnik/mapnik/wiki/RasterColorizer>`_ for more details.
        
        Parameters
        ----------
        value : float
            Numerical value of the raster pixel at which the stop begins to be applied.
        color : str, optional
            Color assigned to the stop. If not specified, the colorizers default_color will be used. A name of color or its exadecimal representation '#rrggbb' can be used. Default is 'red'.
        mode : str, optional
            Stop mode: defines how the assignment of colors is implemented. Possible modes are 'discrete', 'exact' or 'linear' (default).
        """
        pass

    
    # Add a colorlist linearly scaled from a min to a max value
    def colorlist(self, scalemin, scalemax, colorlist):
        """
        Add a series of colorizer stops, one for each item of a list of colors, so that the pixel values inside a range [scalemin, scalemax] are linearly assigned to the colors of the list. Read the description of the method :py:meth:`~rasterlayer.colorizer` for an example.

        Parameters
        ----------
        scalemin : float
            Minimum pixel value to define the range of pixel values assigned to the list or colors.
        scalemin : float
            Maximum pixel value to define the range of pixel values assigned to the list or colors.
        colorlist : list of str
            List of strings defining the colors. Common names of colors can be used (i.e 'red') or their exadecimal RGB representation '#rrggbb'.
        """
        pass

    
    # Add a dictionary having key: raster values, value: colors
    def colormap(self, values2colors, mode='linear'):
        """
        Add a series of colorizer stops from a dictionary that maps some pixel values to specific colors. Read the description of the method :py:meth:`~rasterlayer.colorizer` for an example.

        Parameters
        ----------
        values2colors : dict
            Dict with pixel values as keys and colors as values.
        mode : str, optional
            Stop mode: defines how the assignment of colors is implemented. Possible modes are 'discrete', 'exact' or 'linear' (default).
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
        """
        Get/Set the dictionary to be used in the identify operation (click on a pixel) to convert a numerical pixel value into a string description. It can be useful to display class names instead of numerical values when querying categorical raster bands (datasets where each integer value represents a class or category)
        
        Returns
        --------
        d : dict
            Dictionary that assigns a string to each pixel value.

        Example
        -------
        Programmatically change the identify dictionary::
            
            vlayer.identify_dict = {1: 'wheat', 2: 'maize'}
            print(vlayer.identify_dict)
        """
        pass
        
    @identify_dict.setter
    def identify_dict(self, d):
        pass

        
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
            
            vlayer.identify_integer = True
            print(vlayer.identify_integer)
        """
        pass
        
    @identify_integer.setter
    def identify_integer(self, flag):
        pass

        
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
            
            vlayer.identify_digits = 2
            print(vlayer.identify_digits)
        """
        pass
        
    @identify_digits.setter
    def identify_digits(self, n):
        pass

        
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
            
            vlayer.identify_label = 'Intensity value'
            print(vlayer.identify_label)
        """
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
            rlayer = rasterlayer.single(...)
            
            # Create an ipyleaflet Map
            m = ipyleaflet.Map()
            
            # Add the layer to the map
            m.add(rlayer.tileLayer())
            
            # Display the map
            display(m)
        """
        pass

        
    