import logging
import smc.elements.element
import smc.api.web as web_api
import smc.api.common as common_api
from smc.actions.search import get_logical_interface
from smc.elements.element import EngineNode, SingleLayer3, SingleIPS, SingleLayer2, \
    inline_interface, l3_interface

logger = logging.getLogger(__name__)


def host(name, ipaddress, secondary_ip=[], comment=None):
    """ create host object       
    :param name: name, must be unique
    :param ipaddress: ip address of host
    :param secondary_ip[] (optional): optional additional IP's for host
    :param comment (optional)
    :return None
    """
    
    if smc.helpers.is_valid_ipv4(ipaddress): 
        entry_href = smc.search.element_entry_point('host')
        
        host = smc.elements.element.Host()
        host.href = entry_href         
        host.name = name
        host.ip = ipaddress
        host.secondary_ip = secondary_ip
        host.comment = comment
        
        common_api._create(host.create())
                              
    else:
        logger.error("Failed: Invalid IPv4 address specified: %s, create object: %s failed" % (ipaddress, name)) 
    

def iprange(name, addr_range, comment=None):
    """ create iprange object 
    :param name: name for object
    :param addr_range: ip address range, i.e. 1.1.1.1-1.1.1.10
    :param comment (optional)
    :return None
    """
    
    addr = addr_range.split('-') #just verify each side is valid ip addr
    if len(addr) == 2: #has two parts
        if not smc.helpers.is_valid_ipv4(addr[0]) or not smc.helpers.is_valid_ipv4(addr[1]):
            logger.error("Invalid ip address range provided: %s" % addr_range)
            return None
    else: 
        logger.error("Invalid ip address range provided: %s" % addr_range)
        return None
    
    entry_href = smc.search.element_entry_point('address_range')
    
    iprange = smc.elements.element.IpRange()
    iprange.href = entry_href
    iprange.name = name
    iprange.iprange = addr_range
    
    common_api._create(iprange.create())
    
    
def router(name, ipaddress, secondary_ip=None, comment=None):
    """ create router element
    :param name: name for object
    :param ipaddress: ipv4 address
    :param comment (optional)
    :return None
    """  
      
    if smc.helpers.is_valid_ipv4(ipaddress):
        entry_href = smc.search.element_entry_point('router')
        
        router = smc.elements.element.Router()
        router.href = entry_href
        router.name = name
        router.comment = comment
        router.address = ipaddress
        router.secondary_ip = secondary_ip
        
        common_api._create(router.create())  
                                
    else:
        logger.error("Invalid IPv4 address specified: %s, create object: %s failed" % (ipaddress, name)) 


def network(name, ip_network, comment=None):
    """ create network element   
    :param name: name for object
    :param ip_network: ipv4 address in cidr or full netmask format (1.1.1.1/24, or 1.1.1.0/255.255.0.0)
    :param comment (optional)
    :return None
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
    """ create group element, optionally with members
    Members must already exist in SMC. Before being added to the group a search will be 
    performed for each member specified.     
    :param name: name for object
    :param members list; i.e. ['element1', 'element2', etc]. Most elements can be used in a group
    :param comment (optional)
    :return None
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
    #from pprint import pprint
    #pprint(group.json)                     

       
def single_fw(name, mgmt_ip, mgmt_network, mgmt_interface='0', dns=None, fw_license=False):
    """ create single firewall with a single management interface
    :param name: name of single layer 2 fw
    :param mgmt_ip: ip address for management layer 3 interface
    :param mgmt_network: netmask for management network
    :param mgmt_interface: interface id for l3 mgmt
    :param dns: dns servers for management interface (optional)
    :param fw_license: attempt license after creation (optional)
    :return None
    """
    
    if not smc.helpers.is_ipaddr_in_network(mgmt_ip, mgmt_network):
        logger.error("Management IP: %s is not in the management network: %s, cannot add single_fw" % (mgmt_ip,mgmt_network))
        return None
      
    single_fw = SingleLayer3(**locals())
    single_fw.href = smc.search.element_entry_point('single_fw') #get entry point for single_fw
        
    log_server = smc.search.get_first_log_server()
    if not log_server:
        logger.error("Can't seem to find an available Log Server on specified SMC, cannot add single_fw: %s" % name)
        return None
    
    single_fw.log_server = log_server
    single_fw._mgmt_interface()

    common_api._create(single_fw.create())    
    #from pprint import pprint
    #pprint(l3fw.json)
 

