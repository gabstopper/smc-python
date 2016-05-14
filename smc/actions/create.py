import logging
import smc.elements.element
import smc.elements.license
import smc.api.web as web_api
import smc.api.common as common

logger = logging.getLogger(__name__)


def host(name, ip, secondary_ip=[], comment=None):
    """ Create host object
        Args:
            * name: name, must be unique
            * ip: ip address of host
            * secondary_ip[] (optional): optional additional IP's for host
            * comment (optional)
        Returns:
            None
    """
    if smc.helpers.is_valid_ipv4(ip): 
        entry_href = web_api.session.get_entry_href('host')        
        
        host = smc.elements.element.Host()
        host.href = entry_href    
        host.type = "host"        
        host.name = name
        host.ip = ip
        host.secondary_ip = secondary_ip
        host.comment = comment
        
        common._create(host.create())
                              
    else:
        logger.error("Failed: Invalid IPv4 address specified: %s, create object: %s failed" % (ip, name)) 
    

def iprange(name, ip_range, comment=None):
    """ Create iprange object 
        Args:
            * name: name for object
            * iprange: ip address range, i.e. 1.1.1.1-1.1.1.10
            * comment (optional)
        Returns:
            None
    """
    addr = ip_range.split('-') #just verify each side is valid ip addr
    if len(addr) == 2: #has two parts
        if not smc.helpers.is_valid_ipv4(addr[0]) or not smc.helpers.is_valid_ipv4(addr[1]):
            logger.error("Invalid ip address range provided: %s" % ip_range)
            return None
    else: 
        logger.error("Invalid ip address range provided: %s" % ip_range)
        return None
    
    entry_href = web_api.session.get_entry_href('address_range')
    
    iprange = smc.elements.element.IpRange()
    iprange.href = entry_href
    iprange.type = "address range"
    iprange.name = name
    iprange.iprange = ip_range
    
    common._create(iprange.create()) 
    
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
        entry_href = web_api.session.get_entry_href('router')
        
        router = smc.elements.element.Router() #TODO: Need router comment field
        router.href = entry_href
        router.type = "router"
        router.name = name
        router.address = ip
        router.secondary_ip = secondary_ip
        
        common._create(router.create())  
                                
    else:
        logger.error("Invalid IPv4 address specified: %s, create object: %s failed" % (ip, name)) 


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
        entry_href = web_api.session.get_entry_href('network')
        
        network = smc.elements.element.Network()
        network.href = entry_href
        network.type = "network"
        network.name = name
        network.ip4_network = cidr
        network.comment = comment
        
        common._create(network.create()) 
        
    else:
        logger.error("Invalid address specified for network: %s; make sure address specified is in network: %s" % (name, ip_network))

           
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
    entry_href = web_api.session.get_entry_href('group')
    
    group = smc.elements.element.Group()
    group.href = entry_href
    group.type = "group"
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
    
    common._create(group.create()) 
                         
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
 
#TODO: allow interface number to be configured for initial fw        
def single_fw(name, mgmt_ip, mgmt_network, interface_id=None, dns=None, fw_license=False):
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
        logger.error("Management IP: %s is not in the management network: %s, cannot add single_fw" % (mgmt_ip,mgmt_network))
        return None
   
    available_log_servers = smc.search.get_element_by_entry_point('log_server')
    if not available_log_servers:
        logger.error("Can't seem to find an available Log Server on specified SMC, cannot add single_fw: %s" % name)
        return None
    
    entry_href = web_api.session.get_entry_href('single_fw') #get entry point for single_fw
    
    single_fw = smc.elements.element.SingleFW()
    single_fw.href = entry_href
    single_fw.type = "single_fw"
    single_fw.dns = dns
    single_fw.name = name
    single_fw.mgmt_ip = mgmt_ip
    single_fw.fw_license = fw_license
    single_fw.mgmt_network = mgmt_network
    single_fw.interface_id = interface_id
    
    for found in available_log_servers:
        #TODO: If multiple log servers are present, how to handle - just get the first one
        single_fw.log_server = found['href']
    
    common._create(single_fw.create())
    
    print "After update, have href: %s" % single_fw.href
    #logger.debug("Modified json for single_fw: %s" % new_fw)
        
    #    if fw_license: #fw license is specified
    #        logger.debug("Bind license specified, checking for available license")
    #        fw_from_link = smc.search.get_element_by_href(new_href)
            
    #        bind_license_href = fw_from_link['nodes'][0]['firewall_node']['link']
    #        bind_href = next(item for item in bind_license_href if item['rel'] == 'bind')
    #        logger.debug("Firewall: %s, bind license href: %s" % (single_fw.name,bind_href['href']))
            
    #        smc.elements.license.bind_license(bind_href['href']) #TODO: Check return to make sure it actually bound
    #        logger.info("Successfully bound license to single_fw: %s" % name)    
    

