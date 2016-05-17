'''
Created on May 13, 2016

@author: davidlepage
'''

import logging
import smc.api.web as web_api
from smc.api.web import SMCOperationFailure
from smc.elements.element import SMCElement

logger = logging.getLogger(__name__)


def _create(element):
    """ create element
    If the creation was successful, SMCElement.href will reference the new location
    If creation fails, it will be None
    """
    logger.debug("Creating element: %s, href: %s, json: %s" % (element.name, element.href, element.json))
    try:
        #smc_result = web_api.session.http_post(element.href, element.json)
        element.href = web_api.session.http_post(element.href, element.json)
        logger.info("Success creating element; %s" % (element))       
        
    except SMCOperationFailure, e:
        element.href = None
        logger.error("Failed creating element; %s, %s" % (element, e.msg))


def _update(element):
    logger.debug("Updating element: %s, href: %s, json: %s" % (element.name, element.href, element.json))
    try: 
        web_api.session.http_put(element.href, element.json, element.etag)
        logger.info("Success updating element; %s" % element)
        
    except SMCOperationFailure, e:
        logger.error("Failed updating element; %s, %s" % (element, e.msg))

        
def _remove(element):
    logger.debug("Removing element: %s, href: %s" % (element.name, element.href))
    try:
        web_api.session.http_delete(element.href) #delete to href
        logger.info("Success removing element; %s" % element)
            
    except SMCOperationFailure, e:
        logger.error("Failed removing element; %s, %s" % (element, e.msg))

        
def _fetch_element(name=None, href=None, entry_point=None, obj_type=None, \
                   follow_href=False, use_name_field=True):
    try: 
        if href:    #return SMCElement
            result = web_api.session.http_get(href)
            if result:
                element = SMCElement()
                element.href = href
                element.etag = result.etag
                element.json = result.json
                return element 
        if name and obj_type:   #by name and object type filter
            entry_href = web_api.session.get_entry_href(obj_type) #cache
            if not entry_href:
                logger.error("Object type entry point specified was not found: %s" % obj_type)
                return None
        elif name:
            entry_href = web_api.session.get_entry_href('elements') #cache
            
        logger.debug("Searching for element: %s at href: %s" % (name, entry_href))
        result = web_api.session.http_get(entry_href + '?filter=' + name) #execute search
       
        if not result.json: #no results returned
            logger.info("No results found for element name: %s" % name)
        else:
            match = None
            if not use_name_field: # Return any host objects using name as filter (match all)
                logger.debug("Returning all elements matching: %s" % name)
                return result.json
            else: # Only return object where name matches host object name field
                for host in result.json:
                    if host['name'] == name:
                        match = host
                        break   #exits on first match
                if not match:
                    logger.debug("No search results found for name: %s" % name)
                else:
                    logger.debug("Search found direct match for element: %s, %s" % (name,match))
            if follow_href: #follow the href to element
                return _fetch_element(href=match['href'])                
            else:
                return match    #return href str
    
    except SMCOperationFailure, e:
        logger.error("Failure occurred: %s" % e.msg)

        