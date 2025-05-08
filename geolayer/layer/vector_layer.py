"""Geospatial Vector layer"""
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
import os
import datetime
import requests
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import ipyvuetify as v
from collections import Counter
import statistics
import numpy as np
import hashlib
import math

# vois import
from vois import colors
from vois.vuetify import settings, textlist, palettePicker

# geolayer import
from geolayer import settings
from geolayer.api import redisAPI, rasterAPI, vectorAPI
from geolayer.utility import classifiers, templates


# Symbols dimension in pixels
SMALL_SYMBOLS_DIMENSION  = 30
MEDIUM_SYMBOLS_DIMENSION = 80
LARGE_SYMBOLS_DIMENSION  = 256


#####################################################################################################################################################
# Notes on symbology:
#
# A symbol is a list of lists of items each having 3 elements: [SymbolizerName, KeyName, Value]
# Each list inside the symbol is mapped into a style (from style0 to style9), thus allowing for overlapped symbols
#
# Example:
# symbol = [
#             [
#                ["PolygonSymbolizer", "fill", '#ff0000'],
#                ["PolygonSymbolizer", "fill-opacity", 0.3],
#                ["LineSymbolizer", "stroke", "#010000"],
#                ["LineSymbolizer", "stroke-width", 2.0]
#             ]
# ]
#
# Example on how to manage symbology:
#
#    vlayer = VectorLayer.file('path to a .shp file', epsg=4326)
#    vlayer.symbologyClear()
#    vlayer.symbologyAdd(rule='all', symbol=symbol)                  # Apply symbol to all features of the vectorlayer
#    vlayer.symbologyAdd(rule="[CNTR_CODE] = 'IT'", symbol=symbol)   # Apply symbol only to features that are filtered by the rule on attributes
#                                                                    # See https://github.com/mapnik/mapnik/wiki/Filter for help on filter sintax
#    mapUtils.addLayer(m, vlayer.tileLayer(), name='Polygons')
#
#
# The static methos VectorLayer.symbolChange can be used to change a parametric symbol
#
# Example:
# symbol = [
#             [
#                ["PolygonSymbolizer", "fill", 'FILL-COLOR'],
#                ["PolygonSymbolizer", "fill-opacity", 0.3],
#                ["LineSymbolizer", "stroke", "#010000"],
#                ["LineSymbolizer", "stroke-width", 2.0]
#             ]
# ]
#
# s = VectorLayer.symbolChange(fillColor='red')
#
#####################################################################################################################################################


