"""
Helpers functions
"""
import smc.actions.search as search
#from smc.elements.element import Zone, LogicalInterface

def find_link_by_name(link_name, linklist):
    """ 
    Find the href based on SMC API return rel
    """
    for entry in linklist:
        if entry.get('rel') == link_name:
            return entry.get('href')

'''        
def location_helper(name):
    href = search.element_as_json_with_filter(name, 'location')
    if href:
        return href
    else:
        return Location(name).create().href
'''
'''
def zone_helper(zone):
    zone_ref = search.element_href_use_filter(zone, 'interface_zone')
    if zone_ref:
        return zone_ref
    else:
        return Zone(zone).create().href
    
def logical_intf_helper(interface):
    intf_ref = search.element_href_use_filter(interface, 'logical_interface')
    if intf_ref:
        return intf_ref
    else:
        return LogicalInterface(interface).create().href
'''            
def get_element_etag(href):
    return search.element_by_href_as_smcresult(href)