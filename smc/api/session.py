'''
Created on Aug 14, 2016

@author: davidlepage
'''
import json
import requests
import logging
from smc.api.web import SMCConnectionError, SMCAPIConnection, ConfigLoadError
from smc.api.configloader import load_from_file

logger = logging.getLogger(__name__)

class Session(object):
    def __init__(self):
        self.url = None
        self.api_key = None
        self.session = None
        self.cookies = None
        self.api_version = None
        self.cache = None #SessionCache
        self.connection = None #SMCAPIConnection
    
    def login(self, **kwargs):
        """
        Login to SMC API and retrieve a valid session.
        Session will be re-used when multiple queries are required.
        
        An example login and logout session::
        
            import smc.api.web as web_api    
            web_api.session.login('http://1.1.1.1:8082', 'SomeSMCG3ener@t3dPwd')
            .....do stuff.....
            web_api.session.logout()
            
        :param url: ip of SMC management server
        :param api_key: API key created for api client in SMC
        :param api_version (optional): specify api version

        Logout should be called to remove the session immediately from the
        SMC server.
        #TODO: Implement SSL tracking
        """
        if kwargs:
            for key, value in kwargs.items():
                setattr(self, key, value)
        else:
            try:
                self.login(**load_from_file())
            except ConfigLoadError:
                raise
                    
        self.cache = SessionCache()
        self.cache.get_api_entry(self.url, self.api_version)
        self.api_version = self.cache.api_version

        s = requests.session() #no session yet
        r = s.post(self.cache.get_entry_href('login'),
                   json={'authenticationkey': self.api_key},
                   headers={'content-type': 'application/json'}
                   )
        if r.status_code == 200:
            self.session = s #session creation was successful
            self.cookies = self.session.cookies.items()
            logger.debug("Login succeeded and session retrieved: %s", \
                         self.cookies)
            self.connection = SMCAPIConnection(self)

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
        else: #TODO: Throw exception here
            logger.error("No previous SMC session found. "
                         "This may require a new login attempt")

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
            for entry in self.api_entry:
                if entry.get('rel') == verb:
                    return entry.get('href', None)
        else:
            raise SMCConnectionError("No entry points found, it is likely "
                                     "there is no valid login session.")

    def get_all_entry_points(self):
        """ Returns all entry points into SMC api """
        return self.api_entry

session = Session()


if __name__ == '__main__':
    logging.getLogger()
    logging.basicConfig(level=logging.DEBUG)
    session.login()
    #session.login(url='http://172.18.1.150:8082', api_key='EiGpKD4QxlLJ25dbBEp20001', timeout=60)
    #session.connection.http_get('http://172.18.1.150:8082/6.0/elements/single_fw/9499/internal_gateway')

    from pprint import pprint
    pprint(vars(session))
    #pprint(session.cache.get_all_entry_points())

    session.logout()
