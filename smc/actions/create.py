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
from smc.elements.element import logical_intf_helper, SMCElement, DomainName,\
    TCPService, EthernetService, ICMPService, ICMPIPv6Service, ServiceGroup,\
    TCPServiceGroup, UDPServiceGroup, UDPService, IPServiceGroup, IPService, Host, \
    AdminUser
import smc.api.web
from smc.elements.engines import Node, Layer3Firewall, Layer2Firewall, IPS, Layer3VirtualEngine, FirewallCluster
from smc.actions import helpers

from smc.api.web import SMCException
from smc.elements.interfaces import VlanInterface, PhysicalInterface
from smc.elements.system import SystemInfo
from __builtin__ import True


logger = logging.getLogger(__name__)

def host(name, ipaddress, secondary_ip=[], comment=None):
    """ Create host object
      
    :param name: name, must be unique
    :param ipaddress: ip address of host
    :param secondary_ip[] (optional): additional IP for host
    :param comment (optional)
    :return: href upon success otherwise None
    """   
    if helpers.is_valid_ipv4(ipaddress):         
        return smc.elements.element.Host(name, ipaddress, 
                                         secondary_ip=secondary_ip, 
                                         comment=comment).create()
    else:
        logger.error("Failed: Invalid IPv4 address specified: %s, "
                     "create object: %s failed" % (ipaddress, name)) 
    

def iprange(name, addr_range, comment=None):
    """ Create iprange object

    :param name: name for object
    :param addr_range: ip address range, i.e. 1.1.1.1-1.1.1.10
    :param comment (optional)
    :return: href upon success otherwise None
    """   
    addr = addr_range.split('-') #just verify each side is valid ip addr
    if len(addr) == 2: #has two parts
        if not helpers.is_valid_ipv4(addr[0]) or not helpers.is_valid_ipv4(addr[1]):
            logger.error("Invalid ip address range provided: %s" % addr_range)
            return None
    else: 
        logger.error("Invalid ip address range provided: %s" % addr_range)
        return None
    
    return smc.elements.element.IpRange(name, addr_range,
                                           comment=comment).create()   
    
    
def router(name, ipaddress, secondary_ip=None, comment=None):
    """ Create router element

    :param name: name for object
    :param ipaddress: ipv4 address
    :param comment (optional)
    :return: href upon success otherwise None
    """     
    if helpers.is_valid_ipv4(ipaddress):
        return smc.elements.element.Router(name, ipaddress,
                                             secondary_ip=secondary_ip,
                                             comment=comment).create()
    else:
        logger.error("Invalid IPv4 address specified: %s, create object: %s failed" % (ipaddress, name)) 


def network(name, ip_network, comment=None):
    """ Create network element
 
    :param name: name for object
    :param ip_network: ipv4 address in cidr or full netmask format (1.1.1.1/24, or 1.1.1.0/255.255.0.0)
    :param comment (optional)
    :return: href upon success, or None
    """
    cidr = helpers.ipaddr_as_network(ip_network)
    if cidr: 
        return smc.elements.element.Network(name, cidr,
                                               comment=comment).create()
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
    :return: href: upon success, or None
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
    
    return smc.elements.element.Group(name,
                                       members=grp_members,
                                       comment=comment).create()

'''    
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
        
        return smc.elements.element.Service(name, min_dst_port,
                                            proto=proto, 
                                            comment=comment).create()
''' 
def single_fw(name, mgmt_ip, mgmt_network, mgmt_interface='0', dns=None, fw_license=False):
    """ Create single firewall with a single management interface
    
    :param name: name of single layer 2 fw
    :param mgmt_ip: ip address for management layer 3 interface
    :param mgmt_network: netmask for management network
    :param mgmt_interface: interface id for l3 mgmt
    :param dns: dns servers for management interface (optional)
    :param fw_license: attempt license after creation (optional)
    :return: href upon success otherwise None
    """
    if not helpers.is_ipaddr_in_network(mgmt_ip, mgmt_network):
        logger.error("Management IP: %s is not in the management network: %s, "
                     "cannot add single_fw" % (mgmt_ip,mgmt_network))
        return None
  
    mgmt_network = helpers.ipaddr_as_network(mgmt_network) #convert to cidr
    
    result = Layer3Firewall.create(name, mgmt_ip, mgmt_network, 
                                   log_server=None,
                                   mgmt_interface=mgmt_interface,
                                   dns=dns)
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
    :return: href upon success otherwise None
    """   
    if not helpers.is_ipaddr_in_network(mgmt_ip, mgmt_network):
        logger.error("Management IP: %s is not in the management network: %s, cannot add single_fw" % (mgmt_ip,mgmt_network))
        return None

    mgmt_network = helpers.ipaddr_as_network(mgmt_network) #convert to cidr
                         
    result = Layer2Firewall.create(name, mgmt_ip, mgmt_network, 
                                   log_server=None,
                                   mgmt_interface=mgmt_interface,
                                   inline_interface=inline_interface,
                                   logical_interface=logical_intf_helper(logical_interface),
                                   dns=dns)
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
    :return: href upon success otherwise None
    """ 
    if not helpers.is_ipaddr_in_network(mgmt_ip, mgmt_network):
        logger.error("Management IP: %s is not in the management network: %s, cannot add single_fw" % (mgmt_ip,mgmt_network))
        return None
    
    mgmt_network = helpers.ipaddr_as_network(mgmt_network) #convert to cidr
        
    result = IPS.create(name, mgmt_ip, mgmt_network, 
                        log_server=None,
                        mgmt_interface=mgmt_interface,
                        inline_interface=inline_interface,
                        logical_interface=logical_intf_helper(logical_interface),
                        dns=dns)
    return result
   
