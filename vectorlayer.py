"""Display of vector datasets (shapefiles, geopackage, POSTGIS queries and WKT strings) on a ipyleaflet Map"""
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
# Class vectorlayer to create server-side VectorLayer instances for vector display without using inter client library
# Manages vector datasets in files (shapefiles, geopackage, etc.), WKT strings and POSTGIS queries
#####################################################################################################################################################
class vectorlayer:
    """
    Vector datasets visualization. Class to display vector file datasets (shapefiles, geopackage, etc.), WKT strings (see: `Well Known Text format <https://en.wikipedia.org/wiki/Well-known_text_representation_of_geometry>`_) and POSTGIS geospatial tables and queries.
    
    An instance of this class can be created using one of these class methods:
    
    - :py:meth:`~vectorlayer.file`
    - :py:meth:`~vectorlayer.wkt`
    - :py:meth:`~vectorlayer.postgis`
    
    To apply symbology to a vectorlayer class, these methods can be used:
    
    - :py:meth:`~vectorlayer.symbologyClear`
    - :py:meth:`~vectorlayer.symbologyAdd`
    
    A *parametric* symbol can be defined using tags like FILL-COLOR, STROKE-WIDTH, etc. that can be substituted with real values using the static method :py:meth:`~vectorlayer.symbolChange`.
    
    See the chapter :ref:`symbol-format-help` for a guide on how symbols are defined and the chapter :ref:`symbol-editor-help` for help on the visual Symbol Editor.

    """
    
    # Initialization for vector files (shapefiles, geopackage, etc.)
    def __init__(self,
                 filepath='',
                 layer='',
                 epsg=4326,
                 proj='',              # To be used for projections that do not have an EPSG code (if not empty it is used instead of the passed epsg)
                 identify_fields=[]):  # List of names of field to display on identify operation
        pass
        
        
    #####################################################################################################################################################
    # Initialization for a vector file (shapefile, geopackage, etc.)
    #####################################################################################################################################################
    @classmethod
    def file(cls,
             filepath,      # Path to the file (shapefile or geopackage, etc...)
             layer=None,      # Name of the layer (for a shapefile leave it empty)
             epsg=None,     # If None is passed, the epsg is calculated
             proj=''):      # To be used for projections that do not have an EPSG code (if not empty it is used instead of the passed epsg)
        """
        Display of a file-based vector dataset on an ipyleaflet Map.
        
        Parameters
        ----------
        filepath : str
            File path of the vector dataset to display (shapefile, geopackage, etc.).
        layer : str, optional
            Name of the layer to display (for a shapefile it can be None). Default is None.
        epsg : int, optional
            EPSG code of the coordinate system to use (default is None meaning that the geolayer library will try to understand the EPSG code itself).
        proj : str, optional
            Proj4 string of the coordinate system to use (default is the empty string). If a non-empty string is passed, the proj parameter has prevalence over the epsg code.
            
        Example
        -------
        Display of a shapefile::
        
            # Import libraries
            from IPython.display import display
            from vois.geo import Map
            from geolayer import vectorlayer

            # Create a vectorlayer instance from a file dataset (shapefile)
            vlayer = vectorlayer.file('.../NUTS_RG_03M_2021_4326_0.shp', epsg=4326)

            # Define a parametric symbol ('FILL-COLOR' to be substituted with the actual color)
            symbol = [
                        [
                           ["PolygonSymbolizer", "fill", 'FILL-COLOR'],
                           ["PolygonSymbolizer", "fill-opacity", 0.8],
                           ["LineSymbolizer", "stroke", "#000000"],
                           ["LineSymbolizer", "stroke-width", 1.0]
                        ]
            ]

            # Remove default symbology
            vlayer.symbologyClear()
            
            # Assign a red symbol to all features
            vlayer.symbologyAdd(symbol=vectorlayer.symbolChange(symbol, fillColor='red'))
            
            # Assign a green symbol to a subset of the features
            vlayer.symbologyAdd(rule="[CNTR_CODE] = 'IT'",
                                symbol=vectorlayer.symbolChange(symbol, fillColor='#00aa00'))

            # Create a Map
            m = Map.Map()
            
            # Add the layer to the map
            m.addLayer(vlayer)
            
            # Set the identify operation
            m.onclick = vlayer.onclick
            
            # Display the map
            display(m)
        """
    
    
    #####################################################################################################################################################
    # Initialization from a list of wkt strings
    #####################################################################################################################################################
    @classmethod
    def wkt(cls,
            wktlist,          # List of strings containing WKT of geospatial features in EPSG4326
            properties=[]):   # List of dictionaries containing the attributes of each of the feature (optional)
        """
        Display of one or more WKT (Well-Known-Text) strings as geospatial vector features over an ipyleaflet Map.
        
        Parameters
        ----------
        wktlist : list of str
            List of strings in WKT format containing the geometry of features to display (see: `Well Known Text format <https://en.wikipedia.org/wiki/Well-known_text_representation_of_geometry>`_).
        properties : list of dict, optional
            List of dict containing attributes of the features (default is []).
            
        Example
        -------
        Display of a WKT string::
        
            # Import libraries
            from IPython.display import display
            from vois.geo import Map
            from geolayer import vectorlayer

            # Create a vectorlayer instance from a WKT string
            vlayer = vectorlayer.wkt(['POLYGON ((20 40, 0 45, 10 52, 30 52, 20 40))'], 
                                     [{"ndx": 22, "value": 12.8798, "units": "abcd"}])

            # Define a symbol
            symbol = [
                        [
                           ["PolygonSymbolizer", "fill", '#0088ff'],
                           ["PolygonSymbolizer", "fill-opacity", 0.8],
                           ["LineSymbolizer", "stroke", "#000000"],
                           ["LineSymbolizer", "stroke-width", 4.0]
                        ]
            ]

            # Remove default symbology
            vlayer.symbologyClear()
            
            # Assign a symbol to a subset of the features
            vlayer.symbologyAdd(rule="[units] = 'abcd'", symbol=symbol)
            
            # Create a Map
            m = Map.Map()
            
            # Add the layer to the map
            m.addLayer(vlayer)
            
            # Set the identify operation
            m.onclick = vlayer.onclick
            
            # Display the map
            display(m)
        """
    
    
    #####################################################################################################################################################
    # Initialization for a postGIS query
    #####################################################################################################################################################
    @classmethod
    def postgis(cls,
                host,
                port,
                dbname,
                user,
                password,
                query,
                epsg=4326,
                proj='',             # To be used for projections that do not have an EPSG code (if not empty it is used instead of the passed epsg)
                geomtype='Polygon',
                geometry_field='',
                geometry_table='',
                extents=''):
        """
        Display of a POSTGIS geospatial query over an ipyleaflet Map.
        
        Parameters
        ----------
        host : str
            Address for the POSTGIS server. You can use an IP address or the hostname of the machine on which database server is running.
        port : int
            Port on which you have configured your POSTGIS instance while installing or initializing. The default port is 5432.
        dbname: str
            The name of the database with which you want to connect. The default name of the database is the same as that of the user.
        user : str
            User name to be used for the connection to the POSTGIS database.
        password : str
            Password for the user name.
        query : str
            Query in SQL format to extract information from the DB. It should include a geoemtry field.
        epsg : int, optional
            EPSG code of the coordinate system to use (default is 4326, the geographical coordinates).
        proj : str, optional
            Proj4 string of the coordinate system to use (default is the empty string). If a non-empty string is passed, the proj parameter has prevalence over the epsg code.
        geomtype : str, optional
            Geometry type of the features returned by the query. In can be 'Polygon', 'LineString' or 'Point'. Default is 'Polygon'.
        geometry_field : str, optional
            Name of the geometry field, in case you have more than one in a single table. This field will be deduced from the query in most cases, but may need to be manually specified in some cases. Default is ''.
        geometry_table : str, optional
            Name of table geometry is retrieved from. Auto detected when not given, but this may fail for complex queries. Default is ''.
        extents : str, optional
            Maximum extent of the geometries in the format "xmin ymin, xmax ymax"; if omitted, the extents will be determined by querying the metadata for the table.
            
            **Important!**: always pass a valid extents string, since this will make the display much faster in most cases.


        Example
        -------
        Display of a POSTGIS query::
        
            # Import libraries
            from IPython.display import display
            from vois.geo import Map
            from geolayer import vectorlayer

            # Create a vectorlayer instance for a POSTGIS query
            vlayer = vectorlayer.postgis(
                        host="XXXXXX",
                        port=5432,
                        dbname="XXXXXX",
                        user="XXXXXX",
                        password="XXXXXX",
                        query="SELECT geom FROM mytable",
                        epsg=3035,
                        geomtype="Polygon",
                        extents="4200207.5 3496795.9,4649995.8 3848272.9")

            # Define a symbol
            symbol = [
                        [
                           ["PolygonSymbolizer", "fill", '#ff0000'],
                           ["PolygonSymbolizer", "fill-opacity", 0.3],
                           ["LineSymbolizer", "stroke", "#000000"],
                           ["LineSymbolizer", "stroke-width", 1.0]
                        ]
            ]

            # Remove default symbology
            vlayer.symbologyClear()
            
            # Assign the symbol to all the features of the query
            vlayer.symbologyAdd(symbol=symbol)
            
            # Create a Map
            m = Map.Map()
            
            # Add the layer to the map
            m.addLayer(vlayer)
            
            # Set the identify operation
            m.onclick = vlayer.onclick
            vlayer.identify_fields = ['FID', 'GEOMETRY']
            
            # Display the map
            display(m)
        """
        pass

    
    #####################################################################################################################################################
    # Static methods to get list of layers of a file-based vector dataset or info on a layer
    #####################################################################################################################################################

    # Returns the list of layers of a file-based vector dataset
    @staticmethod
    def layers(filepath):
        """
        Returns the list of layers of a file-based vector dataset (shapefile, geopackage, sqlite, etc.).
        
        Parameters
        ----------
        filepath : str
            Full path of the file-based dataset (shapefile, geopackage, sqlite, etc.).
        """
        pass

    
    # Returns info dictionary on a layer of a file-based vector dataset
    @staticmethod
    def layer(filepath, layer=None):
        """
        Returns a dictionary containing info on a layer of a file-based vector dataset (extent, feature type, feature count, epsg, etc.).
        
        Parameters
        ----------
        filepath : str
            Full path of the file-based dataset (shapefile, geopackage, sqlite, etc.)
        layer : str
            Name of the layer. It is possible to pass None in case of a shapefile dataset.
        """
        pass
    
    
    #####################################################################################################################################################
    # Info on fields and their values (only for file and wkt)
    #####################################################################################################################################################

    # Returns a dictionary containing info on the fields of a layer of a Dataset
    def fields(self):
        """
        Returns a dictionary containing info on the fields of a file-based vector dataset. Works only for a filebased or a wkt instance.
        """
        pass

        
    # Returns info on a field of a layer of a Dataset
    def field(self, field):
        """
        Returns a dictionary containing info on a field of a file-based vector dataset. Works only for a filebased or a wkt instance.
        
        Parameters
        ----------
        field : str
            Name of the field to query.
        """
        pass

        
    # Returns the list of all values of a field of a layer of a Dataset
    def values(self, field):
        """
        Returns the list of all values of a field of a layer. Works only for a filebased or a wkt instance.
        
        Parameters
        ----------
        field : str
            Name of the field to query.
        """
        pass

    
    # Returns a dictionary of all the distinct values of a field of a layer of a Dataset with their number of occurrencies
    def distinct(self, field):
        """
        Returns a dictionary of all the distinct values of a field of a layer of a dataset with their number of occurrencies. Works only for a filebased or a wkt instance.
        
        Parameters
        ----------
        field : str
            Name of the field to query.
        """
        pass

        
    # Returns a dictionary containing statistical information on a numeric field of a layer of a Dataset
    def stats(self, field):
        """
        Returns a dictionary containing statistical information on a numeric field of a layer of a dataset. Works only for a filebased or a wkt instance.
        
        Parameters
        ----------
        field : str
            Name of the field to query.
        """
        pass
        
        
    #####################################################################################################################################################
    # Symbology management
    #####################################################################################################################################################
    
    # Remove all default symbology and all symbols added
    def symbologyClear(self, maxstyle=0):
        """
        Remove all the default symbology for a vectorlayer instance and all the symbols eventually added.
        By default a vectorlayer instance has a default symbology (for instance a pale yellow for polygons) so that it can be displayed even if no symbology is added using the :py:meth:`~vectorlayer.symbologyAdd`.
        By calling symbologyClean method, all these default display settings are removed.
        
        Parameters
        ----------
        maxstyle : int, optional
            A symbol in geolayer can have a maximum of 10 layers (corresponding to the number of lists inside its definition. The first list will be mapped to style0, the second to style1, etc., up to style9).
            This parameter can be used to clear only the first style (style0) if 0 is passed (default), or up to all the styles if 10 is passed.
            If the symbols you use are only made of a single layer, call this function without specifying the maxstyle parameter, since the default value of 0 is sufficient to clean the symbology.
        """

            
    # Apply a symbol to a subset of the features filtered by a rule ('all' applies to all features, "[attrib] = 'value'" only to a subset of the features. See https://github.com/mapnik/mapnik/wiki/Filter for filter sintax)
    def symbologyAdd(self, rule='all', symbol=[]):
        """
        Add a new symbology rule.
        
        Parameters
        ----------
        rule : str, optional
            Filter to define the feature that will be rendered with the symbol.
            Passing 'all' applies the symbol to all the features, while a filter like "[attrib] = 'value'" makes the symbol applied only to a subset of the features.
            See `Mapnik Filter Syntax <https://github.com/mapnik/mapnik/wiki/Filter>`_ for help in writing the filter. Default is 'all'.
        symbol: list of lists, optional
            Symbol to be used for the rendering of the features. See the chapter :ref:`symbol-format-help` for a guide on how symbols are defined and the chapter :ref:`symbol-editor-help` for help on the visual Symbol Editor.
        """
        pass
                
        
    
    #####################################################################################################################################################
    # Legend creation. A Legend is a list of dictionaries, each one repredenting an item of the legend, containing description, rule and symbol
    #####################################################################################################################################################

    # Create a legend using a single symbol for all the features
    def legendSingle(self,
                     symbol=[],
                     description=''):
        """
        Create a legend that uses a single symbol for all the features.
        
        Parameters
        ----------
        symbol: list of lists, optional
            Symbol to be used for the rendering of the features. See the chapter :ref:`symbol-format-help` for a guide on how symbols are defined and the chapter :ref:`symbol-editor-help` for help on the visual Symbol Editor.
        description : str, optional
            Description of the unique item of the legend (default is '').
        """
        pass

    
    # Create a legend containing one item for each distinct value of a field
    def legendCategories(self,
                         fieldname,
                         colorlist,
                         symbol=[],
                         interpolate=True,
                         distinctValues=None):
        """
        Create a legend containing one item for each distinct value of a field. In case of file-based datasets (shapefiles, geopackage, aqlite, etc.) or wkt datasets, given a fieldname, the distinct values of this field are retrieved by the method legendCategories itself. On the contrary, for a postgis vectorlayer instance, the distinctValues parameter must be passed containing the list of all the unique values of the field (it is responsibility of the user to retrieve this list using a call to the underlying DB).
        
        Parameters
        ----------
        fieldname : str
            Name of the field whose distinct values must be used.
        colorlist : list of str
            List of colors to be used for the creation of the legend. 
        symbol: list of lists, optional
            Symbol to be used for the rendering of the features. See the chapter :ref:`symbol-format-help` for a guide on how symbols are defined and the chapter :ref:`symbol-editor-help` for help on the visual Symbol Editor.
        interpolate : bool, optional
            If True, the colors assigned to the items of the legend are calculated by using linear interpolation on the list of colors (thus potentially generating also intermediate colors). If False, only the colors in the list are used. In this case, if the number of distinct values is greated than the number of colors in the list, some legend items will have repeated colors.
        distinctValues : list, optional
            Custom list of distinct values to use for the creation of the legend. Default is None, meaning that, for filebased and wkt vectorlayer instances, the list of distinct values is autonomously calculated. This parameter must be mandatory passed when the vectorlayer instance is a postgis dataset.
        """
        pass
            
    
    # Create a legend on graduated values of a numerical field
    def legendGraduated(self,
                        fieldname,
                        colorlist,
                        symbol=[],
                        allValues=None,                 # All the values of the input fieldname (in case of postgis instance)
                        classifier_name='Quantiles',
                        classifier_param1=5,
                        classifier_param2=None,
                        interpolate=True,
                        markersize_min=1.0,             # Multiplier of markers/lines sizes to generate dimensionally graduated symbols
                        markersize_max=1.0,
                        digits=2
                       ):
        """
        Create a legend on the graduated values of a numerical field. In case of file-based datasets (shapefiles, geopackage, aqlite, etc.) or wkt datasets, given a fieldname, the values of this field are retrieved by the method legendGraduated itself. On the contrary, for a postgis vectorlayer instance, the allValues parameter must be passed containing the list of all the values of the field (it is responsibility of the user to retrieve this list using a call to the underlying DB).

        See `mapclassify help <https://github.com/pysal/mapclassify>`_ for additional guidance.

        Each of the different classification methods takes one or more input parameters:

        'EqualInterval': classifier_param1 = the number of classes required

        'BoxPlot': None

        'NaturalBreaks': classifier_param1 = the number of classes required

        'FisherJenksSampled':  classifier_param1 = the number of classes required, classifier_param1 = the percentage of values that should form the sample (standard value is 0.1)

        'StdMean': classifier_param1 = a list containing the multiples of the standard deviation to add/subtract from the sample mean to define the bins (example [-2, -1, 1, 2]

        'JenksCaspallForced':  classifier_param1 = the number of classes required

        'HeadTailBreaks': None

        'Quantiles':  classifier_param1 = the number of classes required


        Parameters
        ----------
        fieldname : str
            Name of the field whose values must be used.
        colorlist : list of str
            List of colors to be used for the creation of the legend. 
        symbol: list of lists, optional
            Symbol to be used for the rendering of the features. See the chapter :ref:`symbol-format-help` for a guide on how symbols are defined and the chapter :ref:`symbol-editor-help` for help on the visual Symbol Editor.
        allValues : list, optional
            Custom list of values to use for the creation of the legend. Default is None, meaning that, for filebased and wkt vectorlayer instances, the list of all the field values is autonomously retrieved. This parameter must be mandatory passed when the vectorlayer instance is a postgis dataset.
        classifier_name : str, optional
            Name of the classifier to use for generating the classes. Possible values are: 'EqualInterval', 'BoxPlot', 'NaturalBreaks', 'FisherJenksSampled', 'StdMean', 'JenksCaspallForced', 'HeadTailBreaks' and 'Quantiles'. Default value is 'Quantiles'. 
        classifier_param1 : float, optional
            First optional parameter of the classification method selected.
        classifier_param2 : float, optional
            Second optional parameter of the classification method selected.
        interpolate : bool, optional
            If True, the colors assigned to the items of the legend are calculated by using linear interpolation on the list of colors (thus potentially generating also intermediate colors). If False, only the colors in the list are used. In this case, if the number of distinct values is greated than the number of colors in the list, some legend items will have repeated colors.
        markersize_min : float, optional
            Minimal marker size to generate dimensionally graduated symbols (default is 1.0).
        markersize_max : float, optional
            Maximal marker size to generate dimensionally graduated symbols (default is 1.0).
        digits : int, optional
            Number of decimal digits to use to display floating point values in the description of the legend items (default is 2). Passing a negative number instructs the method to use a G format for all the floating point values.
        
        """
        pass

    
    #####################################################################################################################################################
    # Legend representation
    #####################################################################################################################################################
    
    # Returns an Image containing all the items of a legend
    def legend2Image(self, legend, size=1, clipdimension=999, width=300, fontweight=400, fontsize=9, textcolor="black"):
        """
        Given as input a legend returned by a call to one of the methods: :py:meth:`~vectorlayer.legendSingle`, :py:meth:`~vectorlayer.legendCategories` or :py:meth:`~vectorlayer.legendGraduated`, this function returns an PILLOW image containing all the items of the legend.
        
        Parameters
        ----------
        legend : list of dicts
            Legend returned by one of the three methods to build a legend.
        size : int, optional
            Size of the image to create, in the range [1,3] for "small" (30x30 pixels), "medium" (80x80 pixels) and "big" (256x256 pixels) dimensions. Default is 1.
        clipdimension : int, optional
            Optional dimension of the square in pixel to be used to clip the output image to a smaller dimension (default is 999).
        width : int, optional
            Width in pixels of the image (default is 300).
        fontweight : int, optional
            Weight of the font used to display the descriptions of the legend items (default is 400, meaning plain text, use 300 for a thinner font, 600 or above for a bold font).
        fontsize : int, optional
            Height in pixels of the font used to display the descriptions of the legend items (default is 9).
        textcolor : str, optional
            Color of the text (default is 'black').
        """
        pass
    
    
    # Returns a v.List containing the legend items as list items
    def legend2List(self, legend, title='', size=1, disabled=False, onclick=None):
        """
        Given as input a legend returned by a call to one of the methods: :py:meth:`~vectorlayer.legendSingle`, :py:meth:`~vectorlayer.legendCategories` or :py:meth:`~vectorlayer.legendGraduated`, this function returns a clickable ipyvuetify List widget containing all the items of  the legend.
        
        Parameters
        ----------
        legend : list of dicts
            Legend returned by one of the three methods to build a legend.
        title : str, optional
            Title of the legend (default is '').
        size : int, optional
            Size of the image to create, in the range [1,3] for "small" (30x30 pixels), "medium" (80x80 pixels) and "big" (256x256 pixels) dimensions. Default is 1.
        disabled : bool, optional
            If True, the 
        onclick : callable, optional
            Python function to call when the user clicks on one of the items of the List widget (default is None). The function has to have three parameters: widget, event, data. By accessing widgets.value the function can understand on which item the click event occurred (from 0 to nitems - 1.
        """
        pass
        
        
    #####################################################################################################################################################
    # Static method to instantiate a parametric symbol
    #####################################################################################################################################################
    
    # Change color and other properties of a symbol and returns the modified symbol
    @staticmethod
    def symbolChange(symbol, color='#ff0000', fillColor='#ff0000', fillOpacity=1.0, strokeColor='#ffff00', strokeWidth=0.5, scalemin=None, scalemax=None, size_multiplier=1.0):
        """
        Change color and other properties of a *parametric* (i.e. generic) symbol and returns the modified symbol.
        
        These tags can be used inside a symbol definition for creating a *parametric* symbol that can then be instantiated using these substitutions: 
        
        - COLOR (parameter color)
        - FILL-COLOR (parameter fillColor)
        - FILL-OPACITY (parameter fillOpacity)
        - STROKE-COLOR (parameter strokeColor)
        - STROKE-WIDTH (parameter strokeWidth)
        - SCALE-MIN (parameter scalemin)
        - SCALE-MAX (parameter scalemax)

        
        Parameters
        ----------
        symbol : list of lists, optional
            Symbol to be used for the rendering of the features. See the chapter :ref:`symbol-format-help` for a guide on how symbols are defined and the chapter :ref:`symbol-editor-help` for help on the visual Symbol Editor.
        color : str, optional
            Color to be substituted to the tag COLOR (default is '#ff0000').
        fillColor : str, optional
            Color to be substituted to the tag FILL-COLOR (default is '#ff0000').
        fillOpacity : float, optional
            Opacity value in [0,1] range to be substituted to the tag FILL-OPACITY (default is 1.0).
        strokeColor : str, optional
            Color to be substituted to the tag STROKE-COLOR (default is '#ffff00').
        strokeWidth : float, optional
            Width of the stroke in pixels to be substituted to the tag STROKE-WIDTH (default is 0.5).
        scalemin : float, optional
            Minimum scale denominator to be substituted to the tag SCALE-MIN to limit the zoom levels for which the symbol is visible (default is None).
        scalemax : float, optional
            Maximum scale denominator to be substituted to the tag SCALE-MAX to limit the zoom levels for which the symbol is visible (default is None).
        size_multiplier : float, optional
            Multiplier factor to be used for increasing/decreasing the size of markers of the width of strokes (default is 1.0).

        Returns
        --------
        modified_symbol : list of lists
            The input symbol modified by substituting the tags with the input parameter values.
            
            
        Example
        -------
        Create and instantiate a *parametric* symbol::
        
            # Import libraries
            from geolayer import vectorlayer

            # Define a parametric symbol (FILL-COLOR to be substituted with the actual color)
            symbol = [
                        [
                           ["PolygonSymbolizer", "fill", 'FILL-COLOR'],
                           ["PolygonSymbolizer", "fill-opacity", 0.8],
                           ["LineSymbolizer", "stroke", "#000000"],
                           ["LineSymbolizer", "stroke-width", 1.0]
                        ]
            ]

            # Instantiate the parametric symbol by substituting the FILL-COLOR tag with 'red'
            symbol_modified = vectorlayer.symbolChange(symbol, fillColor='red')
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
    # Identify methods
    #####################################################################################################################################################
    
    # Identify: returns a string
    def identify(self, lon, lat, zoom):
        """
        Given in input a geographic coordinate  and a zoom level, returns a string containing info on the attributes of the feature under the (lat,lon) position.

        
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
        res : str
            The string containing the attribute names and values of the identified feature.
        """
        pass
        

    # onclick called by a Map.Map instance
    def onclick(self, m, lon, lat, zoom):
        pass
            
            
    #####################################################################################################################################################
    # Properties
    #####################################################################################################################################################

    @property
    def identify_fields(self):
        """
        Get/Set the list of attributes to return on an identify operation (click on a vector feature).
        
        Returns
        --------
        list_of_attributes : list
            Names of the attributes to return on an identify operation

        Example
        -------
        Programmatically change the list of attributes::
            
            vlayer.identify_fields = ['attribute1', 'attribute2']
            print(vlayer.identify_fields)
        """
        pass
        
    @identify_fields.setter
    def identify_fields(self, listofattributes):
        pass
                

    @property
    def identify_width(self):
        """
        Get/Set the width of the popup widget that opens when an identify operation is done on a feature of the vector layer.
        
        Returns
        --------
        width : str
            Width in pixels or any other CSS units of the popup widget (default is '180px')

        Example
        -------
        Programmatically change the width of the identify popup::
            
            vlayer.identify_width = '3vw'
            print(vlayer.identify_width)
        """
        pass
        
    @identify_width.setter
    def identify_width(self, width):
        pass
    

    #####################################################################################################################################################
    # Create an ipyleaflet.TileLayer
    #####################################################################################################################################################
    
    # Returns an instance of ipyleaflet.TileLayer
    def tileLayer(self, max_zoom=22):
        """
        Creates an ipyleaflet.TileLayer object from an instance of vectorlayer, to be added to a Map for display.
        
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
            from geolayer import vectorlayer

            # Create a vectorlayer instance
            vlayer = vectorlayer.file(...)
            
            # Create an ipyleaflet Map
            m = ipyleaflet.Map()
            
            # Add the layer to the map
            m.add(vlayer.tileLayer())
            
            # Display the map
            display(m)
        """
        pass

    
    
#####################################################################################################################################################
# Generate an image from a symbol
#####################################################################################################################################################
def symbol2Image(symbol=[], size=1, feature='Point', clipdimension=999, showborder=False):
    """
    Convert a symbol into a Pillow image (to be used in legends, etc.).

    Parameters
    ----------
    symbol : list of lists, optional
        Symbol to convert into a Pillow image. See the chapter :ref:`symbol-format-help` for a guide on how symbols are defined and the chapter :ref:`symbol-editor-help` for help on the visual Symbol Editor.
    size : int, optional
        Size of the image to create, in the range [1,3] for "small" (30x30 pixels), "medium" (80x80 pixels) and "big" (256x256 pixels) dimensions. Default is 1.
    feature : str, optional
        Type of feature to display: Polygon, Point or Polyline (default is 'Point').
    clipdimension : int, optional
        Optional dimension of the square in pixel to be used to clip the output image to a smaller dimension (default is 999).
    showborder : bool, optional
        If True a thin border is added to the image (default is False).
        
    Example
    -------
    Create a Pillow image from a symbol::
        
        # Import libraries
        from IPython.display import display
        from geolayer.vectorlayer import symbol2Image
            
        symbol = [
                    [
                        ["PolygonSymbolizer", "fill", 'yellow'],
                        ["PolygonSymbolizer", "fill-opacity", 0.2],
                        ["LineSymbolizer", "stroke", "#00ff00"],
                        ["LineSymbolizer", "stroke-width", 4.0]
                    ]
        ]
            
        # Create the image
        img = symbol2Image(symbol, feature='Polygon', size=2, showborder=True)
            
        # Display the image
        display(img)
            
            
    .. image:: figures/PillowImage.png
        :width: 100px
        
    Image created by the example code above to convert a polygonal symbol to a Pillow image
    
    """
    pass
    
