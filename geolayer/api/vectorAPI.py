"""Simplified interface to the tilegeo VECTORAPI."""
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
import json
import requests
from pathlib import Path

# geolayer import
from geolayer import settings


# Returns a FeatureType from a GeometryType ('Point', 'Polyline', 'Polygon' or 'Unknown')
# See: https://github.com/OSGeo/gdal/blob/8943200d5fac69f0f995fc11af7e7e3696823b37/gdal/ogr/ogr_core.h#L314-L402
def getFeatureType(geomTypeName):
    if 'Point' in geomTypeName:
        return 'Point'
    elif 'LineString' in geomTypeName:
        return 'Polyline'
    elif 'Polygon' in geomTypeName:
        return 'Polygon'
    else:
        return 'Unknown'

    

#####################################################################################################################################################
# Python user-defined exceptions
#####################################################################################################################################################

# Bad answer from a HTTP(S) request
class InvalidAnswerException(Exception):
    "Raised when tilegeo server fails to answer"

    def __init__(self, url, data=''):
        self.message = 'tilegeo failed to correctly execute the command: ' + str(url)
        if len(data) > 0:
            self.message += '\nData: ' + str(data)
        super().__init__(self.message)    



#####################################################################################################################################################
# Returns the list of layers of a vector dataset
# Example: https://jeodpp.jrc.ec.europa.eu/jiplib-view?VECTORAPI=1&cmd=LAYERS&dataset=/eos/jeodpp/data/base/NaturalRiskZones/EUROPE/EFFIS/BurntAreas/VER1-0/Data/Spatialite/BA_effis.sqlite
#####################################################################################################################################################
def layers(dataset_path : str):
    
    url = '%slayers'%settings.VECTOR_ENDPOINT
    req = requests.get(url, params={'dataset_path': dataset_path})
    
    res = {}
    if req.status_code == 200:
        if len(req.text) > 0:
            res = json.loads(req.text)
        else:
            res = {}
    else:
        raise InvalidAnswerException(url=req.url)
        
    return res



#####################################################################################################################################################
# Returns info dictionary on a layer of a Dataset
# Example: https://jeodpp.jrc.ec.europa.eu/jiplib-view?VECTORAPI=1&cmd=LAYER&dataset=/eos/jeodpp/data/base/AdministrativeUnits/GLOBAL/GISCO/VER2016/Data/1M-scale/Shapefile/CNTR_BN_01M_2016_4326.shp&layer=CNTR_BN_01M_2016_4326
#####################################################################################################################################################
def layer(dataset_path : str,
          layer_name = None):
    
    if layer_name is None:
        layer_name = Path(dataset_path).stem
    
    url = '%slayer'%settings.VECTOR_ENDPOINT
    req = requests.get(url, params={'dataset_path': dataset_path,
                                    'layer_name':   layer_name})
    
    res = {}
    if req.status_code == 200:
        if len(req.text) > 0:
            res = json.loads(req.text)
            
            if 'geom_type_name' in res:
                res['feature_type'] = getFeatureType(res['geom_type_name'])
        else:
            res = {}
    else:
        raise InvalidAnswerException(url=req.url)
        
    return res


#####################################################################################################################################################
# Returns a dictionary containing info on the fields of a layer of a Dataset
# Example: https://jeodpp.jrc.ec.europa.eu/jiplib-view?VECTORAPI=1&cmd=FIELDS&dataset=/eos/jeodpp/data/base/AdministrativeUnits/GLOBAL/GISCO/VER2016/Data/1M-scale/Shapefile/CNTR_BN_01M_2016_4326.shp&layer=CNTR_BN_01M_2016_4326
#####################################################################################################################################################
def fields(dataset_path : str,
           layer_name = None):
    
    if layer_name is None:
        layer_name = Path(dataset_path).stem
    
    url = '%sfields'%settings.VECTOR_ENDPOINT
    req = requests.get(url, params={'dataset_path': dataset_path,
                                    'layer_name':   layer_name})
    res = {}
    if req.status_code == 200:
        if len(req.text) > 0:
            j = json.loads(req.text)
            for f in zip(j['fields'],j['types'],j['types_name']):
                field = {'name':     f[0],
                         'type':     f[1],
                         'typename': f[2]}
                res[f[0]] = field
        else:
            res = {}
    else:
        raise InvalidAnswerException(url=req.url)
        
    return res


