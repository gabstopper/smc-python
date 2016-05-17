'''
Created on May 1, 2016

@author: davidlepage
'''
import smc.api.web as web_api
import logging
from smc.api.web import SMCOperationFailure
from smc.api.common import _fetch_element

logger = logging.getLogger(__name__)


def _get_element_href(name):
    """ Get specified element href by name 
    Args:
        * name: name of element
    Returns:
        String href location of object 
    """
    element = _fetch_element(name)
    if element:
        return element['href'] 

def _get_element_href_wildcard(name):
    element = _fetch_element(name, use_name_field=False)
    if element:
        return element  #list
    
def _get_element_href_filter(name, _filter):
    element = _fetch_element(name, obj_type=_filter)
    if element:
        return element['href']
    
def _get_element_href_json(name):
    """ Get specified element full json based on search query
    This is the base level search that returns basic object info
    including the href to find the full data
    Args: 
        * name: name of element
    Returns:
        json representation of top level element and location
    """
    element = _fetch_element(name)
    if element:
        return element
        
def _get_element_json(name):
    """ Get specified element json data by name 
    Args:
        * name: name of element
    Returns: 
        json data representing element 
    """
    element = _fetch_element(name, follow_href=True)
    if element:
        return element.json
        
def _get_element_json_by_href(href):
    """ Get specified element by href already obtained 
    Args: 
        * href: link to object
    Returns: 
        json data representing element
    """
    element = _fetch_element(href=href)
    if element:
        return element.json
        
def _get_element_as_smc_element(name):
    """ Get specified element returned as an SMCElement object 
    Args: 
        * name: name of object
    Returns:
        SMCElement object with etag, href and element field holding json
    """
    element = _fetch_element(name, follow_href=True)
    if element:
        return element
        
#TODO: Need to fix - not sending back etag from search library - causes a second query
def get_element(name, obj_type=None, as_json=False, use_name_field=True):
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
   
    if not result.json: #no results returned
        logger.info("No results found for element name: %s" % name)
    else:
        match = None
        if not use_name_field: # Return any host objects using name as filter (match all)
            logger.debug("Returning all elements matching: %s" % name)
            match = result.json
        else: # Only return object where name matches host object name field
            for host in result.json:
                if host['name'] == name:
                    match = host
                    break   #exits on first match
            if not match:
                logger.debug("No search results found for name: %s" % name)
            else:
                logger.debug("Search found direct match for element: %s, %s" % (name,match))
        if as_json:
            return get_element_by_href(match['href'])
        else:
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
    
    if not result.json:
        logger.info("No results found for href, maybe a bad reference: %s" % name)
    return result.json

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
        return result.json #TODO: return at bottom
    else:
        logger.error("Entry point specified was not found: %s" % name)

def get_logical_interface(name):
    interface = _get_element_href(name)
    if not interface:
        return None
    return interface
     
def get_log_servers():
    available_log_servers = get_element_by_entry_point('log_server')
    if not available_log_servers:
        return None
    return available_log_servers

def get_first_log_server():
    available_log_servers = get_element_by_entry_point('log_server')
    if not available_log_servers:
        return None
    for found in available_log_servers:
            #TODO: If multiple log servers are present, how to handle - just get the first one
            return found['href']
                 
if __name__ == '__main__':
    web_api.session.login('http://172.18.1.150:8082', 'EiGpKD4QxlLJ25dbBEp20001')
    
    from pprint import pprint  
    import smc.api.common as common
    
    
    print "Element href only: %s" % _get_element_href('ami')
    print "Element as json: %s" % _get_element_json('ami')
    print "element href_with_filter: %s" % _get_element_href_filter('mygroup', 'group')
    print "element href json: %s" % _get_element_href_json('ami')
    print "Element href by wildcard: %s" % _get_element_href_wildcard('ami')
    
    e = _get_element_as_smc_element('ami')
    pprint(e.json)
    print "with filter: %s" % _get_element_href_filter('ami', 'host')
    
    print _get_element_href_json('default_eth')
    print "Logical interface: %s" % get_logical_interface('default_eth')
    
    pprint(_get_element_json('mylayer3'))
    #pprint(_get_element_json_by_href('http://172.18.1.150:8082/6.0/elements/single_layer2/1151'))
    #pprint(_get_element_json('InlineFW'))
    #print "element as smcobject: %s" % _get_element_as_smc_element('ami')
    #########
    #by name and object type
    #a = common._fetch_element('ami', follow_href=True) #get json
    #pprint(a.element)
    #print "element2: %s" % common._fetch_element('myfw')#just get href   
    #print common._fetch_element('ami', use_name_field=False)
    #f = common._fetch_element('ami', as_json=True)
    
    #pprint(common._fetch_element('ami')) #return query json
    ##########
    
    #pprint(get_element('172.20.1.1', as_json=False))
    #pprint(get_element('172.20.1.1'))
    
    #pprint(get_element('InlineFW', as_json=True)) 
    #pprint(get_element_by_href('http://172.18.1.150:8082/6.0/elements/logical_interface/1'))
    
    #pprint(get_element('default_eth')['href'])
    logical_int = {
    "comment": "made by smc-python",
    "name": "apitool"
    }
    try:
        web_api.session.http_post('http://172.18.1.150:8082/6.0/elements/logical_interface', logical_int)
    except SMCOperationFailure, e:
        print e.msg
            
    web_api.session.logout()