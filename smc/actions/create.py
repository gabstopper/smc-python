import logging
import smc.elements.element
import smc.api.web as web_api
import smc.api.common as common_api
from smc.actions.search import get_logical_interface

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
        entry_href = smc.search.element_entry_point('host')
        
        host = smc.elements.element.Host()
        host.href = entry_href         
        host.name = name
        host.ip = ip
        host.secondary_ip = secondary_ip
        host.comment = comment
        
        common_api._create(host.create())
                              
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
    
    entry_href = smc.search.element_entry_point('address_range')
    
    iprange = smc.elements.element.IpRange()
    iprange.href = entry_href
    iprange.name = name
    iprange.iprange = ip_range
    
    common_api._create(iprange.create())
    
    
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
        entry_href = smc.search.element_entry_point('router')
        
        router = smc.elements.element.Router()
        router.href = entry_href
        router.name = name
        router.comment = comment
        router.address = ip
        router.secondary_ip = secondary_ip
        
        common_api._create(router.create())  
                                
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
        entry_href = smc.search.element_entry_point('network')
        
        network = smc.elements.element.Network()
        network.href = entry_href
        network.name = name
        network.ip4_network = cidr
        network.comment = comment
        
        common_api._create(network.create()) 
        
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
    
    entry_href = smc.search.element_entry_point('group')
    
    group = smc.elements.element.Group()
    group.href = entry_href
    group.name = name
    group.comment = comment
    
    if members:
        for m in members: #add each member
            found_member = smc.search.element_href(m)
            if found_member:
                logger.debug("Found member: %s, adding to group: %s" % (m, group.name))
                group.members.append(found_member)
                continue
            else:
                logger.info("Element: %s could not be found, not adding to group" % m)    
    
    common_api._create(group.create()) 
    from pprint import pprint
    pprint(group.json)                     

       
def single_fw(name, mgmt_ip, mgmt_network, interface_id='0', dns=None, fw_license=False):
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
    
    #l3fw = _create_engine_node("l3fw", **locals())
    
    if not smc.helpers.is_ipaddr_in_network(mgmt_ip, mgmt_network):
        logger.error("Management IP: %s is not in the management network: %s, cannot add single_fw" % (mgmt_ip,mgmt_network))
        return None
    
    log_server = smc.search.get_first_log_server()
    if not log_server:
        logger.error("Can't seem to find an available Log Server on specified SMC, cannot add single_fw: %s" % name)
        return None
       
    entry_href = smc.search.element_entry_point('single_fw') #get entry point for single_fw
    
    l3_intf = smc.elements.element.SingleNodeInterface()
    l3_intf.address = mgmt_ip
    l3_intf.network_value = mgmt_network
    l3_intf.auth_request = True
    l3_intf.primary_mgt = True
    l3_intf.outgoing = True
    l3_intf.nicid = l3_intf.interface_id = interface_id
    l3_intf.create()
    
    #l3fw = __create_engine_node(name, mgmt_ip, mgmt_network, interface_id, dns)
    l3fw = smc.elements.element.L3FW()
    l3fw.href = entry_href
    l3fw.name = name
    l3fw.dns += [dns] if dns is not None else []
    l3fw.log_server = log_server
    l3fw.interfaces.append(l3_intf.json)   
    
    common_api._create(l3fw.create())
    
    #from pprint import pprint
    #pprint(l3fw.json)
 
   
def single_layer2(name, mgmt_ip, mgmt_network, interface_id='1,2', dns=None, fw_license=False):
    """ Create single layer 2 firewall element
    Layer 2 firewall will have a layer 3 management interface (interface 0) and will also need to
    create at least one inline or capture interface. 
    Args:
        * name: name of single layer 2 fw
        * mgmt_ip: ip address for management layer 3 interface
        * mgmt_network: netmask for management network
        * interface_id: int specifying interface id's to be used for inline interfaces (default: [1,2])
        * dns: dns servers for management interface (optional)
        * fw_license: attempt license after creation (optional)
    Returns:
        None
    """
    
    if not smc.helpers.is_ipaddr_in_network(mgmt_ip, mgmt_network):
        logger.error("Management IP: %s is not in the management network: %s, cannot add single_fw" % (mgmt_ip,mgmt_network))
        return None

    log_server = smc.search.get_first_log_server()
    if not log_server:
        logger.error("Can't seem to find an available Log Server on specified SMC, cannot add single_fw: %s" % name)
        return None
    
    entry_href = smc.search.element_entry_point('single_layer2')
    
    l3_intf = smc.elements.element.NodeInterface()
    l3_intf.address = mgmt_ip
    l3_intf.network_value = mgmt_network
    l3_intf.primary_mgt = True
    l3_intf.outgoing = True
    l3_intf.nicid = l3_intf.interface_id = 0
    l3_intf.create()
    
    inline_intf = smc.elements.element.InlineInterface()
    inline_intf.logical_interface_ref = get_logical_interface('default_eth')
    inline_intf.interface_id = '1'
    inline_intf.nicid = '1-2'
    inline_intf.create()
        
    l2fw = smc.elements.element.FWLayer2()
    l2fw.href = entry_href
    l2fw.name = name
    l2fw.dns += [dns] if dns is not None else []
    l2fw.log_server = log_server
    l2fw.interfaces.append(l3_intf.json)
    l2fw.interfaces.append(inline_intf.json)
    
    common_api._create(l2fw.create())

    #from pprint import pprint
    #pprint(l2fw.json)


