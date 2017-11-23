import logging
import smc.api.session

__author__ = 'David LePage'
__version__ = '0.5.7'

# Default SMC Session
session = smc.api.session.Session()


# Set default logging handler to avoid "No handler found" warnings.
# Best practice from http://docs.python-guide.org/en/latest/writing/logging/
try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

logging.getLogger(__name__).addHandler(NullHandler())
