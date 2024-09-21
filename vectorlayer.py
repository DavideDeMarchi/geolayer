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
    Vector datasets visualization. It can display vector file datasets (shapefiles, geopackage, etc.), WKT strings (see: `Well Known Text format <https://en.wikipedia.org/wiki/Well-known_text_representation_of_geometry>`_) and POSTGIS geospatial tables and queries.
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
             layer='',      # Name of the layer (for a shapefile leave it empty)
             epsg=4326,
             proj=''):      # To be used for projections that do not have an EPSG code (if not empty it is used instead of the passed epsg)
        """
        Display of a file-based vector dataset on an ipyleaflet Map.
        
        Parameters
        ----------
        filepath : str
            File path of the vector dataset to display (shapefile, geopackage, etc.)
        layer : str, optional
            Name of the layer to display (for a shapefile it can be empty). Default is ''.
        epsg : int, optional
            EPSG code of the coordinate system to use (default is 4326, the geographical coordinates).
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
            vlayer.symbologyAdd(rule="[CNTR_CODE] = 'IT'", symbol=vectorlayer.symbolChange(symbol, fillColor='#00aa00'))

            # Create a Map
            m = Map.Map()
            
            # Add the layer to the map
            m.addLayer(vlayer)
            
            # Set the identify operation
            m.onclick = vlayer.onclick
            
            # Display the map
            display(m)

.. tip::            
        To visually edit symbols, please use the `Symbol Editor <https://geolayer.azurewebsites.net>`_ described in chapter :ref:`symbol-editor-help`.
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
            List of strings in WKT format containing the geometry of features to display (see: `Well Known Text format <https://en.wikipedia.org/wiki/Well-known_text_representation_of_geometry>`_)
        properties : list of dict, optional
            List of dict containing attributes of the features (default is [])
            
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
            
.. tip::            
        To visually edit symbols, please use the `Symbol Editor <https://geolayer.azurewebsites.net>`_ described in chapter :ref:`symbol-editor-help`.
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
        
.. tip::
        Always pass a valid extents string, since this will make the display much faster in most cases.
        
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
            
.. tip::
        To visually edit symbols, please use the `Symbol Editor <https://geolayer.azurewebsites.net>`_ described in chapter :ref:`symbol-editor-help`.
        """
        pass

    
    #####################################################################################################################################################
    # Symbology management
    #####################################################################################################################################################
    
    # Remove all default symbology and all symbols added
    def symbologyClear(self, maxstyle=0):
        """
        Remove all the default symbology for a vectorlayer instance and all the symbols eventually added.
        By default a vectorlayer instance has a default symbology (for instance a pale yellow for polygons) so that it can be displayed even if no symbology is added using the :py:method:`vectorlayer.symbologyAdd`.
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
        pass
                
    
    # Change color and other properties of a symbol and returns the modified symbol
    @staticmethod
    def symbolChange(symbol, color='#ff0000', fillColor='#ff0000', fillOpacity=1.0, strokeColor='#ffff00', strokeWidth=0.5, scalemin=None, scalemax=None):
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
    # Identify methods
    #####################################################################################################################################################
    
    # Identify: returns a string
    def identify(self, lon, lat, zoom):
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
                
                
    #####################################################################################################################################################
    # Create an ipyleaflet.TileLayer
    #####################################################################################################################################################
    
    # Returns an instance of ipyleaflet.TileLayer
    def tileLayer(self, max_zoom=22):
        pass

    
    
#####################################################################################################################################################
# Generate an image from a symbol
#####################################################################################################################################################
def symbol2Image(symbol=[], size=1, feature='Point', clipdimension=999, showborder=False):
    pass
    