def single_ips(name, mgmt_ip, mgmt_network, interface_id='1,2', dns=None, fw_license=False):
    pass
    

def l3interface(name, ip, network, interface_id=None):
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
    
    entry_href = smc.search.element_href(name)
    
    if entry_href is not None:
        
        fw_orig = web_api.session.http_get(entry_href)
        
        l3_intf = smc.elements.element.SingleNodeInterface()
        l3_intf.address = ip
        l3_intf.network_value = network
        l3_intf.nicid = l3_intf.interface_id = interface_id
        l3_intf.create()
        
        engine = smc.elements.element.EngineNode()
        engine.interfaces.append(l3_intf.json)
        engine.type = l3_intf.type
        engine.name = name
        engine.href = entry_href
        engine.etag = fw_orig.etag
           
        common_api._update(engine.update(fw_orig.json))
        
    else:
        logger.error("Can't find layer 3 FW specified: %s, cannot add interface" % name)
 
 
def l2interface(name, interface_id='1-2', logical_int='default_eth'):
    """ Add layer 2 inline interface   
    Inline interfaces require two physical interfaces for the bridge and a logical 
    interface to be assigned. By default, interface 1,2 will be used if interface_id is 
    not specified. 
    The logical interface is used by SMC for policy to logically group both interfaces
    It is not possible to have inline and capture interfaces on the same node with the
    same logical interface definition. Automatically create logical interface if it does
    not already exist.    
    Args: 
        * node: node name to add inline interface pair
        * interface_id [], int values of interfaces to use for inline pair (default: 1,2)
        * logical_int: logical interface name to map to inline pair (default: 'default_eth')
    Returns:
        None
    """
          
    entry_href = smc.search.element_href(name)
    
    if entry_href is not None:
        
        l2_orig = web_api.session.http_get(entry_href)
        
        logical_int_href = smc.search.get_logical_interface(logical_int)
        if logical_int_href is None:
            logger.info("Logical interface: %s not found, creating automatically" % logical_int)
            logical_int_href = logical_interface(logical_int, comment="made by api tool")
        
        inline_intf = inline_interface(interface_id)
        
        engine = smc.elements.element.EngineNode()
        engine.interfaces.append(inline_intf.json)
        engine.type = inline_intf.type
        engine.name = name
        engine.href = entry_href
        engine.etag = l2_orig.etag
        
        common_api._update(engine.update(l2_orig.json))
        
        #from pprint import pprint
        #pprint(l2_orig.json)
        
    else:
        logger.error("Cannot find node specified to add layer 2 inline interface: %s" % name)

   
def logical_interface(name, comment=None):
    """ Create logical interface
    Logical interfaces are required to be unique for a single IPS or layer 2 firewall that
    has both inline and capture interfaces on the same host. If the IPS or layer2 FW only 
    use capture or inline interfaces, the same logical interface can be used for all. 
    Args: 
        * name: name of logical interface
        * comment: optional
    Returns:
        str href for new logical interface element
    """
    
    entry_href = web_api.session.get_entry_href('logical_interface')
    
    logical_int = smc.elements.element.LogicalInterface()
    logical_int.name = name
    logical_int.href = entry_href
    logical_int.comment = comment if comment is not None else ""
   
    common_api._create(logical_int.create())
    
    return logical_int.href
 

def mgmt_interface(mgmt_ip, mgmt_network, interface_id=0):
    l3_intf = smc.elements.element.SingleNodeInterface()
    l3_intf.address = mgmt_ip
    l3_intf.network_value = mgmt_network
    l3_intf.auth_request = True
    l3_intf.primary_mgt = True
    l3_intf.outgoing = True
    l3_intf.nicid = l3_intf.interface_id = interface_id
    
    l3_intf.create()
    return l3_intf


