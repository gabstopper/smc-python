import smc.elements.element
import smc.elements.license
import smc.api.web as web_api
from smc.api.web import SMCOperationFailure

import logging
logger = logging.getLogger(__name__)

def host(name, ip, secondary_ip=[], comment=None):
    """ Create host element
        Args:
            * name: name for object
            * ip: ipv4 address
            * comment (optional)
        Returns:
            None
    """
    if smc.helpers.is_valid_ipv4(ip):
        entry_href = web_api.session.cache.get_href('host')        
        
        host = smc.elements.element.Host()            
        host.name = name
        host.ip = ip
        host.secondary_ip = secondary_ip
        host.comment = comment
        
        try:
            r = web_api.session.http_post(entry_href, host.create())           
            logger.info("Success creating single host: %s, href: %s" % (host.name, r))
        
        except SMCOperationFailure, e:
            logger.error("Failed creating single host: %s, api message: %s" % (host.name, e.msg))                           
    else:
        logger.error("Failed: Invalid IPv4 address specified: %s, create object: %s failed" % (ip, name)) 

    
def router(name, ip, secondary_ip=None, comment=None):
    """ Create router element
        Args:
            * name: name for object
            * ip: ipv4 address
            * comment (optional)
        Returns:
            None
    """    
    if smc.helpers.is_valid_ipv4(ip):
        entry_href = web_api.session.cache.get_href('router')
        
        router = smc.elements.element.Router() #TODO: Need router comment field
        router.name = name
        router.address = ip
        router.secondary_ip = secondary_ip
        
        try:
            r = web_api.session.http_post(entry_href, router.create())
            logger.info("Success creating router object: %s, href: %s" % (router.name, r))
        
        except SMCOperationFailure, e:
            logger.error("Failed creating router object: %s, api message: %s" % (router.name, e.msg))                          
    else:
        logger.error("Failed: Invalid IPv4 address specified: %s, create object: %s failed" % (ip, name)) 

def network(name, ip_network, comment=None):
    """ Create network element
        Args:
            * name: name for object
            * ip_network: ipv4 address in cidr or full netmask format (1.1.1.1/24, or 1.1.1.0/255.255.0.0)
            * comment (optional)
        Returns:
            None
    """
    cidr = smc.helpers.ipaddr_as_network(ip_network)
    if cidr:
        entry_href = web_api.session.cache.get_href('network')
        
        network = smc.elements.element.Network()
        network.name = name
        network.ip4_network = cidr
        network.comment = comment
        
        try:
            r = web_api.session.http_post(entry_href, network.create())
            logger.info("Success creating network object: %s, href: %s" % (network.name, r))
        
        except SMCOperationFailure, e:
            logger.error("Failed creating network object: %s, api message: %s" % (network.name, e.msg))
            print network.create()
    else:
        logger.error("Error with network object creation: %s; make sure address specified is in network: %s" % (name, ip_network))

            
def group(name, members=[], comment=None):
    """ Create group element, optionally with members
        Members must already exist in SMC. Before being added to the group a search will be 
        performed for each member specified. 
        Args:
            * name: name for object
            * members list; i.e. ['element1', 'element2', etc]. Most elements can be used in a group
            * comment (optional)
        Returns:
            None
    """
    entry_href = web_api.session.cache.get_href('group')
    
    group = smc.elements.element.Group()
    group.name = name
    group.comment = comment
    
    if members:
        for m in members: #add each member
            found_member = smc.search.get_element(m)
            if found_member:
                logger.debug("Found member: %s, adding to group: %s" % (m, group.name))
                group.members.append(found_member['href'])
                continue
            else:
                logger.info("Element: %s could not be found, not adding to group" % m)    
    try:
        r = web_api.session.http_post(entry_href, group.create())
        logger.info("Success creating group: %s, href: %s" % (group.name, r))
    
    except SMCOperationFailure, e:
        logger.error("Failed creating group record: %s, api message: %s" % (name, e.msg))
                         
#TODO: Not finished implementing;This works if it's applied directly to a single fw, but not globally
'''def blacklist(src, dst, duration="3600"):
    if smc.helpers.is_valid_ipv4(src) and smc.helpers.is_valid_ipv4(dst):
        
        entry = smc.web_api.get_entry_href('blacklist')   
        bl_template = smc.helpers.get_json_template('blacklist.json') 
        
        print "Blah"  
        if bl_template:  
            bl_template['duration'] = duration
            bl_template['end_point1']['ip_network'] = src + '/32'
            bl_template['end_point2']['ip_network'] = dst + '/0'
        print bl_template
        try:
            smc.web_api.http_post('http://172.18.1.150:8082/6.0/elements/fw_cluster/116/blacklist', bl_template)
        except SMCOperationFailure, e:
            print "Error!: %s" % e.msg
                
    else:
        #logger.error("Invalid IP address given for blacklist entry, src: %s, dst: %s" % (src,dst))  
        print "Invalid IP address given for blacklist entry, src: %s, dst: %s" % (src,dst)
'''
        
