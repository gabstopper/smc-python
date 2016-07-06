""" 
Shortcut API to access common operations done by the SMC python API. 

Each function defined is specifically for creating certain object types, engines,
interfaces, routes, policies, etc.

Input validation is done to ensure the correct fields are provided and that 
they are the right type. In addition, in some cases 
other objects will need to be retrieved as a reference to create another object. 
If these references are not resolvable, the create operation can fail. This will do the up
front validation and interact with the SMC operations.

All create functions will return the HREF of the newly created object or NONE if there was a failure.
In order to view error messages, do the following in your calling script::

    import logging
    logging.getLogger()
    logging.basicConfig(level=logging.ERROR, format='%(asctime)s %(levelname)s: %(message)s')
    
"""

import logging
import smc.elements.element
import smc.api.web as web_api
import smc.api.common as common_api
import smc.elements.license
from smc.actions.search import get_logical_interface
from smc.elements.engines import Node, Layer3Firewall, Layer2Firewall, IPS
from smc.elements.interfaces import LogicalInterface
from smc.actions import helpers
from smc.api.web import SMCException

logger = logging.getLogger(__name__)

def host(name, ipaddress, secondary_ip=[], comment=None):
    """ Create host object       
    :param name: name, must be unique
    :param ipaddress: ip address of host
    :param secondary_ip[] (optional): additional IP for host
    :param comment (optional)
    :return href upon success otherwise None
    """
    
    if helpers.is_valid_ipv4(ipaddress): 
        
        host = smc.elements.element.Host(name, ipaddress, 
                                         secondary_ip=secondary_ip, 
                                         comment=comment)
       
        return common_api._create(host.create())
                                    
    else:
        logger.error("Failed: Invalid IPv4 address specified: %s, "
                     "create object: %s failed" % (ipaddress, name)) 
    

def iprange(name, addr_range, comment=None):
    """ Create iprange object 
    :param name: name for object
    :param addr_range: ip address range, i.e. 1.1.1.1-1.1.1.10
    :param comment (optional)
    :return href upon success otherwise None
    """
    
    addr = addr_range.split('-') #just verify each side is valid ip addr
    if len(addr) == 2: #has two parts
        if not helpers.is_valid_ipv4(addr[0]) or not helpers.is_valid_ipv4(addr[1]):
            logger.error("Invalid ip address range provided: %s" % addr_range)
            return None
    else: 
        logger.error("Invalid ip address range provided: %s" % addr_range)
        return None
    
    iprange = smc.elements.element.IpRange(name, addr_range,
                                           comment=comment)
    
    return common_api._create(iprange.create())
    
    
def router(name, ipaddress, secondary_ip=None, comment=None):
    """ Create router element
    :param name: name for object
    :param ipaddress: ipv4 address
    :param comment (optional)
    :return href upon success otherwise None
    """  
      
    if helpers.is_valid_ipv4(ipaddress):
        
        router = smc.elements.element.Router(name, ipaddress,
                                             secondary_ip=secondary_ip,
                                             comment=comment)
        
        return common_api._create(router.create())  
                                
    else:
        logger.error("Invalid IPv4 address specified: %s, create object: %s failed" % (ipaddress, name)) 


def network(name, ip_network, comment=None):
    """ Create network element   
    :param name: name for object
    :param ip_network: ipv4 address in cidr or full netmask format (1.1.1.1/24, or 1.1.1.0/255.255.0.0)
    :param comment (optional)
    :return href upon success otherwise None
    """
    
    cidr = helpers.ipaddr_as_network(ip_network)
    if cidr:
        
        network = smc.elements.element.Network(name, cidr,
                                               comment=comment)
       
        return common_api._create(network.create()) 
        
    else:
        logger.error("Invalid address specified for network: %s; make sure address specified is in network: %s" % (name, ip_network))

           
