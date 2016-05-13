'''
Created on May 1, 2016

@author: davidlepage
'''
import smc.api.web as web_api
import logging

logger = logging.getLogger(__name__)

#TODO: Need to fix - not sending back etag from search library - causes a second query
def get_element(name, obj_type=None, use_name_field=True):
    """ Get specified element/s by name
        When specifying just name arg, all elements are searched
        Query will look like: http://1.1.1.1/elements?filter=name
        Use obj_type if you know the type of element to filter further
            Arg:
                * name: what element to search for
                * obj_type (optional): search filter by type of obj (host,router,network,etc); default=None
                * use_name_field (optional): verifies name field match in return records; default=True
            Returns:
                Json record/s representing top level element match
                None; no results
    """
    #cache = web_api.session.cache.get_element(name)
    #if cache is not None:
    #    print "Found in cache: %s, location: %s" % (name,cache)
    #    return cache
       
    entry_href = None
    if obj_type:
        entry_href = web_api.session.get_entry_href(obj_type)
        if not entry_href:
            logger.error("Object type entry point specified was not found: %s" % obj_type)
            return None
    else:
        entry_href = web_api.session.get_entry_href('elements') #entry point for all elements
    
    logger.debug("Searching for element: %s" % name)
    result = web_api.session.http_get(entry_href + '?filter=' + name) #execute search
   
    if not result.msg: #no results returned
        logger.info("No results found for element name: %s" % name)
    else:
        if not use_name_field: # Return any host objects using name as filter (match all)
            logger.debug("Returning all elements matching: %s" % name)
            return result.msg  # Return anything that was found
        else: # Only return object where name matches host object name field
            match = None #TODO: This could return multiple entries
            for host in result.msg:
                if host['name'] == name:
                    match = host
                    break   #exits on first match
            if not match:
                logger.debug("No search results found for name: %s" % name)
            else:
                logger.debug("Search found direct match for element: %s, %s" % (name,match))
            return match

def get_element_by_href(name): #TODO: Check to see what other methods get this result, should return ResultObject in case etag is needed
    """ Get specified element from fully qualified href
        For example, name could be: http://1.1.1.1:8082/elements/single_fw/119
        Args: 
            * name: href (typically reference from smc) for object to retrieve
        Returns:
            Json record representing match
    """
    result = web_api.session.http_get(name)
    
    if not result.msg:
        logger.info("No results found for href, maybe a bad reference: %s" % name)
    return result.msg

def get_element_by_entry_point(name):
    """ Get specified element based on the entry point verb from SMC api
        To get the entry points available, you can call web_api.get_all_entry_points()
        For example: smc.get_element_by_entry_point('log_server')
        Args:
            * name: top level entry point name
        Returns:
            Json representation of name match
    """
    entry = web_api.session.get_entry_href(name)
    
    if entry: #in case an invalid entry point is specified
        result = web_api.session.http_get(entry)
        return result.msg #TODO: return at bottom
    else:
        logger.error("Entry point specified was not found: %s" % name)

     
if __name__ == '__main__':
    web_api.session.login('http://172.18.1.150:8082', 'EiGpKD4QxlLJ25dbBEp20001')
      
    p = get_element('1.1.1.1a')
    q = get_element_by_href(p['href'])
    from pprint import pprint
    pprint(q)
    web_api.session.logout()