"""
Session module for tracking existing connection state to SMC
"""
import copy
import json
import logging
import requests
import collections

import smc.api.web
from smc.api.entry_point import Resource
from smc.api.configloader import load_from_file, load_from_environ
from smc.api.common import SMCRequest
from smc.base.decorators import cached_property
from smc.api.exceptions import ConfigLoadError, SMCConnectionError,\
    UnsupportedEntryPoint, SessionManagerNotFound, SessionNotFound
from smc.base.model import ElementFactory
# requests.packages.urllib3.disable_warnings()

logger = logging.getLogger(__name__)


'''
#from requests.adapters import HTTPAdapter
#from requests.packages.urllib3.poolmanager import PoolManager
class SSLAdapter(HTTPAdapter):
    """
    An HTTPS Transport Adapter that uses an arbitrary SSL version.
    Version should be a valid protocol from python ssl library.
    """
    def __init__(self, ssl_version=None, **kwargs):
        self.ssl_version = ssl_version

        super(SSLAdapter, self).__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_version=self.ssl_version)
'''            

#from threading import local

class SessionManager(object):
    """
    The SessionManager keeps track of sessions created within smc-python.
    In most cases, this is transparent functionality as most scripts will
    use only a single session for it's lifetime.
    
    By default a single Session Manager is created that will be used
    when processing all requests to the SMC. 
    
    Session Manager also has a hook that can be called that will change the
    way the session manager retrieves the session from the manager.
    An example might be that you are using smc-python in a web application
    and authenticating the user to the SMC. Each web session stores the
    name of the authenticated user. You want to use that to map to the 
    SMC session by retrieving the user from the web session ID and then
    from the SessionManager.
    
    A function hook can be registered that will retrieve use some external
    criteria to determine which session to retrieve from the SessionManager.
    .. seealso:: :meth:`~register_hook`.
    
    Creating your own session manager might be useful if you needed custom
    functionality or needed to extend the default. Create a new manager
    and call mount to set it on the global request object::
    
        manager = SessionManager()
        manager.mount()    
    
    ..note:: By default, a single session is maintained and considered the
        `default` session.
    
    :param list(Session) sessions: list of sessions
    """
    _session_hook = None
    
    def __init__(self, sessions=None):
        self._sessions = collections.OrderedDict()
        sessions = sessions or []
        for session in sessions:
            self._register(session)
        #self._connections = local() #TODO: Make self._sessions an attribute of threading local
    
    @classmethod
    def create(cls, sessions=None):
        """
        A session manager will be mounted to the SMCRequest class through
        this classmethod. If there is already an existing SessionManager,
        that is returned instead.
        
        :param list sessions: a list of Session objects
        :rtype: SessionManager
        """
        manager = getattr(SMCRequest, '_session_manager')
        if manager is not None:
            return manager
        manager = SessionManager(sessions)
        manager.mount()
        return manager
    
    def mount(self): 
        """   
        Mount this session manager on the request class, making this
        the global manager for processing requests
        
        :return: None
        """
        setattr(SMCRequest, '_session_manager', self)
    
    def register_hook(self, hook):
        """
        Add a hook that specifies how to retrieve the session from the
        session manager. A hook must be a callable that takes one argument
        (the SessionManager) and extracts the session based on some criteria.
        An example of using a hook::
        
            from smc import manager
            def retrieve_session(session_manager):
                ...
                admin = session_manager.get_session('admin')
                return admin if admin.is_active else session_manager.get_default_session()
        
            manager.register_hook(retrieve_session)
           
        Hooks can be used when your application requires multiple sessions
        within the same python interpreter. For example, in a web app, you
        might use the SMC administrator account to log in and store the session
        within the web application which allows you to also store and retrieve
        that SMC based session for further operations.
        """
        if callable(hook):
            self._session_hook = hook
    
    def __contains__(self, session):
        """
        A session is considered to exist if the current user attached to
        the session matches. In SMC, an administrative account must be
        unique even if it only exists in a specific domain.
        
        :rtype: bool
        """
        return session in self.sessions
    
    @property
    def sessions(self):
        """
        All available sessions in this session manager

        :rtype: list(Session)
        """
        return list(self._sessions.values())
        
    def get_default_session(self):
        """
        The default session is nothing more than the first session added
        into the session handler pool. This will likely change in the future
        but for now each session identifies the domain and also manages
        domain switching within a single session.
        
        :rtype: Session
        """
        if self._sessions:
            return self.get_session(next(iter(self._sessions)))
        return self.get_session()
    
    def get_session(self, user=None):
        """
        Retrieve the session based on user, or return and empty session.
        Note that an empty session is not inserted into the Session Manager
        until `login` has been successfully called on the session.
        
        :param str user: optional user to find in the session manager
        :raises SessionNotFound: session was not found in manager
        :rtype: Session
        """
        return self._sessions.get(user, Session())