def group(name, members=[], comment=None):
    """ Create group element, optionally with members
    Members must already exist in SMC. Before being added to the group a search will be 
    performed for each member specified.
    blah
        
    :param name: name for object
    :param members: list; i.e. ['element1', 'element2', etc]. Most elements can be used in a group
    :param comment: (optional)
    :return href: upon success otherwise None
    """
 
    grp_members = []
    if members:
        for m in members: #add each member
            found_member = smc.search.element_href(m)
            if found_member:
                logger.debug("Found member: %s, adding to group" % m)
                grp_members.append(found_member)
                continue
            else:
                logger.info("Element: %s could not be found, not adding to group" % m)    
    
    group = smc.elements.element.Group(name,
                                       members=grp_members,
                                       comment=comment)
    
    return common_api._create(group.create())
    
def service(name, min_dst_port, proto, comment=None):
    """ Create a service element in SMC 
    
    :param name: name of element
    :param min_dst_port: port to use
    :param proto: protocol, i.e. tcp, udp, icmp
    :param comment: custom comment
    :return: href upon success otherwise None
    """
    
    entry_href = smc.search.element_entry_point(proto)
    if entry_href:
        try:
            int(min_dst_port)
        except ValueError:
            logger.error("Min Dst Port was not integer: %s" % min_dst_port)
            return
        
        service = smc.elements.element.Service(name, min_dst_port,
                                               entry_href,
                                               proto=proto, 
                                               comment=comment)
        
        return common_api._create(service.create())
         
def single_fw(name, mgmt_ip, mgmt_network, mgmt_interface='0', dns=None, fw_license=False):
    """ Create single firewall with a single management interface
    
    :param name: name of single layer 2 fw
    :param mgmt_ip: ip address for management layer 3 interface
    :param mgmt_network: netmask for management network
    :param mgmt_interface: interface id for l3 mgmt
    :param dns: dns servers for management interface (optional)
    :param fw_license: attempt license after creation (optional)
    :return href upon success otherwise None
    """
    if not helpers.is_ipaddr_in_network(mgmt_ip, mgmt_network):
        logger.error("Management IP: %s is not in the management network: %s, "
                     "cannot add single_fw" % (mgmt_ip,mgmt_network))
        return None
  
    mgmt_network = helpers.ipaddr_as_network(mgmt_network) #convert to cidr
    log_server = smc.search.get_first_log_server()

    engine = Layer3Firewall.create(name, mgmt_ip, mgmt_network, log_server,
                                   mgmt_interface=mgmt_interface,
                                   dns=dns)
    #href = smc.search.element_entry_point('single_fw')
    element = smc.elements.element.SMCElement.factory(href=engine.href, json=engine.engine_json)
   
    result = common_api._create(element)
    
    #if result and fw_license:
    #    bind_license(name)
    
    return result  
    
def single_layer2(name, mgmt_ip, mgmt_network, mgmt_interface='0', inline_interface='1-2', 
               logical_interface='default_eth', dns=None, fw_license=False):    
    """ Create single layer 2 firewall 
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
    :return href upon success otherwise None
    """
   
    if not helpers.is_ipaddr_in_network(mgmt_ip, mgmt_network):
        logger.error("Management IP: %s is not in the management network: %s, cannot add single_fw" % (mgmt_ip,mgmt_network))
        return None

    mgmt_network = helpers.ipaddr_as_network(mgmt_network) #convert to cidr
    log_server = smc.search.get_first_log_server()
    
    logical = get_logical_interface(logical_interface) \
                        if get_logical_interface(logical_interface) is not None \
                        else _logical_interface(logical_interface)
                        
    engine = Layer2Firewall.create(name, mgmt_ip, mgmt_network, log_server,
                                   mgmt_interface=mgmt_interface,
                                   inline_interface=inline_interface,
                                   logical_interface=logical,
                                   dns=dns)
    
    element = smc.elements.element.SMCElement.factory(href=engine.href, 
                                                      json=engine.engine_json)
   
    result = common_api._create(element)
    
    #if result and fw_license:
    #    bind_license(name)
        
    return result