#####################################################################################################################################################
# Class VectorLayer for vector display
# Manages vector datasets in files (shapefiles, geopackage, etc.), WKT strings and POSTGIS queries
#####################################################################################################################################################
class VectorLayer:
    """
    Vector datasets visualization. Class to display vector file datasets (shapefiles, geopackage, etc.), WKT strings (see: `Well Known Text format <https://en.wikipedia.org/wiki/Well-known_text_representation_of_geometry>`_) and POSTGIS geospatial tables and queries.
    
    An instance of this class can be created using one of these class methods:
    
    - :py:meth:`~VectorLayer.file`
    - :py:meth:`~VectorLayer.wkt`
    - :py:meth:`~VectorLayer.postgis`
    
    To apply symbology to a vectorlayer class, these methods can be used:
    
    - :py:meth:`~VectorLayer.symbologyClear`
    - :py:meth:`~VectorLayer.symbologyAdd`
    
    A *parametric* symbol can be defined using tags like FILL-COLOR, STROKE-WIDTH, etc. that can be substituted with real values using the static method :py:meth:`~VectorLayer.symbolChange`.
    
    See the chapter :ref:`symbol-format-help` for a guide on how symbols are defined and the chapter :ref:`symbol-editor-help` for help on the visual Symbol Editor.

    """
    
    # Initialization for vector files (shapefiles, geopackage, etc.)
    def __init__(self,
                 filepath='',
                 layer='',
                 epsg=4326,
                 proj='',              # To be used for projections that do not have an EPSG code (if not empty it is used instead of the passed epsg)
                 identify_fields=[]):  # List of names of field to display on identify operation

        self.md5 = None
        
        self.isPostgis = False
        self.isWKT     = False
        
        self.filepath = filepath
        self.layer    = layer
        self.epsg     = epsg
        self.proj     = proj
        
        self.feature_type = 'Point'
        
        self._identify_fields = identify_fields
        
        self._identify_width = '180px'
        
        
        # Store the procid (after a call to self.toLayer())
        self.procid = None
        
        # Symbology rules
        self.rules = {}

        
    #####################################################################################################################################################
    # Initialization for a vector file (shapefile, geopackage, etc.)
    #####################################################################################################################################################
    @classmethod
    def file(cls,
             filepath,      # Path to the file (shapefile or geopackage, etc...)
             layer=None,    # Name of the layer (for a shapefile leave it empty)
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
            from geolayer.layer.vector_layer import VectorLayer

            # Create a VectorLayer instance from a file dataset (shapefile)
            vlayer = VectorLayer.file('/data/NUTS_RG_03M_2021_4326_0.shp', epsg=4326)

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
            vlayer.symbologyAdd(symbol=VectorLayer.symbolChange(symbol, fillColor='red'))
            
            # Assign a green symbol to a subset of the features
            vlayer.symbologyAdd(rule="[CNTR_CODE] = 'IT'",
                                symbol=VectorLayer.symbolChange(symbol, fillColor='#00aa00'))

            # Create a Map
            m = Map.Map()
            
            # Add the layer to the map
            m.addLayer(vlayer)
            
            # Set the identify operation
            m.onclick = vlayer.onclick
            
            # Display the map
            display(m)
        """

        if layer is None:
            layer = Path(filepath).stem

        info = vectorAPI.layer(filepath, layer)
        
        if epsg is None:
            if 'epsg' in info and info['epsg'] is not None:
                epsg = int(info['epsg'])
                
        instance = cls(filepath, layer, epsg, proj)
        instance.feature_type = info['feature_type']
        return instance
    
    
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
            from geolayer.layer.vector_layer import VectorLayer

            # Create a vectorlayer instance from a WKT string
            vlayer = VectorLayer.wkt(['POLYGON ((20 40, 0 45, 10 52, 30 52, 20 40))'], 
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
    
        instance = cls('', '', 4326, '')
        instance.isWKT      = True
        instance.wktlist    = wktlist
        instance.properties = properties
        
        if len(wktlist) > 0:
            if   'POINT'   in wktlist[0]: instance.feature_type = 'Point'
            elif 'POLYGON' in wktlist[0]: instance.feature_type = 'Polygon'
            else:                         instance.feature_type = 'Polyline'
        
        return instance
    
    
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
                geometry_field='geometry',
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
            from geolayer.layer.vector_layer import VectorLayer

            # Create a vectorlayer instance for a POSTGIS query
            vlayer = VectorLayer.postgis(
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
        
        instance = cls()

        instance.isPostgis = True
        instance.isWKT     = False
        
        instance.postgis_host           = host
        instance.postgis_port           = port
        instance.postgis_dbname         = dbname
        instance.postgis_user           = user
        instance.postgis_password       = password
        instance.postgis_query          = query
        instance.postgis_epsg           = epsg
        instance.postgis_proj           = proj
        instance.postgis_geomtype       = geomtype
        instance.postgis_geometry_field = geometry_field
        instance.postgis_geometry_table = geometry_table
        instance.postgis_extents        = extents

        instance.feature_type = instance.postgis_geomtype
        
        return instance                

    
    #####################################################################################################################################################
    # Static methods to get list of layers of a file-based vector dataset or info on a layer
    #####################################################################################################################################################

    # Returns the list of layers of a file-based vector dataset
    @staticmethod
    def layers(dataset_path : str):
        """
        Returns the list of layers of a file-based vector dataset (shapefile, geopackage, sqlite, etc.).
        
        Parameters
        ----------
        dataset_path : str
            Full path of the file-based dataset (shapefile, geopackage, sqlite, etc.).
        """
        
        return vectorAPI.layers(dataset_path)

    
    # Returns info dictionary on a layer of a file-based vector dataset
    @staticmethod
    def layer(dataset_path : str, layer_name : str = None):
        """
        Returns a dictionary containing info on a layer of a file-based vector dataset (extent, feature type, feature count, epsg, etc.).
        
        Parameters
        ----------
        dataset_path : str
            Full path of the file-based dataset (shapefile, geopackage, sqlite, etc.)
        layer_name : str
            Name of the layer. It is possible to pass None in case of a shapefile dataset.
        """
        
        return vectorAPI.layer(dataset_path, layer_name)
    
    
    #####################################################################################################################################################
    # Info on fields and their values (only for file and wkt)
    #####################################################################################################################################################

    # Returns a dictionary containing info on the fields of a layer of a Dataset
    def fields(self):
        """
        Returns a dictionary containing info on the fields of a file-based vector dataset. Works only for a filebased or a wkt instance.
        """
        
        if self.isPostgis:
            return {}
        elif self.isWKT:
            s = set()
            for p in self.properties:
                s.update(list(p.keys()))
            return {x: {} for x in s}
        else:
            return vectorAPI.fields(self.filepath, self.layer)

        
    # Returns info on a field of a layer of a Dataset
    def field(self, field):
        """
        Returns a dictionary containing info on a field of a file-based vector dataset. Works only for a filebased or a wkt instance.
        
        Parameters
        ----------
        field : str
            Name of the field to query.
        """
        
        if self.isPostgis:
            return {}
        elif self.isWKT:
            return {}
        else:
            return vectorAPI.field(self.filepath, field_name=field, layer_name=self.layer)

        
    # Returns the list of all values of a field of a layer of a Dataset
    def values(self, field):
        """
        Returns the list of all values of a field of a layer. Works only for a filebased or a wkt instance.
        
        Parameters
        ----------
        field : str
            Name of the field to query.
        """
        
        if self.isPostgis:
            return []
        elif self.isWKT:
            res = []
            for p in self.properties:
                if field in p:
                    res.append(p[field])
            return res
        else:
            return vectorAPI.values(self.filepath, field_name=field, layer_name=self.layer)

        
    # Returns a dictionary of all the distinct values of a field of a layer of a Dataset with their number of occurrencies
    def distinct(self, field):
        """
        Returns a dictionary of all the distinct values of a field of a layer of a dataset with their number of occurrencies. Works only for a filebased or a wkt instance.
        
        Parameters
        ----------
        field : str
            Name of the field to query.
        """
        
        if self.isPostgis:
            return {}
        elif self.isWKT:
            return Counter(self.values(field))
        else:
            return vectorAPI.distinct(self.filepath, field_name=field, layer_name=self.layer)

        
    # Returns a dictionary containing statistical information on a numeric field of a layer of a Dataset with their number of occurrencies
    def stats(self, field):
        """
        Returns a dictionary containing statistical information on a numeric field of a layer of a dataset. Works only for a filebased or a wkt instance.
        
        Parameters
        ----------
        field : str
            Name of the field to query.
        """
        
        if self.isPostgis:
            return {}
        elif self.isWKT:
            values = self.values(field)
            if len(values) > 1: stdev = statistics.stdev(values)
            else:               stdev = 0.0
            return {'min': min(values), 'max': max(values), 'mean': statistics.mean(values), 'stdev': stdev}
        else:
            return vectorAPI.stats(self.filepath, field_name=field, layer_name=self.layer)
    
    
    
    #####################################################################################################################################################
    # Symbology management
    #####################################################################################################################################################
    
    # Remove all symbology rules
    def symbologyClear(self, maxstyle=0):
        """
        Remove all the default symbology for a VectorLayer instance and all the symbols eventually added.
        By default a VectorLayer instance has a default symbology (for instance a pale yellow for polygons) so that it can be displayed even if no symbology is added using the :py:meth:`~VectorLayer.symbologyAdd`.
        By calling symbologyClean method, all these default display settings are removed.
        
        Parameters
        ----------
        maxstyle : int, optional
            A symbol in geolayer can have a maximum of 10 layers (corresponding to the number of lists inside its definition. The first list will be mapped to style0, the second to style1, etc., up to style9).
            This parameter can be used to clear only the first style (style0) if 0 is passed (default), or up to all the styles if 10 is passed.
            If the symbols you use are only made of a single layer, call this function without specifying the maxstyle parameter, since the default value of 0 is sufficient to clean the symbology.
        """
        
        self.rules = {}
        
        
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
        
        self.rules[rule] = symbol
        

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

        Returns
        --------
        legend : list of dicts
            A legend is a list of dictionaries, one for each item. Each dict contains the keys: description, rule and symbol
        """
        
        self.symbologyClear()
        self.symbologyAdd(rule='all', symbol=symbol)
        return [{'description': description, 'rule': 'all', 'symbol': symbol}]

    
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
            List of colors to be used for the creation of the legend. See `Plotly sequential color scales <https://plotly.com/python/builtin-colorscales/#builtin-sequential-color-scales>`_ and `Plotly qualitative color sequences <https://plotly.com/python/discrete-color/#color-sequences-in-plotly-express>`_ for possible color lists.
        symbol: list of lists, optional
            Symbol to be used for the rendering of the features. See the chapter :ref:`symbol-format-help` for a guide on how symbols are defined and the chapter :ref:`symbol-editor-help` for help on the visual Symbol Editor.
        interpolate : bool, optional
            If True, the colors assigned to the items of the legend are calculated by using linear interpolation on the list of colors (thus potentially generating also intermediate colors). If False, only the colors in the list are used. In this case, if the number of distinct values is greated than the number of colors in the list, some legend items will have repeated colors.
        distinctValues : list, optional
            Custom list of distinct values to use for the creation of the legend. Default is None, meaning that, for filebased and wkt vectorlayer instances, the list of distinct values is autonomously calculated. This parameter must be mandatory passed when the vectorlayer instance is a postgis dataset.

        Returns
        --------
        legend : list of dicts
            A legend is a list of dictionaries, one for each item. Each dict contains the keys: description, rule and symbol

        Example
        -------
        Create a categories legend on a field of a shapefile::
        
            # Import libraries
            from IPython.display import display
            from geolayer.layer.vector_layer import VectorLayer
            import plotly.express as px
    
            # Create a vectorlayer instance from a file dataset (shapefile)
            vlayer = VectorLayer.file('/data/NUTS_RG_03M_2021_4326_0.shp')

            # Define a parametrical symbol
            symbol = [
                        [
                           ["PolygonSymbolizer", "fill", 'FILL-COLOR'],
                           ["PolygonSymbolizer", "fill-opacity", 0.8],
                           ["LineSymbolizer", "stroke", "#000000"],
                           ["LineSymbolizer", "stroke-width", 1.0]
                        ]
            ]

            # Create a legend on the distinct values of the CNTR_CODE field
            legend = vlayer.legendCategories('CNTR_CODE',
                                             px.colors.qualitative.Dark24,
                                             symbol=symbol,
                                             interpolate=False)
        """
        
        if distinctValues is None:
            values = list(self.distinct(fieldname).keys())
            values.sort()
        else:
            values = list(distinctValues)
    
        self.symbologyClear()
        
        if interpolate:
            ci = colors.colorInterpolator(colorlist, 0.0, float(len(values)-1.0))
        
        res = []
        for index, value in enumerate(values):
            if isinstance(value, float):
                description = '%G'%value
            else:
                description = str(value)
            
            if interpolate:
                c = ci.GetColor(float(index))
            else:
                c = colorlist[index%len(colorlist)]
            
            s = VectorLayer.symbolChange(symbol, color=c, fillColor=c, strokeColor=c, featureValue=value)
            
            if isinstance(value, str): rule = "[" + fieldname + "] = '"  + str(value) + "'"
            else:                      rule = '[' + fieldname + '] = '  + str(value)

            item = {'description': description, 'rule': rule, 'symbol': s}
            self.symbologyAdd(rule=rule, symbol=s)
            res.append(item)
            
        return res
            
    
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

        Returns
        --------
        legend : list of dicts
            A legend is a list of dictionaries, one for each item. Each dict contains the keys: description, rule and symbol

        Example
        -------
        Create a graduated legend on a numerical field of a geopackage dataset::
        
            # Import libraries
            from IPython.display import display
            from geolayer.layer.vector_layer import VectorLayer
            import plotly.express as px
    
            # Create a vectorlayer instance from a file dataset (geopackage)
            vlayer = VectorLayer.file('/data/EuroGlobalMap.gpkg', layer='CoastA', epsg=4258)

            # Define a parametrical symbol
            symbol = [
                        [
                           ["PolygonSymbolizer", "fill", 'FILL-COLOR'],
                           ["PolygonSymbolizer", "fill-opacity", 0.8],
                           ["LineSymbolizer", "stroke", "#000000"],
                           ["LineSymbolizer", "stroke-width", 1.0]
                        ]
            ]

            # Create a graduated legend with 8 classes on the Shape_Area field
            legend = vlayer.legendGraduated('Shape_Area',
                                            px.colors.sequential.Viridis,
                                            symbol=symbol,
                                            interpolate=True,
                                            classifier_name='Quantiles',
                                            classifier_param1=8,
                                            digits=6)
        """
        
        if allValues is None:
            values = list(self.values(fieldname))
        else:
            values = list(allValues)
        
        values = [float(x) for x in values]
        
        # Create the classes
        bins = VectorLayer.createClasses(values,classifier_name,classifier_param1,classifier_param2)
        
        res = []
        if len(bins) > 0:

            if digits >= 0:
                f = "{:.%df}" % digits
            else:
                f = "{:g}"

            # Create the color interpolator on the number of classes
            if interpolate:
                ci = colors.colorInterpolator(colorlist, 0.0, float(len(bins)-1.0))

            if len(bins) > 1:
                markersize_step = (markersize_max - markersize_min) / float(len(bins)-1.0)
            else:
                markersize_step = (markersize_max - markersize_min) / float(len(bins))

            multiplier = markersize_min

            # Cycle on the classes
            for index, binvalue in enumerate(bins):

                if index == 0:
                    description = '<= ' + f.format(binvalue)
                    minvalue = None
                    maxvalue = binvalue
                elif index == len(bins)-1:
                    description = '> ' + f.format(bins[index-1])
                    minvalue = bins[index-1]
                    maxvalue = binvalue
                else:
                    description = f.format(bins[index-1]) + ' - ' + f.format(binvalue)
                    minvalue = bins[index-1]
                    maxvalue = binvalue

                if interpolate:
                    c = ci.GetColor(float(index))
                else:
                    c = colorlist[index%len(colorlist)]

                s = VectorLayer.symbolChange(symbol, color=c, fillColor=c, strokeColor=c, size_multiplier=multiplier, featureValue=binvalue)
                
                if minvalue is None:
                    rule = "[" + fieldname + "] &lt;= "  + str(maxvalue)
                elif maxvalue is None:
                    rule = "[" + fieldname + "] &gt; "  + str(minvalue)
                else:
                    rule = "[" + fieldname + "] &gt; "  + str(minvalue) + " and [" + fieldname + "] &lt;= "  + str(maxvalue)

                item = {'description': description, 'rule': rule, 'symbol': s}
                self.symbologyAdd(rule=rule, symbol=s)
                res.append(item)


                multiplier += markersize_step
        
        return res


    
    # Create the classification. Returns the bins array
    @staticmethod
    def createClasses(values,                       # Array of numerical values
                      classifier_name='Quantiles',  # Classification algorithm
                      classifier_param1=5,          # First parameter for the classification algorithm
                      classifier_param2=None):      # Second parameter for the classification algorithm
        if classifier_name == 'EqualInterval':
            c = classifiers.EqualInterval(np.array(values),int(classifier_param1))
        elif classifier_name == 'BoxPlot':
            c = classifiers.BoxPlot(np.array(values))
        elif classifier_name == 'NaturalBreaks':
            c = classifiers.NaturalBreaks(np.array(values),int(classifier_param1))
        elif classifier_name == 'FisherJenksSampled':
            c = classifiers.FisherJenksSampled(np.array(values),int(classifier_param1),float(classifier_param2))
        elif classifier_name == 'StdMean':
            c = classifiers.StdMean(np.array(values),list(classifier_param1))
        elif classifier_name == 'JenksCaspallForced':
            c = classifiers.JenksCaspallForced(np.array(values),int(classifier_param1))
        elif classifier_name == 'HeadTailBreaks':
            c = classifiers.HeadTailBreaks(np.array(values))
        else:                 # Quantiles
            c = classifiers.Quantiles(np.array(values),int(classifier_param1))
        #print(c)
        return c.bins
    

    #####################################################################################################################################################
    # Legend representation
    #####################################################################################################################################################
    
    # Returns an Image containing all the items of a legend
    def legend2Image(self, legend, size=1, clipdimension=999, width=300, fontweight=400, fontsize=9, textcolor="black"):
        """
        Given as input a legend returned by a call to one of the methods: :py:meth:`~VectorLayer.legendSingle`, :py:meth:`~VectorLayer.legendCategories` or :py:meth:`~VectorLayer.legendGraduated`, this function returns an PILLOW image containing all the items of the legend.
        
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
            
        Example
        -------
        Display a legend as a PILLOW image::
            
            # Import libraries
            from IPython.display import display
            from geolayer.layer.vector_layer import VectorLayer
            import plotly.express as px
    
            # Create a VectorLayer instance from a file dataset (geopackage)
            vlayer = VectorLayer.file('.../EuroGlobalMap.gpkg', layer='CoastA', epsg=4258)

            # Define a parametrical symbol
            symbol = [
                        [
                           ["PolygonSymbolizer", "fill", 'FILL-COLOR'],
                           ["PolygonSymbolizer", "fill-opacity", 0.8],
                           ["LineSymbolizer", "stroke", "#000000"],
                           ["LineSymbolizer", "stroke-width", 1.0]
                        ]
            ]

            # Create a graduated legend with 8 classes on the Shape_Area field
            legend = vlayer.legendGraduated('Shape_Area',
                                            px.colors.sequential.Viridis,
                                            symbol=symbol,
                                            interpolate=True,
                                            classifier_name='Quantiles',
                                            classifier_param1=8,
                                            digits=6)
            
            # Display the legend as an image
            img = vlayer.legend2Image(legend, size=1, fontsize=13, fontweight=400, width=400)
            display(img)
            
        .. figure:: figures/legend_image.png
           :scale: 100 %
           :alt: Image of a graduated legend
        """
        
        if size >= 3:
            dim = LARGE_SYMBOLS_DIMENSION
        elif size == 2:
            dim = MEDIUM_SYMBOLS_DIMENSION
        else:
            dim = SMALL_SYMBOLS_DIMENSION
            
        if clipdimension < dim:
            dim = clipdimension
        
        border = 2
        w = width
        h = len(legend) * (dim + border)
        img = Image.new("RGBA", (w,h), (255,255,255,255))
        draw = ImageDraw.Draw(img)

        folder = os.path.dirname(__file__)
        
        if fontweight >= 700:
            font = ImageFont.truetype('%s/fonts/Roboto-Black.ttf'%folder, fontsize)
        elif fontweight >= 600:
            font = ImageFont.truetype('%s/fonts/Roboto-Bold.ttf'%folder, fontsize)
        elif fontweight >= 500:
            font = ImageFont.truetype('%s/fonts/Roboto-Medium.ttf'%folder, fontsize)
        elif fontweight >= 400:
            font = ImageFont.truetype('%s/fonts/Roboto-Regular.ttf'%folder, fontsize)
        elif fontweight >= 300:
            font = ImageFont.truetype('%s/fonts/Roboto-Light.ttf'%folder, fontsize)
        else:
            font = ImageFont.truetype('%s/fonts/Roboto-Thin.ttf'%folder, fontsize)
                        
        xi = border
        xt = dim + border*3
        for index, item in enumerate(legend):
            y = border+index*dim
            yt = y + (dim-fontsize)/2
            imgItem = symbol2Image(item['symbol'], size=size, clipdimension=clipdimension, feature=self.feature_type)
            img.paste(imgItem, (xi,y))
            draw.text((xt,yt),item['description'],textcolor,font=font)
            
        return img
    
    
    # Returns a v.List containing the legend items as list items
    def legend2List(self, legend, title='', size=1, disabled=False, onclick=None):
        """
        Given as input a legend returned by a call to one of the methods: :py:meth:`~VectorLayer.legendSingle`, :py:meth:`~VectorLayer.legendCategories` or :py:meth:`~VectorLayer.legendGraduated`, this function returns a clickable ipyvuetify List widget containing all the items of  the legend.
        
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
            Python function to call when the user clicks on one of the items of the List widget (default is None). The function must manage three parameters: widget, event, data. By accessing widgets.value the function can understand on which item the click event occurred (from 0 to nitems-1).
            
        Example
        -------
        Display a legend as a ipyvuetify List widget::
            
            # Import libraries
            from IPython.display import display
            from geolayer.layer.vector_layer import VectorLayer
            import plotly.express as px
    
            # Create a VectorLayer instance from a file dataset (geopackage)
            vlayer = VectorLayer.file('.../EuroGlobalMap.gpkg', layer='CoastA', epsg=4258)

            # Define a parametrical symbol
            symbol = [
                        [
                           ["PolygonSymbolizer", "fill", 'FILL-COLOR'],
                           ["PolygonSymbolizer", "fill-opacity", 0.8],
                           ["LineSymbolizer", "stroke", "#000000"],
                           ["LineSymbolizer", "stroke-width", 1.0]
                        ]
            ]

            # Create a graduated legend with 8 classes on the Shape_Area field
            legend = vlayer.legendGraduated('Shape_Area',
                                            px.colors.sequential.Viridis,
                                            symbol=symbol,
                                            interpolate=True,
                                            classifier_name='Quantiles',
                                            classifier_param1=8,
                                            digits=6)
            
            # Callback to be called when the user clicks on an item of the legend
            def onclick(widget, event, data):
                print(legend[widget.value])

            # Create a List widget from the legend
            w = vlayer.legend2List(legend, title='Legend', size=2, onclick=onclick)
            display(w)
            
        .. figure:: figures/legend_list.png
           :scale: 100 %
           :alt: List widget created from a graduated legend
           
        """
        
        if size >= 3:
            dim = LARGE_SYMBOLS_DIMENSION
        elif size == 2:
            dim = MEDIUM_SYMBOLS_DIMENSION
        else:
            dim = SMALL_SYMBOLS_DIMENSION
            
        if len(title) > 0:
            legendtitle = v.Subheader(children=[title], style_='font-size: 14px; font-weight: 700; color: black;', class_='pa-0 ma-0 mb-n2')
        else:
            legendtitle = ''
            
        items = []
        for index, item in enumerate(legend):
            img = symbol2Image(item['symbol'], size=size, feature=self.feature_type)
            url = palettePicker.image2Base64(img)
            vimg = v.Img(src=url)
            icon = v.ListItemIcon(style_='height: %dpx;'%dim, children=[vimg], class_='pa-0 ma-0 ml-n3 mt-2 mr-2')

            item_title = v.ListItemTitle(children=[item['description']])
            content = v.ListItemContent(children=[item_title], class_='pa-0 ma-0 mt-1')
            
            listitem = v.ListItem(children=[icon,content], value=index, dense=True, disabled=disabled, style_='color: black;')
            if onclick is not None and not disabled: listitem.on_event('click', onclick)
            items.append(listitem)

        legendgroup = v.ListItemGroup(v_model=None, children=items)

        if len(title) > 0:
            return v.List(dense=True, children=[legendtitle,legendgroup])
        else:
            return v.List(dense=True, children=[legendgroup])
    
    
    #####################################################################################################################################################
    # Static method to instantiate a parametric symbol
    #####################################################################################################################################################
    
    # Change color and other properties of a symbol and returns the modified symbol
    @staticmethod
    def symbolChange(symbol, color='#ff0000', fillColor='#ff0000', fillOpacity=1.0, strokeColor='#ffff00', strokeWidth=0.5, scalemin=None, scalemax=None, size_multiplier=1.0, featureValue=None):
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
            from geolayer.layer.vector_layer import VectorLayer

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
            symbol_modified = VectorLayer.symbolChange(symbol, fillColor='red')
        """
        
        newsymbol = []
        for layer in symbol:
            newlayer = []
            for member in layer:
                symbolizer,attribute,value = member

                if value == 'COLOR':
                    value = color

                if value == 'FILL-COLOR':
                    value = fillColor

                if value == 'FILL-OPACITY':
                    value = fillOpacity

                if value == 'STROKE-COLOR':
                    value = strokeColor

                if value == 'STROKE-WIDTH':
                    value = strokeWidth

                if value == 'SCALE-MIN':
                    value = scalemin

                if value == 'SCALE-MAX':
                    value = scalemax
                    
                if isinstance(value, str) and 'FEATURE-VALUE' in value:
                    value = value.replace('FEATURE-VALUE',str(featureValue))

                if size_multiplier != 1.0:
                    if symbolizer == 'MarkersSymbolizer' and (attribute == 'width' or attribute == 'height'):
                        value = float(value) * multiplier

                    if symbolizer == 'LineSymbolizer' and attribute == 'stroke-width':
                        value = float(value) * multiplier
                        
                if not value is None:
                    newlayer.append((symbolizer,attribute,value))

            newsymbol.append(newlayer)

        return newsymbol

    
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
        
        if self.isPostgis:
            print("TILEGEO vector layer POSTGIS:")
            #print("   procid:         %s"%str(self.procid))
            print("   host:           %s"%self.postgis_host)
            print("   port:           %d"%self.postgis_port)
            print("   dbname:         %s"%self.postgis_dbname)
            print("   user:           %s"%self.postgis_user)
            print("   password:       %s"%self.postgis_password)
            print("   query:          %s"%self.postgis_query)
            print("   epsg:           %d"%self.epsg)
            print("   proj:           %s"%self.proj)
            print("   geomtype:       %s"%self.postgis_geomtype)
            print("   geometry_field: %s"%self.postgis_geometry_field)
            print("   geometry_table: %s"%self.postgis_geometry_table)
            print("   extents:        %s"%self.postgis_extents)
        elif self.isWKT:
            print("TILEGEO vector layer WKT:")
            print("   wktlist:        %s"%str(self.wktlist))
            print("   properties:     %s"%str(self.properties))
        else:
            print("TILEGEO vector layer FILE:")
            #print("   procid:         %s"%str(self.procid))
            print("   filepath:       %s"%self.filepath)
            print("   layer:          %s"%self.layer)
            print("   epsg:           %d"%self.epsg)
            print("   proj:           %s"%self.proj)
            
        print("   symbology:")
        for rule, symbol in self.rules.items():
            print("       %s:"%rule, symbol)
    
    
    # Return MD5 of the layer
    def MD5(self):
        return hashlib.md5(self.__repr__().encode()).hexdigest()


    
    #####################################################################################################################################################
    # Identify methods
    #####################################################################################################################################################
    
    # Identify: returns a string
    def identify(self, lon, lat, tolerance=0.0):
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
        
        while lon < -180.0: lon += 360.0
        while lon >  180.0: lon -= 360.0
        
        res = vectorAPI.identify(self.filepath, layer_name=self.layer, lon=lon, lat=lat, tolerance=tolerance, geom=True)
        return res
        

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
        Display of a shapefile with identify operation on click event::
        
            # Import libraries
            from IPython.display import display
            from vois.geo import Map
            from geolayer.layer.vector_layer import VectorLayer

            # Create a VectorLayer instance from a file dataset (shapefile)
            vlayer = VectorLayer.file('/data/NUTS_RG_03M_2021_4326_0.shp', epsg=4326)

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
            vlayer.symbologyAdd(symbol=VectorLayer.symbolChange(symbol, fillColor='red'))
            
            # Assign a green symbol to a subset of the features
            vlayer.symbologyAdd(rule="[CNTR_CODE] = 'IT'",
                                symbol=VectorLayer.symbolChange(symbol, fillColor='#00aa00'))

            # Create a Map
            m = Map.Map()
            
            # Add the layer to the map
            m.addLayer(vlayer)
            
            # Set the identify operation
            m.onclick = vlayer.onclick
            
            # Display the map
            display(m)
            
        The default implementation of the VectorLayer.onclick method calls the VectorLayer.identify method and displays a popup on the map showing the textual content returned by the identify method.
        """
        
        tile_dimension_in_degree = 360.0/math.pow(2, zoom)
        tolerance = tile_dimension_in_degree / 100.0
        
        res = self.identify(lon, lat, tolerance=tolerance)
        if not res is None and len(res) > 0:
            descriptions = []
            values       = []
            for key, value in res.items():
                if key in self._identify_fields:
                    descriptions.append(key)
                    values.append(value)

            t = textlist.textlist(descriptions, values,
                                  titlefontsize=10,
                                  textfontsize=11,
                                  titlecolumn=4,
                                  textcolumn=8,
                                  titlecolor='#000000',
                                  textcolor='#000000',
                                  lineheightfactor=1.1)

            t.card.width = self._identify_width
            popup = ipyleaflet.Popup(location=[lat,lon], child=t.draw(), auto_pan=False, close_button=True, auto_close=True, close_on_escape_key=True)
            m.add_layer(popup)
            
            
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
        return self._identify_fields
        
    @identify_fields.setter
    def identify_fields(self, listofattributes):
        self._identify_fields = listofattributes
                

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
        return self._identify_width
        
    @identify_width.setter
    def identify_width(self, width):
        self._identify_width = width

        
    #####################################################################################################################################################
    # Create an ipyleaflet.TileLayer
    #####################################################################################################################################################
    
    # Returns an instance of ipyleaflet.TileLayer
    def tileLayer(self, max_zoom=22, file_format='png', cache=False):
        """
        Creates an ipyleaflet.TileLayer object from an instance of VectorLayer, to be added to a Map for display.
        
        Parameters
        ----------
        max_zoom : int, optional
            Maximum zoom level to define for the layer (default is 22)
        file_format : str, optional
            Format of the tiles generated by the tilegeo server to serve the raster dataset in WMTS (default is 'png')
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
            from geolayer.layer.raster_layer import VectorLayer

            # Create a VectorLayer instance
            vlayer = VectorLayer.file('/data/NUTS_RG_03M_2021_4326_0.shp', epsg=4326)
            
            # Create an ipyleaflet Map
            m = ipyleaflet.Map()
            
            # Add the layer to the map
            m.add(vlayer.tileLayer())
            
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
            Format of the tiles generated by the tilegeo server to serve the raster dataset in WMTS (default is 'png')
        cache : bool, optional
            Flag that enables the server-side caching of the tiles (default is False)
            
        Returns
        --------
        url : str
            URL to be used to display the layer in a WMTS client, for instance ipyleaflet.Map widget, by creating a ipyleaflet.TileLayer instance from the returned URL string.
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
            
        # Calculating the number of styles 
        numstyles = 0
        for rule, symbol in self.rules.items():
            numstyles = max(numstyles, len(symbol))   # len(symbol) is the number of layers present in the symbol
            
        res = ''
        
        # Write the styles
        for i in range(numstyles):
            name = '%s_%d'%(self.md5, i)
            
            if i == 0:
                style = ''
            else:
                style = '\n'
                
            style += '    <Style name="%s" comp-op="%s">'%(name,compositing)

            # Cycle on all rules
            for rule, symbol in self.rules.items():
                n = len(symbol)
                if n > i:
                    style += '\n        <Rule>'
                    if rule != 'all' and len(rule) > 0:
                        style += '\n            <Filter>%s</Filter>'%rule
                        
                    layer = symbol[i]

                    # Distinct symbolizers
                    symbolizers = sorted(list(set([elem[0] for elem in layer])))

                    for symbolizer in symbolizers:
                        style += '\n            <%s'%symbolizer

                        elem_value = ''
                        # For all the elemnts of the layer
                        for elem in layer:
                            if elem[0] == symbolizer:
                                if elem[1] == 'elem-value':
                                    elem_value = str(elem[2])
                                else:
                                    style += ' %s="%s"'%(elem[1], str(elem[2]))

                        if len(elem_value) > 0:
                            style += '>' + elem_value + '</' + symbolizer + '>'
                        else:
                            style += '/>'
                            
                    style += '\n        </Rule>'
            
            style += '\n    </Style>'
            
            if i < numstyles-1:
                style += '\n'
            
            res += style
            
        return res
    
    
    # Return the XML of the Layer
    def xml_layer(self):
        
        if self.md5 is None:
            self.md5 = self.MD5()
        
        # Calculating the number of styles 
        numstyles = 0
        for rule, symbol in self.rules.items():
            numstyles = max(numstyles, len(symbol))   # len(symbol) is the number of layers present in the symbol

            
        # Add specific settings of the three formats
        if self.isPostgis:
        
            srs = "epsg:%d"%self.postgis_epsg
            if self.postgis_proj is not None and len(self.postgis_proj) > 0:
                srs = self.postgis_proj
                
            layer = '\n    <Layer name="%s" srs="%s">'%(self.md5, srs)
            
            # Write the styles
            for i in range(numstyles):
                name = '%s_%d'%(self.md5, i)
                layer += '\n        <StyleName>%s</StyleName>'%name
                
            # Write the Datasource
            layer += '\n        <Datasource>'
            layer += '\n            <Parameter name="type">postgis</Parameter>'
            layer += '\n            <Parameter name="host">%s</Parameter>'%self.postgis_host
            layer += '\n            <Parameter name="port">%d</Parameter>'%self.postgis_port
            layer += '\n            <Parameter name="dbname">%s</Parameter>'%self.postgis_dbname
            layer += '\n            <Parameter name="user">%s</Parameter>'%self.postgis_user
            layer += '\n            <Parameter name="password">%s</Parameter>'%self.postgis_password
            layer += '\n            <Parameter name="table">(%s)</Parameter>'%self.postgis_query
            layer += '\n            <Parameter name="persist_connection">false</Parameter>'
            layer += '\n            <Parameter name="estimate_extent">true</Parameter>'
            layer += '\n            <Parameter name="extent">%s</Parameter>'%self.postgis_extents
            layer += '\n            <Parameter name="geometry_field">%s</Parameter>'%self.postgis_geometry_field
            layer += '\n            <Parameter name="geometry_table">%s</Parameter>'%self.postgis_geometry_table
            layer += '\n        </Datasource>'

            layer += '\n    </Layer>'
            
        
        elif self.isWKT:
            layer = '\n    <Layer name="%s" srs="+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs">'%self.md5
            
            # Write the styles
            for i in range(numstyles):
                name = '%s_%d'%(self.md5, i)
                layer += '\n        <StyleName>%s</StyleName>'%name
                
            features = '\n'.join(['"%s"'%x for x in self.wktlist])

            # Retrieve the list of all fields
            fields = set()
            for p in self.properties:
                fields.update(set(p.keys()))
            fields = list(fields)
                
            # Write the Datasource
            layer += '\n        <Datasource>'
            layer += '\n            <Parameter name="type">csv</Parameter>'
            layer += '\n            <Parameter name="inline">'
            layer += '\nwkt'
            if len(fields) > 0:
                layer += ',' + ','.join(fields)
                
            for i, wkt in enumerate(self.wktlist):
                layer += '\n"' + wkt + '"'
                if len(fields) > 0:
                    if len(self.properties) > i:
                        prop = self.properties[i]
                        for field in fields:
                            if field in prop:
                                layer += ',%s'%str(prop[field])
                            else:
                                layer += ','
                    else:
                        for field in fields:
                            layer += ','
                        
            layer += '\n            </Parameter>'
            layer += '\n        </Datasource>'

            layer += '\n    </Layer>'
        # File
        else:
            srs = "epsg:%d"%self.epsg
            if self.proj is not None and len(self.proj) > 0:
                srs = self.proj
                
            layer = '\n    <Layer name="%s" srs="%s">'%(self.md5, srs)
            
            # Write the styles
            for i in range(numstyles):
                name = '%s_%d'%(self.md5, i)
                layer += '\n        <StyleName>%s</StyleName>'%name
                
            # Write the Datasource
            layer += '\n        <Datasource>'
            layer += '\n            <Parameter name="type">ogr</Parameter>'
            layer += '\n            <Parameter name="layer">%s</Parameter>'%self.layer
            layer += '\n            <Parameter name="file">%s</Parameter>'%self.filepath
            layer += '\n        </Datasource>'

            layer += '\n    </Layer>'

            
        return layer
    
    
   
    
#####################################################################################################################################################
# Generate an image from a symbol
#####################################################################################################################################################
def symbol2Image(symbol=[], size=1, feature='Point', clipdimension=999, showborder=False):
    """
    Generate an image from a symbol.
    """

    doclip = False
    if feature == 'Line' or feature == 'Polyline':
        if size >= 3:    wkt = 'LINESTRING (-170 82, -100 55, -60 70, -10 38)'
        elif size == 2:  wkt = 'LINESTRING (-175 83, -158 81, -148 83, -129 81)'
        else:            wkt = 'LINESTRING (-177 84.45, -171 83.9, -167.4 84.25, -161 83.75)'
    elif feature == 'Polygon':
        if size >= 3:    wkt = 'POLYGON ((-170 83.85, -170 10, -10 10, -10 83.85, -170 83.85))'
        elif size == 2:  wkt = 'POLYGON ((-175 84.5, -175 78, -128.5 78, -128.5 84.5, -175 84.5))'
        else:            wkt = 'POLYGON ((-178 84.85, -178 83.2, -160.5 83.2, -160.5 84.85, -178 84.85))'
    else:
        if size >= 3:    wkt = 'POINT (-90 65)'
        elif size == 2:  wkt = 'POINT (-152 82)'
        else:            wkt = 'POINT (-169.52 84.05)'

    if size >= 3:
        if clipdimension < LARGE_SYMBOLS_DIMENSION:
            doclip = True
    elif size == 2:
        if clipdimension < MEDIUM_SYMBOLS_DIMENSION:
            doclip = True
    else:
        if clipdimension < SMALL_SYMBOLS_DIMENSION:
            doclip = True

    vlayer = VectorLayer.wkt([wkt])
    vlayer.symbologyClear()
    vlayer.symbologyAdd(rule='all', symbol=symbol)
    #print(vlayer.rules)
    #print(vlayer.xml())

    url = '%s%s/1/0/0.png'%(settings.TILE_ENDPOINT, vlayer.toLayer())
    response = requests.get(url)
    
    if len(response.content) > 5 and response.content[0] == 137 and response.content[1] == 80 and response.content[2] == 78 and response.content[3] == 71 and response.content[4] == 13:
        img = Image.open(BytesIO(response.content))
        if size >= 3:
            img = img.crop((0, 0, LARGE_SYMBOLS_DIMENSION, LARGE_SYMBOLS_DIMENSION))
        elif size == 2:
            img = img.crop((0, 0, MEDIUM_SYMBOLS_DIMENSION, MEDIUM_SYMBOLS_DIMENSION))
        else:
            img = img.crop((0, 0, SMALL_SYMBOLS_DIMENSION, SMALL_SYMBOLS_DIMENSION))

        if doclip:
            s = img.size
            cx = s[0]/2
            cy = s[1]/2
            img = img.crop((cx-clipdimension/2, cy-clipdimension/2, cx+clipdimension/2, cy+clipdimension/2))
    else:
        print('URL with errors:',url)
        if size >= 3:    img = Image.new("RGB", (LARGE_SYMBOLS_DIMENSION,  LARGE_SYMBOLS_DIMENSION),  (255, 255, 255))
        elif size == 2:  img = Image.new("RGB", (MEDIUM_SYMBOLS_DIMENSION, MEDIUM_SYMBOLS_DIMENSION), (255, 255, 255))
        else:            img = Image.new("RGB", (SMALL_SYMBOLS_DIMENSION,  SMALL_SYMBOLS_DIMENSION),  (255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((0, 0),"Error",(0,0,0))

    # Add a thin black border
    if showborder:
        draw = ImageDraw.Draw(img)
        s = img.size
        draw.rectangle(((0, 0), (s[0]-1, s[1]-1)), outline='black')

    return img
    