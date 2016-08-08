"""
Search module provides convenience methods for retrieving specific data from 
the SMC. Each method will return data in a certain way with different inputs.
All methods are using :mod:`smc.api.common` methods which wrap any exceptions
and if there are no results, each method would return None

Example of retrieving an SMC element by name, as json::

    smc.actions.search.element_as_json('myelement')
    
Element as json with etag (etag is required for modifications)::

    smc.actions.search.element_as_json_with_etag('myelement')
    
Get element reference::
    
    smc.actions.search.element_href('myelement')
    
All elements by type::
    
    smc.actions.search.element_by_type('host')
"""
import logging
from smc.api.common import fetch_href_by_name, fetch_json_by_href,\
    fetch_json_by_name, fetch_entry_point
import smc.api.web as web_api
logger = logging.getLogger(__name__)


def element(name):
    """ Convenience method to get element href by name
    
    :param name: name of element
    :return: str href of element, else None
    """
    if name:
        return element_href(name)


def element_href(name):
    """ Get specified element href by element name 
    
    :param name: name of element
    :return: string href location of object, else None 
    """
    if name:
        element = fetch_href_by_name(name)
        if element.href:
            return element.href

def element_as_json(name):
    """ Get specified element json data by name 
    
    :param name: name of element
    :return: json data representing element, else None 
    """
    if name:
        element = fetch_json_by_name(name)
        if element.json:
            return element.json

def element_as_json_with_filter(name, _filter):
    """ Get specified element json data by name with filter
    
    :param name: name of element
    :param _filter: element filter
    :return: json data representing element, else None
    """
    if name:
        element_href = element_href_use_filter(name, _filter)
        if element_href:
            return element_by_href_as_json(element_href)
            
def element_as_json_with_etag(name):
    """ Convenience method to return SMCElement that
    holds href, etag and json in result object
    
    :param name: name of element
    :return: SMCResult, else None
    """
    return element_as_smcresult(name)
       
def element_info_as_json(name):
    """ Get specified element full json based on search query
    This is the base level search that returns basic object info
    including the href to find the full data
    
    :param name: name of element
    :return: json representation of top level element (multiple attributes), else None
    """   
    if name:
        element = fetch_href_by_name(name)
        if element.json:
            return element.json.pop()
       
def element_href_use_wildcard(name):
    """ Get element href using a wildcard rather than matching only on the name field
    This will likely return multiple results
    
    :param name: name of element
    :return: list of matched elements, else None
    """
    if name:
        element = fetch_href_by_name(name, exact_match=False)
        if element.json:
            return element.json  #list
  
def element_href_use_filter(name, _filter):
    """ Get element href using filter 
    
    Filter should be a valid entry point value, ie host, router, network, single_fw, etc
    
    :param name: name of element
    :param _filter: filter type, unknown filter will result in no matches
    :return: element href (if found), else None
    """
    if name and _filter:
        #element = fetch_by_name_and_filter(name, _filter)
        element = fetch_href_by_name(name, filter_context=_filter)
        if element.json:
            return element.json.pop().get('href')

def element_by_href_as_json(href):
    """ Get specified element by href
      
    :param href: link to object
    :return: json data representing element, else None
    """   
    if href:
        element = fetch_json_by_href(href)
        if element:
            return element.json

def element_by_href_as_smcresult(href):
    """ Get specified element returned as an SMCElement object
     
    :param href: href direct link to object
    :return: SMCElement with etag, href and element field holding json, else None
    """   
    if href:
        element = fetch_json_by_href(href)
        if element:
            return element
           
def element_as_smcresult(name):   
    """ Get specified element returned as an SMCElement object
    
    :param name: name of object
    :return: SMCResult, else None
    """
    if name:
        element = fetch_json_by_name(name)
        if element.json:
            return element

def element_as_smcresult_use_filter(name, _filter):
    """ Return SMCResult object and use search filter to
    find object
    
    :param name: name of element to find
    :param _filter: filter to use, i.e. tcp_service, host, etc
    :return: SMCResult
    """
    if name:
        element_href = element_href_use_filter(name, _filter)
        if element_href:
            return element_by_href_as_smcresult(element_href)

def element_href_by_batch(list_to_find):
    """ Find batch of entries by name. Reduces number of find calls from
    calling class. 
    
    :param list_to_find: list of names to find
    :type: list
    :return: dict: {name: href, name: href}, href may be None if not found
    """
    try:
        return {k:element_href(k) for k in list_to_find} 
    except TypeError:
        logger.error(list_to_find, 'is not iterable')
            
def all_elements_by_type(name):
    """ Get specified elements based on the entry point verb from SMC api
    To get the entry points available, you can call web_api.get_all_entry_points()
    Execution is get the entry point for the element type, then get all elements that
    match.
    
    For example::
    
        smc.get_element_by_entry_point('log_server')
        
    :param name: top level entry point name
    :return: list with json representation of name match, else None
    """
    if name:
        entry = element_entry_point(name)
    
        if entry: #in case an invalid entry point is specified
            result = element_by_href_as_json(entry)
            return result
        else:
            logger.error("Entry point specified was not found: %s" % name)