#####################################################################################################################################################
# Returns info on a field of a layer of a Dataset
#####################################################################################################################################################
def field(dataset_path : str,
          field_name : str,
          layer_name = None):
    
    if layer_name is None:
        layer_name = Path(dataset_path).stem
    
    url = '%sfield'%settings.VECTOR_ENDPOINT
    req = requests.get(url, params={'dataset_path': dataset_path,
                                    'layer_name':   layer_name,
                                    'field_name':   field_name})
    res = {}
    if req.status_code == 200:
        if len(req.text) > 0:
            res = json.loads(req.text)
    else:
        raise InvalidAnswerException(url=req.url)
        
    return res


#####################################################################################################################################################
# Returns the list of all values of a field of a layer of a Dataset
#####################################################################################################################################################
def values(dataset_path : str,
           field_name : str,
           layer_name = None):
    
    if layer_name is None:
        layer_name = Path(dataset_path).stem
    
    url = '%svalues'%settings.VECTOR_ENDPOINT
    req = requests.get(url, params={'dataset_path': dataset_path,
                                    'layer_name':   layer_name,
                                    'field_name':   field_name})
    res = {}
    if req.status_code == 200:
        if len(req.text) > 0:
            res = json.loads(req.text)
            if 'values' in res:
                res = res['values']
    else:
        raise InvalidAnswerException(url=req.url)
        
    return res


#####################################################################################################################################################
# Returns a dictionary of all the distinct values of a field of a layer of a Dataset with their number of occurrencies
#####################################################################################################################################################
def distinct(dataset_path : str,
             field_name : str,
             layer_name = None):
    
    if layer_name is None:
        layer_name = Path(dataset_path).stem
    
    url = '%sdistinct'%settings.VECTOR_ENDPOINT
    req = requests.get(url, params={'dataset_path': dataset_path,
                                    'layer_name':   layer_name,
                                    'field_name':   field_name})
    res = {}
    if req.status_code == 200:
        if len(req.text) > 0:
            res = json.loads(req.text)
            if 'distinct' in res:
                res = res['distinct']
    else:
        raise InvalidAnswerException(url=req.url)
        
    return res


#####################################################################################################################################################
# Returns a dictionary containing statistical information on a numeric field of a layer of a Dataset with their number of occurrencies
#####################################################################################################################################################
def stats(dataset_path : str,
          field_name : str,
          layer_name = None):
    
    if layer_name is None:
        layer_name = Path(dataset_path).stem
    
    url = '%sstats'%settings.VECTOR_ENDPOINT
    req = requests.get(url, params={'dataset_path': dataset_path,
                                    'layer_name':   layer_name,
                                    'field_name':   field_name})
    res = {}
    if req.status_code == 200:
        if len(req.text) > 0:
            res = json.loads(req.text)
    else:
        raise InvalidAnswerException(url=req.url)
        
    return res


#####################################################################################################################################################
# Identify vector features under a lat/lon point. Returns a dictionary containing the feature field values or the empty dict
# NOTE: use a tolerance in degrees greater than 0 for POINT or POLYLINE dataset layers!
#####################################################################################################################################################
def identify(dataset_path : str,
             lon : float,
             lat : float,
             layer_name = None,
             geom : bool = False,
             tolerance : float = 0.0):
    
    if layer_name is None:
        layer_name = Path(dataset_path).stem
    
    url = '%sidentify'%settings.VECTOR_ENDPOINT
    req = requests.get(url, params={'dataset_path': dataset_path,
                                    'layer_name':   layer_name,
                                    'lon':          lon,
                                    'lat':          lat,
                                    'geom':         geom,
                                    'tolerance':    tolerance,
                                   })

    res = {}
    if req.status_code == 200:
        if len(req.text) > 0:
            res = json.loads(req.text)
    else:
        raise InvalidAnswerException(url=req.url)
        
    return res
