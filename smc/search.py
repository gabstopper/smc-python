'''
Created on May 1, 2016

@author: davidlepage
'''

import logging
import smc

logger = logging.getLogger(__name__)

def filter_by_element(name):
    """ Get specified element/s by name
    This is a more generic search inclusive of all objects under the 
    entry point /elements
    Name is converted into a filter query string, for example:
    http://1.1.1.1/elements?filter=name
    If no element is found, None is returned. If results are returned,
    it is likely there will be multiple """    
    entry = smc.web_api.get_entry_href('elements')
    r = smc.web_api.http_get(entry + '?filter=' + name)
    return get_result(r)


def filter_by_type(obj_type, name, use_name_field=True):
    """ Search for name using the object type, i.e. 'host', 'single_fw', 'group', etc.
    It is not necessary to know the entry point url as this will be retrieved from the 
    entry point cache. Request will be built with the correct format:
    http://1.1.1.1/entry_point/type?filter=name
    Setting use_name_field to False enforces the host filter search to look at the 
    any available field in a host object. This may return multiple results.""" 
    entry = smc.web_api.get_entry_href(obj_type)
   
    if entry: #protect web req in case invalid object type given
        r = smc.web_api.http_get(entry + '?filter=' + name)
        result = get_result(r)
        if result: #Some results were returned
            if not use_name_field: # Return any host objects using name as filter
                return result
            else: # Only return object where name matches host object name field
                for host in result:
                    if host['name'] == name:
                        return host
        else:
            logger.info("No results found for object type: %s and name: %s" % (obj_type,name))
    else:
        logger.error("Entry point specified was not found: %s" % name)

 
def filter_by_entry_point(entry_href, query):
    """ Search for name using entry_point_filter for specific type
    entry_href should be an entry point retrieved from get_entry_href('verb')
    For example: http://1.1.1.1/elements/single_fw
    This will be formatted to: http://1.1.1.1/elements/single_fw?filter=query """
    r = smc.web_api.http_get(entry_href + '?filter=' + query)
    return get_result(r)


def get_element_by_href(name):
    """ Get specified element from fully qualified href, typically this
    comes from a reference from the SMC api. 
    For example, name could be: http://1.1.1.1:8082/elements/single_fw/119"""
    return smc.web_api.http_get(name)


def get_element_by_entry_point(name):
    """ Get specified element based on the entry point verb from SMC api
    To get the entry points available, you can call web_api.get_all_entry_points()
    For example: smc.get_element_by_entry_point('log_server')"""
    entry = smc.web_api.get_entry_href(name)
    if entry: #in case an invalid entry point is specified
        r = smc.web_api.http_get(entry)
        return get_result(r)
    else:
        print "Entry point specified was not found: %s" % name


def get_result(reply):
    """ Utility to check for empty result
    Return result """
    if reply:
        if 'result' in reply:
            return reply['result']
        else:
            return reply