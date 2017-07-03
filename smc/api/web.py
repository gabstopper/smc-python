"""
Session management for SMC client connections
When a session is first set up using login(), this persists for the duration
of the python run. Run logout() after to remove the session from the SMC
server.

SSL certificates are not verified to the CA authority, need to implement for
urllib3:
https://urllib3.readthedocs.io/en/latest/user-guide.html#ssl
"""
import os.path
import collections
import requests
import logging
from smc.api.exceptions import SMCOperationFailure, SMCConnectionError

logger = logging.getLogger(__name__)


class SMCAPIConnection(object):
    """
    Represents the ReST methods used to perform operations against the
    SMC API.

    :param session: :py:class:`smc.api.session.Session` object
    """
    GET = 'GET'
    PUT = 'PUT'
    POST = 'POST'
    DELETE = 'DELETE'

    def __init__(self, session):
        self._session = session
        self.timeout = self._session.timeout

    @property
    def session(self):
        return self._session.session

    def send_request(self, method, request):
        """
        Send request to SMC
        """
        if self.session:
            try:
                method = method.upper() if method else ''

                if method == SMCAPIConnection.GET:
                    if request.filename:  # File download request
                        return self.file_download(request)

                    response = self.session.get(request.href,
                                                params=request.params,
                                                headers=request.headers,
                                                timeout=self.timeout)
                    response.encoding = 'utf-8'

                    logger.debug(vars(response))
                    counters.update(read=1)

                    if response.status_code not in (200, 304):
                        raise SMCOperationFailure(response)

                elif method == SMCAPIConnection.POST:
                    if request.files:  # File upload request
                        return self.file_upload(request)

                    response = self.session.post(request.href,
                                                 # data=json.dumps(request.json),
                                                 json=request.json,
                                                 headers=request.headers,
                                                 params=request.params)
                    response.encoding = 'utf-8'

                    logger.debug(vars(response))
                    counters.update(create=1)

                    if response.status_code not in (200, 201, 202):
                        # 202 is asynchronous response with follower link
                        raise SMCOperationFailure(response)

                elif method == SMCAPIConnection.PUT:
                    # Etag should be set in request object
                    request.headers.update(Etag=request.etag)

                    response = self.session.put(request.href,
                                                json=request.json,
                                                params=request.params,
                                                headers=request.headers)

                    logger.debug(vars(response))
                    counters.update(update=1)

                    if response.status_code != 200:
                        raise SMCOperationFailure(response)

                elif method == SMCAPIConnection.DELETE:
                    response = self.session.delete(request.href,
                                                   headers=request.headers)

                    counters.update(delete=1)

                    # Conflict (409) if ETag is not current
                    if response.status_code in (409,):
                        req = self.session.get(request.href)
                        etag = req.headers.get('ETag')
                        response = self.session.delete(
                            request.href,
                            headers={'if-match': etag})

                    response.encoding = 'utf-8'

                    if response.status_code not in (200, 204):
                        raise SMCOperationFailure(response)

                else:  # Unsupported method
                    return SMCResult(msg='Unsupported method: %s' % method)

            except SMCOperationFailure as error:
                if error.code in (401,):
                    self._session.refresh()
                    return self.send_request(method, request)
                raise error
            except requests.exceptions.RequestException as e:
                raise SMCConnectionError(
                    "Connection problem to SMC, ensure the "
                    "API service is running and host is correct: %s, "
                    "exiting." % e)
            else:
                return SMCResult(response)
        else:
            raise SMCConnectionError(
                "No session found. Please login to continue")

    def file_download(self, request):
        """
        Called when GET request specifies a filename to retrieve.
        """
        logger.debug(vars(request))
        response = self.session.get(request.href,
                                    params=request.params,
                                    headers=request.headers,
                                    stream=True)

        if response.status_code == 200:
            logger.debug("Streaming to file... Content length: {}"
                         .format(len(response.content)))
            try:
                path = os.path.abspath(request.filename)
                logger.debug("Operation: {}, saving to file: {}"
                             .format(request.href, path))
                with open(path, "wb") as handle:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            handle.write(chunk)
                            handle.flush()
            except IOError as e:
                raise IOError('Error attempting to save to file: {}'.format(e))

            result = SMCResult(response)
            result.content = path
            return result
        else:
            raise SMCOperationFailure(response)

    def file_upload(self, request):
        """
        Perform a file upload POST to SMC. Request should have the
        files attribute set which will be an open handle to the
        file that will be binary transfer.
        """
        logger.debug(vars(request))
        response = self.session.post(request.href,
                                     params=request.params,
                                     files=request.files
                                     )
        if response.status_code == 202:
            logger.debug('Success sending file in elapsed time: {}'
                         .format(response.elapsed))
            return SMCResult(response)

        raise SMCOperationFailure(response)


class SMCResult(object):
    """
    SMCResult will store the return data for operations performed against the
    SMC API. If the function returns an SMCResult, the following attributes
    are set. Note: SMC API will return a list if searches are done and a dict
    if the attempt is made to get the element directly from href.

    Instance attributes:

    :ivar str etag: etag from HTTP GET, representing unique value from server
    :ivar str href: href of location header if it exists
    :ivar str content: content if return was application/octet
    :ivar str msg: error message, if set
    :ivar int code: http code
    :ivar dict json: element full json
    """

    def __init__(self, respobj=None, msg=None):
        self.etag = None
        self.href = None
        self.content = None
        self.msg = msg  # Only set in case of error
        self.code = None
        self.json = self._unpack_response(respobj)  # list or dict

    def _unpack_response(self, response):
        if response:
            self.code = response.status_code
            self.href = response.headers.get('location')
            self.etag = response.headers.get('ETag')
            if response.headers.get('content-type') == 'application/json':
                try:
                    result = response.json()
                except ValueError:
                    result = None
                # Search results return list, direct link fetch
                # will return a dict or list
                if result:
                    if 'result' in result:
                        self.json = result.get('result')
                    else:
                        self.json = result
                else:
                    self.json = result  # Empty dict
                return self.json
            elif response.headers.get('content-type') == 'application/octet-stream':
                self.content = response.text if response.text else None
            elif response.headers.get('content-type') == 'text/plain':
                self.content = response.text if response.text else None

    def __str__(self):
        sb = []
        for key in self.__dict__:
            sb.append(
                "{key}='{value}'".format(
                    key=key,
                    value=self.__dict__[key]))
        return ', '.join(sb)


counters = collections.Counter(
    {'read': 0, 'create': 0, 'update': 0, 'delete': 0, 'cache': 0})
