import logging
import smc
from smc import SMCOperationFailure

logger = logging.getLogger(__name__)

#generic
def element(name, objtype=None):
    removable = smc.search.get_element(name, objtype)
    if removable:
        logger.debug("Element: %s found and is of type: %s. Attempting to remove" % (name, removable['type']))
        try:
            smc.web_api.http_delete(removable['href']) #delete to href
            logger.info("Successfully removed host: %s" % name)
        except SMCOperationFailure, e:
            logger.error("Failed removing host: %s, msg: %s" % (name, e.msg))
    else:
        logger.info("No element named: %s, nothing to remove" % name)


if __name__ == '__main__':
    smc.web_api.login('http://172.18.1.150:8082', 'EiGpKD4QxlLJ25dbBEp20001')
    
    smc.remove.element('test-run')  #single fw
    smc.remove.element('ami2')      #single host
    smc.remove.element('anewgroup')      #group
    
    smc.web_api.logout()