import logging
import smc.api.session

from .__version__ import __description__, __url__, __version__
from .__version__ import __author__, __author_email__, __license__


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
