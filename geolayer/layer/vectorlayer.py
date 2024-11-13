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

# vois import
from vois import colors
from vois.vuetify import settings, textlist, palettePicker

# local import
from geolayer import classifiers
from geolayer.api import rasterAPI, vectorAPI

# Symbols dimension in pixels
SMALL_SYMBOLS_DIMENSION = 30
MEDIUM_SYMBOLS_DIMENSION = 80
LARGE_SYMBOLS_DIMENSION = 256


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
class VectorLayer:

    # Initialization for vector files (shapefiles, geopackage, etc.)
    def __init__(self,
                 filepath: str = '',
                 layer: str = '',
                 epsg: int = 4326,
                 proj: str = '',
                 # To be used for projections that do not have an EPSG code (if not empty it is used instead of the passed epsg)
                 identify_fields: list[str] = []):  # List of names of field to display on identify operation

        self.isPostgis = False
        self.isWKT = False

        self.filepath = filepath
        self.layer = layer
        self.epsg = epsg
        self.proj = proj

        self.feature_type = 'Point'

        self._identify_fields = identify_fields

        self._identify_width = '180px'

        # Store the procid (after a call to self.toLayer())
        self.procid = None

        # Symbology rules
        self.symbologyRules = []

    #####################################################################################################################################################
    # Initialization for a vector file (shapefile, geopackage, etc.)
    #####################################################################################################################################################
    @classmethod
    def file(cls,
             filepath,  # Path to the file (shapefile or geopackage, etc...)
             layer=None,  # Name of the layer (for a shapefile leave it empty)
             epsg=None,  # If None is passed, the epsg is calculated
             proj=''):  # To be used for projections that do not have an EPSG code (if not empty it is used instead of the passed epsg)

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
            wktlist,  # List of strings containing WKT of geospatial features in EPSG4326
            properties=[]):  # List of dictionaries containing the attributes of each of the feature (optional)

        instance = cls('', '', 4326, '')
        instance.isWKT = True
        instance.wktlist = wktlist
        instance.properties = properties

        if len(wktlist) > 0:
            if 'POINT' in wktlist[0]:
                instance.feature_type = 'Point'
            elif 'POLYGON' in wktlist[0]:
                instance.feature_type = 'Polygon'
            else:
                instance.feature_type = 'Polyline'

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
                proj='',
                # To be used for projections that do not have an EPSG code (if not empty it is used instead of the passed epsg)
                geomtype='Polygon',
                geometry_field='',
                geometry_table='',
                extents=''):

        instance = cls()

        instance.isPostgis = True
        instance.isWKT = False

        instance.postgis_host = host
        instance.postgis_port = port
        instance.postgis_dbname = dbname
        instance.postgis_user = user
        instance.postgis_password = password
        instance.postgis_query = query
        instance.postgis_epsg = epsg
        instance.postgis_proj = proj
        instance.postgis_geomtype = geomtype
        instance.postgis_geometry_field = geometry_field
        instance.postgis_geometry_table = geometry_table
        instance.postgis_extents = extents

        instance.feature_type = instance.postgis_geomtype

        return instance

        #####################################################################################################################################################

    # Static methods to get list of layers of a file-based vector dataset or info on a layer
    #####################################################################################################################################################

    # Returns the list of layers of a file-based vector dataset
    @staticmethod
    def layers(filepath):
        return vectorAPI.layers(filepath)

    # Returns info dictionary on a layer of a file-based vector dataset
    @staticmethod
    def layer(filepath, layer=None):
        return vectorAPI.layer(filepath, layer)

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
            return vectorAPI.field(self.filepath, field=field, layer=self.layer)

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
            return vectorAPI.values(self.filepath, field=field, layer=self.layer)

    # Returns a dictionary of all the distinct values of a field of a layer of a Dataset with their number of occurrencies
    def distinct(self, field):
        if self.isPostgis:
            return {}
        elif self.isWKT:
            return Counter(self.values(field))
        else:
            return vectorAPI.distinct(self.filepath, field=field, layer=self.layer)

    # Returns a dictionary containing statistical information on a numeric field of a layer of a Dataset with their number of occurrencies
    def stats(self, field):
        if self.isPostgis:
            return {}
        elif self.isWKT:
            values = self.values(field)
            if len(values) > 1:
                stdev = statistics.stdev(values)
            else:
                stdev = 0.0
            return {'min': min(values), 'max': max(values), 'mean': statistics.mean(values), 'stdev': stdev}
        else:
            return vectorAPI.stats(self.filepath, field=field, layer=self.layer)

    #####################################################################################################################################################
    # Symbology management
    #####################################################################################################################################################

    # Symbology reset (remove all symbol rules)
    def __symbologyReset(self):
        self.symbologyRules = []

    # Symbology remove (add a rule to remove the default symbology)
    def __symbologyRemove(self, styleName='default', ruleName='all'):
        self.symbologyRules.append(RuleModify(changeType=False, styleName=styleName, ruleName=ruleName))

    # Symbology remove (add a rule to change the symbology)
    def __symbologySet(self, styleName='default', ruleName='all', symbolizerName='', keyName='', value=''):
        self.symbologyRules.append(
            RuleModify(changeType=True, styleName=styleName, ruleName=ruleName, symbolizerName=symbolizerName,
                       keyName=keyName, value=value))

    # Remove all default symbology and all symbols added
    def symbologyClear(self, maxstyle=0):

        self.__symbologyReset()
        self.__symbologyRemove(styleName='default', ruleName='all')

        # Clear the style from 0 to 
        for stylelayer in range(maxstyle + 1):
            self.__symbologyRemove(styleName="style%d" % stylelayer, ruleName='all')

    # Apply a symbol to a subset of the features filtered by a rule ('all' applies to all features, "[attrib] = 'value'" only to a subset of the features. See https://github.com/mapnik/mapnik/wiki/Filter for filter sintax)
    def symbologyAdd(self, rule='all', symbol=[]):
        stylelayer = 0
        for layer in symbol:
            style = "style%d" % stylelayer
            # style = "default"
            for member in layer:
                symbolizer, attribute, value = member
                self.__symbologySet(style, rule, symbolizer, attribute, str(value))
            stylelayer += 1

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
        else:
            values = list(distinctValues)

        values.sort()

        self.symbologyClear()

        if interpolate:
            ci = colors.colorInterpolator(colorlist, 0.0, float(len(values) - 1.0))

        res = []
        for index, value in enumerate(values):
            if isinstance(value, float):
                description = '%G' % value
            else:
                description = str(value)

            if interpolate:
                c = ci.GetColor(float(index))
            else:
                c = colorlist[index % len(colorlist)]

            s = vectorlayer.symbolChange(symbol, color=c, fillColor=c, strokeColor=c)

            if isinstance(value, str):
                rule = "[" + fieldname + "] = '" + str(value) + "'"
            else:
                rule = '[' + fieldname + '] = ' + str(value)

            item = {'description': description, 'rule': rule, 'symbol': s}
            self.symbologyAdd(rule=rule, symbol=s)
            res.append(item)

        return res

    # Create a legend on graduated values of a numerical field
    def legendGraduated(self,
                        fieldname,
                        colorlist,
                        symbol=[],
                        allValues=None,  # All the values of the input fieldname (in case of postgis instance)
                        classifier_name='Quantiles',
                        classifier_param1=5,
                        classifier_param2=None,
                        interpolate=True,
                        markersize_min=1.0,
                        # Multiplier of markers/lines sizes to generate dimensionally graduated symbols
                        markersize_max=1.0,
                        digits=2
                        ):

        if allValues is None:
            values = list(self.values(fieldname))
        else:
            values = list(allValues)

        values = [float(x) for x in values]

        # Create the classes
        bins = vectorlayer.createClasses(values, classifier_name, classifier_param1, classifier_param2)

        res = []
        if len(bins) > 0:

            if digits >= 0:
                f = "{:.%df}" % digits
            else:
                f = "{:g}"

            # Create the color interpolator on the number of classes
            if interpolate:
                ci = colors.colorInterpolator(colorlist, 0.0, float(len(bins) - 1.0))

            if len(bins) > 1:
                markersize_step = (markersize_max - markersize_min) / float(len(bins) - 1.0)
            else:
                markersize_step = (markersize_max - markersize_min) / float(len(bins))

            multiplier = markersize_min

            # Cycle on the classes
            for index, binvalue in enumerate(bins):

                if index == 0:
                    description = '<= ' + f.format(binvalue)
                    minvalue = None
                    maxvalue = binvalue
                elif index == len(bins) - 1:
                    description = '> ' + f.format(bins[index - 1])
                    minvalue = bins[index - 1]
                    maxvalue = binvalue
                else:
                    description = f.format(bins[index - 1]) + ' - ' + f.format(binvalue)
                    minvalue = bins[index - 1]
                    maxvalue = binvalue

                if interpolate:
                    c = ci.GetColor(float(index))
                else:
                    c = colorlist[index % len(colorlist)]

                s = vectorlayer.symbolChange(symbol, color=c, fillColor=c, strokeColor=c, size_multiplier=multiplier)

                if minvalue is None:
                    rule = "[" + fieldname + "] <= " + str(maxvalue)
                elif maxvalue is None:
                    rule = "[" + fieldname + "] > " + str(minvalue)
                else:
                    rule = "[" + fieldname + "] > " + str(minvalue) + " and [" + fieldname + "] <= " + str(maxvalue)

                item = {'description': description, 'rule': rule, 'symbol': s}
                self.symbologyAdd(rule=rule, symbol=s)
                res.append(item)

                multiplier += markersize_step

        return res

    # Create the classification. Returns the bins array
    @staticmethod
    def createClasses(values,  # Array of numerical values
                      classifier_name='Quantiles',  # Classification algorithm
                      classifier_param1=5,  # First parameter for the classification algorithm
                      classifier_param2=None):  # Second parameter for the classification algorithm
        if classifier_name == 'EqualInterval':
            c = classifiers.EqualInterval(np.array(values), int(classifier_param1))
        elif classifier_name == 'BoxPlot':
            c = classifiers.BoxPlot(np.array(values))
        elif classifier_name == 'NaturalBreaks':
            c = classifiers.NaturalBreaks(np.array(values), int(classifier_param1))
        elif classifier_name == 'FisherJenksSampled':
            c = classifiers.FisherJenksSampled(np.array(values), int(classifier_param1), float(classifier_param2))
        elif classifier_name == 'StdMean':
            c = classifiers.StdMean(np.array(values), list(classifier_param1))
        elif classifier_name == 'JenksCaspallForced':
            c = classifiers.JenksCaspallForced(np.array(values), int(classifier_param1))
        elif classifier_name == 'HeadTailBreaks':
            c = classifiers.HeadTailBreaks(np.array(values))
        else:  # Quantiles
            c = classifiers.Quantiles(np.array(values), int(classifier_param1))
        # print(c)
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
        img = Image.new("RGBA", (w, h), (255, 255, 255, 255))
        draw = ImageDraw.Draw(img)

        if fontweight >= 700:
            font = ImageFont.truetype('fonts/Roboto-Black.ttf', fontsize)
        elif fontweight >= 600:
            font = ImageFont.truetype('fonts/Roboto-Bold.ttf', fontsize)
        elif fontweight >= 500:
            font = ImageFont.truetype('fonts/Roboto-Medium.ttf', fontsize)
        elif fontweight >= 400:
            font = ImageFont.truetype('fonts/Roboto-Regular.ttf', fontsize)
        elif fontweight >= 300:
            font = ImageFont.truetype('fonts/Roboto-Light.ttf', fontsize)
        else:
            font = ImageFont.truetype('fonts/Roboto-Thin.ttf', fontsize)

        xi = border
        xt = dim + border * 3
        for index, item in enumerate(legend):
            y = border + index * dim
            yt = y + (dim - fontsize) / 2
            imgItem = symbol2Image(item['symbol'], size=size, clipdimension=clipdimension, feature=self.feature_type)
            img.paste(imgItem, (xi, y))
            draw.text((xt, yt), item['description'], textcolor, font=font)

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
            legendtitle = v.Subheader(children=[title], style_='font-size: 14px; font-weight: 700; color: black;',
                                      class_='pa-0 ma-0 mb-n2')
        else:
            legendtitle = ''

        items = []
        for index, item in enumerate(legend):
            img = symbol2Image(item['symbol'], size=size, feature=self.feature_type)
            url = palettePicker.image2Base64(img)
            vimg = v.Img(src=url)
            icon = v.ListItemIcon(style_='height: %dpx;' % dim, children=[vimg], class_='pa-0 ma-0 ml-n3 mt-2 mr-2')

            item_title = v.ListItemTitle(children=[item['description']])
            content = v.ListItemContent(children=[item_title], class_='pa-0 ma-0 mt-1')

            listitem = v.ListItem(children=[icon, content], value=index, dense=True, disabled=disabled,
                                  style_='color: black;')
            if onclick is not None and not disabled: listitem.on_event('click', onclick)
            items.append(listitem)

        legendgroup = v.ListItemGroup(v_model=None, color=settings.color_first, children=items)

        if len(title) > 0:
            return v.List(dense=True, children=[legendtitle, legendgroup])
        else:
            return v.List(dense=True, children=[legendgroup])

    #####################################################################################################################################################
    # Static method to instantiate a parametric symbol
    #####################################################################################################################################################

    # Change color and other properties of a symbol and returns the modified symbol
    @staticmethod
    def symbolChange(symbol, color='#ff0000', fillColor='#ff0000', fillOpacity=1.0, strokeColor='#ffff00',
                     strokeWidth=0.5, scalemin=None, scalemax=None, size_multiplier=1.0):
        newsymbol = []
        for layer in symbol:
            newlayer = []
            for member in layer:
                symbolizer, attribute, value = member

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

                if size_multiplier != 1.0:
                    if symbolizer == 'MarkersSymbolizer' and (attribute == 'width' or attribute == 'height'):
                        value = float(value) * multiplier

                    if symbolizer == 'LineSymbolizer' and attribute == 'stroke-width':
                        value = float(value) * multiplier

                if not value is None:
                    newlayer.append((symbolizer, attribute, value))

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
            print("BDAP vector layer POSTGIS:")
            print("   procid:         %s" % str(self.procid))
            print("   host:           %s" % self.postgis_host)
            print("   port:           %d" % self.postgis_port)
            print("   dbname:         %s" % self.postgis_dbname)
            print("   user:           %s" % self.postgis_user)
            print("   password:       %s" % self.postgis_password)
            print("   query:          %s" % self.postgis_query)
            print("   epsg:           %d" % self.epsg)
            print("   proj:           %s" % self.proj)
            print("   geomtype:       %s" % self.postgis_geomtype)
            print("   geometry_field: %s" % self.postgis_geometry_field)
            print("   geometry_table: %s" % self.postgis_geometry_table)
            print("   extents:        %s" % self.postgis_extents)
        elif self.isWKT:
            print("BDAP vector layer WKT:")
            print("   wktlist:        %s" % str(self.wktlist))
            print("   properties:     %s" % str(self.properties))
        else:
            print("BDAP vector layer FILE:")
            print("   procid:         %s" % str(self.procid))
            print("   filepath:       %s" % self.filepath)
            print("   layer:          %s" % self.layer)
            print("   epsg:           %d" % self.epsg)
            print("   proj:           %s" % self.proj)

        print("   symbology:")
        for rule in self.symbologyRules:
            print("       %s" % rule.print())

    #####################################################################################################################################################
    # Identify methods
    #####################################################################################################################################################

    # Identify: returns a string
    def identify(self, lon, lat, zoom):
        while lon < -180.0: lon += 360.0
        while lon > 180.0: lon -= 360.0
        url = 'https://jeodpp.jrc.ec.europa.eu/jiplib-view/?IDENTIFYEX=1&vl=%s&x=%f&y=%f&epsg=%d&zoom=%d' % (
        self.toLayer(), lon, lat, 4326, int(zoom))
        # print(url)
        response = requests.get(url)
        bio = BytesIO(response.content)
        s = bio.read()
        svalue = s.decode("utf-8").replace('Values = ', '').replace('Value = ', '')
        return svalue

    # onclick called by a Map.Map instance
    def onclick(self, m, lon, lat, zoom):
        res = self.identify(lon, lat, zoom)
        if not res is None and len(res) > 0:
            if '#' in res:
                descriptions = self._identify_fields
                values = res.split('#')
            else:
                if ', ' in res:
                    attribs = res.split(', ')

                    descriptions = []
                    values = []
                    for attrib in attribs:
                        s = attrib.split('=')
                        if len(s) >= 2:
                            descriptions.append(s[0])
                            values.append(s[1])
                else:
                    descriptions = ['Attributes']
                    values = [res]

            t = textlist.textlist(descriptions, values,
                                  titlefontsize=10,
                                  textfontsize=11,
                                  titlecolumn=4,
                                  textcolumn=8,
                                  titlecolor='#000000',
                                  textcolor='#000000',
                                  lineheightfactor=1.1)

            t.card.width = self._identify_width
            popup = ipyleaflet.Popup(location=[lat, lon], child=t.draw(), auto_pan=False, close_button=True,
                                     auto_close=True, close_on_escape_key=True)
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
    def tileLayer(self, max_zoom=22):
        url = self.tileUrl()
        if not url is None:
            return ipyleaflet.TileLayer(url=url, max_zoom=max_zoom, max_native_zoom=max_zoom)

    #####################################################################################################################################################
    # Internal functions
    #####################################################################################################################################################

    # Returns the url to display the layer
    def tileUrl(self):
        procid = self.toLayer()
        if not procid is None:
            tileBaseUrl = 'https://jeodpp.jrc.ec.europa.eu/jiplib-view'
            return tileBaseUrl + "?x={x}&y={y}&z={z}&procid=%s" % procid

    # Save the layer in Redis and returns the procid
    def toLayer(self):
        j = self.toJson()
        strjson = json.dumps(j)
        self.procid = rasterAPI.saveLayer(strjson)
        return self.procid

    # Return the JSON representation of the vector layer
    def toJson(self):
        filelinkproj = "+init=epsg:%d" % self.epsg
        if self.proj is not None and len(self.proj) > 0:
            filelinkproj = self.proj

        filelinklayer = self.layer
        if len(filelinklayer) == 0:
            path, file = os.path.split(self.filepath)
            filelinklayer = file.rsplit('.', 1)[0]

        j = {'AbsolutePath': '',
             'Collection': 1002,
             'CustomXML': '',
             'Description': '',
             'HeatmapMode': 0,
             'HeatmapQuery': '',
             'HeatmapRadius': 0,
             'HeatmapWeightField': '',
             'HeatmapWeightMax': 1000000,
             'HeatmapWeightMin': -1000000,
             'IdentifyAll': 0,
             'IdentifyDigits': -1,
             'IdentifyField': '',
             'IdentifyFilter': '',
             'IdentifySeparator': '#',
             'IdentifySortField': '',
             'Name': 'wkt',
             'POSTGIS_dbname': '',
             'POSTGIS_epsg': 4326,
             'POSTGIS_extents': '',
             'POSTGIS_geometry_field': '',
             'POSTGIS_geometry_table': '',
             'POSTGIS_geomtype': 'Polygon',
             'POSTGIS_host': '',
             'POSTGIS_password': '',
             'POSTGIS_port': 0,
             'POSTGIS_query': '',
             'POSTGIS_user': '',
             'Raster_XML': '',
             'Raster_band': 1,
             'Raster_colors': '#000000,#ffffff',
             'Raster_epsgcode': 4326,
             'Raster_file': '',
             'Raster_interpolate': 'near',
             'Raster_nodata': 0,
             'Raster_scalemax': 255,
             'Raster_scalemin': 0,
             'ScaleResolution': 1,
             'filelinklayer': '',
             'filelinkpath': '',
             'filelinkproj': '',
             'joins': None,
             'modify': None,
             'opacity': 255,
             'properties': None,
             'wkt': None}

        # Set the filestamp
        j['filelinktimestamp'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Set the identify fields
        if isinstance(self._identify_fields, list):
            if len(self._identify_fields) > 0:
                j['IdentifyField'] = ' '.join(self._identify_fields)

        # Rules to modify the symbology
        j["modify"] = [x.toJson() for x in self.symbologyRules]

        # Add specific settings of the three formats
        if self.isPostgis:
            j["Name"] = "postgis"
            j["POSTGIS_host"] = self.postgis_host
            j["POSTGIS_port"] = self.postgis_port
            j["POSTGIS_dbname"] = self.postgis_dbname
            j["POSTGIS_user"] = self.postgis_user
            j["POSTGIS_password"] = self.postgis_password
            j["POSTGIS_query"] = self.postgis_query
            j["POSTGIS_epsg"] = self.postgis_epsg
            j["POSTGIS_proj"] = self.postgis_proj
            j["POSTGIS_geomtype"] = self.postgis_geomtype
            j["POSTGIS_geometry_field"] = self.postgis_geometry_field
            j["POSTGIS_geometry_table"] = self.postgis_geometry_table
            j["POSTGIS_extents"] = self.postgis_extents
        elif self.isWKT:
            j["Name"] = "wkt"
            j["wkt"] = self.wktlist
            while len(self.properties) < len(self.wktlist): self.properties.append({})
            j["properties"] = [str(x).replace("'", '"') for x in self.properties]
        else:
            j["Name"] = "wkt"
            j["filelinklayer"] = filelinklayer
            j["filelinkpath"] = self.filepath
            j["filelinkproj"] = filelinkproj

        return j


#####################################################################################################################################################
# Generate an image from a symbol
#####################################################################################################################################################
def symbol2Image(symbol=[], size=1, feature='Point', clipdimension=999, showborder=False):
    doclip = False
    if feature == 'Line' or feature == 'Polyline':
        if size >= 3:
            wkt = 'LINESTRING (-170 82, -100 55, -60 70, -10 38)'
        elif size == 2:
            wkt = 'LINESTRING (-175 83, -158 81, -148 83, -129 81)'
        else:
            wkt = 'LINESTRING (-177 84.45, -171 83.9, -167.4 84.25, -161 83.75)'
    elif feature == 'Polygon':
        if size >= 3:
            wkt = 'POLYGON ((-170 83.85, -170 10, -10 10, -10 83.85, -170 83.85))'
        elif size == 2:
            wkt = 'POLYGON ((-175 84.5, -175 78, -128.5 78, -128.5 84.5, -175 84.5))'
        else:
            wkt = 'POLYGON ((-178 84.85, -178 83.2, -160.5 83.2, -160.5 84.85, -178 84.85))'
    else:
        if size >= 3:
            wkt = 'POINT (-90 65)'
        elif size == 2:
            wkt = 'POINT (-152 82)'
        else:
            wkt = 'POINT (-169.52 84.05)'

    if size >= 3:
        if clipdimension < LARGE_SYMBOLS_DIMENSION:
            doclip = True
    elif size == 2:
        if clipdimension < MEDIUM_SYMBOLS_DIMENSION:
            doclip = True
    else:
        if clipdimension < SMALL_SYMBOLS_DIMENSION:
            doclip = True

    vlayer = vectorlayer.wkt([wkt])
    vlayer.symbologyClear()
    vlayer.symbologyAdd(symbol=symbol)
    # print(vlayer.toJson())

    url = 'https://jeodpp.jrc.ec.europa.eu/jiplib-view?x=0&y=0&z=1&procid=%s' % vlayer.toLayer()
    response = requests.get(url)

    if len(response.content) > 5 and response.content[0] == 137 and response.content[1] == 80 and response.content[
        2] == 78 and response.content[3] == 71 and response.content[4] == 13:
        img = Image.open(BytesIO(response.content))
        if size >= 3:
            img = img.crop((0, 0, LARGE_SYMBOLS_DIMENSION, LARGE_SYMBOLS_DIMENSION))
        elif size == 2:
            img = img.crop((0, 0, MEDIUM_SYMBOLS_DIMENSION, MEDIUM_SYMBOLS_DIMENSION))
        else:
            img = img.crop((0, 0, SMALL_SYMBOLS_DIMENSION, SMALL_SYMBOLS_DIMENSION))

        if doclip:
            s = img.size
            cx = s[0] / 2
            cy = s[1] / 2
            img = img.crop(
                (cx - clipdimension / 2, cy - clipdimension / 2, cx + clipdimension / 2, cy + clipdimension / 2))
    else:
        print('URL with errors:', url)
        if size >= 3:
            img = Image.new("RGB", (LARGE_SYMBOLS_DIMENSION, LARGE_SYMBOLS_DIMENSION), (255, 255, 255))
        elif size == 2:
            img = Image.new("RGB", (MEDIUM_SYMBOLS_DIMENSION, MEDIUM_SYMBOLS_DIMENSION), (255, 255, 255))
        else:
            img = Image.new("RGB", (SMALL_SYMBOLS_DIMENSION, SMALL_SYMBOLS_DIMENSION), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((0, 0), "Error", (0, 0, 0))

    # Add a thin black border
    if showborder:
        draw = ImageDraw.Draw(img)
        s = img.size
        draw.rectangle(((0, 0), (s[0] - 1, s[1] - 1)), outline='black')

    return img


#####################################################################################################################################################
# RuleModify class: modification to a symbology rule (see interapro VectorLayer.cpp)
#####################################################################################################################################################
class RuleModify():

    # Initialization
    def __init__(self,
                 changeType,  # If true it is a change rule, if False a remove rule
                 styleName,
                 ruleName,
                 symbolizerName='',
                 keyName='',
                 value=''):

        self.changeType = changeType
        self.styleName = styleName
        self.ruleName = ruleName
        self.symbolizerName = symbolizerName
        self.keyName = keyName
        self.value = value

    # Return a string showing the rule members
    def print(self):
        if self.changeType:
            return 'type: CHANGE    style: %-10s    rule: %-20s    symbolizer: %-20s     key: %-16s    value: %-20s' % (
            self.styleName, self.ruleName, self.symbolizerName, self.keyName, self.value)
        else:
            return 'type: REMOVE    style: %-10s    rule: %-20s' % (self.styleName, self.ruleName)

    # Serialization to Json
    def toJson(self):
        jsonobj = {}

        if self.changeType:
            jsonobj["type"] = 0  # Change rule
        else:
            jsonobj["type"] = 1  # Remove rule

        jsonobj["style"] = self.styleName
        jsonobj["rule"] = self.ruleName

        if self.changeType:
            jsonobj["symbolizer"] = self.symbolizerName
            jsonobj["key"] = self.keyName
            jsonobj["value"] = self.value

        return jsonobj
