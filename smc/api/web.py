'''
Created on May 9, 2016

@author: davidlepage
'''

import requests
import json
import logging

logger = logging.getLogger(__name__)

class SMCEntryCache(object):
    """ 
    Keep track of api entry points retrieved after login to 
    prevent subsequent queries 
    """
    def __init__(self):
        
        self.cache = None
        self.api_entry = None
        self.api_version = None
        
    def get_api_entry(self, url, api_version=None):
        """ 
        Called internally after login to get cache of SMC entry points 
        :param: url for SMC api 
        :param api_version: if specified, use this version
        """
        try:
            if api_version is None:
                r = requests.get('%s/api' % url, timeout=5) #no session required
                j = json.loads(r.text)
                versions = []
                for version in j['version']:
                    versions.append(version['rel'])
                versions = [float(i) for i in versions]
                api_version = max(versions)
            
            #else api_version was defined
            logger.info("Using SMC API version: %s", api_version)
            smc_url = url + '/' + str(api_version)
      
            r = requests.get('%s/api' % (smc_url), timeout=5)
            if r.status_code==200:
                j = json.loads(r.text)
                self.api_version = api_version
                logger.debug("Successfully retrieved API entry points from SMC")
            else:
                raise SMCConnectionError("Error occurred during initial api "
                                         "request, json was not returned. "
                                         "Return data was: %s" % r.text)
            self.api_entry = j['entry_point']
                
        except requests.exceptions.RequestException as e:
            raise SMCConnectionError(e)
                  
    def get_entry_href(self, verb):
        """ 
        Get entry point from entry point cache 
        Call get_all_entry_points to find all available entry points 
        :param verb: top level entry point into SMC api
        :return dict of entry point specified
        :raises Exception if no entry points are found. 
        That would mean no login has occurred
        """
        if self.api_entry:
            for entry in self.api_entry:
                if entry.get('rel') == verb:
                    return entry.get('href', None)
        else:
            raise SMCConnectionError("No entry points found, it is likely "
                                     "there is no valid login session.") 
           
    def get_all_entry_points(self): 
        """ Returns all entry points into SMC api """   
        return self.api_entry
    
    def get_element(self, name):
        """ Check if we've already retrieved the item location """
        return self.elements.get(name)
    
    
class SMCAPIConnection(SMCEntryCache):
    def __init__(self):
        SMCEntryCache.__init__(self)
        
        self.url = None
        self.key = None
        self.cookies = None
        self.session = None
        
    def login(self, url, smc_key, api_version=None):    
        """ 
        Login to SMC API and retrieve a valid session. 
        Session will be re-used when multiple queries are required.
        :param url: ip of SMC management server
        :param smc_key: API key created for api client in SMC
        :param api_version (optional): specify api version
                    
        Logout should be called to remove the session immediately from the 
        SMC server.
        TODO: pickle session for longer term re-use? Implement SSL tracking
        """
        
        self.get_api_entry(url, api_version)
        
        s = requests.session() #no session yet
        r = s.post(self.get_entry_href('login'),
                   json={'authenticationkey': smc_key},
                   headers={'content-type': 'application/json'}
                   )
        if r.status_code == 200:
            self.session = s #session creation was successful
            self.cookies = self.session.cookies.items()
            self.url = url #used for session refresh
            self.key = smc_key
            logger.debug("Login succeeded and session retrieved: %s", \
                         self.cookies)
        else:
            raise SMCConnectionError("Login failed, HTTP status code: %s" \
                                     % r.status_code)
    def logout(self):
        """ Logout session from SMC """
        if self.session:
            r = self.session.put(self.get_entry_href('logout'))
            if r.status_code==204:
                logger.info("Logged out successfully")
            else:
                if r.status_code == 401:
                    logger.error("Logout failed, session has already expired, "
                                 "status code: %s", (r.status_code))
                else:
                    logger.error("Logout failed, status code: %s", r.status_code)
    
    def refresh(self):
        """ 
        Refresh SMC session if it timed out. This may be the case if the CLI
        is being used and the user was idle. SMC has a time out value for API
        client sessions (configurable). Refresh will use the previously saved url
        and apikey and get a new session and refresh the api_entry cache
        """
        if self.session is not None: #user has logged in previously
            logger.info("Session refresh called, previous session has expired")
            self.login(self.url, self.key, self.api_version)
        else:
            logger.error("No previous SMC session found. "
                         "This may require a new login attempt")
            
    def http_get(self, href): #TODO: Implement self.visited for already seen queries
        """ 
        Get data object from SMC
        If response code is success, results are returned with etag
        :param href: fully qualified href for resource
        :return SMCResult object with json data and etag attrs
        :raise SMCOperationFailure if non-http 200 response received
        """   
        try:
            if self.session:
                r = self.session.get(href, timeout=5)
                if r.status_code == 200: 
                    logger.debug("HTTP get result: %s", r.text)
                    return SMCResult(r)
                elif r.status_code == 401:
                    #unauthorized, session timed out
                    self.refresh() #TODO: Exception could be thrown here however unlikely
                    return self.http_get(href)
                else:
                    logger.error("HTTP get returned non-http 200 code [%s] "
                                 "for href: %s", (r.status_code, href))
                    raise SMCOperationFailure(r)
            else:
                raise SMCConnectionError("No session found. Please login to continue")
                
        except requests.exceptions.RequestException as e:
            raise SMCConnectionError("Connection problem to SMC, ensure the "
                            "API service is running and host is correct: %s, "
                            "exiting." % e)
     
            
    def http_post(self, href, data, uri=None):
        """ 
        Add object to SMC
        If response code is success, return href to new object location
        If not success, raise exception, caught in middle tier calling method
        :param href: entry point to add specific object type
        :param data: json document with object def
        :param uri (optional): not implemented
        :return href of the resource pulled from returned location header
        :raise SMCOperationFailure in case of non-http 201 return
        """ 
        try:
            if self.session:         
                r = self.session.post(href,
                            data=json.dumps(data),
                            headers={'content-type': 'application/json'}
                            )
                if r.status_code == 201 or r.status_code == 200:
                    logger.debug("Successfully added: %s, linked to href: %s", \
                                 data, r.headers.get('location'))
                    return r.headers.get('location')
                elif r.status_code == 401:
                    self.refresh()
                    return self.http_post(href, data)
                else:
                    raise SMCOperationFailure(r)
            else:
                raise SMCConnectionError("No session found. Please login to continue")
                
        except requests.exceptions.RequestException as e:
            raise SMCConnectionError("Connection problem to SMC, ensure the "
                                     "API service is running and host is "
                                     "correct: %s, exiting." % e)
      
            
    def http_put(self, href, data, etag):
        """ 
        Change state of existing SMC object
        :param data: json encoded document
        :param etag: required by SMC, retrieve first via http get
        :return Href of the resource pulled from returned location header
        :raise SMCOperationFailure in case of non-http 200 return
        """ 
        try:
            if self.session:  
                r = self.session.put(href,
                    data = json.dumps(data),
                    headers={'content-type': 'application/json', 'Etag': etag}
                    )
                if r.status_code == 200:
                    logger.debug("Successful modification, new host href: %s", \
                                  r.headers['location'])
                    return r.headers.get('location') #TODO: Return these as an SMCResult
                elif r.status_code == 401:
                    self.refresh()
                    return self.http_put(href, data, etag) 
                else:
                    raise SMCOperationFailure(r)
            else:
                raise SMCConnectionError("No session found. Please login to continue")
                
        except requests.exceptions.RequestException as e:
            raise SMCConnectionError("Connection problem to SMC, ensure the "
                                     "API service is running and host is "
                                     "correct: %s, exiting." % e)
    
        
    def http_delete(self, href):
        """ 
        Delete element by fully qualified href
        :param href: fully qualified reference to object in SMC
        :return None
        :raise SMCOperationFailure for non-http 204 code
        """
        try: 
            if self.session:
                r = self.session.delete(href)
                if r.status_code == 204:
                    pass
                elif r.status_code == 401:
                    self.refresh()
                    return self.http_delete(href)
                else:
                    raise SMCOperationFailure(r)
            else:
                raise SMCConnectionError("No session found. Please login to continue")
                
        except requests.exceptions.RequestException as e:
            raise SMCConnectionError("Connection problem to SMC, ensure the "
                                     "API service is running and host is "
                                     "correct: %s, exiting." % e)
          

