'''
Created on May 1, 2016

@author: davidlepage
'''
import smc.api.web as web_api
import logging

logger = logging.getLogger(__name__)

def get_element(name, obj_type=None, use_name_field=True):
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
    entry_href = None
    if obj_type:
        entry_href = web_api.session.cache.get_href(obj_type)
        if not entry_href:
            logger.error("Object type entry point specified was not found: %s" % obj_type)
            return
    else:
        entry_href = web_api.session.cache.get_href('elements') #entry point for all elements
    
    logger.debug("Searching for element: %s" % name)
    result = web_api.session.http_get(entry_href + '?filter=' + name) #execute search
   
    if not result.msg: #no results returned
        logger.info("No results found for element name: %s" % name)
    else:
        if not use_name_field: # Return any host objects using name as filter (wildcard match)
            logger.debug("Returning all elements matching: %s" % name)
            return result.msg  # Return anything that was found
        else: # Only return object where name matches host object name field
            match = None #TODO: This could return multiple entries!!!
            for host in result.msg:
                if host['name'] == name:
                    match = host
                    break   #exits on first match
            if not match:
                logger.debug("No search results found for name: %s" % name)
            else:
                logger.debug("Search found direct match for element: %s, %s" % (name,match))
            return match

def get_element_by_href(name):
    """ Get specified element from fully qualified href
        For example, name could be: http://1.1.1.1:8082/elements/single_fw/119
        Args: 
            * name: href (typically reference from smc) for object to retrieve
        Returns:
            Json record representing match
    """
    result = web_api.session.http_get(name)
    
    if not result.msg:
        logger.info("No results found for href, maybe a bad reference: %s" % name)
    return result.msg

def get_element_by_entry_point(name):
    """ Get specified element based on the entry point verb from SMC api
        To get the entry points available, you can call web_api.get_all_entry_points()
        For example: smc.get_element_by_entry_point('log_server')
        Args:
            * name: top level entry point name
        Returns:
            Json representation of name match
    """
    entry = web_api.session.cache.get_href(name)
    
    if entry: #in case an invalid entry point is specified
        result = web_api.session.http_get(entry)
        return result.msg #TODO: return at bottom
    else:
        logger.error("Entry point specified was not found: %s" % name)

     
if __name__ == '__main__':
    web_api.session.login('http://172.18.1.150:8082', 'EiGpKD4QxlLJ25dbBEp20001')
    
    web_api.session.logout()
    
    '''
    #Get FW link
    fw = smc.filter_by_type('single_fw', 'test-run') 
    print "Getting fw at: %s" % fw['href']   
    #Get FW detaild
    fw_details = smc.get_element_by_href(fw['href'])
    #pprint(fw_details['link'])
    #print any(d['rel'] == 'routing' for d in fw_details['link'])
    #Get link to routing
    link_to_routing = next(item for item in fw_details['link'] if item['rel'] == 'routing')
    print "Link to routing: %s" % link_to_routing['href']
    routing_details = smc.get_element_by_href(link_to_routing['href'])
    #print "Routing details:"
    #pprint(routing_details)
    #Find routing node in hash
    print "I'm here"
    pprint(routing_details['routing_node'][0]['routing_node'])
    print "Routing"
    a = routing_details['routing_node'][0]['routing_node'][0]
    
    b = { 'invalid': False,
        'key': 765,
        'name': 'network-3.3.3.0/24',
        'routing_node': [] }
    #pprint(a)
    print "......"
    smc.http_get('http://172.18.1.150:8082/6.0/elements/single_fw/1326/physical_interface/321')
    #Just try and PUT it anyways....
    try:
        r = smc.web_api.http_put('http://172.18.1.150:8082/6.0/elements/single_fw/1326/physical_interface/321', b, "MzIxMzk5MQ==")
    except SMCOperationFailure, e:
        print e.msg
    
    #pprint(smc.get_element_by_href('http://172.18.1.150:8082/6.0/elements/network/677'))
    #Generic routing node level
    #pprint(smc.web_api.get_all_entry_points())'''
    
    web_api.session.logout()