def single_fw(name, mgmt_ip, mgmt_network, dns=None, fw_license=False):
    """ Create single firewall with a single management interface
        Args:
            * name: name of fw instance
            * mgmt_ip: ipv4 address of management interface (interface 0)
            * mgmt_network: netmask of mgmt ip
            * dns (optional): string for DNS server
            * fw_license (optional): After successful creation, try to auto-license
        Returns:
            None
    """
    if not smc.helpers.is_ipaddr_in_network(mgmt_ip, mgmt_network):
        logger.error("Failed: Management IP is not in the management network, can't add single_fw")
        return None
   
    available_log_servers = smc.search.get_element_by_entry_point('log_server')
    if not available_log_servers:
        logger.error("Can't seem to find an available Log Server on specified SMC, can't add single_fw: %s" % name)
        return None
    
    single_fw = smc.elements.element.SingleFW()
    single_fw.name = name
    single_fw.mgmt_ip = mgmt_ip
    single_fw.mgmt_network = mgmt_network
    single_fw.dns = dns
    single_fw.fw_license = fw_license
    
    for found in available_log_servers:
        #TODO: If multiple log servers are present, how to handle - just get the first one
        single_fw.log_server = found['href']
    
    entry_href = web_api.session.cache.get_href('single_fw') #get entry point for single_fw
    
    logger.debug("Modified json for single_fw: %s" % single_fw.create())
    
    try: 
        new_href = web_api.session.http_post(entry_href, single_fw.create())
        logger.info("Success creating single firewall: %s, new href: %s" % (single_fw.name, new_href))
        
        if fw_license: #fw license is specified
            logger.debug("Bind license specified, checking for available license")
            fw_from_link = smc.search.get_element_by_href(new_href)
            
            bind_license_href = fw_from_link['nodes'][0]['firewall_node']['link']
            bind_href = next(item for item in bind_license_href if item['rel'] == 'bind')
            logger.debug("Firewall: %s, bind license href: %s" % (single_fw.name,bind_href['href']))
            
            smc.elements.license.bind_license(bind_href['href']) #TODO: Check return to make sure it actually bound
            logger.info("Successfully bound license to single_fw: %s" % name)    
                       
    except SMCOperationFailure, e:
        logger.error("Create single_fw: %s failed: %s" % (single_fw.name, e.msg))

    
def cluster_fw(data):
    pass

def single_ips(data):
    pass

def cluster_ips(data):
    pass

def master_engine(data):
    pass

def virtual_ips(data):
    pass

def virtual_fw(data):
    pass


if __name__ == '__main__':
    web_api.session.login('http://172.18.1.150:8082', 'EiGpKD4QxlLJ25dbBEp20001')
   
    '''   
    smc.create.host('aidan', '23.23.23.23')   
    smc.create.group('lepagegroup', comment='test comments - see this')
    smc.create.network('hostbitsnotinnetwork', '1.2.3.0/255.255.252.0')
    smc.create.network('goodnetwork', '1.2.0.0/255.255.252.0')
    smc.create.network('networkwithcidr', '1.3.0.0/24', 'created by api tool')
    smc.create.router('gatewayrouter', '5.5.5.5')
    
    smc.remove.element('aidan')
    smc.remove.element('lepagegroup')
    '''
    
    
    #smc.remove.element('myfw')
    #smc.create.single_fw('myfw', '172.18.1.5', '172.18.1.0/24', dns='5.5.5.5', fw_license=True)
    from pprint import pprint
    href = smc.search.get_element('myfw')
    print "Link to api_fw: %s " % href
    data = web_api.session.http_get(href['href'])
    print data.etag
    #pprint(data.msg)
    
    #### GOOD
    element = smc.elements.element.SMCElement(data.msg)
    single_fw = smc.elements.element.SingleFW(element)
    a = single_fw.add_interface('11.11.11.11', '11.11.11.0/24')
    pprint(a)

    #pprint(data.msg)
    try: 
        location = web_api.session.http_put(href['href'], a, data.etag)
        print "Host now found at: %s" % location
    except SMCOperationFailure, e:
        print e.msg
    web_api.session.logout()
