"""Simplified interface to the tilegeo REDISAPI."""
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

# Expiration time for redis keys in seconds
REDIS_EXPIRE_SECONDS = 60 * 60 * 24  # 1-day


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
# Store text content (i.e. XML) in redis key-value db
# Returns a code string
# ####################################################################################################################################################
def redisStore(text: str,
               expire: int = REDIS_EXPIRE_SECONDS):
    
    req = requests.post(settings.REDIS_ENDPOINT, json={'text': text, 'expire': expire})
    
    code = None
    if req.status_code == 200:
        if len(req.text) > 0:
            res = json.loads(req.text)
            if 'done' in res and res['done']:
                code = res['code']
    else:
        raise InvalidAnswerException(url=settings.REDIS_ENDPOINT)
        
    return code


#####################################################################################################################################################
# Retrieve text content from a code
#####################################################################################################################################################
def redisGet(code: str):
    
    url = '%s%s'%(settings.REDIS_ENDPOINT,code)
    req = requests.get(url)
    
    text = None
    if req.status_code == 200:
        if len(req.text) > 0:
            res = json.loads(req.text)
            if 'value' in res:
                text = res['value']
    else:
        raise InvalidAnswerException(url=url)
        
    return text


#####################################################################################################################################################
# Delete a key-value record from redis db
# Return True or False
#####################################################################################################################################################
def redisDelete(code: str):
    
    url = '%s%s'%(settings.REDIS_ENDPOINT,code)
    req = requests.delete(url)
    
    result = False
    if req.status_code == 200:
        if len(req.text) > 0:
            res = json.loads(req.text)
            if 'value' in res:
                result = res['value'] is not None
    else:
        raise InvalidAnswerException(url=url)
        
    return result