class SMCResult(object):
    """ 
    SMCResult will store the data needed to do modify based operations on
    an existing record. To modify, an HTTP GET is first made returning the 
    element json and the current etag. The modified json will be POST to the
    SMC with json as payload and etag to verify the element has not been 
    modified since previous GET.
    :attributes
        self.etag: etag from HTTP GET, representing unique str from server
        self.href: None
        self.json: element full json
    """
    def __init__(self, respobj=None):
        self.etag = None
        self.href = None
        self.json = self.extract(respobj)
        
    def extract(self, response):
        if response:
            self.etag = response.headers.get('ETag')
            if response.headers.get('content-type') == 'application/json':
                result = json.loads(response.text)
                if result:
                    if 'result' in result:
                        self.json = result['result']
                    else:
                        self.json = result
                return self.json
            
           
class SMCOperationFailure(Exception):
    """ Exception class for storing results from calls to the SMC
    This is thrown for HTTP methods that do not return the expected HTTP
    status code. See each method above for expected success status
    :param respobj: response object returned from HTTP method
    :attributes
        self.code: HTTP response status code
        self.body: HTTP response body
        self.msg: parsed representation of the error string to display
    """
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
        return '{}, {}'.format("Http status code: %s" % self.code, self.formatmsg())
    
    def formatmsg(self):
        errorstr = []
        if isinstance(self.body, dict):
            for i in self.body:
                if isinstance(self.body[i], list):
                    errorstr.append(str(i) + ": ")
                    for err in self.body[i]:
                        a =  err.rstrip().split('\n')
                    errorstr.append(' '.join(a))
                else:
                    errorstr.append(str(i) + ": " + str(self.body[i]))
        return ' '.join(errorstr)
    
    def __str__(self):
        return self.msg

class SMCConnectionError(Exception):
    """ 
    Thrown when there are connection related issues with the SMC. 
    This could be that the underlying http requests library could not connect
    due to wrong IP address, wrong port, time out, or the operator provided 
    invalid credentials (API Client and API key)
    :param value: Error message to display. If http requests exception thrown,
    this just wraps the error
    """
    def __init__(self, value):
        self.value = value
    
    def __str__(self):
        return self.value

session = SMCAPIConnection()

if __name__ == "__main__":
    
    import smc.api.web
    session.http_get('http://172.18.1.150:8082/api/6.0/elements')
    
    