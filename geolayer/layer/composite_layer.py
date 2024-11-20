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
    
    # Initialization
    def __init__(self):
        
        # List of layers and composition operations
        self.layers = []
        self.composition_operations = []
        
        # Store the procid (after a call to self.toLayer())
        self.procid = None
    

    # Remove all layers
    def clear(self):
        self.layers = []
        self.composition_operations = []
        
    
    # Add a layer
    def add(self, layer, composition_operation='src-over'):
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
        print("TILEGEO composite layer instance:")
        print("   procid: %s"%str(self.procid))
        for layer, comp in zip(self.layers, self.composition_operations):
            print("   layer: %s (%s)"%(layer.MD5(), comp))
    
    

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
    def xml(self):
        
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
