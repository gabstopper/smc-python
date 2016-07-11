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
    if removable:
        print "Removing, and removable is: %s" % removable
        return common_api.delete(removable.get('href'))
        
    else:
        logger.info("No element named: %s, nothing to remove" % name)