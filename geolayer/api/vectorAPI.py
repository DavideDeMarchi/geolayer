"""Simplified interface to the BDAP VECTORAPI."""
# Author(s): Davide.De-Marchi@ec.europa.eu, Edoardo.RAMALLI@ec.europa.eu
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
import json
import requests
from pathlib import Path
from osgeo import ogr

from geolayer.utility.exceptions import InvalidBDAPAnswerException

# Base URL for the Vector API calls
#VECTORAPI_URL = 'https://jeodpp.jrc.ec.europa.eu/jiplib-view-dev?VECTORAPI=1&'
VECTORAPI_URL = 'https://jeodpp.jrc.ec.europa.eu/jiplib-view?VECTORAPI=1&'


# Returns a FeatureType from a GeometryType ('Point', 'Polyline', 'Polygon' or 'Unknown')
# See: https://github.com/OSGeo/gdal/blob/8943200d5fac69f0f995fc11af7e7e3696823b37/gdal/ogr/ogr_core.h#L314-L402
def getFeatureType(geomType):
    if geomType in [ogr.wkbPoint,    ogr.wkbMultiPoint,
                    ogr.wkbPoint25D, ogr.wkbMultiPoint25D,
                    ogr.wkbPointM,   ogr.wkbMultiPointM,
                    ogr.wkbPointZM,  ogr.wkbMultiPointZM]:
        return 'Point'
    elif geomType in [ogr.wkbLineString,    ogr.wkbMultiLineString,
                      ogr.wkbLineString25D, ogr.wkbMultiLineString25D,
                      ogr.wkbLineStringM,   ogr.wkbMultiLineStringM,
                      ogr.wkbLineStringZM,  ogr.wkbMultiLineStringZM]:
        return 'Polyline'
    elif geomType in [ogr.wkbPolygon,    ogr.wkbMultiPolygon,
                      ogr.wkbPolygon25D, ogr.wkbMultiPolygon25D,
                      ogr.wkbPolygonM,   ogr.wkbMultiPolygonM,
                      ogr.wkbPolygonZM,  ogr.wkbMultiPolygonZM]:
        return 'Polygon'
    else:
        return 'Unknown'




#####################################################################################################################################################
# Returns the list of layers of a vector dataset
# Example: https://jeodpp.jrc.ec.europa.eu/jiplib-view?VECTORAPI=1&cmd=LAYERS&dataset=/eos/jeodpp/data/base/NaturalRiskZones/EUROPE/EFFIS/BurntAreas/VER1-0/Data/Spatialite/BA_effis.sqlite
#####################################################################################################################################################
def layers(filepath):
    
    res = []
    url = '%scmd=LAYERS&dataset=%s' % (VECTORAPI_URL, filepath)
    
    req = requests.get(url)
    if req.status_code == 200:
        if len(req.text) > 0:
            j = json.loads(req.text)
            res = j['layers']
    else:
        raise InvalidBDAPAnswerException(url=url)
        
    return res



#####################################################################################################################################################
# Returns info dictionary on a layer of a Dataset
# Example: https://jeodpp.jrc.ec.europa.eu/jiplib-view?VECTORAPI=1&cmd=LAYER&dataset=/eos/jeodpp/data/base/AdministrativeUnits/GLOBAL/GISCO/VER2016/Data/1M-scale/Shapefile/CNTR_BN_01M_2016_4326.shp&layer=CNTR_BN_01M_2016_4326
#####################################################################################################################################################
def layer(filepath, layer=None):
    
    if layer is None:
        layer = Path(filepath).stem
    
    res = {}
    url = '%scmd=LAYER&layer=%s&dataset=%s' % (VECTORAPI_URL, layer, filepath)
    
    req = requests.get(url)
    if req.status_code == 200:
        if len(req.text) > 0:
            j = json.loads(req.text)
            if 'extent' in j:
                res = j
                res['feature_type'] = getFeatureType(res['geom_type'])
    else:
        raise InvalidBDAPAnswerException(url=url)
        
    return res


#####################################################################################################################################################
# Returns a dictionary containing info on the fields of a layer of a Dataset
# Example: https://jeodpp.jrc.ec.europa.eu/jiplib-view?VECTORAPI=1&cmd=FIELDS&dataset=/eos/jeodpp/data/base/AdministrativeUnits/GLOBAL/GISCO/VER2016/Data/1M-scale/Shapefile/CNTR_BN_01M_2016_4326.shp&layer=CNTR_BN_01M_2016_4326
#####################################################################################################################################################
def fields(filepath, layer=None):
    
    if layer is None:
        layer = Path(filepath).stem
    
    res = {}
    url = '%scmd=FIELDS&layer=%s&dataset=%s' % (VECTORAPI_URL, layer, filepath)
    
    req = requests.get(url)
    if req.status_code == 200:
        if len(req.text) > 0:
            j = json.loads(req.text)
            for f in zip(j['fields'],j['types'],j['typesname']):
                field = {'name':     f[0],
                         'type':     f[1],
                         'typename': f[2]}
                res[f[0]] = field
    else:
        raise InvalidBDAPAnswerException(url=url)
        
    return res


