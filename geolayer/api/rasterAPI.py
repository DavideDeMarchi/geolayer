"""Simplified interface to the tilegeo RASTERAPI."""
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

# geolayer import
from geolayer import settings


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
# Query information on a raster file giving its server side full path
#####################################################################################################################################################
def rasterInfo(dataset_path   : str,
               request_stats  : bool = False,
               detailed_stats : bool = False):
    
    url = '%sinfo'%settings.RASTER_ENDPOINT
    req = requests.get(url, params={'dataset_path': dataset_path,
                                    'stats':        request_stats,
                                    'detailed':     detailed_stats})
    
    if req.status_code == 200:
        if len(req.text) > 0:
            info = json.loads(req.text)
        else:
            info = {}
    else:
        raise InvalidAnswerException(url=url)
        
    return info


#####################################################################################################################################################
# Identify a pixel of a raster band
#####################################################################################################################################################
def rasterIdentify(dataset_path: str,
                   band: int = 1,
                   epsg: int = None,
                   lon: float = 0.0,
                   lat: float = 0.0):
    
    url = '%sidentify'%settings.RASTER_ENDPOINT
    req = requests.get(url, params={'dataset_path': dataset_path,
                                    'band': band,
                                    'epsg': epsg,
                                    'lon':  lon,
                                    'lat':  lat,
                                   })
    
    if req.status_code == 200:
        if len(req.text) > 0:
            res = json.loads(req.text)
        else:
            res = {}
    else:
        raise InvalidAnswerException(url=url)
        
    return res

        
#####################################################################################################################################################
# Query raster. Read raster value at some points in geographic coordinates
#####################################################################################################################################################
def rasterQuery(dataset_path: str, 
                band: int = 1,
                epsg: int = None,
                lon = list[float],
                lat = list[float]):
    
    j = { "lon": list(lon), "lat": list(lat) }
    strjson = json.dumps(j)
    
    url = '%squery'%settings.RASTER_ENDPOINT
    req = requests.get(url,
                       params={'dataset_path': dataset_path,
                               'band': band,
                               'epsg': epsg},
                       data=strjson)
    
    if req.status_code == 200:
        if len(req.text) > 0:
            res = json.loads(req.text)
        else:
            res = {}
    else:
        raise InvalidAnswerException(url=url)
        
    return res



        