def single_layer2(name, mgmt_ip, mgmt_network, mgmt_interface='0', inline_interface='1-2', 
               logical_intf='default_eth', dns=None, fw_license=False):    
    """ create single layer 2 firewall 
    Layer 2 firewall will have a layer 3 management interface and initially needs atleast 
    one inline or capture interface. 
    :param name: name of single layer 2 fw
    :param mgmt_ip: ip address for management layer 3 interface
    :param mgmt_network: netmask for management network
    :param mgmt_interface: interface id for l3 mgmt
    :param inline_interface: int specifying interface id's to be used for inline interfaces (default: [1-2])
    :param logical_interface: name of logical interface, must be unique if using capture and inline interfaces
    :param dns: dns servers for management interface (optional)
    :param fw_license: attempt license after creation (optional)
    :return None
    """
    
    single_layer2 = SingleLayer2(**locals())
    single_layer2.href = smc.search.element_entry_point('single_layer2')
    
    if not smc.helpers.is_ipaddr_in_network(mgmt_ip, mgmt_network):
        logger.error("Management IP: %s is not in the management network: %s, cannot add single_fw" % (mgmt_ip,mgmt_network))
        return None

    log_server = smc.search.get_first_log_server()
    if not log_server:
        logger.error("Can't seem to find an available Log Server on specified SMC, cannot add single_fw: %s" % name)
        return None
    
    single_layer2.log_server = log_server
    single_layer2.logical_interface = get_logical_interface(logical_intf) \
                        if get_logical_interface(logical_intf) is not None else logical_interface(logical_intf)   
    single_layer2._mgmt_interface()
    single_layer2._inline_interface()
    
    common_api._create(single_layer2.create())   
    #from pprint import pprint
    #pprint(single_layer2.json)


def single_ips(name, mgmt_ip, mgmt_network, mgmt_interface='0', inline_interface='1-2', 
               logical_intf='default_eth', dns=None, fw_license=False):
    """ create single ips  
    :param name: name of single layer 2 fw
    :param mgmt_ip: ip address for management layer 3 interface
    :param mgmt_network: netmask for management network
    :param mgmt_interface: interface id for l3 mgmt
    :param inline_interface: int specifying interface id's to be used for inline interfaces (default: [1-2])
    :param logical_interface: name of logical interface, must be unique if using capture and inline interfaces
    :param dns: dns servers for management interface (optional)
    :param fw_license: attempt license after creation (optional)
    :return None
    """
    
    single_ips = SingleIPS(**locals())
    single_ips.href = smc.search.element_entry_point('single_ips')
    
    log_server = smc.search.get_first_log_server()
    if not log_server:
        logger.error("Can't seem to find an available Log Server on specified SMC, cannot add ips: %s" % single_ips.name)
        return None     
    
    single_ips.log_server = log_server
    single_ips.logical_interface = get_logical_interface(logical_intf) \
                        if get_logical_interface(logical_intf) is not None else logical_interface(logical_intf) 
    single_ips._mgmt_interface()
    single_ips._inline_interface()
    
    common_api._create(single_ips.create())        
    #from pprint import pprint
    #pprint(ips.json)

    
