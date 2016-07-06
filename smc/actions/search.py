import logging
from smc.api.common import fetch_href_by_name, fetch_json_by_href,\
    fetch_json_by_name, fetch_entry_point, fetch_by_name_and_filter

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
        if element:
            return element.get('href')

def element_as_json(name):
    """ Get specified element json data by name 
    
    :param name: name of element
    :return: json data representing element, else None 
    """
    if name:
        element = fetch_json_by_name(name)
        if element:
            return element.json

def element_as_json_with_etag(name):
    """ Convenience method to return SMCElement that
    holds href, etag and json in result object
    
    :return: SMCElement
    """
    return element_as_smc_element(name)
    
   
def element_info_as_json(name):
    """ Get specified element full json based on search query
    This is the base level search that returns basic object info
    including the href to find the full data
    
    :param name: name of element
    :return: json representation of top level element (multiple attributes), else None
    """   
    if name:
        element = fetch_href_by_name(name)
        if element:
            return element

        
def element_href_use_wildcard(name):
    """ Get element href using a wildcard rather than matching only on the name field
    This will likely return multiple results
    
    :param name: name of element
    :return: list of matched elements, else None
    """
    if name:
        element = fetch_href_by_name(name, use_name_field=False)
        if element:
            return element  #list

    
def element_href_use_filter(name, _filter):
    """ Get element href using filter 
    
    Filter should be a valid entry point value, ie host, router, network, single_fw, etc
    
    :param name: name of element
    :param _filter: filter type, unknown filter will result in no matches
    :return: element href (if found), else None
    """
    if name and _filter:
        element = fetch_by_name_and_filter(name, _filter)
        if element:
            return element.get('href')

            
def element_by_href_as_json(href):
    """ Get specified element by href
      
    :param href: link to object
    :return: json data representing element, else None
    """   
    if href:
        element = fetch_json_by_href(href)
        if element:
            return element.json


def element_by_href_as_smcelement(href):
    """ Get specified element returned as an SMCElement object
     
    :param href: href direct link to object
    :return: SMCElement with etag, href and element field holding json, else None
    """   
    if href:
        element = fetch_json_by_href(href)
        if element:
            return element

            
def element_as_smc_element(name):   
    """ Get specified element returned as an SMCElement object
    
    :param name: name of object
    :return: SMCElement with etag, href and element field holding json, else None
    """
    if name:
        element = fetch_json_by_name(name)
        if element:
            return element


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
       
   
def get_routing_node(name):
    """ Get the json routing node for name """
    if name:
        node = element_as_json(name)
        if node:
            route_link = next(item for item in node.get('link') if item.get('rel') == 'routing')   
            routing_orig = element_by_href_as_json(route_link.get('href'))
            return routing_orig

        
def get_logical_interface(name):
    """ Get href of logical interface. Useful for creating inline or capture
    interfaces that require this be set
    
    :return: href of logical interface, or None
    """
    interface = element_href(name)
    if interface:
        return interface

     
def log_servers():
    available_log_servers = all_elements_by_type('log_server')
    if available_log_servers:
        return available_log_servers


def get_first_log_server():
    available_log_servers = all_elements_by_type('log_server')
    if available_log_servers:
        for found in available_log_servers:
            #TODO: If multiple log servers are present, how to handle - just get the first one
            return found.get('href')

def fw_template_policies(policy=None):
    """ Convenience method to find fw templates 
    
    :param policy: find specific href of policy by name
    :return: list of tuple (name, href) for found file filtering policies 
    """
    policies = all_elements_by_type('fw_template_policy')
    if policies:
        if policy:
            return _href_from_name_href_tuple(policies, policy)
        else:
            return _iter_list_to_tuple(policies)

def ips_template_policies(policy=None):
    """ Convenience method to find ips templates
    
    :param policy: find specific href of policy by name
    :return: list of tuple (name, href) for found file filtering policies 
    """
    policies = all_elements_by_type('ips_template_policy')
    if policies:
        if policy:
            return _href_from_name_href_tuple(policies, policy)
        else:
            return _iter_list_to_tuple(policies)

def layer2_template_policies(policy=None):
    """ Convenience method to find layer2 templates
    
    :param policy: find specific href of policy by name
    :return: list of tuple (name, href) for found file filtering policies 
    """
    policies = all_elements_by_type('layer2_template_policy')
    if policies:
        if policy:
            return _href_from_name_href_tuple(policies, policy)
        else:
            return _iter_list_to_tuple(policies)

def inspection_template_policies(policy=None):
    """ Convenience method to find inspection templates
    
    :param policy: find specific href of policy by name
    :return: list of tuple (name, href) for found file filtering policies 
    """
    policies = all_elements_by_type('inspection_template_policy')
    if policies:
        if policy:
            return _href_from_name_href_tuple(policies, policy)
        else:
            return _iter_list_to_tuple(policies)

def fw_policies(policy=None):
    """ Convenience method to find file fw policies
    
    :param policy: find specific href of policy by name
    :return list of tuple (name, href) for found file filtering policies 
    """
    policies = all_elements_by_type('fw_policy')
    if policies:
        if policy:
            return _href_from_name_href_tuple(policies, policy)
        else:
            return _iter_list_to_tuple(policies)
    
def ips_policies(policy=None):
    """ Convenience method to find ips policies 
    
    :param policy: find specific href of policy by name
    :return list of tuple (name, href) for found file filtering policies 
    """
    policies = all_elements_by_type('ips_policy')
    if policies:
        if policy:
            return _href_from_name_href_tuple(policies, policy)
        else:
            return _iter_list_to_tuple(policies)
    
def layer2_policies(policy=None):
    """ Convenience method to find file layer2 policies
    
    :param policy: find specific href of policy by name
    :return list of tuple (name, href) for found file filtering policies 
    """
    policies = all_elements_by_type('layer2_policy')
    if policies:
        if policy:
            return _href_from_name_href_tuple(policies, policy)
        else:
            return _iter_list_to_tuple(policies)

def inspection_policies(policy=None):
    """ Convenience method to find inspection policies
    
    :param policy: find specific href of policy by name
    :return list of tuple (name, href) for found file filtering policies 
    """
    policies = all_elements_by_type('inspection_template_policy')
    if policies:
        if policy:
            return _href_from_name_href_tuple(policies, policy)
        else:
            return _iter_list_to_tuple(policies)

def file_filtering_policies(policy=None):
    """ Convenience method to find file filtering policies
    
    :param policy: find specific href of policy by name
    :return list of tuple (name, href) for found file filtering policies 
    """
    policies = all_elements_by_type('file_filtering_policy')
    if policies:
        if policy:
            return _href_from_name_href_tuple(policies, policy)
        else:
            return _iter_list_to_tuple(policies)
            
def _iter_list_to_tuple(lst):
    """ Return tuple name,href from top level json query:
    {'href'='http://x.x.x.x', 'name'='blah', 'type'='sometype'}
    
    :param policy: find specific href of policy by name
    :return list of tuple (name, href)
    """
    return [(opt.get('name'),opt.get('href')) for opt in lst]

def _href_from_name_href_tuple(dictentry, element_name):
    element = [entry.get('href') for entry in dictentry if entry.get('name') == element_name]
    if element:
        return element.pop()
    
if __name__ == "__main__":
    
    import smc.api.web as web_api    
    from pprint import pprint
    web_api.session.login('http://172.18.1.150:8082', 'EiGpKD4QxlLJ25dbBEp20001')
    
    pprint(element_as_json('myips'))
    #print file_filtering_policies(policy='No Scanning')
    
    web_api.session.logout()