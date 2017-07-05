import logging
from smc.api.session import Session

__author__ = 'David LePage'
__version__ = '0.5.5'

# Default SMC Session
session = Session()


def set_stream_logger(name='smc', level=logging.DEBUG, format_string=None):
    """
    Stream logger convenience function to log to console
    """
    if format_string is None:
        format_string = "%(asctime)s %(name)s [%(levelname)s] %(message)s"

    logger = logging.getLogger(name)
    logger.setLevel(level)
    handler = logging.StreamHandler()
    handler.setLevel(level)
    formatter = logging.Formatter(format_string)
    handler.setFormatter(formatter)
    logger.addHandler(handler)


# Set default logging handler to avoid "No handler found" warnings.
# Best practice from http://docs.python-guide.org/en/latest/writing/logging/
try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

logging.getLogger(__name__).addHandler(NullHandler())