def l3interface(name, ipaddress, ip_network, interface_id):
    """ Add L3 interface for single FW    
    :param l3fw: name of firewall to add interface to
    :param ip: ip of interface
    :param network: ip is validated to be in network before sending
    :param interface_id: interface_id to use
    :return None
    """
    
    if not smc.helpers.is_ipaddr_in_network(ipaddress, ip_network):
        logger.error("IP address: %s is not part of the network provided: %s, cannot add interface" % (ipaddress,ip_network))
        return None
    
    network = smc.helpers.ipaddr_as_network(network)    #convert to cidr in case full mask provided
    
    entry_href = smc.search.element_href(name)
    
    if entry_href is not None:
        
        fw_orig = smc.search.element_by_href_as_smcelement(entry_href)
               
        l3_intf = l3_interface(ipaddress, network, interface_id)
        
        engine = smc.elements.element.EngineNode()
        engine.interfaces.append(l3_intf.json)
        engine.type = l3_intf.type
        engine.name = name
        engine.href = entry_href
        engine.etag = fw_orig.etag
           
        common_api._update(engine.update(fw_orig.json))
        
    else:
        logger.error("Can't find layer 3 FW specified: %s, cannot add interface" % name)
 
 
def l2interface(name, interface_id='1-2', logical_intf='default_eth'):
    """ Add layer 2 inline interface   
    Inline interfaces require two physical interfaces for the bridge and a logical 
    interface to be assigned. By default, interface 1,2 will be used if interface_id is 
    not specified. 
    The logical interface is used by SMC for policy to logically group both interfaces
    It is not possible to have inline and capture interfaces on the same node with the
    same logical interface definition. Automatically create logical interface if it does
    not already exist.    
    :param node: node name to add inline interface pair
    :param interface_id [], int values of interfaces to use for inline pair (default: 1,2)
    :param logical_int: logical interface name to map to inline pair (default: 'default_eth')
    :return None
    """
          
    entry_href = smc.search.element_href(name)
    
    if entry_href is not None:
        
        l2_orig = smc.search.element_by_href_as_smcelement(entry_href)
        
        logical_int_href = smc.search.get_logical_interface(logical_intf)
        if logical_int_href is None:
            logger.info("Logical interface: %s not found, creating automatically" % logical_intf)
            logical_int_href = logical_interface(logical_intf, comment="made by api tool")
        
        inline_intf = inline_interface(logical_int_href, interface_id)
        
        engine = EngineNode()
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
    :param name: name of logical interface
    :param comment: optional
    :return str href for new logical interface element
    """
    
    entry_href = smc.search.element_entry_point('logical_interface')
    
    logical_int = smc.elements.element.LogicalInterface()
    logical_int.name = name
    logical_int.href = entry_href
    logical_int.comment = comment if comment is not None else ""
   
    common_api._create(logical_int.create())
    
    return logical_int.href
 

def l3route(engine, gw, network, interface_id): 
    """ Add route to l3fw 
    This could be added to any engine type. Non-routable engine roles (L2/IPS) may
    still require route/s defined on the L3 management interface   
    :param l3fw: name of firewall to add route
    :param gw: next hop router object
    :param network: next hop network behind gw
    :param interface_id: interface to apply route
    :return None
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

    smc.remove.element('myips')
    time.sleep(3)
    #smc.create.single_ips('myips', '172.18.1.254', '172.18.1.0/24', mgmt_interface='3', inline_interface='4-5', dns='1.2.3.4',
    #                      logical_interface='apitool')
    #smc.remove.element('myfw')
    #smc.create.single_fw('myfw', '172.18.1.254', '172.18.1.0/24', mgmt_interface='5', dns='5.5.5.5', fw_license=True)
    smc.remove.element('mylayer2')
    smc.create.single_layer2('mylayer2', '172.18.1.254', '172.18.1.0/24', mgmt_interface='5', dns='5.5.5.5', fw_license=True,
                            logical_interface='apitool')
    smc.create.l2interface('mylayer2', interface_id='6-7')
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