def all_entry_points(): #get from session cache
    """ Get all SMC API entry points """
    return web_api.session.get_all_entry_points()

def element_entry_point(name):
    """ Get specified element from cache based on the entry point verb from SMC api
    To get the entry points available, you can call web_api.get_all_entry_points()
    For example::
    
        element_entry_point('log_server')
    
    :param name: top level entry point name
    :return: href: else None
    """
    if name:   
        element = fetch_entry_point(name)
        if element:
            return element

def search_unused():
    """ Search for all unused elements 
    :return: list of dict items holding href,type and name
    """
    return element_by_href_as_json(fetch_entry_point('search_unused'))

def search_duplicate():
    """ Search all duplicate elements 
    :return: list of dict items holding href,type and name
    """
    return element_by_href_as_json(fetch_entry_point('search_duplicate'))
         
def get_routing_node(name):
    """ Get the json routing node for name """
    if name:
        node = element_as_json(name)
        if node:
            route_link = next(item for item in node.get('link') if item.get('rel') == 'routing')   
            routing_orig = element_by_href_as_json(route_link.get('href'))
            return routing_orig
     
def log_servers():
    """ Retrieve a list of all available log servers 
    
    :return: list of log servers, each item is dict(href,name,type), or None
    """   
    available_log_servers = all_elements_by_type('log_server')
    if available_log_servers:
        return available_log_servers

def get_first_log_server():
    """ Convenience method to return the first log server match in
    the case where there might be multiple
    
    :return: href of log server, or None
    """
    available_log_servers = all_elements_by_type('log_server')
    if available_log_servers:
        for found in available_log_servers:
            return found.get('href')

def policy_by_type(policy=None, policy_type=None):
    policy_types = ['fw_template_policy', 'ips_template_policy', 'layer2_template_policy',
                    'inspection_template_policy', 'fw_policy', 'ips_policy',
                    'layer2_policy', 'file_filtering_policy','sub_ipv6_fw_policy',
                    'sub_ipv4_fw_policy','sub_ipv4_layer2_policy', 'sub_ipv4_ips_policy']
    if policy_type in policy_types:
        policies = all_elements_by_type('fw_template_policy')
        if policies:
            if policy:
                return _href_from_name_href_tuple(policies, policy)
            else:
                return _iter_list_to_tuple(policies)
        
def fw_template_policies(policy=None):
    """ Convenience method to find fw templates 
    
    :param policy: find specific href of policy by name
    :return: list of tuple (name, href) for found file filtering policies 
    """
    return policy_by_type(policy=policy, 
                          policy_type='fw_template_policy')

def ips_template_policies(policy=None):
    """ Convenience method to find ips templates
    
    :param policy: find specific href of policy by name
    :return: list of tuple (name, href) for found file filtering policies 
    """
    return policy_by_type(policy=policy,
                          policy_type='ips_template_policy')

def layer2_template_policies(policy=None):
    """ Convenience method to find layer2 templates
    
    :param policy: find specific href of policy by name
    :return: list of tuple (name, href) for found file filtering policies 
    """
    return policy_by_type(policy=policy,
                          policy_type='layer2_template_policy')

def fw_policies(policy=None):
    """ Convenience method to find file fw policies
    
    :param policy: find specific href of policy by name
    :return: list of tuple (name, href) for found file filtering policies 
    """
    return policy_by_type(policy=policy,
                          policy_type='fw_policy')
    
def ips_policies(policy=None):
    """ Convenience method to find ips policies 
    
    :param policy: find specific href of policy by name
    :return: list of tuple (name, href) for found file filtering policies 
    """
    return policy_by_type(policy=policy,
                          policy_type='ips_policy')
    
def layer2_policies(policy=None):
    """ Convenience method to find file layer2 policies
    
    :param policy: find specific href of policy by name
    :return: list of tuple (name, href) for found file filtering policies 
    """
    return policy_by_type(policy=policy,
                          policy_type='layer2_policy')

def inspection_policies(policy=None):
    """ Convenience method to find inspection policies
    
    :param policy: find specific href of policy by name
    :return: list of tuple (name, href) for found file filtering policies 
    """
    return policy_by_type(policy=policy,
                          policy_type='inspection_template_policy')

def file_filtering_policies(policy=None):
    """ Convenience method to find file filtering policies
    
    :param policy: find specific href of policy by name
    :return: list of tuple (name, href) for found file filtering policies 
    """
    return policy_by_type(policy=policy,
                          policy_type='file_filtering_policy')
            
def _iter_list_to_tuple(lst):
    """ Return tuple name,href from top level json query:
    {'href'='http://x.x.x.x', 'name'='blah', 'type'='sometype'}
    
    :param policy: find specific href of policy by name
    :return: list of tuple (name, href)
    """
    return [(opt.get('name'),opt.get('href')) for opt in lst]

def _href_from_name_href_tuple(dictentry, element_name):
    element = [entry.get('href') for entry in dictentry if entry.get('name') == element_name]
    if element:
        return element.pop()