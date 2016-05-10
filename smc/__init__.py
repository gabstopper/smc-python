#from smc.web_api import *
#from smc.elements import *
#from smc.actions import *
from smc.actions import *
from smc.api.web import *


#import logging
# Set default logging handler to avoid "No handler found" warnings.
try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

logging.getLogger(__name__).addHandler(NullHandler())
logging.basicConfig(level=logging.INFO)