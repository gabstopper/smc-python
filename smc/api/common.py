"""
Middle tier helper module to wrap CRUD operations and catch exceptions

SMCRequest is the general data structure that is sent to the send_request
method in smc.api.web.SMCConnection to submit the data to the SMC.
"""
from smc.api.web import send_request
from smc.api.exceptions import SMCOperationFailure, SMCConnectionError, \
    SessionManagerNotFound


def _get_session(session_manager=None):
    if not session_manager:
        session_manager = getattr(SMCRequest, '_session_manager')
    try:
        return session_manager.get_default_session() if not \
            session_manager._session_hook else \
            session_manager._session_hook(session_manager)

    except AttributeError:
        raise SessionManagerNotFound


class SMCRequest(object):
    """
    SMCRequest represents the data structure that will be submitted to the web
    layer for submission to the SMC API.

    :param str href: href for request, required by all methods
    :param dict json: json to submit, required by create, update
    :param dict params: query string parameters
    :param str filename: name of file for download, optional for create
    :param str etag: etag of element, required for update
    """
    _session_manager = None
    
    def __init__(self, href=None, json=None, params=None, filename=None,
                 etag=None, user_session=None, **kwargs):
        
        #: Filename if a file download is requested
        self.filename = filename
        #: dictionary of query parameters
        self.params = params
        #: href for this request
        self.href = href
        #: ETag for PUT or DELETE request modifications
        self.etag = etag
        #: JSON data to send in request
        self.json = {} if json is None else json
        
        # Only used in the case of streaming file download/upload
        self.files = None
        #: Default headers
        self.headers = {'Content-Type': 'application/json'}
        
        # Optional user session for this request
        #self.user_session = user_session # smc.api.session.Session
        
        for k, v in kwargs.items():
            setattr(self, k, v)
    
    def __call__(self, session):
        pass
    
    def create(self):
        return self._make_request(method='POST')

    def delete(self):
        return self._make_request(method='DELETE')

    def update(self):
        return self._make_request(method='PUT')

    def read(self):
        return self._make_request(method='GET')
    
    def _make_request(self, method):
        err = None
        result = None
        try:
            # Obtain the session
            session = _get_session(getattr(self, '_session_manager', None))
            
            if method == 'GET':
                if not self.href:
                    self.href = session.entry_points.get('elements')
            
            result = send_request(session, method, self)
            
        except SMCOperationFailure as e:
            result = e.smcresult
            try:
                err = self.exception(result.msg)  # Exception set
            except AttributeError:
                pass
        except (SessionManagerNotFound, SMCConnectionError,
                IOError, TypeError) as e:
            err = e
        finally:
            if err:
                raise err
            return result

    def __str__(self):
        sb = []
        for key in self.__dict__:
            sb.append(
                "{key}='{value}'".format(
                    key=key,
                    value=self.__dict__[key]))
        return 'SMCRequest({})'.format(','.join(sb))    


def entry_point():
    return _get_session().entry_points


def fetch_entry_point(name):
    """
    Get the entry point href based on the input name. Entry points are
    cached during the connection and can be accessed through the session
    by calling session.cache.get_all_entry_points()

    :method: GET
    :param str name: valid element entry point, i.e. 'host', 'iprange', etc
    :raises UnsupportedEntryPoint: entry point not available in this API version
    :return: href pulled from API cache
    :rtype: str
    """
    return entry_point().get(name) # from entry point cache

    
def fetch_meta_by_name(name, filter_context=None, exact_match=True):
    """
    Find the element based on name and optional filters. By default, the
    name provided uses the standard filter query. Additional filters can
    be used based on supported collections in the SMC API.

    :method: GET
    :param str name: element name, can use * as wildcard
    :param str filter_context: further filter request, i.e. 'host', 'group',
        'single_fw', 'network_elements', 'services',
        'services_and_applications'
    :param bool exact_match: Do an exact match by name, note this still can
        return multiple entries
    :rtype: SMCResult
    """
    result = SMCRequest(
        params={'filter': name,
                'filter_context': filter_context,
                'exact_match': exact_match}).read()
    
    if not result.json:
        result.json = []
    return result

