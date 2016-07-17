'''
Created on May 13, 2016

@author: davidlepage
'''
import re
import logging
import smc.api.web as web_api
from smc.api.web import SMCOperationFailure, SMCConnectionError
import smc.actions.search

clean_html = re.compile('<.*?>')

logger = logging.getLogger(__name__)

def create(element):
    """ 
    Create element on SMC
    
    :method: POST
    :param element: SMCElement
    :return: SMCResult
    """
    if element:
        err = None
        try:
            result = web_api.session.http_post(element.href, 
                                               element.json, 
                                               element.params)
        except SMCOperationFailure, e:
            result = e.smcresult
        except SMCConnectionError, e:
            err = e
        except TypeError, e:
            err = e
        finally:
            if err:
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
    if element:
        err = None
        try: 
            result = web_api.session.http_put(element.href, 
                                              element.json, 
                                              element.etag, 
                                              element.params)
        except SMCOperationFailure, e:
            result = e.smcresult
        except SMCConnectionError, e:
            err = e
        except TypeError, e:
            err = e
        finally:
            if err:
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

def fetch_entry_point(name):
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

def fetch_content_as_file(element, stream=True):
    logger.debug("Fetching content as file download to file: %s" % element.filename)
    try:
        print "Fetching...>"
        result = web_api.session.http_get(element.href,  
                                          filename=element.filename,
                                          stream=stream)
        print "result: %s" % result #TODO: Return info for downloads
    except IOError, ioe:
        print "IO Error occured: %s" % ioe
        logger.error("IO Error received with msg: %s" % ioe)
    except SMCOperationFailure, e:
        print "op error: %s" % e
    except SMCConnectionError, e:
        print "conn err: %s" % e

def fetch_href_by_name(name, 
                       filter_context=None, 
                       exact_match=True,
                       domain=None):
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
                                                           'filter_context':filter_context,
                                                           'exact_match': exact_match})
            if result.json:
                if len(result.json) > 1:
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


def async_handler(follower_href, wait_for_finish=True, 
                  sleep_interval=3, 
                  display_msg=True):
    """ Handles asynchronous operations called on engine or node levels
    
    :method: POST
    :param element: The element to be sent to SMC
    :param wait_for_finish: whether to wait for it to finish or not
    :param display_msg: whether to return display messages or not
    :param sleep_interval: how long to wait between async checks
    
    If wait_for_finish is False, the generator will yield the follower 
    href only. If true, will return messages as they arrive and location 
    to the result after complete.
    To obtain messages as they arrive, call the async method in a for loop::
        for msg in engine.export():
            print msg
    """
    import time
    if wait_for_finish:
        last_msg = ''
        while True:
            status = smc.actions.search.element_by_href_as_json(follower_href) #TODO: Use fetch?
            msg = status.get('last_message')
            if display_msg:
                if msg != last_msg:
                    yield re.sub(clean_html,'', msg)
                    #yield msg
                    last_msg = msg
            if status.get('success') == True:
                for link in status.get('link'):
                    if link.get('rel') == 'result':
                        yield link.get('href')
                break
            time.sleep(sleep_interval)
    else:
        yield follower_href
