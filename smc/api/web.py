"""
Web actions to SMC

SSL certificates are not verified to the CA authority, need to implement for
urllib3:
https://urllib3.readthedocs.io/en/latest/user-guide.html#ssl
"""
import json
import os.path
import collections
import logging
import requests
from smc.api.exceptions import SMCOperationFailure, SMCConnectionError


logger = logging.getLogger(__name__)


class CacheEncoder(json.JSONEncoder):
    def default(self, o):
        try:
            return o.data
        except AttributeError:
            json.JSONEncoder.default(self, o)


GET = 'GET'
PUT = 'PUT'
POST = 'POST'
DELETE = 'DELETE'

        
def send_request(user_session, method, request):
    """
    Send request to SMC
    
    :param Session user_session: session object
    :param str method: method for request
    :param SMCRequest request: request object
    :raises SMCOperationFailure: failure with reason
    :rtype: SMCResult
    """
    if user_session.session:
        session = user_session.session # requests session
        try:
            method = method.upper() if method else ''
            
            if method == GET:
                if request.filename:  # File download request
                    return file_download(user_session, request)
                
                response = session.get(
                    request.href,
                    params=request.params,
                    headers=request.headers,
                    timeout=user_session.timeout)
                
                response.encoding = 'utf-8'
                
                counters.update(read=1)

                if logger.isEnabledFor(logging.DEBUG):
                    debug(response)
                
                if response.status_code not in (200, 204, 304):
                    raise SMCOperationFailure(response)

            elif method == POST:
                if request.files:  # File upload request
                    return file_upload(user_session, method, request)
                
                response = session.post(
                    request.href,
                    data=json.dumps(request.json, cls=CacheEncoder),
                    headers=request.headers,
                    params=request.params)
                
                response.encoding = 'utf-8'

                counters.update(create=1)
                if logger.isEnabledFor(logging.DEBUG):
                    debug(response)
                
                if response.status_code not in (200, 201, 202):
                    # 202 is asynchronous response with follower link
                    raise SMCOperationFailure(response)

            elif method == PUT:
                if request.files:  # File upload request
                    return file_upload(user_session, method, request)
                
                # Etag should be set in request object
                request.headers.update(Etag=request.etag)
                
                response = session.put(
                    request.href,
                    data=json.dumps(request.json, cls=CacheEncoder),
                    params=request.params,
                    headers=request.headers)

                counters.update(update=1)
                
                if logger.isEnabledFor(logging.DEBUG):
                    debug(response)

                if response.status_code != 200:
                    raise SMCOperationFailure(response)

            elif method == DELETE:
                response = session.delete(
                    request.href,
                    headers=request.headers)

                counters.update(delete=1)

                # Conflict (409) if ETag is not current
                if response.status_code in (409,):
                    req = session.get(request.href)
                    etag = req.headers.get('ETag')
                    response = session.delete(
                        request.href,
                        headers={'if-match': etag})

                response.encoding = 'utf-8'

                if logger.isEnabledFor(logging.DEBUG):
                    debug(response)
                
                if response.status_code not in (200, 204):
                    raise SMCOperationFailure(response)

            else:  # Unsupported method
                return SMCResult(msg='Unsupported method: %s' % method,
                    user_session=user_session)

        except SMCOperationFailure as error:
            if error.code in (401,):
                user_session.refresh()
                return send_request(user_session, method, request)
            raise error
        except requests.exceptions.RequestException as e:
            raise SMCConnectionError('Connection problem to SMC, ensure the API '
                'service is running and host is correct: %s, exiting.' % e)
        else:
            return SMCResult(response, user_session=user_session)
    else:
        raise SMCConnectionError('No session found. Please login to continue')
            

def file_download(user_session, request):
    """
    Called when GET request specifies a filename to retrieve.
    
    :param Session user_session: session object
    :param SMCRequest request: request object
    :raises SMCOperationFailure: failure with reason
    :rtype: SMCResult
    """
    logger.debug('Download file: %s', vars(request))
    response = user_session.session.get(
        request.href,
        params=request.params,
        headers=request.headers,
        stream=True)

    if response.status_code == 200:
        logger.debug('Streaming to file... Content length: %s', len(response.content))
        try:
            path = os.path.abspath(request.filename)
            logger.debug('Operation: %s, saving to file: %s', request.href, path)

            with open(path, "wb") as handle:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        handle.write(chunk)
                        handle.flush()
        except IOError as e:
            raise IOError('Error attempting to save to file: {}'.format(e))

        result = SMCResult(response, user_session=user_session)
        result.content = path
        return result
    else:
        raise SMCOperationFailure(response)


def file_upload(user_session, method, request):
    """
    Perform a file upload PUT/POST to SMC. Request should have the
    files attribute set which will be an open handle to the
    file that will be binary transfer.
    
    :param Session user_session: session object
    :param str method: method to use, could be put or post
    :param SMCRequest request: request object
    :raises SMCOperationFailure: failure with reason
    :rtype: SMCResult
    """
    logger.debug('Upload: %s', vars(request))
    http_command = getattr(user_session.session, method.lower())
    
    try:
        response = http_command(
            request.href,
            params=request.params,
            files=request.files)
    except AttributeError:
        raise TypeError('File specified in request was not readable: %s' % request.files)
    else:
        if response.status_code in (200, 201, 202, 204):
            logger.debug('Success sending file in elapsed time: %s', response.elapsed)
            return SMCResult(response, user_session=user_session)
        
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

    def __init__(self, respobj=None, msg=None, user_session=None):
        self.etag = None
        self.href = None
        self.content = None
        self.msg = msg  # Only set in case of error
        self.code = None
        self.user_session = user_session
        self.domain = getattr(user_session, 'domain', None)
        self.json = self._unpack_response(respobj)  # list or dict

    def _unpack_response(self, response):
        if response:
            self.code = response.status_code
            self.href = response.headers.get('location')
            self.etag = response.headers.get('ETag')
            content_type = response.headers.get('content-type', '')
            
            if content_type == 'application/json':
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
            
            elif 'text/plain' in content_type or 'application/octet-stream' in \
                content_type:
                self.content = response.text if response.text else None
            
    def __str__(self):
        sb = []
        for key in self.__dict__:
            sb.append(
                "{key}='{value}'".format(
                    key=key,
                    value=self.__dict__[key]))
        return ', '.join(sb)


def debug(response):
    logger.debug('Request method: %s', response.request.method)
    logger.debug('Request URL: %s', response.url)
    logger.debug('Request headers:')
    for k, v in response.request.headers.items():
        logger.debug('\t%r: %r', k, v)
    logger.debug('Request body:')
    logger.debug('%s', response.request.body)
    logger.debug('Response status: %s', response.status_code)
    logger.debug('Response headers:')
    for k, v in response.headers.items():
        logger.debug('\t%r: %r', k, v)
    logger.debug('Response content:')
    logger.debug('%s', response.text)
    
                    
counters = collections.Counter(
    {'read': 0, 'create': 0, 'update': 0, 'delete': 0, 'cache': 0})
