"""
Simplified interface to the tilegeo VRTAPI.
"""
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
# ####################################################################################################################################################

# Bad answer from a HTTP(S) request
class InvalidAnswerException(Exception):
    "Raised when tilegeo server fails to answer"

    def __init__(self, url, data=''):
        self.message = 'tilegeo failed to correctly execute the command: ' + str(url)
        if len(data) > 0:
            self.message += '\nData: ' + str(data)
        super().__init__(self.message)    



#####################################################################################################################################################
# Store text content (i.e. VRT files) in a temporary server folder
# Returns a json containing file_path and the corresponding code
# ####################################################################################################################################################
def vrtStore(vrt_string: str):
    
    req = requests.post(settings.VRT_ENDPOINT, json={'vrt_string': vrt_string})
    
    res = {}
    if req.status_code == 200:
        if len(req.text) > 0:
            res = json.loads(req.text)
    else:
        raise InvalidAnswerException(url=settings.VRT_ENDPOINT)
        
    return res


#####################################################################################################################################################
# Retrieve text content from a code
# ####################################################################################################################################################
def vrtGet(code: str):
    
    url = '%s%s'%(settings.VRT_ENDPOINT,code)
    req = requests.get(url)
    
    res = {}
    if req.status_code == 200:
        if len(req.text) > 0:
            res = json.loads(req.text)
    else:
        raise InvalidAnswerException(url=url)
        
    return res
