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
        return vectorAPI.layers(dataset_path)

    
    # Returns info dictionary on a layer of a file-based vector dataset
    @staticmethod
    def layer(dataset_path : str, layer_name : str = None):
        return vectorAPI.layer(dataset_path, layer_name)
    
    
    #####################################################################################################################################################
    # Info on fields and their values (only for file and wkt)
    #####################################################################################################################################################

    # Returns a dictionary containing info on the fields of a layer of a Dataset
    def fields(self):
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
        if self.isPostgis:
            return {}
        elif self.isWKT:
            return {}
        else:
            return vectorAPI.field(self.filepath, field_name=field, layer_name=self.layer)

        
    # Returns the list of all values of a field of a layer of a Dataset
    def values(self, field):
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
        if self.isPostgis:
            return {}
        elif self.isWKT:
            return Counter(self.values(field))
        else:
            return vectorAPI.distinct(self.filepath, field_name=field, layer_name=self.layer)

        
    # Returns a dictionary containing statistical information on a numeric field of a layer of a Dataset with their number of occurrencies
    def stats(self, field):
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
        self.rules = {}
            
    # Apply a symbol to a subset of the features filtered by a rule ('all' applies to all features, "[attrib] = 'value'" only to a subset of the features. See https://github.com/mapnik/mapnik/wiki/Filter for filter sintax)
    def symbologyAdd(self, rule='all', symbol=[]):
        self.rules[rule] = symbol
        

    #####################################################################################################################################################
    # Legend creation. A Legend is a list of dictionaries, each one repredenting an item of the legend, containing description, rule and symbol
    #####################################################################################################################################################

    # Create a legend using a single symbol for all the features
    def legendSingle(self,
                     symbol=[],
                     description=''):
        
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
        if self.isPostgis:
            print("TILEGEO vector layer POSTGIS:")
            print("   procid:         %s"%str(self.procid))
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
            print("   procid:         %s"%str(self.procid))
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
        while lon < -180.0: lon += 360.0
        while lon >  180.0: lon -= 360.0
        
        res = vectorAPI.identify(self.filepath, layer_name=self.layer, lon=lon, lat=lat, tolerance=tolerance, geom=True)
        return res
        

    # onclick called by a Map.Map instance
    def onclick(self, m, lon, lat, zoom):
        
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
        return self._identify_fields
        
    @identify_fields.setter
    def identify_fields(self, listofattributes):
        self._identify_fields = listofattributes
                

    @property
    def identify_width(self):
        return self._identify_width
        
    @identify_width.setter
    def identify_width(self, width):
        self._identify_width = width

        
    #####################################################################################################################################################
    # Create an ipyleaflet.TileLayer
    #####################################################################################################################################################
    
    # Returns an instance of ipyleaflet.TileLayer
    def tileLayer(self, max_zoom=22, file_format='png'):
        url = self.tileUrl(file_format=file_format)
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
    def xml(self, compositing='src-over'):
        
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
    