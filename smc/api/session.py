"""
Session module for tracking existing connection state to SMC
"""
import json
import logging
import collections
import requests
import smc.api.web
from smc.api.exceptions import SMCConnectionError, UnsupportedEntryPoint,\
    ConfigLoadError
from smc.api.configloader import load_from_file, load_from_environ

# requests.packages.urllib3.disable_warnings()

logger = logging.getLogger(__name__)


class _EntryPoint(object):
    def __init__(self, _listof):
        self.entries = _listof

    def __iter__(self):
        for entry in self.entries:
            yield EntryPoint(
                href=entry.get('href'),
                rel=entry.get('rel'))

    def __len__(self):
        return len(self.entries)

    def get(self, rel):
        for link in iter(self):
            if link.rel == rel:
                return link.href
        raise UnsupportedEntryPoint(
            "The specified entry point '{}' was not found in this "
            "version of the SMC API. Check the element documentation "
            "to determine the correct version and specify the api_version "
            "parameter during session.login() if necessary.".format(rel))

    def all(self):
        """
        Return all available rel's for this API
        """
        return [entry_rel.rel for entry_rel in iter(self)]


EntryPoint = collections.namedtuple('EntryPoint', 'href rel')


class Session(object):

    AUTOCOMMIT = False
    _MODS_LOADED = False

    def __init__(self):
        self._entry_points = []
        self._api_version = None
        self._session = None
        self._connection = None
        self._url = None
        self._api_key = None
        self._timeout = 10
        self._domain = 'Shared Domain'
        self._extra_args = {}

    @property
    def entry_points(self):
        if not len(self._entry_points):
            raise SMCConnectionError(
                "No entry points found, it is likely there is no valid "
                "login session.")
        return self._entry_points

    @property
    def api_version(self):
        """ API Version """
        return self._api_version

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
    def url(self):
        """ SMC URL """
        return self._url

    @property
    def api_key(self):
        """ SMC Client API key """
        return self._api_key

    @property
    def timeout(self):
        """ Session timeout """
        return self._timeout

    @property
    def domain(self):
        """ Logged in domain """
        return self._domain

    def login(self, url=None, api_key=None, api_version=None,
              timeout=None, verify=True, alt_filepath=None,
              domain=None, **kwargs):
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
        :param str domain: domain to log in to. If domains are not configured, this
            field will be ignored and api client logged in to 'Shared Domain'.
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
        """
        if not url or not api_key:
            # First try load from file
            try:
                cfg = load_from_file(alt_filepath) if alt_filepath\
                    is not None else load_from_file()
            except ConfigLoadError:
                # Last ditch effort, try to load from environment
                cfg = load_from_environ()

            logger.debug('Read config data: %s', cfg)
            url = cfg.get('url')
            api_key = cfg.get('api_key')
            api_version = cfg.get('api_version')
            verify = cfg.get('verify')
            timeout = cfg.get('timeout')
            domain = cfg.get('domain')

        self._url = url
        self._api_key = api_key

        if timeout:
            self._timeout = timeout

        if domain:
            self._domain = domain

        self._api_version = get_api_version(url, api_version, timeout, verify)

        base = get_api_base(url, self.api_version, verify=verify)

        self._entry_points = get_entry_points(base, timeout, verify)

        s = requests.session()  # no session yet

        json={'authenticationkey': self.api_key,
              'domain': domain}

        if kwargs:
            json.update(**kwargs)
            self._extra_args.update(**kwargs)

        r = s.post(
            self.entry_points.get('login'),
            json=json,
            headers={'content-type': 'application/json'},
            verify=verify)

        logger.info("Using SMC API version: %s", self._api_version)

        if r.status_code == 200:
            self._session = s  # session creation was successful
            self._session.verify = verify  # make verify setting persistent
            logger.debug(
                "Login succeeded and session retrieved: %s", self.session_id)

            self._connection = smc.api.web.SMCAPIConnection(self)
        else:
            raise SMCConnectionError(
                "Login failed, HTTP status code: %s and reason: %s" % (
                    r.status_code, r.reason))

        if not self._MODS_LOADED:
            logger.debug('Registering class mappings.')
            # Load the modules to register needed classes
            for pkg in ('smc.policy', 'smc.elements', 'smc.routing',
                        'smc.vpn', 'smc.administration', 'smc.core'):
                import_submodules(pkg, recursive=False)

            self._MODS_LOADED = True

    def logout(self):
        """ Logout session from SMC """
        if self.session:
            try:
                r = self.session.put(self.entry_points.get('logout'))
                if r.status_code == 204:
                    logger.info("Logged out successfully")
                    logger.debug("Call counters: %s" % smc.api.web.counters)
                else:
                    logger.error("Logout status was unexpected. Received response "
                                 "was status code: %s", (r.status_code))
            except requests.exceptions.SSLError as e:
                # When SSL is enabled and verification is disabled, logout may throw an
                # SSL VERIFY FAILED error from requests module. Not sure why, will have
                # to investigate
                logger.error("SSL exception thrown during logout: %s", e)
            finally:
                self.session.cookies.clear()
                self._entry_points = []

    def refresh(self):
        """
        Refresh session on 401. Wrap this in a loop with retries.

        :raises SMCConnectionError
        """
        # Did we already have a session that just timed out
        if self.session and self.api_key and self.url:
            # Try relogging in to refresh, otherwise fail
            logger.info(
                'Session timed out, will try obtaining a new session using '
                'previously saved credential information.')
            self.login(
                url=self.url,
                api_key=self.api_key,
                api_version=self.api_version,
                timeout=self.timeout,
                verify=False,
                domain=self.domain,
                **self._extra_args)
            return
        raise SMCConnectionError('Session expired and attempted refresh failed.')


def get_entry_points(base_url, timeout=10, verify=True):
    """
    Return the entry points in iterable class
    """
    try:
        r = requests.get('%s/api' % (base_url), timeout=timeout,
                         verify=verify)

        if r.status_code == 200:
            j = json.loads(r.text)
            logger.debug("Successfully retrieved API entry points from SMC")

            return _EntryPoint(j['entry_point'])

        else:
            raise SMCConnectionError("Error occurred during initial api "
                                     "request, json was not returned. "
                                     "Return data was: %s" % r.text)

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
        j = json.loads(r.text)
        versions = []
        for version in j['version']:
            versions.append(version['rel'])
        versions = [float(i) for i in versions]
        return versions
    except requests.exceptions.RequestException as e:
            raise SMCConnectionError(e)


def get_api_version(base_url, api_version=None, timeout=10, verify=True):
    """
    Get the API version specified or resolve the latest version

    :return api version
    :rtype: float
    """
    versions = available_api_versions(base_url, timeout, verify)

    if api_version is None:  # Use latest
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

    return api_version


def get_api_base(base_url, api_version=None, verify=True):
    """
    From the base url and optional api version, return the
    fully qualified API base URL

    :rtype: str
    """
    return '{}/{}'.format(
        base_url,
        str(get_api_version(base_url, api_version, verify=verify)))


def import_submodules(package, recursive=True):
    """
    Import all submodules of a module, recursively,
    including subpackages.

    From http://stackoverflow.com/questions/3365740/how-to-import-all-submodules

    :param package: package (name or actual module)
    :type package: str | module
    :rtype: dict[str, types.ModuleType]
    """
    import importlib
    import pkgutil
    if isinstance(package, str):
        package = importlib.import_module(package)
    results = {}
    for _loader, name, is_pkg in pkgutil.walk_packages(package.__path__):
        full_name = package.__name__ + '.' + name
        results[full_name] = importlib.import_module(full_name)
        if recursive and is_pkg:
            results.update(import_submodules(full_name))
