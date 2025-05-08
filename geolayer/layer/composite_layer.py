"""Composition of layers"""
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
import hashlib

# vois import
from vois import colors
from vois.vuetify import textlist

# geolayer import
from geolayer import settings
from geolayer.api import rasterAPI, redisAPI, vrtAPI
from geolayer.utility import templates


#####################################################################################################################################################
# Class CompositeLayer to group RasterLayer and VectorLayer instances using a composition operation (i.e to mask raster with vector)
# ####################################################################################################################################################
class CompositeLayer:
    """
    Composite layer visualization. Class to jointly display vector or raster datasets (shapefiles, geopackage, WKT, POSTGIS, GeoTIFFs, VRTs, etc.). It can be useful both for efficiency reasons (combine two layers together in a sort of "mosaic" and thus minimize the number of tile requests to the server), and for creating compositions (for instance mask a raster layer with a vector polygons file)
    
    After the creation of an instance of the CompositeLayer class, these methods can be called to manage the list of (raster or vector) layers to compose:
    
    - :py:meth:`~CompositeLayer.clear`
    - :py:meth:`~CompositeLayer.add`

    In particular the :py:meth:`~CompositeLayer.add` method manages a parameter called 'composition_operation' which defines how the composition is done, i.e. how the added layer will be displayed on top of the previously added layes.
    
    The available composition modes are described in detail here: `Compositing Operations <https://tilemill-project.github.io/tilemill/docs/guides/comp-op/>`_ and can be summarized with these figures:
    
    .. figure:: figures/Compositing.png
        :scale: 100 %
    
    .. figure:: figures/montage_triangles.jpg
        :scale: 150 %
    """
    
    # Initialization
    def __init__(self):
        
        # List of layers and composition operations
        self.layers = []
        self.composition_operations = []
        
        # Store the procid (after a call to self.toLayer())
        self.procid = None
    

    # Remove all layers
    def clear(self):
        """
        Remove all the compositing layers.
        """
        self.layers = []
        self.composition_operations = []
        
    
    # Add a layer
    def add(self, layer, composition_operation='src-over'):
        """
        Add a layer to the composition.
        
        Parameters
        ----------
        layer : instance of VectorLayer, RasterLayer or CompositeLayer
            Layer to be added to the composition
        composition_operation : str, optional
            Composition mode to apply for the mixing of the added layer with the previously added ones (default is 'src-over')
        
        Example
        -------
        Compose a Raster with a Vector polygon layer and use the polygons to clip the raster display inside the administrative boundaries of a country::
        
            # Import libraries
            from IPython.display import display
            import plotly.express as px
            from vois.geo import Map
            from geolayer.layer.vector_layer import VectorLayer
            from geolayer.layer.raster_layer import RasterLayer
            from geolayer.layer.composite_layer import CompositeLayer

            # Create a VectorLayer instance to display the NUTS0 (country) polygonal level of Italy
            vlayer = VectorLayer.file('/data/NUTS_RG_03M_2021_4326_0.shp')
            vlayer.symbologyAdd(rule="[CNTR_CODE] = 'IT'", symbol=[ [ ["PolygonSymbolizer", "fill", '#ff0000'] ] ])

            # Create a RasterLayer instance to display a TIFF file and use viridis colorlist
            rlayer = RasterLayer.single('/data/CAMX_LAMMA_2019_NO2_IT_TUSCANY-MAP_FILE-20240731-ee2be3-1167.tiff')
            rlayer.colorlist(0.0, 10.0, px.colors.sequential.Viridis)

            # Create an instance of the CompositeLayer class
            clayer = CompositeLayer()
            
            # Add the VectorLayer to the composite
            clayer.add(vlayer)

            # Add the RasterLayer to the composite using the 'src-in' composition mode (the raster will be visible only on areas covered by the administrative polygons)
            clayer.add(rlayer, composition_operation='src-in')

            # Create a Map and add the composite layer
            m = Map.Map(zoom=8, center=[43.33316939281735, 11.282949043606514], basemapindex=0)
            m.addLayer(clayer)
            m.onclick = rlayer.onclick
            
            # Display the map
            display(m)
            
            
        Example
        -------
        Group three different vector layer in a single composite layer::

            # Import libraries
            from IPython.display import display
            import plotly.express as px
            from vois.geo import Map
            from geolayer.layer.vector_layer import VectorLayer
            from geolayer.layer.composite_layer import CompositeLayer
            
            # Create a layer that displays the ITALY boundaries polygon
            vlayer1 = VectorLayer.file('/data/NUTS_RG_03M_2021_4326_0.shp')
            vlayer1.symbologyAdd(rule="[CNTR_CODE] = 'IT'", symbol=[ [ ["PolygonSymbolizer", "fill", '#ff0000'] ] ])

            # Create a layer that displays the FRANCE boundaries polygon
            vlayer2 = VectorLayer.file('/data/NUTS_RG_03M_2021_4326_0.shp')
            vlayer2.symbologyAdd(rule="[CNTR_CODE] = 'FR'", symbol=[ [ ["PolygonSymbolizer", "fill", '#00ff00'] ] ])

            # Create a layer that displays the GERMANY boundaries polygon
            vlayer3 = VectorLayer.file('/data/NUTS_RG_03M_2021_4326_0.shp')
            vlayer3.symbologyAdd(rule="[CNTR_CODE] = 'DE'", symbol=[ [ ["PolygonSymbolizer", "fill", '#0000ff'] ] ])

            # Compose the three layers
            clayer = CompositeLayer()
            clayer.add(vlayer1)
            clayer.add(vlayer2)
            clayer.add(vlayer3)            
            
            # Create a Map and add the composite layer
            m = Map.Map(zoom=5, center=[46.8, 11.56], basemapindex=0)
            m.addLayer(clayer)
            m.onclick = vlayer1.onclick
            
            # Display the map
            display(m)
        """
        
        self.layers.append(layer)
        self.composition_operations.append(composition_operation)
        
            
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
        print("TILEGEO composite layer instance:")
        #print("   procid: %s"%str(self.procid))
        for layer, comp in zip(self.layers, self.composition_operations):
            print("   layer: %s (%s)"%(layer.MD5(), comp))
    
    

    #####################################################################################################################################################
    # Create an ipyleaflet.TileLayer
    #####################################################################################################################################################

    # Returns an instance of ipyleaflet.TileLayer
    def tileLayer(self, max_zoom=22, file_format='png', cache=False):
        """
        Creates an ipyleaflet.TileLayer object from an instance of CompositeLayer, to be added to a Map for display.
        
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
    def xml(self):
        """
        Returns the full XML in Mapnik syntax.
        """
        
        res = templates.MAP_PREFIX
        
        res += self.xml_styles()

        res += self.xml_layer()
        
        res += '\n' + templates.MAP_END
        
        return res
    
    
    # Return the XML of the Styles
    def xml_styles(self, compositing='src-over'):

        res = ''
        
        for layer, comp in zip(self.layers, self.composition_operations):
            res += '\n\n' + layer.xml_styles(comp)
            
        return res
    
    
    # Return the XML of the Layer
    def xml_layer(self):
        
        res = ''
        
        # Layers
        for layer, comp in zip(self.layers, self.composition_operations):
            res += '\n' + layer.xml_layer()

        return res
