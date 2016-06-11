'''
Created on May 1, 2016

@author: davidlepage
'''
import smc.api.web as web_api
import logging
from smc.api.common import _fetch_element

logger = logging.getLogger(__name__)


def element(name):
    """ convenience method to get element href
    :param name
    :return str href of element
    """
    
    return element_href(name)


def element_href(name):
    """ Get specified element href by element name 
    :param name: name of element
    :return string href location of object 
    """
    
    element = _fetch_element(name)
    if element:
        return element['href'] 


def element_as_json(name):
    """ Get specified element json data by name 
    :param name: name of element
    :return json data representing element 
    """
    
    element = _fetch_element(name, follow_href=True)
    if element:
        return element.json


def element_info_as_json(name):
    """ Get specified element full json based on search query
    This is the base level search that returns basic object info
    including the href to find the full data
    :param name: name of element
    :return json representation of top level element and location (contains multiple attributes)
    """
    
    element = _fetch_element(name)
    if element:
        return element

        
def element_href_use_wildcard(name):
    """ Get element href using a wildcard rather than matching only on the name field
    This will likely return multiple results
    :param name: name of element
    :return list of matched elements
    """
    
    element = _fetch_element(name, use_name_field=False)
    if element:
        return element  #list

    
def element_href_use_filter(name, _filter):
    """ Get element href using filter 
    Filter should be a valid entry point value, ie host, router, network, single_fw, etc
    :param name: name of element
    :param _filter: filter type, unknown filter will result in no matches
    :return element href (if found), or None
    """
    
    element = _fetch_element(name, obj_type=_filter)
    if element:
        return element['href']

            
def element_by_href_as_json(href):
    """ Get specified element by href  
    :param href: link to object
    :return json data representing element
    """
    
    element = _fetch_element(href=href)
    if element:
        return element.json


def element_by_href_as_smcelement(href):
    """ Get specified element returned as an SMCElement object 
    :param href: href direct link to object
    :return SMCElement with etag, href and element field holding json
    """
    
    element = _fetch_element(href=href)
    if element:
        return element

            
def element_as_smc_element(name):   
    """ Get specified element returned as an SMCElement object 
    :param name: name of object
    :return SMCElement with etag, href and element field holding json
    """
    
    element = _fetch_element(name, follow_href=True)
    if element:
        return element


def all_elements_by_type(name):
    """ Get specified elements based on the entry point verb from SMC api
    To get the entry points available, you can call web_api.get_all_entry_points()
    Execution is get the entry point for the element type, then get all elements that
    match. 
    For example: smc.get_element_by_entry_point('log_server')
    :param name: top level entry point name
    :return Json representation of name match
    """
    
    entry = element_entry_point(name)

    if entry: #in case an invalid entry point is specified
        result = element_by_href_as_json(entry)
        return result
    else:
        logger.error("Entry point specified was not found: %s" % name)


def element_entry_point(name):
    """ Get specified element from cache based on the entry point verb from SMC api
    To get the entry points available, you can call web_api.get_all_entry_points()
    For example: element_entry_point('log_server')
    :param name: top level entry point name
    :return href or None
    """
    
    element = _fetch_element(entry_point=name)
    if element:
        return element
   
   
def get_routing_node(name):
    """ Get the json routing node for name """
    node = element_as_json(name)
    if node:
        route_link = next(item for item in node.get('link') if item.get('rel') == 'routing')   
        routing_orig = element_by_href_as_json(route_link.get('href'))
        return routing_orig

        
def get_logical_interface(name):
    interface = element_href(name)
    if interface:
        return interface

     
def get_log_servers():
    available_log_servers = all_elements_by_type('log_server')
    if available_log_servers:
        return available_log_servers


def get_first_log_server():
    available_log_servers = all_elements_by_type('log_server')
    if available_log_servers:
        for found in available_log_servers:
            #TODO: If multiple log servers are present, how to handle - just get the first one
            return found['href']
 
 
 
                 
if __name__ == '__main__':
    web_api.session.login('http://172.18.1.150:8082', 'EiGpKD4QxlLJ25dbBEp20001')

    logging.getLogger()
    logging.basicConfig(level=logging.DEBUG)
    #import smc
    #smc.create.host('ami', '12.12.12.12')
    '''
    print "all elements by type: %s" % all_elements_by_type('log_server') #good
    assert all_elements_by_type('hostssd') == None
    
    print "element entry point: %s" % element_entry_point('host')  #good
    assert element_entry_point('host2') == None
      
    print "element href: %s" % element_href('ami')        #good
    assert element_href('regergergr') == None   
    '''
    print "element as json: %s" % element_as_json('ewf')    #good
    #assert element_as_json('weewfe') == None
    '''
    print "element full json: %s" % element_info_as_json('ami') #good   
    assert element_info_as_json('asdfdsfsd') == None
    
    print "element href w/ wildcard: %s" % element_href_use_wildcard('ami') #good
    assert element_href_use_wildcard('amissss') == None
    
    print "element href using filter: %s " % element_href_use_filter('ami', 'host') #good
    assert element_href_use_filter('amisss', 'host') == None    
    
    print "element by href as json: %s" % element_by_href_as_json(element_href('ami')) #good
    #assert element_by_href_as_json(element_href('ami2322')) == None
    
    print "logical interface: %s" % get_logical_interface('default_eth') #good
    assert get_logical_interface('wregregerg') == None
    
    print "get log servers: %s" % get_log_servers()
    
    print "First log server: %s" % get_first_log_server()
    '''
    
    web_api.session.logout()