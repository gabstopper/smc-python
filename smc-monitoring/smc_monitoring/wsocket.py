import os
import ssl
import json
import select
import logging
import threading
from pprint import pformat
from smc import session

import websocket


logger = logging.getLogger(__name__)


def websocket_debug():
    websocket.enableTrace(True)


class FetchAborted(Exception):
    pass

class InvalidFetch(Exception):
    pass

class SessionNotFound(Exception):
    pass


def _get_ca_bundle():
    """  
    If verify=True, then requests is using the built in
    certifi CA database. Attempt to get that path for
    the websocket.
    """
    try:
        import certifi
        return certifi.where()
    except ImportError:
        pass
    

class SMCSocketProtocol(websocket.WebSocket):
    """
    SMCSocketProtocol manages the web socket connection between this
    client and the SMC. It provides the interface to monitor the query
    results and yield them back to the caller as a context manager.
    """
    def __init__(self, query, sock_timeout=3, **kw):
        """
        Initialize the web socket.
        
        :param Query query: Query type from `smc_monitoring.monitors`
        :param int sock_timeout: length of time to wait on a select call
            before trying to receive data. For LogQueries, this should be
            short, i.e. 1 second. For other queries the default is 3 sec.
        :param int max_iterations: for queries that are not 'live', set
            this to supply a max wait time. Calculation is max_iterations *
            sock_timeout.
        :param kw: supported keyword args:
            cert_reqs: ssl.CERT_NONE|ssl.CERT_REQUIRED|ssl.CERT_OPTIONAL
            check_hostname: True|False
            enable_multithread: True|False (Default: True)
        
        .. note:: The keyword args are not required unless you want to override
            default settings. If SSL is used for the SMC session, the settings
            for verifying the server with the root CA is based on whether the
            'verify' setting has been provided with a path to the root CA file.
        """
        if not session.session or not session.session.cookies:
            raise SessionNotFound('No SMC session found. You must first '
                'obtain an SMC session through session.login before making '
                'a web socket connection.')
        
        sslopt = {}
        if session.is_ssl:
            # SSL verification is based on the session settings since the
            # session must be made before calling this class. If verify=True, 
            # try to get the CA bundle from certifi if the package exists
            # Set check_hostname to False because python ssl doesn't appear
            # to validate the subjectAltName properly, however requests does
            # and would have already validated this when the session was set
            # up. This can still be overridden by setting check_hostname=True.
            sslopt.update(
                cert_reqs=ssl.CERT_NONE,
                check_hostname=False)
    
            certfile = session.session.verify
            if certfile:
                if isinstance(certfile, bool): # verify=True
                    certfile = _get_ca_bundle()
                    if certfile is None:
                        certfile = ''
                
                sslopt.update(
                    cert_reqs=kw.pop('cert_reqs', ssl.CERT_REQUIRED),
                    check_hostname=kw.pop('check_hostname', False))
                
                if sslopt.get('cert_reqs') != ssl.CERT_NONE:
                    os.environ['WEBSOCKET_CLIENT_CA_BUNDLE'] = certfile
        
        # Enable multithread locking
        if 'enable_multithread' not in kw:
            kw.update(enable_multithread=True)
           
        super(SMCSocketProtocol, self).__init__(sslopt=sslopt, **kw)
        
        self.query = query
        self.fetch_id = None
        # Inner thread used to keep socket select alive
        self.thread = None
        self.event = threading.Event()
        self.sock_timeout = sock_timeout
            
    def __enter__(self):
        self.connect(
            url=session.web_socket_url + self.query.location,
            cookie=session.session_id)
        
        if self.connected:
            self.settimeout(self.sock_timeout)
            self.on_open()
        return self
      
    def __exit__(self, exctype, value, traceback):
        if exctype in (SystemExit, GeneratorExit):
            return False
        elif exctype in (InvalidFetch,):
            raise FetchAborted(value)
        return True
        
    def on_open(self):
        """
        Once the connection is made, start the query off and
        start an event loop to wait for a signal to
        stop. Results are yielded within receive().
        """
        def event_loop():
            logger.debug(pformat(self.query.request))
            self.send(json.dumps(self.query.request))
            while not self.event.is_set():
                #print('Waiting around on the socket')
                self.event.wait(self.gettimeout())
            
            logger.debug('Event loop terminating.')
    
        self.thread = threading.Thread(
            target=event_loop)
        self.thread.setDaemon(True)
        self.thread.start()
    
    def send_message(self, message):
        """
        Send a message down the socket. The message is expected
        to have a `request` attribute that holds the message to
        be serialized and sent.
        """
        if self.connected:
            self.send(
                json.dumps(message.request))
    
    def abort(self):
        """
        Abort the connection
        """
        logger.info("Abort called, cleaning up.")
        raise FetchAborted
        
    def receive(self):
        """
        Generator yielding results from the web socket. Results
        will come as they are received.
        """
        try:
            while self.connected:
                r, w, e = select.select(
                    (self.sock, ), (), (), 10)
                
                if r:
                    message = json.loads(self.recv())
                    
                    if 'fetch' in message:
                        self.fetch_id = message['fetch']
                    
                    if 'failure' in message:
                        raise InvalidFetch(message['failure'])
                    
                    if 'records' in message:
                        if 'added' in message['records']:
                            num = len(message['records']['added'])
                        else:
                            num = len(message['records'])
                        
                        logger.debug('Query returned %s records.', num)
                    
                    if 'end' in message:
                        logger.debug('Received end message: %s' % message['end'])
                        yield message
                        break
        
                    yield message
    
        except (Exception, KeyboardInterrupt, SystemExit, FetchAborted) as e:
            logger.info('Caught exception in receive: %s', type(e))
            if isinstance(e, (SystemExit, InvalidFetch)):
                # propagate SystemExit, InvalidFetch
                raise
        finally:
            if self.connected:
                if self.fetch_id:
                    self.send(json.dumps({'abort': self.fetch_id}))
                self.close()
    
            if self.thread:
                self.event.set()
                while self.thread.isAlive():
                    self.event.wait(1)
            
            logger.info('Closed web socket connection normally.')

