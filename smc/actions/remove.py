import logging
import smc.actions
import smc.api.web as web_api
from smc.api.web import SMCOperationFailure

logger = logging.getLogger(__name__)

#generic
def element(name, objtype=None):
    """ Remove by element
        Args:
            * name: name for object to remove
            * objtype (optional): filter to add to search for element, i.e. host,network,single_fw,etc
        Returns:
            None
    """
    removable = smc.actions.search.get_element(name, objtype)
    if removable is not None:
        logger.debug("Element: %s found and is of type: %s. Attempting to remove" % (name, removable['type']))
        try:
            #smc.web_api.http_delete(removable['href']) #delete to href
            web_api.session.http_delete(removable['href']) #delete to href
            logger.info("Successfully removed host: %s" % name)
            #try:
            #    a = web_api.session.cache.elements.pop(name)
            #    print "Popped that beeotch: %s" % a
            #except KeyError:
            #    print "Key not found in cache: %s" % name
            #    pass
            
        except SMCOperationFailure, e:
            logger.error("Failed removing host: %s, msg: %s" % (name, e.msg))
    else:
        logger.info("No element named: %s, nothing to remove" % name)


if __name__ == '__main__':

    web_api.session.login('http://172.18.1.150:8082', 'EiGpKD4QxlLJ25dbBEp20001')
    
    smc.remove.element('test-run')  #single fw
    smc.remove.element('ami2')      #single host
    smc.remove.element('anewgroup')      #group
    
    web_api.session.logout()