def single_ips(name, mgmt_ip, mgmt_network, mgmt_interface='0', inline_interface='1-2', 
               logical_interface='default_eth', dns=None, fw_license=False):
    """ Create single IPS 
    :param name: name of single layer 2 fw
    :param mgmt_ip: ip address for management layer 3 interface
    :param mgmt_network: netmask for management network
    :param mgmt_interface: interface id for l3 mgmt
    :param inline_interface: int specifying interface id's to be used for inline interfaces (default: [1-2])
    :param logical_interface: name of logical interface, must be unique if using capture and inline interfaces
    :param dns: dns servers for management interface (optional)
    :param fw_license: attempt license after creation (optional)
    :return href upon success otherwise None
    """
   
    if not helpers.is_ipaddr_in_network(mgmt_ip, mgmt_network):
        logger.error("Management IP: %s is not in the management network: %s, cannot add single_fw" % (mgmt_ip,mgmt_network))
        return None
    
    mgmt_network = helpers.ipaddr_as_network(mgmt_network) #convert to cidr
    log_server = smc.search.get_first_log_server()    
    
    logical = get_logical_interface(logical_interface) \
                        if get_logical_interface(logical_interface) is not None \
                        else _logical_interface(logical_interface)
    
    
    engine = Layer2Firewall.create(name, mgmt_ip, mgmt_network, log_server,
                                   mgmt_interface=mgmt_interface,
                                   inline_interface=inline_interface,
                                   logical_interface=logical,
                                   dns=dns)
    
    element = smc.elements.element.SMCElement.factory(href=engine.href, json=engine.engine_json)
   
    result = common_api._create(element)
    
    #if result and fw_license:
    #    bind_license(name)
        
    return result     
    #from pprint import pprint
    #pprint(ips.json)

    
def l3interface(name, ipaddress, ip_network, interface_id):
    """ Add L3 interface for single FW    
    :param l3fw: name of firewall to add interface to
    :param ip: ip of interface
    :param network: ip is validated to be in network before sending
    :param interface_id: interface_id to use
    :return href upon success otherwise None
    """
    
    if not helpers.is_ipaddr_in_network(ipaddress, ip_network):
        logger.error("IP address: %s is not part of the network provided: %s, \
            cannot add interface" % (ipaddress,ip_network))
        return None
    
    ip_network = helpers.ipaddr_as_network(ip_network)    #convert to cidr in case full mask provided
    
    try:
        engine = Node(name).load()
        engine.add_l3_interface(ipaddress, ip_network, interface_id=interface_id)
        element = smc.elements.element.SMCElement.factory(href=engine.href, json=engine.engine_json,
                                                          etag=engine.etag)
        return common_api._update(element)
    except SMCException, e:
        print "Error occurred during modification of %s, message: %s" % (name, e) #tmp  
    
 