#         raise SessionNotFound('Session specified by name: %s does not currently '
#             'exist.' % user)
    
    def close_all(self):
        for admin_session in list(self._sessions.keys()):
            self._sessions[admin_session].logout()
        self._sessions.clear()
    
    def _get_session_key(self, session):
        for name, _session in self._sessions.items():
            if _session == session:
                return name  
    
    def _register(self, session):
        """
        Register a session
        """
        if session.session_id:
            self._sessions[session.name] = session
        
    def _deregister(self, session):
        """
        Deregister a session. 
        """
        if session in self:
            self._sessions.pop(self._get_session_key(session), None)    
        

class Session(object):
    """
    Session represents the clients session to the SMC. A session is obtained
    by calling login(). If sessions need to be long lived as might be the case
    when running under a web platform, a session is automatically refreshed
    when it expires. Best practice is to call logout() after to clear the
    session from the SMC.
    """
    def __init__(self, manager=None):
        self._params = {} # Retrieved from login
        self._session = None # requests.Session
        self._connection = None # SMCAPIConnection
        
        self._resource = None # Entry points
        
        self._manager = manager # Session Manager that tracks this session
        
        # Transactions are supported in version 0.6.2 and beyond. When
        # run with atomic, this session parameter indicates whether the
        # operation in process is within an atomic block or not
        self.in_atomic_block = False
        # Savepoint indicates a nested context manager block
        self.is_savepoint = False
        # Transactions that are within the given atomic block
        self.transactions = []
    
    @property
    def manager(self):
        """
        Return the session manager for this session
        
        :rtype: SessionManager
        """
        manager = SMCRequest._session_manager if not self._manager \
            else self._manager
        if not manager:
            raise SessionManagerNotFound('A session manager was not found. '
                'This is an initialization error binding the SessionManager. ')
        return manager
    
    @property
    def is_active(self):
        """
        Is this session active. Active means there is a stored session ID for
        the SMC using the current account. This does not specify whether the
        session ID has been timed out on the server but does indicate the
        account has not called logout.
        
        :rtype: bool
        """
        return self._session is not None and 'JSESSIONID' in self._session.cookies
    
    @property
    def _extra_args(self):
        """
        Extra args are collected from login and used if provided. These are
        generally not needed but may be used to enable visibility of beta
        features or set special settings
        """
        return self._params.get('kwargs', {})
        
    @property
    def entry_points(self):
        """
        Entry points that are bound to this session. Entry points are exposed
        by the SMC API and provide links to top level resources
        
        :rtype: Resource
        """
        if not self._resource:
            raise SMCConnectionError('No entry points found, it is likely '
                'there is no valid login session.')
        return self._resource

    @property
    def api_version(self):
        """
        Current API Version
        
        :rtype: str
        """
        return self._params.get('api_version')

    @property
    def session(self):
        return self._session

    @property
    def connection(self):
        return self._connection

    @property
    def session_id(self):
        """
        The session ID in header type format. Can be inserted into a
        connection if necessary using::
        
            {'Cookie': session.session_id}
        
        :rtype: str
        """
        return None if not self.session or 'JSESSIONID' not in \
            self.session.cookies else 'JSESSIONID={}'.format(
                self.session.cookies['JSESSIONID'])

    @property
    def credential(self):
        # Login credentials
        return Credential(**{k: self._params.get(k)
            for k in ('api_key', 'login', 'pwd')})
    
    @property
    def url(self):
        """
        The fully qualified SMC URL in use, includes the port number
        
        :rtype: str
        """
        return self._params.get('url', '')
    
    @property
    def web_socket_url(self):
        socket_proto = 'wss' if self.is_ssl else 'ws'    
        return '{}://{}/{}'.format(
            socket_proto, self.url.split('://')[-1], self.api_version)
    
    @property
    def is_ssl(self):
        """
        Is this an SSL connection
        
        :rtype: bool
        """
        return self.url.startswith('https') if self.session else False

    @property
    def timeout(self):
        """
        Session timeout in seconds
        
        :rtype: int
        """
        return self._params.get('timeout', 30)

    @property
    def domain(self):
        """
        Logged in SMC domain
        
        :rtype: str
        """
        return self._params.get('domain', 'Shared Domain')
        
    @property
    def name(self):
        """
        Return the administrator name for this session. Can be None if
        the session has not yet been established.
        
        .. note:: The administrator name was introduced in SMC version
            6.4. Previous versions will show the unique session
            identifier for this session.
        
        :rtype: str
        """
        if self.session: # protect cached property from being set before session
            try:
                return self.current_user.name
            except AttributeError: # TODO: Catch ConnectionError? No session
                pass
        return hash(self)
    
    @cached_property
    def current_user(self):
        """
        .. versionadded:: 0.6.0
            Requires SMC version >= 6.4
        
        Return the currently logged on API Client user element.
        
        :raises UnsupportedEntryPoint: Current user is only supported with SMC
            version >= 6.4
        :rtype: Element
        """
        if self.session:
            try:
                response = self.session.get(self.entry_points.get('current_user'))
                if response.status_code in (200, 201):
                    admin_href=response.json().get('value')
                    request = SMCRequest(admin_href)
                    smcresult = self.connection.send_request('get', request)
                    return ElementFactory(admin_href, smcresult)
            except UnsupportedEntryPoint:
                pass
    
    def login(self, url=None, api_key=None, login=None, pwd=None,
            api_version=None, timeout=None, verify=True, alt_filepath=None,
            domain=None, **kwargs):
        """
        Login to SMC API and retrieve a valid session.
        Sessions use a pool connection manager to provide dynamic scalability
        during times of increased load. Each session is managed by a global
        session manager making it possible to have more than one session per
        interpreter.

        An example login and logout session::

            from smc import session
            session.login(url='http://1.1.1.1:8082', api_key='SomeSMCG3ener@t3dPwd')
            .....do stuff.....
            session.logout()

        :param str url: ip of SMC management server
        :param str api_key: API key created for api client in SMC
        :param str login: Administrator user in SMC that has privilege to SMC API.
        :param str pwd: Password for user login.
        :param api_version (optional): specify api version
        :param int timeout: (optional): specify a timeout for initial connect; (default 10)
        :param str|boolean verify: verify SSL connections using cert (default: verify=True)
            You can pass verify the path to a CA_BUNDLE file or directory with certificates
            of trusted CAs
        :param str alt_filepath: If using .smcrc, alternate path+filename
        :param str domain: domain to log in to. If domains are not configured, this
            field will be ignored and api client logged in to 'Shared Domain'.
        :param bool retry_on_busy: pass as kwarg with boolean if you want to add retries
            if the SMC returns HTTP 503 error during operation. You can also optionally customize
            this behavior and call :meth:`.set_retry_on_busy`
        :raises ConfigLoadError: loading cfg from ~.smcrc fails

        For SSL connections, you can disable validation of the SMC SSL certificate by setting
        verify=False, however this is not a recommended practice.

        If you want to use the SSL certificate generated and used by the SMC API server
        for validation, set verify='path_to_my_dot_pem'. It is also recommended that your
        certificate has subjectAltName defined per RFC 2818
        
        If SSL warnings are thrown in debug output, see:
        https://urllib3.readthedocs.io/en/latest/advanced-usage.html#ssl-warnings

        Logout should be called to remove the session immediately from the
        SMC server.
        
        .. note:: As of SMC 6.4 it is possible to give a standard Administrative user access
            to the SMC API. It is still possible to use an API Client by providing the api_key
            in the login call.
        """
        params = {}
        if not url or (not api_key and not (login and pwd)):
            try: # First try load from file
                params = load_from_file(alt_filepath) if alt_filepath\
                    is not None else load_from_file()
                logger.debug('Read config data from file: %s', params)
            except ConfigLoadError:
                # Last ditch effort, try to load from environment
                params = load_from_environ()
                logger.debug('Read config data from environ: %s', params)
        
        params = params or dict(
            url=url,
            api_key=api_key,
            login=login,
            pwd=pwd,
            api_version=api_version,
            verify=verify,
            timeout=timeout,
            domain=domain,
            kwargs=kwargs or {})
        
        # Check to see if a session already exists with the same user
        # (SMC >= 6.4) or session ID. A single session by user supported which
        # means if an existing session does exist, it will be logged out and a
        # new session created
        if self.manager and (self.session and self in self.manager):
            logger.info('An attempt to log in occurred when a session already '
                'exists, bypassing login for session: %s' % self)
            return
        
        self._params = {k: v for k, v in params.items() if v is not None}
        
        verify_ssl = self._params.get('verify', True)
        
        # Determine and set the API version we will use.
        self._params.update(
            api_version=get_api_version(
                self.url, self.api_version, self.timeout, verify_ssl))
        
        extra_args = self._params.get('kwargs', {})
        
        # Retries configured
        retry_on_busy = extra_args.pop('retry_on_busy', False)
        
        request = self._build_auth_request(verify_ssl, **extra_args)
            
        # This will raise if session login fails...
        self._session = self._get_session(request)
        self.session.verify = verify_ssl

        if retry_on_busy:
            self.set_retry_on_busy()
        
        # Set up new API connection reference
        self._connection = smc.api.web.SMCAPIConnection(self)
        
        # Load entry points
        load_entry_points(self)
        
        # Put session in manager
        self.manager._register(self)
        
        logger.debug('Login succeeded for admin: %s in domain: %s, session: %s',
            self.name, self.domain, self.session_id)
   
    def __repr__(self):
        return 'Session(name=%s,domain=%s)' % (self.name, self.domain)
        
    def _build_auth_request(self, verify=False, **kwargs):
        """
        Build the authentication request to SMC
        """
        json = {
            'domain': self.domain
        }
        
        credential = self.credential
        params = {}
        
        if credential.provider_name.startswith('lms'):
            params = dict(
                login=credential._login,
                pwd=credential._pwd)
        else:
            json.update(authenticationkey=credential._api_key)
        
        if kwargs:
            json.update(**kwargs)
            self._extra_args.update(**kwargs) # Store in case we need to rebuild later
        
        request = dict(
            url=self.credential.get_provider_entry_point(self.url, self.api_version),
            json=json,
            params=params,
            headers={'content-type': 'application/json'},
            verify=verify)
        
        return request
    
    def _get_session(self, request):
        """
        Authenticate the request dict
        
        :param dict request: request dict built from user input
        :raises SMCConnectionError: failure to connect
        :return: python requests session
        :rtype: requests.Session
        """
        _session = requests.session()  # empty session
        
        response = _session.post(**request)
        logger.info('Using SMC API version: %s', self.api_version)
        
        if response.status_code != 200:
            raise SMCConnectionError(
                'Login failed, HTTP status code: %s and reason: %s' % (
                    response.status_code, response.reason))
        return _session

    def logout(self):
        """ 
        Logout session from SMC
        
        :return: None
        """
        if not self.session:
            self.manager._deregister(self)
            return
        try:
            r = self.session.put(self.entry_points.get('logout'))
            if r.status_code == 204:
                logger.info('Logged out admin: %s of domain: %s successfully',
                    self.name, self.domain)
            else:
                logger.error('Logout status was unexpected. Received response '
                    'with status code: %s', (r.status_code))

        except requests.exceptions.SSLError as e:
            logger.error('SSL exception thrown during logout: %s', e)
        except requests.exceptions.ConnectionError as e:
            logger.error('Connection error on logout: %s', e)
        finally:
            self.entry_points.clear()
            self.manager._deregister(self)
            self._session = None
            try:
                delattr(self, 'current_user')
            except AttributeError:
                pass
        
        logger.debug('Call counters: %s' % smc.api.web.counters)    
        
    def refresh(self):
        """
        Refresh session on 401. This is called automatically if your existing
        session times out and resends the operation/s which returned the
        error.

        :raises SMCConnectionError: Problem re-authenticating using existing
            api credentials
        """
        if self.session and self.session_id: # Did session timeout?
            logger.info('Session timed out, will try obtaining a new session using '
                'previously saved credential information.')
            self.logout() # Force log out session just in case
            return self.login(**self.copy())
        raise SMCConnectionError('Session expired and attempted refresh failed.')        
    
    def switch_domain(self, domain):
        """
        Switch from one domain to another. You can call session.login() with
        a domain key value to log directly into the domain of choice or alternatively
        switch from domain to domain. The user must have permissions to the domain or
        unauthorized will be returned. In addition, when switching domains, you will
        be logged out of the current domain to close the connection pool associated
        with the previous session. This prevents potentially excessive open
        connections to SMC
        ::
        
            session.login() # Log in to 'Shared Domain'
            ...
            session.switch_domain('MyDomain')
        
        :raises SMCConnectionError: Error logging in to specified domain.
            This typically means the domain either doesn't exist or the
            user does not have privileges to that domain.
        """
        if self.domain != domain:
            if self in self.manager: # Exit current domain
                self.logout()
            logger.info('Switching to domain: %r and creating new session', domain)
            params = self.copy()
            params.update(domain=domain)
            self.login(**params)
    
    def set_retry_on_busy(self, total=5, backoff_factor=0.1, status_forcelist=None, **kwargs):
        """
        Mount a custom retry object on the current session that allows service level
        retries when the SMC might reply with a Service Unavailable (503) message.
        This can be possible in larger environments with higher database activity.
        You can all this on the existing session, or provide as a dict to the login
        constructor.
        
        :param int total: total retries
        :param float backoff_factor: when to retry
        :param list status_forcelist: list of HTTP error codes to retry on
        :param list method_whitelist: list of methods to apply retries for, GET, POST and
            PUT by default
        :return: None
        """
        if self.session:
            from requests.adapters import HTTPAdapter
            from requests.packages.urllib3.util.retry import Retry
    
            method_whitelist = kwargs.pop('method_whitelist', []) or ['GET', 'POST', 'PUT']
            status_forcelist = frozenset(status_forcelist) if status_forcelist else frozenset([503])
            retry = Retry(
                total=total,
                backoff_factor=backoff_factor,
                status_forcelist=status_forcelist,
                method_whitelist=method_whitelist)
            
            for proto_str in ('http://', 'https://'):
                self.session.mount(proto_str, HTTPAdapter(max_retries=retry))
            logger.debug('Mounting retry object to HTTP session: %s' % retry) 
    
    def copy(self):
        # Copy the relevant parameters to make another session login
        # using the existing information
        params = copy.copy(self._params)
        kwargs = params.pop('kwargs', {})
        params.update(**kwargs)
        return params
    
    def _get_log_schema(self):
        """
        Get the log schema for this SMC version.
        
        :return: dict
        """
        if self.session and self.session_id:
            schema = '{}/{}/monitoring/log/schemas'.format(self.url, self.api_version)
            
            response = self.session.get(
                url=schema,
                headers={'cookie': self.session_id,
                         'content-type': 'application/json'})

            if response.status_code in (200, 201):
                return response.json()
                

