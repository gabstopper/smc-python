'''
Created on May 13, 2016

@author: davidlepage
'''

import logging
import smc.api.web as web_api
from smc.api.web import SMCOperationFailure, SMCConnectionError, SMCResult
import smc.elements.element

logger = logging.getLogger(__name__)

#cache = web_api.session.cache.get_element(name)
#if cache is not None:
#    print "Found in cache: %s, location: %s" % (name,cache)
#    return cache

def create(element):
    """ 
    Create element on SMC
    
    :method: POST
    :param element: SMCElement
    :return: SMCResult
    """
    assert(isinstance(element, smc.elements.element.SMCElement))
    if element:
        connect_err = None
        try:
            result = web_api.session.http_post(element.href, 
                                               element.json, 
                                               element.params)
        except SMCOperationFailure, e:
            result = e.smcresult
        except SMCConnectionError, e:
            connect_err = e
        finally:
            if connect_err:
                raise
            logger.debug(result)
            return result

def update(element):
    """ 
    Update element on SMC
    
    :method: PUT
    :param element: SMCElement
    :return: SMCResult
    """
    assert(isinstance(element, smc.elements.element.SMCElement))
    if element:
        connect_err = None
        try: 
            result = web_api.session.http_put(element.href, 
                                              element.json, 
                                              element.etag, 
                                              element.params)
        except SMCOperationFailure, e:
            result = e.smcresult
        except SMCConnectionError, e:
            connect_err = e
        finally:
            if connect_err:
                raise
            logger.debug(result)
            return result

def delete(href):
    """
    Delete element on SMC
    
    :method: DELETE
    :param: href: item reference to delete
    :return: SMCResult
    """
    if href:
        connect_err = None
        try:
            result = web_api.session.http_delete(href) #delete to href           
        except SMCOperationFailure, e:
            result = e.smcresult
        except SMCConnectionError, e:
            connect_err = e
        finally:
            if connect_err:
                raise
            logger.debug(result)
            return result

def fetch_entry_point(name): #TODO: Fix this to return SMCResult??
    """ 
    Get the entry point href based on the input name
    
    :method: GET
    :param name: valid element entry point, i.e. 'host', 'iprange', etc
    smc.api.web.get_all_entry_points caches the entry points after login
    :return: SMCResult
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

def fetch_content_as_file(element):
    logger.debug("Fetching content as file download to file: %s" % element.filename)
    try:
        result = web_api.session.http_get(element.href, 
                                          stream=element.stream, 
                                          filename=element.filename)
        print "result: %s" % result #TODO: Return info for downloads
        return result
    except IOError, ioe:
        logger.error("IO Error received with msg: %s" % ioe)
    except SMCOperationFailure, e:
        logger.error("Failure occurred fetching by filename: %s" % e)
    except SMCConnectionError, e:
        raise    


def fetch_href_by_name(name, filter_context=None, use_name_field=True):
    """
    :method: GET
    :param name: element name
    :param use_name_field: match on element name field in SMC
    :return SMCResult
    """
    if name:
        connect_err = None
        try:
            entry_href = web_api.session.get_entry_href('elements')
            result = web_api.session.http_get(entry_href, {'filter': name, 
                                                           'filter_context':filter_context})
            if result.json:
                found_lst = []
                if not use_name_field: # match all
                    result.msg = 'Returning all elements as a wildcard match'
                    return result
                else: # Only return objects where name matches name field
                    for host in result.json:
                        if host.get('name', None) == name:
                            found_lst.append(host)
                    if not found_lst:
                        result.msg = "No search results found for name: %s" % name
                result.json = found_lst
                if len(found_lst) > 1:
                    result.msg = "More than one search result found. Try using a filter based on element type"
                else:
                    result.href = result.json[0].get('href')
            else:
                result.msg = "No results found for: %s" % name                  
        
        except SMCOperationFailure, e:
            result = e.smcresult
        except SMCConnectionError, e:
            connect_err = e
        finally:
            if connect_err:
                raise
            logger.debug(result)
            return result

def fetch_json_by_name(name):
    """ 
    Fetch json based on the element name
    First gets the href based on a search by name, then makes a 
    second query to obtain the element json
    
    :method: GET
    :param name: element name
    :return: SMCResult
    """
    if name:
        connect_err = None
        try:
            result = fetch_href_by_name(name)
            if result.href:
                result = fetch_json_by_href(result.href)
                #else element not found
        except SMCOperationFailure, e:
            result = e.smcresult
        except SMCConnectionError, e:
            connect_err = e
        finally:
            if connect_err:
                raise
            logger.debug(result)
            return result
    
def fetch_json_by_href(href):
    """ 
    Fetch json for element by using href
    
    :method: GET
    :param href: href of the element
    :return: SMCResult
    """
    if href:
        connect_err = None
        try:
            result = web_api.session.http_get(href)
            if result:
                result.href = href
        except SMCOperationFailure, e:
            result = e.smcresult
        except SMCConnectionError, e:
            connect_err = e
        finally:
            if connect_err:
                raise
            logger.debug(result)
            return result
        