import logging
import smc.actions
import smc.api.web as web_api
import smc.api.common as common_api
from smc.elements.element import SMCElement

logger = logging.getLogger(__name__)

def element(name, objtype=None):
    """ 
    Remove element from the SMC by name. Optionally you can also specify an object
    filter
    :param name: name for object to remove
    :param objtype (optional): filter to add to search for element, i.e. host,network,single_fw,etc
    :return None 
    """
  
    removable = smc.actions.search.element_info_as_json(name)
    if removable is not None:
        logger.debug("Element: %s found and is of type: %s. Attempting to remove" % (name, removable.get('type')))
        element = SMCElement()
        element.name = name
        element.type = removable.get('type', None)
        element.href = removable.get('href', None)
        
        common_api._remove(element)
        
    else:
        logger.info("No element named: %s, nothing to remove" % name)