class Credential(object):
    """
    Provider for authenticating the user. LMS Login is a user created within
    the SMC as a normal administrative account. Login is the standard way of
    using an API client and key as password.
    The key of the CredentialMap also indicates the entry point for which to
    POST the authentication.
    """
    CredentialMap = {
        'lms_login': ('login', 'pwd'),
        'login': ('api_key',)
    }
    
    def __init__(self, api_key=None, login=None, pwd=None):
        self._api_key = api_key
        self._login = login
        self._pwd = pwd
    
    @property
    def provider_name(self):
        return 'login' if self._api_key else 'lms_login'
    
    def get_provider_entry_point(self, url, api_version):
        return '{url}/{api_version}/{provider_name}'.format(
            url=url,
            api_version=api_version,
            provider_name=self.provider_name)

    @property
    def has_credentials(self):
        """
        Does this session have valid credentials
        
        :rtype: bool
        """
        return all([
            getattr(self, '_%s' % field, None) is not None
            for field in self.CredentialMap.get(self.provider_name)])


def load_entry_points(self):
    try:
        r = self.session.get('{url}/{api_version}/api'.format(
                url=self.url, api_version=self.api_version))
        
        if r.status_code == 200:
            result_list = json.loads(r.text)

            self._resource = Resource(result_list['entry_point'])
            logger.debug("Loaded entry points with obtained session.")
        
        else:
            raise SMCConnectionError(
                'Invalid status received while getting entry points from SMC. '
                'Status code received %s. Reason: %s' % (r.status_code, r.reason))
    
    except requests.exceptions.RequestException as e:
        raise SMCConnectionError(e)


def available_api_versions(base_url, timeout=10, verify=True):
    """
    Get all available API versions for this SMC

    :return version numbers
    :rtype: list
    """
    try:
        r = requests.get('%s/api' % base_url, timeout=timeout,
                         verify=verify)  # no session required
        
        if r.status_code == 200:
            j = json.loads(r.text)
            versions = []
            for version in j['version']:
                versions.append(version['rel'])
            return versions
        
        raise SMCConnectionError(
            'Invalid status received while getting entry points from SMC. '
            'Status code received %s. Reason: %s' % (r.status_code, r.reason))

    except requests.exceptions.RequestException as e:
        raise SMCConnectionError(e)


def get_api_version(base_url, api_version=None, timeout=10, verify=True):
    """
    Get the API version specified or resolve the latest version

    :return api version
    :rtype: float
    """
    versions = available_api_versions(base_url, timeout, verify)
    
    newest_version = max([float(i) for i in versions])
    if api_version is None:  # Use latest
        api_version = newest_version
    else:
        if api_version not in versions:
            api_version = newest_version
    
    return api_version