def l3interface(name, ipaddress, ip_network, interfaceid):
    """ Add L3 interface for single FW
       
    :param l3fw: name of firewall to add interface to
    :param ip: ip of interface
    :param network: ip is validated to be in network before sending
    :param interface_id: interface_id to use
    :return: href upon success otherwise None
    """    
    if not helpers.is_ipaddr_in_network(ipaddress, ip_network):
        logger.error("IP address: %s is not part of the network provided: %s, \
            cannot add interface" % (ipaddress,ip_network))
        return None
    
    ip_network = helpers.ipaddr_as_network(ip_network)    #convert to cidr in case full mask provided
    
    try:
        engine = Node(name).load()
        physical = PhysicalInterface(interfaceid)
        physical.add_single_node_interface(ipaddress, ip_network)
        result = engine.add_physical_interfaces(physical.data)
    
        return result
    
    except SMCException, e:
        print "Error occurred during modification of %s, message: %s" % (name, e) #tmp  
    
 
def l2interface(name, interface_id, logical_interface_ref='default_eth', zone=None):
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
    :return: href upon success otherwise None
    """  
    try:
        engine = Node(name).load()
        
        physical = PhysicalInterface(interface_id)
        physical.add_inline_interface(logical_intf_helper(logical_interface_ref))
     
        result = engine.add_physical_interfaces(physical.data)
        
        return result
       
    except SMCException, e:
        print "Error occurred during modification of %s, message: %s" % (name, e) #tmp          
    else:
        logger.error("Cannot find node specified to add layer 2 inline interface: %s" % name)

def capture_interface(name, interface_id, logical_interface_ref='default_eth', zone=None):
    try:
        engine = Node(name).load()
              
        physical = PhysicalInterface(interface_id)
        physical.add_capture_interface(logical_intf_helper(logical_interface_ref), 
                                       zone_ref=zone)
        result = engine.add_physical_interfaces(physical.data)
        
        return result
    
    except SMCException, e:
        print "Error occurred during modification of %s, message: %s" % (name, e) #tmp          
    else:
        logger.error("Cannot find node specified to add capture interface: %s" % name)

def l3route(name, gateway, ip_network): 
    """ Add route to l3fw 
    This could be added to any engine type. Non-routable engine roles (L2/IPS) may
    still require route/s defined on the L3 management interface   
    
    :param l3fw: name of firewall to add route
    :param gw: next hop router object
    :param ip_network: next hop network behind gw
    :return: href upon success otherwise None
    """
    try:
        engine = Node(name).load()
        return engine.add_route(gateway, ip_network)

    except SMCException, e:
        logger.error("Exception adding route: %s" % (name, e)) 
    
def blacklist(name, src, dst, duration=3600):
    """ Add blacklist entry to engine node by name
    
    :param name: name of engine node or cluster
    :param src: source to blacklist, can be /32 or network cidr
    :param dst: dest to deny to, 0.0.0.0/32 indicates all destinations
    :param duration: how long to blacklist in seconds
    :return: href, or None
    """
    try:
        engine = Node(name).load()
        return engine.blacklist(src, dst, duration)
    
    except SMCException, e:
        logger.error("Exception during blacklist: %s" % e)

def blacklist_flush(name):
    """ Flush entire blacklist for node name
    
    :param name: name of node or cluster to remove blacklist
    :return: None, or message if failure
    """
    try:
        engine = Node(name).load()
        print engine.blacklist_flush()
    
    except SMCException, e:
        logger.error("Exception during blacklist: %s" % e)
            
def bind_license(name):
    engine = Node(name).load()
    return engine.bind_license()
    
def unbind_license(name):
    engine = Node(name).load()
    return engine.unbind_license()
         
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
    smc.api.web.session.login('http://172.18.1.150:8082', 'EiGpKD4QxlLJ25dbBEp20001', timeout=60)
    
    logging.getLogger()
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s.%(funcName)s: %(message)s')
    
    from pprint import pprint
    import time
    start_time = time.time()
    
    #import smc.elements.policy
    """@type policy: FirewallPolicy"""
    #policy = smc.elements.policy.FirewallPolicy('api-test-policy').load()
    #print policy.ipv4_rule.create('erika6 rule', ['any'], ['any'], ['any'], 'allow')
    #for rule in policy.ipv4_rule.ipv4_rules:
    #    print "rule: %s" % rule

    from smc.elements.interfaces import PhysicalInterface, VirtualPhysicalInterface
    from smc.elements.element import Blacklist
    from smc.elements.element import logical_intf_helper, zone_helper
    
    """@type engine: Node"""
    #engine = Node('bo').load()
    
    #pprint(smc.search.element_by_href_as_json('http://172.18.1.150:8082/6.0/elements/protocol'))
    #pprint(smc.search.element_by_href_as_json('http://172.18.1.150:8082/6.0/elements/protocol/56'))
    #pprint(smc.search.element_by_href_as_json('http://172.18.1.150:8082/6.0/elements/tcp_service/403'))
    
    #pprint(smc.search.element_by_href_as_json('http://172.18.1.150:8082/6.0/elements/vpn_profile'))
    #pprint(smc.search.element_by_href_as_json('http://172.18.1.150:8082/6.0/elements/vpn_profile/16'))
    #vpn_profile
    
    #pprint(smc.search.all_elements_by_type('admin_user'))
    #pprint(smc.search.element_by_href_as_json('http://172.18.1.150:8082/6.0/elements/admin_user/13'))
   
         
    #admin = AdminUser('dlepage-test').create()
    admin = AdminUser.modify('dlepage-test')
    pprint(admin.json)
    #admin.json['superuser'] = True
    #admin.update()
    #pprint(admin.link)
    print admin.change_password('1970keegan')
    #print admin.change_password('1970keegan')
    #print admin.enable_disable()
    #print admin.export()
    
    #print engine.blacklist_add('1.1.1.1/32', '0.0.0.0/32', 3600)
    #pprint(vars(engine))
    #physical = PhysicalInterface(0, engine.physical_interface_get('0'))
    #physical.modify_single_node_interface(address='110.110.110.1', network_value='110.110.110.0/24')
    #engine.update_physical_interface(physical)
    
    
    #pprint(smc.search.element_href_use_filter('ve-1 admins', 'access_control_list'))
    #pprint(smc.search.element_by_href_as_json('http://172.18.1.150:8082/6.0/elements/access_control_list/31'))
    
   
    #pprint(system.engines())
    #print(system.visible_virtual_engine_mapping())
    
    #import smc.elements.license
    #licensekey = smc.elements.license.License('bo')
    #pprint(licensekey.links)
    
    '''
    <access_control_list db_key="31" name="ve-1 admins">
    <list>
      <list_entry ref_key="5" type="access_control_list" value="ALL Elements"/>
      <list_entry type="network_element" value="ve-1"/>
    </list>
  </access_control_list>
  '''
    #system.last_activated_package()
   
    #blacklist_ref = smc.search.element_entry_point('blacklist')
    #bl = Blacklist('1.1.1.1/32', '2.2.2.2/32')
    #pprint(vars(bl))
    
    #print SMCElement(href=blacklist_ref, json=bl).create()
    #v = VirtualPhysicalInterface(10, zone_ref='Web3')
    #v.add_single_node_interface('1.1.1.1', '1.1.1.1')
    #pprint(vars(v))
    '''
    smc.remove.element('myfirewall')
    
    """@type engine: Node"""
    engine = Layer3Firewall.create('myfirewall',
                                   mgmt_ip='172.18.1.250',
                                   mgmt_network='172.18.1.0/24',
                                   mgmt_interface=0,
                                   dns=['8.8.8.8'],
                                   default_nat=True)
    physical = PhysicalInterface(1)
    physical.add_single_node_interface('1.1.1.1', '1.1.1.0/24')
    engine.add_physical_interfaces(physical.data)
    
    physical = PhysicalInterface(2)
    physical.add_single_node_interface_to_vlan('2.2.2.2', '2.2.2.0/24', 2)
    physical.add_single_node_interface_to_vlan('3.3.3.3', '3.3.3.0/24', 3)
    physical.add_single_node_interface_to_vlan('4.4.4.4', '4.4.4.0/24', 4)
    physical.add_single_node_interface_to_vlan('5.5.5.5', '5.5.5.0/24', 5)
    engine.add_physical_interfaces(physical.data)
    
    #physical.interface_id = 3
    #physical.add_single_node_interface('6.6.6.6', '6.6.6.0/24')
    
    #pprint(vars(physical))
    engine.upload(policy='Layer 3 Router Policy')
    print engine.initial_contact('myfirewall', enable_ssh=True)
    '''
  
    '''
    zone = smc.search.element_href_use_filter('Internal', 'zone')
    engine = FirewallCluster.create(name='mycluster', 
                                cluster_virtual='1.1.1.1', 
                                cluster_mask='1.1.1.0/24',
                                cluster_nic=0,
                                macaddress='02:11:11:11:11:11',
                                nodes=[{'address': '1.1.1.2', 'netmask': '1.1.1.0/24'},
                                       {'address': '1.1.1.3', 'netmask': '1.1.1.0/24'},
                                       {'address': '1.1.1.4', 'netmask': '1.1.1.0/24'}],
                                dns=['1.1.1.1'], 
                                zone=smc.search.element_href_use_filter('Internal', 'zone'))
    
    '''
  
    
  
    '''
    
    """@type engine: Node"""
    #engine = Node('tooter').load()
    #print "Here: %s" % engine.export(filename='myfile')
    #engine.initial_contact(filename='engine.cfg')
    #engine.sginfo()
    #Engine level
    
    #engine.node()
    #pprint(engine.interface())
    #print engine.refresh(wait_for_finish=False).next()
    #engine.upload()
    #engine.generate_snapshot(filename="/Users/davidlepage/snapshot.xml")
    #engine.add_route('172.18.1.200', '192.168.7.0/24')
    #engine.blacklist_add('1.1.1.1/32', '0.0.0.0/0', 3600)
    #engine.alias_resolving()
    #engine.routing_monitoring()
    #engine.export(filename="/Users/davidlepage/export.xml")
    #engine.internal_gateway()
    #engine.routing()
    #engine.antispoofing()
    #engine.snapshot()
    #pprint(engine.physical_interface())
    #pprint(engine.physical_interface_del('Interface 54'))
    #engine.tunnel_interface()
    #engine.modem_interface()
    #engine.adsl_interface()
    #pprint(engine.wireless_interface())
    #engine.switch_physical_interface()
    
    #Node level
    #engine.initial_contact(filename="/Users/davidlepage/engine.cfg")
    #pprint(engine.appliance_status(node='ngf-1035'))
    #pprint(engine.status('ngf-1035'))
    #pprint(engine.go_online('ngf-1035'))
    #pprint(engine.go_offline('ngf-1035'))
    #pprint(engine.go_standby('ngf-1035'))
    #pprint(engine.lock_online('ngf-1035', comment='mytestcomment'))
    #pprint(engine.lock_offline('ngf-1035'))
    #pprint(engine.reset_user_db('ngf-1035'))
    #pprint(engine.diagnostic('ngf-1035', filter_enabled=True))
    #pprint(engine.interface())
    #pprint(engine.node_links)
    #pprint(engine.time_sync('ngf-1035'))
    #pprint(engine.fetch_license('ngf-1035'))
    #pprint(engine.bind_license(node='ngf-1035', license_item_id='0000310401'))
    #pprint(engine.unbind_license(node='ngf-1035'))
    #pprint(engine.certificate_info(node='ngf-1065'))
    #pprint(engine.ssh('ngf-1035', enable=True, comment='api test ssh disable'))
    #pprint(engine.change_ssh_pwd('ngf-1035', '1970keegan', comment='api pwd change'))
    #engine.export()
    #engine.initial_contact('ngf-1035')
    #pprint(engine.engine_links)

    '''
    
    print("--- %s seconds ---" % (time.time() - start_time))
    
    print "Number of GET calls: %s" % smc.api.web.session.http_get.calls   
    smc.api.web.session.logout()