def l2interface(name, interface_id='1-2', logical_interface='default_eth'):
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
    :return href upon success otherwise None
    """
    
    try:
        engine = Node(name).load()
        engine.add_inline_interface(logical_interface=logical_interface, 
                                    interface_id=interface_id)
        element = smc.elements.element.SMCElement.factory(href=engine.href, json=engine.engine_json,
                                                          etag=engine.etag)
        return common_api._update(element)
    except SMCException, e:
        print "Error occurred during modification of %s, message: %s" % (name, e) #tmp  
        
    else:
        logger.error("Cannot find node specified to add layer 2 inline interface: %s" % name)

   
def _logical_interface(name, comment=None):
    """ Create logical interface
    Logical interfaces are required to be unique for a single IPS or layer 2 firewall that
    has both inline and capture interfaces on the same host. If the IPS or layer2 FW only 
    use capture or inline interfaces, the same logical interface can be used for all. 
    :param name: name of logical interface
    :param comment: optional
    :return href upon success otherwise None
    """
    
    entry_href = smc.search.element_entry_point('logical_interface')
    
    logical_int = LogicalInterface(name, entry_href,
                                   comment=comment)
      
    return common_api._create(logical_int.create()) 

def l3route(name, gateway, ip_network, interface_id): 
    """ Add route to l3fw 
    This could be added to any engine type. Non-routable engine roles (L2/IPS) may
    still require route/s defined on the L3 management interface   
    :param l3fw: name of firewall to add route
    :param gw: next hop router object
    :param network: next hop network behind gw
    :param interface_id: interface to apply route
    :return href upon success otherwise None
    """
    
    engine_href = smc.search.element_href(name) #ref to engine
         
    if engine_href is None:
        logger.error("Can't find engine node: %s, cannot process route add" % name)
        return None
    
    router_href = smc.search.element_href_use_filter(gateway, 'router') #router object
    if router_href is None:
        logger.error("Can't find router object: %s, cannot process route add" % gateway)
        return None
    
    network_href = smc.search.element_href_use_filter(ip_network, 'network')
    if network_href is None:
        logger.error("Can't find network object: %s, cannot process route add" % ip_network)
        return None
    
    node = smc.search.element_by_href_as_json(engine_href) #get node json
   
    route_link = next(item for item in node.get('link') if item.get('rel') == 'routing')
    routing_orig = smc.search.element_by_href_as_smcelement(route_link.get('href')) 
   
    gw = smc.search.element_by_href_as_json(router_href)
    
    dest_net = smc.search.element_by_href_as_json(network_href) #dest net info
    
    
    route = smc.elements.interfaces.Route(gw.get('name'), gw.get('address'), router_href,
                                       dest_net.get('name'), dest_net.get('ipv4_network'), 
                                       network_href, interface_id)
    
    route.name = name
    route.href = route_link.get('href')
    route.etag = routing_orig.etag
    route.json = routing_orig.json  #will append to original routing json
    routing_json = route.create()
    #from pprint import pprint
    #pprint (vars(route))
    
    if routing_json is not None:    
        
        return common_api._update(routing_json) #TODO
       
    else:
        logger.error("Can not find specified interface: %s for route add, double check the "
                     "interface configuration" % route.interface_id)


def bind_license(name):
    smc.elements.license.License(name).bind()
    
def unbind_license(name):
    smc.elements.license.License(name).unbind()
         
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
    
    logging.getLogger()
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s')
    
    from pprint import pprint
    import time
    start_time = time.time()
    
    #smc.remove.element('tyler-ips')
    #log = smc.search.get_first_log_server()
    #engine = IPS.create('tyler-ips', '56.56.56.56', '56.56.56.0/24', log)
    #print type(engine)
    #print isinstance(engine, IPS)
    #element = smc.elements.element.SMCElement.factory(href=engine.href, json=engine.engine_json)
    #print "IPS created at: %s" % common_api._create(element)
    
    engine = Layer3Firewall('sg_vm').load()
    pprint(engine.appliance_status())
    
    
    engine = Node('henbo').load()
    print "type: %s" % type(engine)
    engine.add_inline_interface(interface_id='1-2')
    print engine.update()
    
    #element = smc.elements.element.SMCElement.factory(href=engine.href, json=engine.engine_json, etag=engine.etag)
    #print "Firewall created at: %s" % common_api._update(element)
    
    
    #engine = Node('henry').load()
    #engine.add_inline_interface(interface_id='50-51')
    #element = smc.elements.element.SMCElement.factory(href=engine.href, json=engine.engine_json, etag=engine.etag)
    #print "IPS created at: %s" % common_api._update(element)
    
   
    
    
    
    #engine.l2interface(interface_id='9-10')
    #element = smc.elements.element.SMCElement.factory(href=engine.href, json=engine.engine_json,
    #                                                  etag=engine.etag)
    #print "IPS interface created at: %s" % common_api._update(element)
    
    #engine = Node('henry').load()
    #engine.add_l3_interface('67.67.67.67', '67.67.67.0/24', interface_id='15')
    #element = smc.elements.element.SMCElement.factory(href=engine.href, json=engine.engine_json,
    #                                                  etag=engine.etag)
    #print "Firewall Interface created at: %s" % common_api._update(element)
    #engine.add_inline_interface(interface_id='20-21')
    #print "Firewall Interface created at: %s" % common_api._update(element)
    
    '''
    engine = Node('henry').load()
    engine.fetch_license()
    engine.bind_license()
    engine.unbind_license()
    engine.cancel_unbind_license()
    engine.initial_contact()
    engine.appliance_status()
    engine.status()
    engine.go_online()
    engine.go_offline()
    engine.go_standby()
    engine.lock_offline()
    engine.reset_user_db()
    engine.diagnostic()
    engine.send_diagnostic()
    engine.reboot()
    engine.sginfo()
    engine.ssh()
    engine.change_ssh_pwd()
    engine.time_sync()
    engine.certificate_info()
    
    #Engine level commands
    engine.physical_interface()
    engine.tunnel_interface()
    engine.modem_interface()
    engine.adsl_interface()
    engine.wireless_interface()
    engine.switch_physical_interface()
    engine.interface()
    engine.refresh()
    engine.upload()
    engine.add_route()
    engine.blacklist()
    engine.blacklist_flush()
    engine.generate_snapshot()
    engine.export()
    engine.routing()
    '''
    #smc.remove.element('mylayer2-test')
    #print single_layer2('mylayer2-test', '172.18.1.254', '172.18.1.0/24', dns=['5.5.5.5'], fw_license=True)
    
    '''
    smc.remove.element('testl2')
    log = smc.search.get_first_log_server()
    engine = Layer2Firewall.create('testl2', '1.1.1.1', '1.1.1.0/24', log)
    href = smc.search.element_entry_point('single_layer2')
    element = smc.elements.element.SMCElement.factory(href=href, json=engine)
    print "Layer2 Firewall engine created at: %s" % common_api._create(element)
    
    engine = Layer2Firewall('testl2').load()
    engine.add_inline_interface(interface_id='15-16')
    engine.add_capture_interface(interface_id='6', logical_interface='apitool')
    element = smc.elements.element.SMCElement.factory(href=engine.href, json=engine.engine_json,
                                                      etag=engine.etag)
    print "Firewall Interface created at: %s" % common_api._update(element)
    '''


    '''
    smc.remove.element('testfw')
    log = smc.search.get_first_log_server()
    engine = Layer3Firewall.create('testfw', '1.2.3.4', '1.2.3.0/24', log, mgmt_interface=4)
    href = smc.search.element_entry_point('single_fw')
    element = smc.elements.element.SMCElement.factory(href=href, json=engine)
    print "Layer3 Firewall engine created at: %s" % common_api._create(element)
    '''
    '''
    #Test Layer2
    smc.remove.element('layer2')
    log = smc.search.get_first_log_server()   
    engine = Layer2Firewall.create('layer2', '172.18.1.254', '172.18.1.0/24', log, dns=['5.5.5.5'])
    href = smc.search.element_entry_point('single_layer2')
    element = smc.elements.element.SMCElement.factory(href=href, json=engine)
    print "Layer2 Firewall engine created at: %s" % common_api._create(element)
    
    engine = Layer2Firewall('layer2').load()
    pprint(engine.engine_json)
    
    engine.add_inline_interface(logical_interface='apitool', interface_id='6-7')
    pprint(engine.engine_json)
    element = smc.elements.element.SMCElement.factory(href=engine.href, json=engine.engine_json, etag=engine.etag)
    print "Layer2 Firewall interface created at: %s" % common_api._update(element)
    '''
    #engine = Layer2Firewall('layer2').load()
    #engine.refresh()
    #engine.upload()
    #engine.lock_offline()
    #engine.reset_user_db()
    
    #pprint(vars(engine))
    
    '''
    smc.remove.element('myfw')
    smc.create.single_fw('myfw', '172.18.1.254', '172.18.1.0/24', dns='5.5.5.5', fw_license=True)
    smc.create.l3interface('myfw', '10.10.0.1', '10.10.0.0/16', 3)
    smc.create.l3interface('myfw', '10.10.1.1', '10.10.0.0/16', 4)
    smc.create.l3route('myfw', '172.18.1.80', 'Any network', 0)
    '''      
    '''
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
    
    #smc.create.l3route('myfw', '172.18.1.85', '192.168.3.0/24', 3) #Good
    #'''
    
    
    '''time.sleep(15)
    smc.remove.element('myfw')
    smc.create.single_layer2('mylayer3', '172.18.1.254', '172.18.1.0/24', dns='5.5.5.5', fw_license=True)
    smc.create.l2interface('mylayer3', interface_id='6-7')
    time.sleep(15)
    smc.remove.element('mylayer3')
    '''
    
    
    print("--- %s seconds ---" % (time.time() - start_time))   
    web_api.session.logout()
