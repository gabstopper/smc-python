import logging
import smc.actions
import smc.api.web as web_api
import smc.api.common as common_api
from smc.elements.element import SMCElement

logger = logging.getLogger(__name__)

def element(name, objtype=None):
    """ Remove by element
    Args:
        * name: name for object to remove
        * objtype (optional): filter to add to search for element, i.e. host,network,single_fw,etc
    Returns:
        None
    """
  
    removable = smc.actions.search.element_info_as_json(name)
    if removable is not None:
        logger.debug("Element: %s found and is of type: %s. Attempting to remove" % (name, removable['type']))
        element = SMCElement()
        element.name = name
        element.type = removable.get('type', None)
        element.href = removable.get('href', None)
        
        common_api._remove(element)
        
    else:
        logger.info("No element named: %s, nothing to remove" % name)


if __name__ == '__main__':

    web_api.session.login('http://172.18.1.150:8082', 'EiGpKD4QxlLJ25dbBEp20001')
    
    smc.create.host('test-run', '2.2.2.2')
    smc.create.host('ami2', '3.4.5.6')
    smc.remove.element('test-run')  #single fw
    smc.remove.element('fe')      #single host
    smc.remove.element('anewgroup')      #group
    
    web_api.session.logout()