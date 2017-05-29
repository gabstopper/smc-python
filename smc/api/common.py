"""
Middle tier helper module to wrap CRUD operations and catch exceptions

SMCRequest is the general data structure that is sent to the prepared_request
method in smc.api.web.SMCConnection to submit the data to the SMC.
"""
import logging
from smc import session
from smc.api.exceptions import SMCOperationFailure, SMCConnectionError,\
    UnsupportedEntryPoint
from smc.base.util import unicode_to_bytes

logger = logging.getLogger(__name__)


def method(method):
    def _method(f):
        def wrapper(self, *args):
            setattr(self, '_method', method)
            return f(self, *args)
        return wrapper
    return _method


class _RequestHandler(object):
    def __init__(self, **kwargs):
        self._method = None
        self.files = None
        self.headers = {'content-type': 'application/json'}

    @property
    def method(self):
        return self._method

    def _make_request(self):
        err = None
        result = None
        try:
            if self.method == 'GET':
                if not self.href:
                    self.href = session.entry_points.get('elements')
            result = session.connection.send_request(self.method, self)

        except SMCOperationFailure as e:
            result = e.smcresult
            try:
                err = self.exception(result.msg)  # Exception set
            except AttributeError:
                pass
        except SMCConnectionError as e:
            err = e
        except TypeError as e:
            err = e
        except IOError as e:
            err = e
        finally:
            if err:
                raise err
            logger.debug(result)
            return result


class SMCRequest(_RequestHandler):
    """
    SMCRequest represents the data structure that will be submitted to the web
    layer for submission to the SMC API.

    :param str href: href for request, required by all methods
    :param dict json: json to submit, required by create, update
    :param dict params: query string parameters
    :param str filename: name of file for download, optional for create
    :param str etag: etag of element, required for update
    """

    def __init__(self, href=None, json=None, params=None, filename=None,
                 etag=None, **kwargs):
        _RequestHandler.__init__(self)
        #: Filename if a file download is requested
        self.filename = filename
        #: dictionary of query parameters
        self.params = params
        #: href for this request
        self.href = href
        #: ETag for PUT request modifications
        self.etag = etag
        #: JSON data to send in request
        self.json = {} if json is None else json

        for k, v in kwargs.items():
            setattr(self, k, v)

    @method('POST')
    def create(self):
        return self._make_request()

    @method('DELETE')
    def delete(self):
        return self._make_request()

    @method('PUT')
    def update(self):
        return self._make_request()

    @method('GET')
    def read(self):
        return self._make_request()

    def __repr__(self):
        return '<SMCRequest [%s]>' % (self.method)


def fetch_entry_point(name):
    """
    Get the entry point href based on the input name. Entry points are
    cached during the connection and can be accessed through the session
    by calling session.cache.get_all_entry_points()

    :method: GET
    :param str name: valid element entry point, i.e. 'host', 'iprange', etc
    :return: href pulled from API cache
    :rtype: str
    """
    try:
        return session.entry_points.get(name)  # from entry point cache
    except UnsupportedEntryPoint:
        raise


def fetch_no_filter(entry_point, filter=None):  # @ReservedAssignment
    """
    Fetch elements with no filter_context filter. This will pull from the
    entry point base.
    """
    return SMCRequest(
        href=session.entry_points.get(entry_point),
        params={'filter': filter}
        ).read().json
    

def fetch_href_by_name(name,
                       filter_context=None,
                       exact_match=True,
                       domain=None):
    """
    Find the element based on name and optional filters. By default, the
    name provided uses the standard filter query. Additional filters can
    be used based on supported collections in the SMC API. This is generally
    not called directly, rather it is easier to use wrapper search utilities
    in :py:mod:`smc.actions.search`

    :method: GET
    :param str name: element name, can use * as wildcard
    :param str filter_context: further filter request, i.e. 'host', 'group',
        'single_fw', 'network_elements', 'services',
        'services_and_applications'
    :param bool exact_match: Do an exact match by name, note this still can
        return multiple entries
    :param str domain: specify domain in which to query
    :return: :py:class:`smc.api.web.SMCResult`
    """
    result = SMCRequest(params={'filter': name,
                                'filter_context': filter_context,
                                'exact_match': exact_match}).read()
    if result.json:
        if len(result.json) > 1:
            result.msg = "More than one search result found. Try using a "\
                         "filter based on element type"
        else:
            result.href = result.json[0].get('href')
    else:
        if not result.msg:
            result.msg = "No results found for: {}".format(
                unicode_to_bytes(name))
        result.json = []
    return result


def fetch_json_by_name(name):
    """
    Fetch json based on the element name
    First gets the href based on a search by name, then makes a
    second query to obtain the element json

    :method: GET
    :param str name: element name
    :return: :py:class:`smc.api.web.SMCResult`
    """
    result = fetch_href_by_name(name)
    if result.href:
        result = fetch_json_by_href(result.href)
    return result


def fetch_json_by_href(href, params=None):
    """
    Fetch json for element by using href. Params should be key/value
    pairs. For example {'filter': 'myfilter'}

    :method: GET
    :param str href: href of the element
    :params dict params: optional search query parameters
    :return: :py:class:`smc.api.web.SMCResult`
    """
    result = SMCRequest(href=href,
                        params=params).read()
    if result:
        result.href = href
    return result


def fetch_json_by_post(href, json=None):
    """
    Some search functions require that query parameters be embedded
    in the body of the request, therefore require POST.

    :param str href: href of element to search for
    :return :py:class: `smc.api.web.SMCResult`
    """
    return SMCRequest(href=href,
                      json=json).create()
