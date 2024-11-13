"""Simplified interface to the BDAP RASTERAPI."""
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
import json
import requests

# Base URL for the Raster API calls
#RASTERAPI_URL = 'https://jeodpp.jrc.ec.europa.eu/jiplib-view-dev/?RASTERAPI=1&'
RASTERAPI_URL = 'https://jeodpp.jrc.ec.europa.eu/jiplib-view/?RASTERAPI=1&'


#####################################################################################################################################################
# Python user-defined exceptions
#####################################################################################################################################################

# Bad answer from a BDAP HTTP(S) request
class InvalidBDAPAnswerException(Exception):
    "Raised when BDAP server fails to answer"

    def __init__(self, url, data=''):
        self.message = 'BDAP failed to correctly execute the command: ' + str(url)
        if len(data) > 0:
            self.message += '\nData: ' + str(data)
        super().__init__(self.message)    



#####################################################################################################################################################
# Query information on a raster file giving its server side full path
# Example: https://jeodpp.jrc.ec.europa.eu/jiplib-view/?RASTERAPI=1&cmd=INFO&filepath=/eos/jeodpp/data/base/Landcover/GLOBAL/UMD/GFC/VER1-7/Data/VRT/first/Hansen_GFC-2019-v1.7_first.vrt
#####################################################################################################################################################
def rasterInfo(filepath, request_stats=False, detailed_stats=False, NoneReplace=-1.0, nanReplace=-1.0):
    
    url = '%scmd=INFO&filepath=%s'%(RASTERAPI_URL, filepath)
    
    # Calculate approximate stats without scanning all the pixels!
    if request_stats:
        url += '&STATS=1'
        
        if detailed_stats:
            url += '&DETAILED=1'
        
    req = requests.get(url)
    if req.status_code == 200:
        if len(req.text) > 0:
            #info = json.loads(req.text.replace('\'','"').replace('None','"None"'))
            info = json.loads(req.text.replace('\'','"').replace('None','%f'%NoneReplace).replace('nan','%f'%nanReplace).replace('-inf','%f'%nanReplace))
        else:
            info = {}    # In case the file is not existant!
    else:
        raise InvalidBDAPAnswerException(url=url)
        
    return info



#####################################################################################################################################################
# Save a layer definition on REDIS server and returns a procid string
#####################################################################################################################################################
def saveLayer(strjson):
    url = '%scmd=TOLAYER'%RASTERAPI_URL

    req = requests.get(url, data=strjson)
    procid = None
    if req.status_code == 200:
        procid = str(req.text)
    else:
        raise InvalidBDAPAnswerException(url=url,data=strjson)
        
    return procid



#####################################################################################################################################################
# Calculate occurrencies of a raster band and returns a dictionary
# Example: https://jeodpp.jrc.ec.europa.eu/jiplib-view/?RASTERAPI=1&cmd=OCCURRENCIES&filepath=/eos/jeodpp/data/products/Landcover/EUROPE/EUCROPMAP/VER2022-1/Data/VRT/JRC_EUROCROPMAP2022_EU27_EPSG3035.vrt&band=1&epsg=3035&nodata=0.0&lon1=12.5&lon2=12.6&lat1=43.5&lat2=43.6&zoom=12
#####################################################################################################################################################
def rasterOccurrencies(filepath,
                       lonmin,
                       latmin,
                       lonmax,
                       latmax,
                       zoom,
                       band=1,
                       epsg=4326,
                       nodata=0.0):
    
    url = '%scmd=OCCURRENCIES&filepath=%s&band=%d&epsg=%d&nodata=%f&lon1=%f&lon2=%f&lat1=%f&lat2=%f&zoom=%d'%(RASTERAPI_URL, filepath, band, epsg, nodata, lonmin, lonmax, latmin, latmax, zoom)
    
    req = requests.get(url)
    if req.status_code == 200:
        import ast
        return ast.literal_eval(req.text)
    else:
        raise InvalidBDAPAnswerException(url=url)

        
#####################################################################################################################################################
# Query raster. Read raster value at some points in geographic coordinates
#####################################################################################################################################################
def rasterQuery(filepath, band=1, lon=[], lat=[], NoneReplace=-1.0, nanReplace=-1.0, epsg=None):
    
    url = '%scmd=QUERY&filepath=%s&band=%d'%(RASTERAPI_URL, filepath, band)
    
    if not epsg is None:
        url += '&epsg=%d'%int(epsg)
    
    j = { "lon": list(lon), "lat": list(lat) }
    strjson = json.dumps(j)
    
    req = requests.get(url, data=strjson)
    if req.status_code == 200:
        return json.loads(req.text.replace('\'','"').replace('None','%f'%NoneReplace).replace('nan','%f'%nanReplace).replace('-inf','%f'%nanReplace))
    else:
        raise InvalidBDAPAnswerException(url=url)



        