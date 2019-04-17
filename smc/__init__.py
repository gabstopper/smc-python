import atexit
import logging
from smc.api.session import SessionManager
from smc.base.util import import_submodules

from .__version__ import __description__, __url__, __version__
from .__version__ import __author__, __author_email__, __license__


manager = SessionManager.create()
atexit.register(manager.close_all)
 
 
session = manager.get_default_session()
 
 
def get_session_by_user(user):
    """
    Get a session specifically by the user name
    """
    return manager.get_session(user)


# Set default logging handler to avoid "No handler found" warnings.
# Best practice from http://docs.python-guide.org/en/latest/writing/logging/
try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

logging.getLogger(__name__).addHandler(NullHandler())


LOG_FORMAT = '%(asctime)s - %(name)s - [%(levelname)s] - %(message)s'

def set_stream_logger(log_level=logging.DEBUG, format_string=None, logger_name='smc'): 
    """ 
    Stream logger convenience function to log to console
    
    :param int log_level: A log level as specified in the `logging` module
    :param str format_string: Optional format string as specified in the 
        `logging` module
    """ 
    if format_string is None: 
        format_string = LOG_FORMAT
 
    logger = logging.getLogger(logger_name) 
    logger.setLevel(log_level)
    
    # create console handler and set level
    ch = logging.StreamHandler() 
    ch.setLevel(log_level)
    # create formatter
    formatter = logging.Formatter(format_string)
    # add formatter to ch
    ch.setFormatter(formatter) 
    logger.addHandler(ch) 


def set_file_logger(path, log_level=logging.DEBUG, format_string=None, logger_name='smc'):
    """
    Convenience function to quickly configure any level of logging
    to a file.

    :param int log_level: A log level as specified in the `logging` module
    :param str format_string: Optional format string as specified in the 
        `logging` module
    :param str path: Path to the log file.  The file will be created
        if it doesn't already exist.
    """
    if format_string is None: 
        format_string = LOG_FORMAT
    
    log = logging.getLogger(logger_name)
    log.setLevel(log_level)

    # create file handler and set level
    ch = logging.FileHandler(path)
    ch.setLevel(log_level)
    # create formatter
    formatter = logging.Formatter(format_string)
    # add formatter to ch
    ch.setFormatter(formatter)
    # add ch to logger
    log.addHandler(ch)
        

def _import_registry():
    # Load the modules to register needed classes
    # This should be extracted and made dynamic
    for pkg in ('smc.policy', 'smc.elements', 'smc.routing',
                'smc.vpn', 'smc.administration', 'smc.core'):
        import_submodules(pkg)

_import_registry()
    