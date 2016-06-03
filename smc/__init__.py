from smc.actions import *
from smc.api.web import *

# Set default logging handler to avoid "No handler found" warnings.
try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

logging.getLogger(__name__).addHandler(NullHandler())
#logging.basicConfig(level=logging.INFO)
logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=logging.INFO)