def l3interface(l3fw, ip, network, interface_id=None):
    """ Add L3 interface for single FW 
        Args:
            * l3fw: name of firewall to add interface to
            * ip: ip of interface
            * network: ip is validated to be in network before sending
            * interface_id: interface_id to use
        Returns: 
            None
    """
    if not smc.helpers.is_ipaddr_in_network(ip, network):
        logger.error("IP address: %s is not part of the network provided: %s, cannot add interface" % (ip,network))
        return None
    
    network = smc.helpers.ipaddr_as_network(network)    #convert to cidr in case full mask provided
    
    entry_href = smc.search.get_element(l3fw)
    
    if entry_href is not None:
        entry_href = entry_href['href']
        fw_orig = web_api.session.http_get(entry_href)
        
        single_fw = smc.elements.element.SingleFW()
        single_fw.type = "interface"
        single_fw.href = entry_href
        single_fw.etag = fw_orig.etag
        single_fw.name = l3fw
        single_fw.element = fw_orig.msg
        
        new_interface = single_fw.add_interface(ip, network, interface_id)
        
        logger.debug("href: %s, json: %s, etag: %s" % (single_fw.href, single_fw.json, single_fw.etag))
        
        common._update(new_interface)
        
    else:
        logger.error("Can't find layer 3 FW specified: %s, cannot add interface" % l3fw)
 
        
def l3route(engine, gw, network, interface_id): 
    """ Add route to l3fw 
        This could be added to any engine type. Non-routable engine roles (L2/IPS) may
        still require route/s defined on the L3 management interface
        Args:
            * l3fw: name of firewall to add route
            * gw: next hop router object
            * network: next hop network behind gw
            * interface_id: interface to apply route
        Returns:
            None
    """
    href = smc.search.get_element(engine) #ref to engine
    if href is None:
        logger.error("Can't find engine node: %s, cannot process route add" % engine)
        return None
    engine_href = href['href']
    
    router_element = smc.search.get_element(gw, 'router') #router object
    if router_element is None:
        logger.error("Can't find router object: %s, cannot process route add" % gw)
        return None
    
    network_element = smc.search.get_element(network, 'network')
    if network_element is None:
        logger.error("Can't find network object: %s, cannot process route add" % network)
        return None
    
    node = web_api.session.http_get(engine_href) #get node json
   
    route_link = next(item for item in node.msg['link'] if item['rel'] == 'routing')   
    route_href = route_link['href'] #http put back to this node 
    routing_node = web_api.session.http_get(route_href) 
    
    route = smc.elements.element.Route()
    route.name = engine
    route.type = "route"
    route.href = route_href
    route.etag = routing_node.etag
    route.element = routing_node.msg
    
    result = web_api.session.http_get(router_element['href']) #populate router info
    route.gw_href = router_element['href']
    route.gw_ip = result.msg['address']             
    route.gw_name = result.msg['name']
        
    result = web_api.session.http_get(network_element['href']) #dest net info
    route.network_href = network_element['href']
    route.network_ip = result.msg['ipv4_network']
    route.network_name = result.msg['name']
    
    route.interface_id = interface_id
    
    routing_json = route.create()
    
    if routing_json is not None:    
        
        common._update(routing_json)
       
    else:
        logger.error("Can not find specified interface: %s for route add, double check the interface configuration" % route.interface_id)
      
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
   
    import time
    start_time = time.time()

    
    smc.create.host('dlepage', '5.6.7.8')
    
    
    #Test create hosts, networks, group and routers   
    smc.create.host('aidan', '23.23.23.23')  
    smc.create.iprange('myrange', '5.5.5.5-5.5.5.6') 
    smc.create.group('lepagegroup', comment='test comments - see this')
    smc.create.network('hostbitsnotinnetwork', '1.2.3.0/255.255.252.0')
    smc.create.network('goodnetwork', '1.2.0.0/255.255.252.0')
    smc.create.network('networkwithcidr', '1.3.0.0/24', 'created by api tool')
    smc.create.router('gatewayrouter', '5.5.5.5')
    smc.create.iprange('myrange', '5.5.5.5-5.5.5.6')
    smc.remove.element('aidan')
    smc.remove.element('lepagegroup')
    
    
    '''
    #Test l3route creation
    smc.create.l3route('myfw7', '192.18.1.80', 'Any network', 0) #Unknown host
    smc.create.l3route('myfw4', '192.18.1.100', 'Any network', 0) #Unknown gw
    smc.create.l3route('myfw4', '192.18.1.100', 'Any2 network', 0) #Unknown network
    smc.create.l3route('myfw4', '172.18.1.80', 'Any network', 0) #Good
    '''  
     

    
    
    #Test single_fw, add interfaces and routes
    smc.remove.element('myfw')
    time.sleep(10)
    #Create the objects required for routes
    smc.create.router('172.18.1.250', '172.18.1.250')   #name, #ip
    smc.create.router('172.20.1.250', '172.20.1.250')   #name, #ip
    smc.create.network('192.168.3.0/24', '192.168.3.0/24') #name, #ip  '''
    smc.create.single_fw('myfw', '172.18.1.254', '172.18.1.0/24', dns='5.5.5.5', fw_license=True)
    smc.create.l3interface('myfw', '10.10.0.1', '10.10.0.0/16', 3)
    #time.sleep(10)
    smc.create.l3interface('myfw', '172.20.1.254', '172.20.1.0/255.255.255.0', 6)
    smc.create.l3route('myfw', '172.18.1.250', 'Any network', 0) #Next hop, dest network, interface
    smc.create.l3route('myfw', '172.20.1.250', '192.168.3.0/24', 6)
    
    
    print("--- %s seconds ---" % (time.time() - start_time))    
    web_api.session.logout()