#####################################################################################################################################################
# Returns info on a field of a layer of a Dataset
# Example: https://jeodpp.jrc.ec.europa.eu/jiplib-view?VECTORAPI=1&cmd=FIELD&dataset=/eos/jeodpp/data/base/AdministrativeUnits/GLOBAL/GISCO/VER2016/Data/1M-scale/Shapefile/CNTR_BN_01M_2016_4326.shp&layer=CNTR_BN_01M_2016_4326&field=CNTR_BN_ID
#####################################################################################################################################################
def field(filepath, field, layer=None):
    
    if layer is None:
        layer = Path(filepath).stem
    
    res = {}
    url = '%scmd=FIELD&layer=%s&dataset=%s&field=%s' % (VECTORAPI_URL, layer, filepath, field)
    
    req = requests.get(url)
    if req.status_code == 200:
        if len(req.text) > 0:
            res = json.loads(req.text)
    else:
        raise InvalidBDAPAnswerException(url=url)
        
    return res


#####################################################################################################################################################
# Returns the list of all values of a field of a layer of a Dataset
# Example: https://jeodpp.jrc.ec.europa.eu/jiplib-view?VECTORAPI=1&cmd=VALUES&dataset=/eos/jeodpp/data/base/AdministrativeUnits/GLOBAL/GISCO/VER2016/Data/1M-scale/Shapefile/CNTR_BN_01M_2016_4326.shp&layer=CNTR_BN_01M_2016_4326&field=CNTR_BN_ID
#####################################################################################################################################################
def values(filepath, field, layer=None):
    
    if layer is None:
        layer = Path(filepath).stem
    
    res = []
    url = '%scmd=VALUES&layer=%s&dataset=%s&field=%s' % (VECTORAPI_URL, layer, filepath, field)
    
    req = requests.get(url)
    if req.status_code == 200:
        if len(req.text) > 0:
            res = json.loads(req.text)['values']
    else:
        raise InvalidBDAPAnswerException(url=url)
        
    return res


#####################################################################################################################################################
# Returns a dictionary of all the distinct values of a field of a layer of a Dataset with their number of occurrencies
# Example: https://jeodpp.jrc.ec.europa.eu/jiplib-view?VECTORAPI=1&cmd=DISTINCT&dataset=/eos/jeodpp/data/base/AdministrativeUnits/GLOBAL/GISCO/VER2016/Data/1M-scale/Shapefile/CNTR_BN_01M_2016_4326.shp&layer=CNTR_BN_01M_2016_4326&field=CNTR_BN_ID
#####################################################################################################################################################
def distinct(filepath, field, layer=None):
    
    if layer is None:
        layer = Path(filepath).stem
    
    res = {}
    url = '%scmd=DISTINCT&layer=%s&dataset=%s&field=%s' % (VECTORAPI_URL, layer, filepath, field)
    
    req = requests.get(url)
    if req.status_code == 200:
        if len(req.text) > 0:
            res = json.loads(req.text)['distinct']
    else:
        raise InvalidBDAPAnswerException(url=url)
        
    return res


#####################################################################################################################################################
# Returns a dictionary containing statistical information on a numeric field of a layer of a Dataset with their number of occurrencies
# Example: https://jeodpp.jrc.ec.europa.eu/jiplib-view?VECTORAPI=1&cmd=STATS&dataset=/eos/jeodpp/data/base/AdministrativeUnits/GLOBAL/GISCO/VER2016/Data/1M-scale/Shapefile/CNTR_BN_01M_2016_4326.shp&layer=CNTR_BN_01M_2016_4326&field=CNTR_BN_ID
#####################################################################################################################################################
def stats(filepath, field, layer=None):
    
    if layer is None:
        layer = Path(filepath).stem
    
    res = {}
    url = '%scmd=STATS&layer=%s&dataset=%s&field=%s' % (VECTORAPI_URL, layer, filepath, field)
    
    req = requests.get(url)
    if req.status_code == 200:
        if len(req.text) > 0:
            res = json.loads(req.text)
    else:
        raise InvalidBDAPAnswerException(url=url)
        
    return res


#####################################################################################################################################################
# Identify vector features under a lat/lon point. Returns a dictionary containing the feature field values of the empty dict
# NOTE: use a tolerance in degrees greater than 0 for POINT or POLYLINE dataset layers!
# Example: https://jeodpp.jrc.ec.europa.eu/jiplib-view?VECTORAPI=1&cmd=IDENTIFY&layer=CNTR_RG_01M_2016_4326&dataset=/eos/jeodpp/data/base/AdministrativeUnits/GLOBAL/GISCO/VER2016/Data/1M-scale/Shapefile/CNTR_RG_01M_2016_4326.shp&x=12.500000&y=43.500000&tolerance=0&wantgeom=1
#####################################################################################################################################################
def identify(filepath, lon, lat, layer=None, wantGeom=False, tolerance=0.0):
    
    if layer is None:
        layer = Path(filepath).stem
    
    res = {}
    url = '%scmd=IDENTIFY&layer=%s&dataset=%s&x=%f&y=%f&wantgeom=%d&tolerance=%f' % (VECTORAPI_URL, layer, filepath, lon, lat, int(wantGeom), tolerance)
    
    req = requests.get(url)
    if req.status_code == 200:
        if len(req.text) > 0:
            res = json.loads(req.text)
    else:
        raise InvalidBDAPAnswerException(url=url)
        
    return res
