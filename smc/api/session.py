"""
Session module for tracking existing connection state to SMC
"""
import json
import logging
import requests
import smc.api.counter
from smc.api.web import SMCAPIConnection
from smc.api.exceptions import SMCConnectionError, ConfigLoadError,\
    UnsupportedEntryPoint
from smc.api.configloader import load_from_file

#requests.packages.urllib3.disable_warnings()

logger = logging.getLogger(__name__)

class Session(object):
    def __init__(self):
        self._cache = SessionCache()
        self._session = None
        self._connection = None
        self._url = None
        self._api_key = None
        self._timeout = 10

    @property
    def api_version(self):
        """ API Version """
        return self.cache.api_version
    
    @property
    def session(self):
        """ Session for this interpreter """
        return self._session

    @property
    def session_id(self):
        """ Session ID representation """
        return self.session.cookies

    @property
    def connection(self):
        return self._connection

    @property
    def cache(self):
        return self._cache
    
    @property
    def url(self):
        """ SMC URL """
        return self._url
    
    @property
    def api_key(self):
        """ SMC Client API key """
        return self._api_key
    
    @property
    def timeout(self):
        return self._timeout
    
    def login(self, url=None, api_key=None, api_version=None,
              timeout=None, verify=True, alt_filepath=None, 
              **kwargs):
        """
        Login to SMC API and retrieve a valid session.
        Session will be re-used when multiple queries are required.
        
        An example login and logout session::
        
            from smc import session   
            session.login(url='http://1.1.1.1:8082', api_key='SomeSMCG3ener@t3dPwd')
            .....do stuff.....
            session.logout()
            
        :param str url: ip of SMC management server
        :param str api_key: API key created for api client in SMC
        :param api_version (optional): specify api version
        :param int timeout: (optional): specify a timeout for initial connect; (default 10)
        :param str|boolean verify: verify SSL connections using cert (default: verify=True)
        :param str alt_filepath: If using .smcrc, alternate file+path

        For SSL connections, you can disable validation of the SMC SSL certificate by setting 
        verify=False, however this is not a recommended practice.
        
        If you want to use the SSL certificate generated and used by the SMC API server
        for validation, set verify='path_to_my_dot_pem'. It is also recommended that your 
        certificate has subjectAltName defined per RFC 2818
        
        If SSL warnings are thrown in debug output, see: 
        https://urllib3.readthedocs.io/en/latest/advanced-usage.html#ssl-warnings
        
        Logout should be called to remove the session immediately from the
        SMC server.
        """
        if url and api_key:
            self._url = url
            self._api_key = api_key
            if timeout:
                self._timeout = timeout
        else:
            try:
                cfg = load_from_file(alt_filepath) if alt_filepath\
                    is not None else load_from_file()
                logger.debug("Config read has data: %s", cfg)
                self._url = cfg.get('url')
                self._api_key = cfg.get('api_key')
                api_version = cfg.get('api_version')
                verify = cfg.get('verify')
                timeout = cfg.get('timeout')
                if timeout:
                    self._timeout = timeout
            except ConfigLoadError:
                raise
    
        self.cache.get_api_entry(self.url, api_version, 
                                 timeout=self.timeout,
                                 verify=verify)
        s = requests.session() #no session yet
        r = s.post(self.cache.get_entry_href('login'),
                   json={'authenticationkey': self.api_key},
                   headers={'content-type': 'application/json'},
                   verify=verify)
        if r.status_code == 200:
            self._session = s #session creation was successful
            self._session.verify = verify #make verify setting persistent
            logger.debug("Login succeeded and session retrieved: %s", \
                         self.session_id)
            self._connection = SMCAPIConnection(self)
        else:
            raise SMCConnectionError("Login failed, HTTP status code: %s" \
                                     % r.status_code)
    def logout(self):
        """ Logout session from SMC """
        if self.session:
            try:
                r = self.session.put(self.cache.get_entry_href('logout'))
                if r.status_code == 204:
                    logger.info("Logged out successfully")
                    c = smc.api.common.countcalls.counts()
                    c.update({'cache': smc.api.counter.cache_hit})
                    logger.debug("Query counters: %s" % c)
                else:
                    logger.error("Logout status was unexpected. Received response "
                                 "was status code: %s", (r.status_code))
            except requests.exceptions.SSLError as e:
                #When SSL is enabled and verification is disabled, logout may throw an
                #SSL VERIFY FAILED error from requests module. Not sure why, will have
                #to investigate
                logger.error("SSL exception thrown during logout: %s", e)
            finally:
                self.session.cookies.clear()
                self.cache.api_entry = None
                
class SessionCache(object):
    def __init__(self):
        self.api_entry = None
        self.api_version = None

    def get_api_entry(self, url, api_version=None, timeout=10,
                      verify=True):
        """
        Called internally after login to get cache of SMC entry points
        
        :param: str url: URL for SMC 
        :param str api_version: if specified, use this version, or use latest
        """
        try:
            # Get api versions
            r = requests.get('%s/api' % url, timeout=timeout, 
                             verify=verify) #no session required
            j = json.loads(r.text)
            versions = []
            for version in j['version']:
                versions.append(version['rel'])
            versions = [float(i) for i in versions]
            
            if api_version is None: # Use latest
                api_version = max(versions)
            else:
                try:
                    specified_version = float(api_version)
                    if specified_version in versions:
                        api_version = specified_version
                    else:
                        api_version = max(versions)
                except ValueError:
                    api_version = max(versions)
            
            #else api_version was defined
            logger.info("Using SMC API version: %s", api_version)
            smc_url = '{}/{}'.format(url, str(api_version))
            
            r = requests.get('%s/api' % (smc_url), timeout=timeout, 
                             verify=verify)
            
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
        Call get_all_entry_points to find all available entry points. 
        
        :param str verb: top level entry point into SMC api
        :return dict: meta data for specified entry point
        :raises: :py:class:`smc.api.exceptions.UnsupportedEntryPoint`
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

    @property
    def entry_points(self):
        return self.get_entry_points()
    
    def get_entry_points(self):
        """
        Build a list of filter contexts for entry points related to elements.
        These filters can be used in the filter_context parameter on search methods 
        that support them.
        
        :return: list names of each available filter context on the element node
        """
        return [entry.get('rel') for entry in self.api_entry]
        
    def get_all_entry_points(self):
        """ Returns all entry points into SMC api """
        return self.api_entry
