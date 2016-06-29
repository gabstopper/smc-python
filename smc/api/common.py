'''
Created on May 13, 2016

@author: davidlepage
'''

import logging
import smc.api.web as web_api
from smc.api.web import SMCOperationFailure, SMCConnectionError
from smc.elements.element import SMCElement

logger = logging.getLogger(__name__)

#cache = web_api.session.cache.get_element(name)
#if cache is not None:
#    print "Found in cache: %s, location: %s" % (name,cache)
#    return cache
    
def _create(element):
    """ 
    Create object by HTTP POST method
    If the creation was successful, SMCElement.href will reference the new location
    If creation fails, it will be None
    :param element: element to create, this is an instance of SMCElement. See elements module for
    more information. SMCElement.json is the payload, href is the location to POST
    :return href upon success otherwise None
    """
    logger.debug("Creating element: %s, href: %s, json: %s" % (element.name, element.href, element.json))
    try:
        element.href = web_api.session.http_post(element.href, element.json)
        logger.info("Success creating element; %s" % (element))       
        
    except SMCOperationFailure, e:
        element.href = None
        logger.error("Failed creating element: %s, Reason: %s", element.name, e)
    except SMCConnectionError, e:
        raise
    return element.href

def _update(element):
    """ 
    Update object by HTTP PUT
    :param element: SMCElement to update, 
    Fields required are:
        element.etag: etag of element, request should have been made previously to get this value
        element.href: href of the element
        element.json: payload to update
    :return href upon success otherwise None
    """
    logger.debug("Updating element: %s, href: %s, json: %s" % (element.name, element.href, element.json))
    try: 
        element = web_api.session.http_put(element.href, element.json, element.etag)
        logger.info("Success updating element; %s" % element)
        
    except SMCOperationFailure, e:
        element = None
        logger.error("Failed updating element; %s %s" % (element, e))
    except SMCConnectionError, e:
        raise
    return element
    
def _remove(element):
    """ 
    Internal for wrapping exceptions when making web delete
    :param element: name of element to remove
    :return None
    """
    logger.debug("Removing element: %s, href: %s" % (element.name, element.href))
    try:
        web_api.session.http_delete(element.href) #delete to href
        logger.info("Success removing element; %s" % element)
            
    except SMCOperationFailure, e:
        logger.error("Failed removing element; %s, %s" % (element, e))
    except SMCConnectionError, e:
        raise


def fetch_entry_point(name):
    """ 
    Get the entry point href based on the input name
    :param name: valid entry point, i.e. 'log_server', 'tcp_server', 'single_fw', etc.
    smc.api.web.get_all_entry_points caches the entry points after login
    :return href upon success otherwise None
    """
    try:
        entry_href = web_api.session.get_entry_href(name) #from entry point cache
        if not entry_href:
            logger.error("Entry point specified was not found: %s" % name)
            return None
        return entry_href
    
    except SMCOperationFailure, e:
        logger.error("Failure occurred fetching element: %s" % e)
    except SMCConnectionError, e:
        raise

def fetch_by_name_and_filter(name, of_type):
    """ 
    Get json data for element name and using a filter
    Filter should be a valid entry point value, ie host, router, network, single_fw, etc
    :param name: element name
    :param of_type: type of element filter
    :return json of element
    """
    try:
        entry_href = web_api.session.get_entry_href(of_type)
        if not entry_href:
            logger.error("Object type entry point specified was not found: %s" % of_type)
            return None
        #else
        result = web_api.session.http_get(entry_href, {'filter': name})
        if result.json:
            return result.json.pop()
                
    except SMCOperationFailure, e:
        logger.error("Failure occurred fetching element: %s" % e)
    except SMCConnectionError, e:
        raise
            
def fetch_json_by_href(href):
    """ 
    Fetch json for element by using href
    :param href: href of the element
    :return SMCElement with following attributes set:
        href: href of element
        etag: etag of the element, used for modifying element
        json: json representation of element
    """
    try:
        result = web_api.session.http_get(href)
        if result:
            element = SMCElement()
            element.href = href
            element.etag = result.etag
            element.json = result.json
            return element
    
    except SMCOperationFailure, e:
        logger.error("Failure occurred fetching element: %s" % e)
    except SMCConnectionError, e:
        raise
        
def fetch_json_by_name(name):
    """ 
    Fetch json based on the element name
    First gets the href based on a search by name, then makes a 
    second query to obtain the elements json
    :param name: element name
    :return SMCElement with following attributes set:
        href: href of element
        etag: etag of the element, used for modifying element
        json: json representation of element
    """
    try:
        element = fetch_href_by_name(name)
        if element:
            return fetch_json_by_href(element.get('href'))
    
    except SMCOperationFailure, e:
        logger.error("Failure occurred fetching element: %s" % e)
    except SMCConnectionError, e:
        raise
    
def fetch_href_by_name(name, use_name_field=True):
    """
    Fetch href of element by it's name. Use_name_field is used to verify that
    the returned element/s match what we're looking for. SMC will return multiple
    results if there are multiple matches. Setting use_name_field to true will 
    only return the object matching the element name field. Setting to False may 
    return a list of multiple results
    :param name: element name
    :param use_name_field: match on element name field in SMC db
    :return dict including href key
    """
    try:
        entry_href = web_api.session.get_entry_href('elements')
        result = web_api.session.http_get(entry_href, {'filter': name})
        
        match = None
        if not use_name_field: # Return any host objects using name as filter (match all)
            logger.debug("Returning all elements matching: %s" % name)
            return result.json
        else: # Only return object where name matches host object name field
            for host in result.json:
                if host.get('name', None) == name:
                    match = host
                    break   #exits on first match
            if not match:
                logger.debug("No search results found for name: %s" % name)
                return
            else:
                logger.debug("Search found direct match for element: %s, %s" % (name, match))
                return host
                        
    except SMCOperationFailure, e:
        logger.error("Failure occurred fetching element: %s" % e)       
    except SMCConnectionError, e:
        raise
