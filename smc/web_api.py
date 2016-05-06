'''
Created on May 1, 2016

@author: davidlepage
'''

import sys, json, requests
import logging

logger = logging.getLogger(__name__)
        
#only meant to be used in the module
api_entry = None
smc_url = None
session = None   

class SMCResult(object):
    def __init__(self, result, etag):
        self.etag = etag
        self.msg = self.get(result)
        
    def get(self, result):
        if 'result' in result:
            self.msg = result['result']
        else:
            self.msg = result
        
class OperationFailure(Exception):
    def __init__(self, http_code, error):
        self.msg = self.extract(error)
        self.http = http_code
        
    def extract(self, error):
        print error
     
            
def get_api_entry(url, api_version=None):
    global api_entry, smc_url
    try:
        if api_version is None:
            r = requests.get('%s/api' % url) #no session required
            j = json.loads(r.text)
            versions = []
            for version in j['version']:
                versions.append(version['rel'])
            api_version = max(versions)
        
        #else api_version was defined
        logger.info("Using SMC API version: %s" % api_version)
        smc_url = url + '/' + api_version
  
        r = requests.get('%s/api' % (smc_url))
        if r.status_code==200:
            j = json.loads(r.text)
            logger.debug("Successfully retrieved API entry points from SMC")
        else:
            raise Exception("Error occurred during initial api request, json was not returned. Return data was: %s" % r.text)
        api_entry = j['entry_point']
            
    except requests.exceptions.RequestException as e:
        raise Exception("Connection problem to SMC, ensure the API service is running and host is correct: %s, exiting." % e)
        
        
def get_entry_href(verb):
    """ Returns the API entry point cache for the specified verb.
        Call get_all_entry_points to find all available entry points 
        Args: 
            * verb: top level entry point into SMC api
    """    
    if api_entry:
        for entry in api_entry:
            if entry['rel'] == verb:
                return entry['href']
    else:
        raise Exception("No entry points found, it is likely there is no valid login session.")
 
            
def get_all_entry_points(): #for callers outside of the module
    """ Returns all entry points into SMC api """   
    return api_entry


def http_get(href):
    """ Get data object from SMC
        If response code is success, results are returned with etag
        Args:
            * href: fully qualified href for resource
    """   
    try:
        if session:
            r = session.get(href)
            j = json.loads(r.text)
            if r.status_code==200:
                return j
                #return ResultObject(j, r.headers['ETag'])
        else:
            print "No session found. Please login to continue"
            sys.exit()
            
    except requests.exceptions.RequestException as e:
        logger.error("Exception occurred during get request: %s, href: %s ignoring" % (e, href))

        
def http_post(href, data, uri=None):
    """ Add object to SMC
        If response code is success, return href to new object location
        If not success, raise exception, caught in middle tier calling method
        Args:
            * data: json document with object def
            * uri (optional): not implemented
    """          
    r = session.post(href,
                data=json.dumps(data),
                headers={'content-type': 'application/json'}
                )
    if r.status_code==201:
        logger.debug("Successfully added: %s, linked to href: %s" % (data, r.headers['location']))
        return r.headers['location']
    elif r.status_code==200: #TODO: Check with dev to see if this is needed, POST of license returns 200 vs 201
        logger.debug("Successfully added: %s" % data)
    else:
        raise OperationFailure("HTTP Response was: %s. Response content: %s" % (r.status_code, r.text))

 
def http_put(href, data, etag):
    """ Change state of existing SMC object
        Args: 
            * data: json encoded document
            * etag: required by SMC, retrieve first via http get
    """   
    r = session.put(href,
        data = json.dumps(data),
        headers={'content-type': 'application/json', 'Etag': etag}
        )
    print "Return status code: %s, text: %s" % (r.status_code, r.text)


def http_delete(href):
    r = session.delete(href)
    if r.status_code==204:
        pass
    else:
        raise OperationFailure("HTTP Response was: %s. Response content: %s" % (r.status_code, r.text))
        

def login(url, smc_key, api_version=None):    
    """ Login to SMC API and retrieve a valid session. 
        Session will be re-used when multiple queries are required.
        Args:
            * url: ip of SMC management server
            * smc_key: API key created for api client in SMC
            * api_version (optional): specify api version
            
        Logout should be called to remove the session immediately from the SMC server
        TODO: pickle session for longer term re-use? Implement SSL tracking
    """
    global session
    smc_url = url    
    if api_version is None:
        get_api_entry(url)
    else:
        get_api_entry(url, api_version)
                
    s = requests.session() #no session yet
    r = s.post(get_entry_href('login'),
               json={'authenticationkey': smc_key},
               headers={'content-type': 'application/json'}
               )
    if r.status_code==200:
        session = s #session creation was successful
        logger.debug("Login succeeded and session retrieved: %s" % session.cookies.items())
    else:
        print "Login failed: status code %s" % r.status_code
        sys.exit()
        
          
def logout():
    """ Logout session from SMC """
    r = session.put(get_entry_href('logout'))
    if r.status_code==204:
        logger.info("Logged out successfully")
    else:
        logger.error("Logout failed, session may not have been logged out, status code: %s and msg: %s" % (r.status_code, r.text))
        sys.exit()
        
if __name__ == '__main__':
    login('test', 'tete')
