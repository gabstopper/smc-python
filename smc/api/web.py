"""
Session management for SMC client connections
When a session is first set up using login(), this persists for the duration 
of the python run. Run logout() after to remove the session from the SMC server.
"""

import os.path
import requests
import json
import logging
from smc.api.exceptions import SMCOperationFailure, SMCConnectionError

logger = logging.getLogger(__name__)

def counted(f):
    def wrapped(*args, **kwargs):
        wrapped.calls += 1
        return f(*args, **kwargs)
    wrapped.calls = 0
    return wrapped

class SMCAPIConnection(object):
    """
    Represents the ReST methods used to perform operations against the
    SMC API. 
    
    :param session: :py:class:`smc.api.session.Session` object
    """
    def __init__(self, session):
        self._session = session
    
    @property
    def session(self):
        return self._session.session

    @counted
    def http_get(self, href, params=None, stream=False, filename=None):
        """
        Get data object from SMC
        If response code is success, results are returned with etag
        :param href: fully qualified href for resource
        :param params: uri parameters
        :param stream: used for file download
        :type stream: boolean
        :param filename: name of file to save content to
        :return SMCResult object with json data and etag attrs
        :raise SMCOperationFailure if non-http 200 response received
        """
        try:
            if self.session:
                if filename and stream == True: #TODO: this is a temp hack
                    r = self.session.get(href, params=params, 
                                         stream=True)
                    if r.status_code == 200:
                        logger.debug("Streaming to file... Content length: %s", len(r.content))
                        try:
                            path = os.path.abspath(filename)
                            logger.debug("Operation: %s, saving to file: %s", href, path)
                            with open(path, "wb") as handle:
                                for data in r.iter_content():
                                    handle.write(data)
                        except IOError:
                            raise
                    result = SMCResult(r)
                    result.content = path
                    return result
                r = self.session.get(href, params=params, timeout=15)               
                if r.status_code == 200:
                    logger.debug("HTTP get result: %s", r.text)
                    return SMCResult(r)
                elif r.status_code == 401:
                    self._session.refresh() #session timed out
                    return self.http_get(href)
                else:
                    logger.error("HTTP get returned non-http 200 code [%s] "
                                 "for href: %s", r.status_code, href)
                    raise SMCOperationFailure(r)
            else:
                raise SMCConnectionError("No session found. Please login to continue")

        except requests.exceptions.RequestException as e:
            raise SMCConnectionError("Connection problem to SMC, ensure the "
                            "API service is running and host is correct: %s, "
                            "exiting." % e)

    def http_post(self, href, data, params=None):
        """
        Add object to SMC
        If response code is success, return href to new object location
        If not success, raise exception, caught in middle tier calling method
        
        :param href: entry point to add specific object type
        :param data: json document with object def
        :param uri (optional): not implemented
        :return SMCResult
        :raise SMCOperationFailure in case of non-http 201 return
        """
        try:
            logger.debug('POST request with href: {}, params: {}, data:{}'.format(\
                                            href, params, data))
            if self.session:
                r = self.session.post(href,
                            data=json.dumps(data),
                            headers={'content-type': 'application/json'},
                            params=params
                            )
                if r.status_code == 200 or r.status_code == 201:
                    logger.debug("Success, returning link for new element: %s", \
                                 r.headers.get('location'))
                    return SMCResult(r)
                elif r.status_code == 202:
                    #in progress
                    logger.debug("Asynchronous response received, monitor progress at link: %s", r.content)
                    return SMCResult(r)
                elif r.status_code == 401:
                    self._session.refresh()
                    return self.http_post(href, data)
                else:
                    raise SMCOperationFailure(r)
            else:
                raise SMCConnectionError("No session found. Please login to continue")
            
        except requests.exceptions.RequestException as e:
            raise SMCConnectionError("Connection problem to SMC, ensure the "
                                     "API service is running and host is "
                                     "correct: %s, exiting." % e)

    def http_put(self, href, data, etag, params=None):
        """
        Change state of existing SMC object
        :param href: href of resource location
        :param data: json encoded document
        :param etag: required by SMC, retrieve first via http get
        :return SMCResult
        :raise SMCOperationFailure in case of non-http 200 return
        """
        try:
            if self.session:
                r = self.session.put(href,
                    data = json.dumps(data),
                    params = params,
                    headers={'content-type': 'application/json', 'Etag': etag}
                    )
                if r.status_code == 200:
                    logger.debug("Successful modification, headers returned: %s", \
                                  r.headers)
                    return SMCResult(r)
                elif r.status_code == 401:
                    self._session.refresh()
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
        :return SMCResult: All result SMCResult fields will be None
        :raise SMCOperationFailure for non-http 204 code, msg attribute will have error
        """
        try:
            if self.session:
                r = self.session.delete(href)
                if r.status_code == 204:
                    return SMCResult(r)
                elif r.status_code == 401:
                    self._session.refresh()
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
    SMCResult will store the return data for operations performed against the
    SMC API. If the function returns an SMCResult, the following attributes are
    set.
    
    Instance attributes:
    
    :ivar etag: etag from HTTP GET, representing unique value from server
    :ivar href: href of location header if it exists
    :ivar content: content if return was application/octet
    :ivar msg: error message, if set
    :ivar json: element full json
    """
    def __init__(self, respobj=None, msg=None):
        self.etag = None
        self.href = None
        self.content = None
        self.msg = msg
        self.code = None
        self.json = self.extract(respobj) #: list

    def extract(self, response):
        if response:
            self.code = response.status_code
            self.href = response.headers.get('location')
            self.etag = response.headers.get('ETag')
            if response.headers.get('content-type') == 'application/json':
                result = json.loads(response.text)
                if result:
                    if 'result' in result:
                        self.json = result.get('result')
                    else:
                        self.json = result
                else:
                    self.json = []
                return self.json
            elif response.headers.get('content-type') == 'application/octet-stream':
                self.content = response.text
            
    def __str__(self):
        sb = []
        for key in self.__dict__:
            sb.append("{key}='{value}'".format(key=key, value=self.__dict__[key]))
        return ', '.join(sb)
                
    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.__dict__)