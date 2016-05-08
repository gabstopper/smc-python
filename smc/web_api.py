'''
Created on May 1, 2016

@author: davidlepage
'''

import sys, json, requests
import logging

logger = logging.getLogger(__name__)

        
class SMCResult(object):
    def __init__(self, respobj=None):
        self.etag = None
        self.msg = self.extract(respobj)
        
    def extract(self, response):
        if response:
            self.etag = response.headers.get('ETag')
            if response.headers.get('content-type') == 'application/json':
                result = json.loads(response.text)
                if result:
                    if 'result' in result:
                        self.msg = result['result']
                    else:
                        self.msg = result
                return self.msg
           
class SMCOperationFailure(Exception):
    def __init__(self, respobj):
        self.code = None
        self.body= None
        self.msg = self.extract(respobj)
        
    def extract(self, response):
        self.code = response.status_code
        if response.headers.get('content-type') == 'application/json':
            j = json.loads(response.text)
            self.body = j
        else:
            if response.text:
                self.body = response.text
            else:
                self.body = response.headers
        return '{}, {}'.format("Http status code: %s" % self.code,"api msg: %s" % self.body)
 
                
api_entry = None
session = None       

#TODO: Wrap session call in exception handler in case connection to SMC is down after login            
def get_api_entry(url, api_version=None):
    """ Called internally after login to get cache of SMC entry points """
    global api_entry
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
        Returns:
            SMCResult object with json data and etag attrs
            SMCOperationFailure if non-http 200 response received
    """   
    try:
        if session:
            r = session.get(href)
            if r.status_code==200:
                logger.debug("Returned: %s" % r.text)
                return SMCResult(r)
            else:
                logger.error("HTTP get returned non-http 200 code [%s] for href: %s" % (r.status_code, href))
                raise SMCOperationFailure(r)
        else:
            print "No session found. Please login to continue"
            sys.exit()
            
    except requests.exceptions.RequestException as e:
        logger.error("Exception occurred during get request: %s, href: %s ignoring" % (e, href))
        return SMCResult()

        
def http_post(href, data, uri=None):
    """ Add object to SMC
        If response code is success, return href to new object location
        If not success, raise exception, caught in middle tier calling method
        Args:
            * href: entry point to add specific object type
            * data: json document with object def
            * uri (optional): not implemented
        Returns:
            Href of the resource pulled from returned location header
            SMCOperationFailure in case of non-http 201 return
    """ 
    if session:         
        r = session.post(href,
                    data=json.dumps(data),
                    headers={'content-type': 'application/json'}
                    )
        if r.status_code==201:
            logger.debug("Successfully added: %s, linked to href: %s" % (data, r.headers.get('location')))
            return r.headers.get('location')
        elif r.status_code==200: #TODO: Check with dev to see if this is needed, POST of license returns 200 vs 201
            logger.debug("Successful POST: %s" % data)
        else:
            raise SMCOperationFailure(r)
    else:
        print "No session found. Please login to continue"
        sys.exit()
               
 
def http_put(href, data, etag):
    """ Change state of existing SMC object
        Args: 
            * data: json encoded document
            * etag: required by SMC, retrieve first via http get
        Returns:
            Href of the resource pulled from returned location header
            SMCOperationFailure in case of non-http 200 return
    """ 
    if session:  
        r = session.put(href,
            data = json.dumps(data),
            headers={'content-type': 'application/json', 'Etag': etag}
            )
        if r.status_code==200:
            logger.debug("Successful modification, new host href: %s" % r.headers['location'])
            return r.headers.get('location') #TODO: Return these as an SMCResult in msg
        else:
            raise SMCOperationFailure(r)
    else:
        print "No session found. Please login to continue"
        sys.exit()

def http_delete(href):
    """ Delete element by fully qualified href
        Args:
            *href: fully qualified reference to object in SMC
        Returns:
            None
            SMCOperationFailure for non-http 204 code
    """
    if session:
        r = session.delete(href)
        if r.status_code==204:
            pass
        else:
            raise SMCOperationFailure(r)
    else:
        print "No session found. Please login to continue"
        sys.exit()
    
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
        raise Exception("Login failed, HTTP status code: %s" % r.status_code)
      
def logout():
    """ Logout session from SMC """
    r = session.put(get_entry_href('logout'))
    if r.status_code==204:
        logger.info("Logged out successfully")
    else:
        logger.error("Logout failed, session may not have been logged out, status code: %s and msg: %s" % (r.status_code, r.text))
        sys.exit()

                
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    login('http://172.18.1.150:8082', 'EiGpKD4QxlLJ25dbBEp20001')
    
    '''try:
        http_post("http://172.18.1.150:8082/bogus/thing", {"some":"data"})
    except SMCOperationFailure, e:
        print "post: %s" % e.msg
    try:
        http_put("http://172.18.1.150:8082/bogus/thing", {"some":"data"}, "etag")
    except SMCOperationFailure, e:
        print "put: %s" % e.msg
    try:
        http_delete('http://172.18.1.150:8082/6.0/elements/internal_user/Y249ZGxlcGFnZSxkYz1zdG9uZWdhdGUsZG9tYWluPUludGVybmFsRG9tYWlu')
    except SMCOperationFailure, e:
        print "delete: %s" % e.msg
    
    a=http_get("http://172.18.1.150:8082/6.0/elements?filter=ami")
    print "Valid search query: %s, etag: %s" % (a.msg,a.etag)
    
    try:
        http_get("http://172.18.1.150:8082/6.0/elements/wsdg/hhh")    
    except SMCOperationFailure, e:
        print "Bad uri, correct smc: %s" % (e.msg)
    
    a=http_get("http://172.18.1.150:8082/6.0/elements?filter=ami2222")
    print "Valid search query, unknown host: %s, etag: %s" % (a.msg,a.etag)'''
    
    #http_delete('http://172.18.1.150:8082/6.0/elements/internal_user/Y249ZGxlcGFnZSxkYz1zdG9uZWdhdGUsZG9tYWluPUludGVybmFsRG9tYWlu')
    http_post("http://172.18.1.148:8080/bogus/thing", {"some":"data"})
    #TODO: Test other HTTP operations without valid session (like http_get)
    logout()