def inline_interface(interface_id='1-2', logical_interface='default_eth'):
    #TODO: protect this from incorrectly specified input format
    first_intf = interface_id.split('-')   
    inline_intf = smc.elements.element.InlineInterface()
    inline_intf.logical_interface_ref = get_logical_interface(logical_interface)
    inline_intf.interface_id = first_intf[0]
    inline_intf.nicid = interface_id
    
    inline_intf.create()
    return inline_intf
 
        
def capture_interface(interface_id=1, logical_interface='default_eth'):
    capture = smc.elements.element.CaptureInterface()
    capture.logical_interface_ref = get_logical_interface(logical_interface)
    capture.interface_id = interface_id
    capture.nicid = interface_id
    
    capture.create()
    return capture

           
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
    
    engine_href = smc.search.element_href(engine) #ref to engine
    if engine_href is None:
        logger.error("Can't find engine node: %s, cannot process route add" % engine)
        return None
    
    router_element = smc.search.element_href_use_filter(gw, 'router') #router object
    if router_element is None:
        logger.error("Can't find router object: %s, cannot process route add" % gw)
        return None
    
    network_element = smc.search.element_href_use_filter(network, 'network')
    if network_element is None:
        logger.error("Can't find network object: %s, cannot process route add" % network)
        return None
    
    node = smc.search.element_by_href_as_json(engine_href) #get node json
   
    route_link = next(item for item in node['link'] if item['rel'] == 'routing')   
    routing_orig = smc.search.element_by_href_as_smcelement(route_link['href']) 
   
    route = smc.elements.element.Route()
    route.name = engine
    route.href = route_link['href']
    route.etag = routing_orig.etag
    route.json = routing_orig.json  #will append to original routing json
    
    result = smc.search.element_by_href_as_json(router_element)
    route.gw_href = router_element
    route.gw_ip = result['address']             
    route.gw_name = result['name']
            
    result = smc.search.element_by_href_as_json(network_element) #dest net info
    route.network_href = network_element
    route.network_ip = result['ipv4_network']
    route.network_name = result['name']
    
    route.interface_id = interface_id
    
    routing_json = route.create()
    
    #from pprint import pprint
    #pprint (vars(route))
    
    if routing_json is not None:    
        
        common_api._update(routing_json)
       
    else:
        logger.error("Can not find specified interface: %s for route add, double check the interface configuration" % route.interface_id)


def _create_engine_node(val, **kwargs):
    
    if not smc.helpers.is_ipaddr_in_network(kwargs['mgmt_ip'], kwargs['mgmt_network']):
        logger.error("Management IP: %s is not in the management network: %s, cannot add single_fw" % \
                                    (kwargs['mgmt_ip'],kwargs['mgmt_network']))
        return None
    
    log_server = smc.search.get_first_log_server()
    if not log_server:
        logger.error("Can't seem to find an available Log Server on specified SMC, cannot add single_fw: %s" % kwargs['name'])
        return None
    
    return smc.elements.element.EngineNodeFactory().makeNode("l3fw", \
                                    kwargs['mgmt_ip'], kwargs['mgmt_network'], kwargs['interface_id'], \
                                            kwargs['dns'], log_server)

         
def cluster_fw(data):
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
    
    '''
    smc.create.host('testobject', '1.2.3.4')
    smc.remove.element('testobject')
    
    smc.create.network('testnetwork', '172.18.7.0/24')
    smc.remove.element('testnetwork')
    
    smc.create.iprange('testrange', '172.19.5.1-172.19.5.200')
    smc.remove.element('testrange')
    
    smc.create.group('testgroup')
    smc.remove.element('testgroup')
    smc.create.host('testobject', '12.3.4.5')
    smc.create.group('testgroup', members=['testobject'])
    smc.remove.element('testgroup')
    
    smc.create.router('testrouter','1.1.2.3')
    smc.remove.element('testrouter')
    '''
    
    smc.remove.element('myfw')
    smc.create.single_fw('myfw', '172.18.1.254', '172.18.1.0/24', dns='5.5.5.5', fw_license=True)
    smc.create.l3interface('myfw', '10.10.0.1', '10.10.0.0/16', 3)
    smc.create.l3interface('myfw', '10.10.1.1', '10.10.0.0/16', 4)
    smc.create.l3route('myfw', '172.18.1.80', 'Any network', 0) #Good
    smc.create.l3route('myfw', '10.10.0.1', '192.168.3.0/24', 3) #Good
    '''time.sleep(15)
    smc.remove.element('myfw')
    smc.create.single_layer2('mylayer3', '172.18.1.254', '172.18.1.0/24', dns='5.5.5.5', fw_license=True)
    smc.create.l2interface('mylayer3', interface_id='6-7')
    time.sleep(15)
    smc.remove.element('mylayer3')
    '''
    
    
    print("--- %s seconds ---" % (time.time() - start_time))   
    web_api.session.logout()
