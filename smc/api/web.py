'''
Created on May 9, 2016

@author: davidlepage
'''
import sys
import requests
import json
import logging

logger = logging.getLogger(__name__)

class SMCAPIConnection(object):
    def __init__(self):
        self.url = None
        self.key = None
        self.api_version = None
        self.cookies = None
        self.session = None
        self.cache = SMCEntryCache()
        
    def login(self, url, smc_key, api_version=None):    
        """ Login to SMC API and retrieve a valid session. 
            Session will be re-used when multiple queries are required.
            Args:
                * url: ip of SMC management server
                * smc_key: API key created for api client in SMC
                * api_version (optional): specify api version
                    
            Logout should be called to remove the session immediately from the SMC server
            TODO: pickle session for longer term re-use? Implement SSL tracking
        """
           
        #Find the login entry point
        self.cache.get_api_entry(url, api_version)
                
        s = requests.session() #no session yet
        r = s.post(self.cache.get_href('login'),
                   json={'authenticationkey': smc_key},
                   headers={'content-type': 'application/json'}
                   )
        if r.status_code==200:
            self.session = s #session creation was successful
            self.cookies = self.session.cookies.items()
            logger.debug("Login succeeded and session retrieved: %s" % self.cookies)
        else:
            raise Exception("Login failed, HTTP status code: %s" % r.status_code)
        
    def logout(self):
        """ Logout session from SMC """
        r = self.session.put(self.cache.get_href('logout'))
        if r.status_code==204:
            logger.info("Logged out successfully")
        else:
            logger.error("Logout failed, session may not have been logged out, status code: %s and msg: %s" % (r.status_code, r.text))
            sys.exit()
    
    def http_get(self, href):
        """ Get data object from SMC
            If response code is success, results are returned with etag
            Args:
                * href: fully qualified href for resource
            Returns:
                SMCResult object with json data and etag attrs
            Raises:
                SMCOperationFailure if non-http 200 response received
        """   
        try:
            if self.session:
                r = self.session.get(href)
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
            raise Exception("Connection problem to SMC, ensure the API service is running and host is correct: %s, exiting." % e)
            #TODO: What to do when connection may be lost during a run, not likely but possible
    
            
    def http_post(self, href, data, uri=None):
        """ Add object to SMC
            If response code is success, return href to new object location
            If not success, raise exception, caught in middle tier calling method
            Args:
                * href: entry point to add specific object type
                * data: json document with object def
                * uri (optional): not implemented
            Returns:
                Href of the resource pulled from returned location header
            Raises:
                SMCOperationFailure in case of non-http 201 return
        """ 
        try:
            if self.session:         
                r = self.session.post(href,
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
                
        except requests.exceptions.RequestException as e:
            raise Exception("Connection problem to SMC, ensure the API service is running and host is correct: %s, exiting." % e)
     
            
    def http_put(self, href, data, etag):
        """ Change state of existing SMC object
            Args: 
                * data: json encoded document
                * etag: required by SMC, retrieve first via http get
            Returns:
                Href of the resource pulled from returned location header
            Raises:
                SMCOperationFailure in case of non-http 200 return
        """ 
        try:
            if self.session:  
                r = self.session.put(href,
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
                
        except requests.exceptions.RequestException as e:
            raise Exception("Connection problem to SMC, ensure the API service is running and host is correct: %s, exiting." % e)
            #TODO: What to do when connection may be lost during a run, not likely but possible
    
    def http_delete(self, href):
        """ Delete element by fully qualified href
            Args:
                *href: fully qualified reference to object in SMC
            Returns:
                None
            Raises:
                SMCOperationFailure for non-http 204 code
        """
        try: 
            if self.session:
                r = self.session.delete(href)
                if r.status_code==204:
                    pass
                else:
                    raise SMCOperationFailure(r)
            else:
                print "No session found. Please login to continue"
                sys.exit()
                
        except requests.exceptions.RequestException as e:
            raise Exception("Connection problem to SMC, ensure the API service is running and host is correct: %s, exiting." % e)
            #TODO: What to do when connection may be lost during a run, not likely but possible
 
class SMCEntryCache(object):
    def __init__(self):
        self.api_entry = None
        
    def get_api_entry(self, url, api_version=None):
        """ Called internally after login to get cache of SMC entry points """
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
            self.api_entry = j['entry_point']
                
        except requests.exceptions.RequestException as e:
            raise Exception("Connection problem to SMC, ensure the API service is running and host is correct: %s, exiting." % e)
                      
    def get_href(self, verb):
        """ Get entry point from entry point cache 
            Call get_all_entry_points to find all available entry points 
            Args: 
                * verb: top level entry point into SMC api
            Returns:
                * dict of entry point specified
            Raises
                Exception is no entry points are found. That would mean 
                no login has occurred
        """    
        if self.api_entry:
            for entry in self.api_entry:
                if entry['rel'] == verb:
                    return entry['href']
        else:
            raise Exception("No entry points found, it is likely there is no valid login session.")
                     
    def get_all_entry_points(self): #for callers outside of the module
        """ Returns all entry points into SMC api """   
        return self.api_entry


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
        print "SMCOperationFailure response: %s" % response
        print "SMCOperationFailure body: %s" % response.text
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
 
session = SMCAPIConnection()

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    session.login('http://172.18.1.150:8082', 'EiGpKD4QxlLJ25dbBEp20001')
    try:
        session.http_post('http://172.18.1.150:8082/efw', {"test":"test"})
    except SMCOperationFailure, e:
        print e.msg
  
    session.logout()
    
    
    
    