'''
Created on Aug 14, 2016

@author: davidlepage
'''
import json
import requests
import logging
from smc.api.web import SMCAPIConnection
from smc.api.exceptions import SMCConnectionError, ConfigLoadError,\
    UnsupportedEntryPoint
from smc.api.configloader import load_from_file

logger = logging.getLogger(__name__)

class Session(object):
    def __init__(self):
        self._cache = None
        self._session = None
        self._connection = None
        self._url = None
        self._api_key = None
        self._timeout = 10

    @property
    def api_version(self):
        return self.cache.api_version
    
    @property
    def session(self):
        return self._session

    @property
    def session_id(self):
        return self.session.cookies

    @property
    def connection(self):
        return self._connection

    @property
    def cache(self):
        if self._cache is not None:
            return self._cache
        else:
            self._cache = SessionCache()
            return self._cache

    @property
    def url(self):
        return self._url
    
    @property
    def api_key(self):
        return self._api_key
    
    @property
    def timeout(self):
        return self._timeout
    
    def login(self, url=None, api_key=None, api_version=None,
              timeout=None, **kwargs):
        """
        Login to SMC API and retrieve a valid session.
        Session will be re-used when multiple queries are required.
        
        An example login and logout session::
        
            from smc.qpi.session import session   
            session.login(url='http://1.1.1.1:8082', api_key='SomeSMCG3ener@t3dPwd')
            .....do stuff.....
            session.logout()
            
        :param str url: ip of SMC management server
        :param str api_key: API key created for api client in SMC
        :param api_version (optional): specify api version
        :param int timeout: (optional): specify a timeout for initial connect; (default 10)

        Logout should be called to remove the session immediately from the
        SMC server.
        #TODO: Implement SSL tracking
        """
        if url and api_key:
            self._url = url
            self._api_key = api_key
            if timeout:
                self._timeout = timeout
        else:
            try:
                self.login(**load_from_file())
            except ConfigLoadError:
                raise
                   
        self.cache.get_api_entry(self.url, api_version, 
                                 timeout=self.timeout)

        s = requests.session() #no session yet
        r = s.post(self.cache.get_entry_href('login'),
                   json={'authenticationkey': self.api_key},
                   headers={'content-type': 'application/json'})
        if r.status_code == 200:
            self._session = s #session creation was successful
            logger.debug("Login succeeded and session retrieved: %s", \
                         self.session_id)
            self._connection = SMCAPIConnection(self)
        else:
            raise SMCConnectionError("Login failed, HTTP status code: %s" \
                                     % r.status_code)
    def logout(self):
        """ Logout session from SMC """
        if self.session:
            r = self.session.put(self.cache.get_entry_href('logout'))
            if r.status_code == 204:
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
            self.login(url=self.url, 
                       api_key=self.api_key, 
                       api_version=self.api_version)
        else:
            raise SMCConnectionError("No previous SMC session found. "
                                     "This will require a new login attempt")

class SessionCache(object):
    def __init__(self):
        self.api_entry = None
        self.api_version = None
                
    def get_api_entry(self, url, api_version=None, timeout=10):
        """
        Called internally after login to get cache of SMC entry points
        :param: url for SMC api
        :param api_version: if specified, use this version
        """
        try:
            if api_version is None:
                r = requests.get('%s/api' % url, timeout=timeout) #no session required
                j = json.loads(r.text)
                versions = []
                for version in j['version']:
                    versions.append(version['rel'])
                versions = [float(i) for i in versions]
                api_version = max(versions)

            #else api_version was defined
            logger.info("Using SMC API version: %s", api_version)
            smc_url = url + '/' + str(api_version)

            r = requests.get('%s/api' % (smc_url), timeout=timeout)
            if r.status_code==200:
                j = json.loads(r.text)
                self.api_version = api_version
                logger.debug("Successfully retrieved API entry points from SMC")
            else:
                raise SMCConnectionError("Error occurred during initial api "
                                         "request, json was not returned. "
                                         "Return data was: %s" % r.text)
            self.api_entry = j['entry_point']

        except requests.exceptions.RequestException, e:
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
            href = None
            for entry in self.api_entry:
                if entry.get('rel') == verb:
                    href = entry.get('href', None)
            if not href:
                raise UnsupportedEntryPoint(
                        "The specified entry point '{}' was not found in this "
                        "version of the SMC API. Check the element documentation "
                        "to determine the correct version and specify the api_version "
                        "parameter during session.login() if necessary. Current api version "
                        "is {}".format(verb, self.api_version))
            else:
                return href      
        else:
            raise SMCConnectionError("No entry points found, it is likely "
                                     "there is no valid login session.")

    def get_all_entry_points(self):
        """ Returns all entry points into SMC api """
        return self.api_entry