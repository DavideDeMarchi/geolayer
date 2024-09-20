"""BDAP (JRC Big Data Analytics Platform) layer creation with minimal dependencies
(to create server-side inter.VectorLayer instances for vector display without using the client version of inter)."""
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
#    vlayer = vectorlayer.file('path to a .shp file', epsg=4326)
#    vlayer.symbologyClear()
#    vlayer.symbologyAdd(symbol=symbol)                              # Apply symbol to all features of the vectorlayer
#    vlayer.symbologyAdd(rule="[CNTR_CODE] = 'IT'", symbol=symbol)   # Apply symbol only to features that are filtered by the rule on attributes
#                                                                    # See https://github.com/mapnik/mapnik/wiki/Filter for help on filter sintax
#    mapUtils.addLayer(m, vlayer.tileLayer(), name='Polygons')
#
#
# The static methos vectorlayer.symbolChange can be used to change a parametric symbol
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
# s = vectorlayer.symbolChange(fillColor='red')
#
#####################################################################################################################################################


#####################################################################################################################################################
# Class vectorlayer to create server-side VectorLayer instances for vector display without using inter client library
# Manages vector datasets in files (shapefiles, geopackage, etc.), WKT strings and POSTGIS queries
#####################################################################################################################################################
class vectorlayer:
    """
    Vector datasets visualization
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
        pass
    
    
    #####################################################################################################################################################
    # Initialization from a list of wkt strings
    #####################################################################################################################################################
    @classmethod
    def wkt(cls,
            wktlist,          # List of strings containing WKT of geospatial features in EPSG4326
            properties=[]):   # List of dictionaries containing the attributes of each of the feature (optional)
        pass
    
    
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
                geomtype='polygon',
                geometry_field='',
                geometry_table='',
                extents=''):
        pass

    
    #####################################################################################################################################################
    # Symbology management
    #####################################################################################################################################################
    
    # Remove all default symbology and all symbols added)
    def symbologyClear(self, maxstyle=0):
        pass

            
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
    
