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
import smc.elements.system as systeminfo
from smc.elements.element import SMCElement, LogicalInterface
from smc.actions.search import get_logical_interface
from smc.elements.engines import Node, Layer3Firewall, Layer2Firewall, IPS
from smc.actions import helpers

from smc.api.web import SMCException

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
        host = smc.elements.element.Host(name, ipaddress, 
                                         secondary_ip=secondary_ip, 
                                         comment=comment)
               
        return common_api.create(host.create())
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
    
    iprange = smc.elements.element.IpRange(name, addr_range,
                                           comment=comment)   
    return common_api.create(iprange.create())
    
    
def router(name, ipaddress, secondary_ip=None, comment=None):
    """ Create router element

    :param name: name for object
    :param ipaddress: ipv4 address
    :param comment (optional)
    :return: href upon success otherwise None
    """     
    if helpers.is_valid_ipv4(ipaddress):
        router = smc.elements.element.Router(name, ipaddress,
                                             secondary_ip=secondary_ip,
                                             comment=comment)
        return common_api.create(router.create())  
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
        network = smc.elements.element.Network(name, cidr,
                                               comment=comment)
        return common_api.create(network.create()) 
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
    
    group = smc.elements.element.Group(name,
                                       members=grp_members,
                                       comment=comment)
    return common_api.create(group.create())

    
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
        return common_api.create(service.create())
         
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
    
    engine = Layer3Firewall.create(name, mgmt_ip, mgmt_network, 
                                   log_server=None,
                                   mgmt_interface=mgmt_interface,
                                   dns=dns)
   
    element = SMCElement.factory(href=engine.href, 
                                 json=engine.engine_json) 
    result = common_api.create(element)
    
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
    :return: href upon success otherwise None
    """   
    if not helpers.is_ipaddr_in_network(mgmt_ip, mgmt_network):
        logger.error("Management IP: %s is not in the management network: %s, cannot add single_fw" % (mgmt_ip,mgmt_network))
        return None

    mgmt_network = helpers.ipaddr_as_network(mgmt_network) #convert to cidr
    
    logical = get_logical_interface(logical_interface) \
                        if get_logical_interface(logical_interface) is not None \
                        else _logical_interface(logical_interface)
                        
    engine = Layer2Firewall.create(name, mgmt_ip, mgmt_network, 
                                   log_server=None,
                                   mgmt_interface=mgmt_interface,
                                   inline_interface=inline_interface,
                                   logical_interface=logical,
                                   dns=dns)
    
    element = SMCElement.factory(href=engine.href, 
                                json=engine.engine_json)   
    result = common_api.create(element)
    
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
    :return: href upon success otherwise None
    """ 
    if not helpers.is_ipaddr_in_network(mgmt_ip, mgmt_network):
        logger.error("Management IP: %s is not in the management network: %s, cannot add single_fw" % (mgmt_ip,mgmt_network))
        return None
    
    mgmt_network = helpers.ipaddr_as_network(mgmt_network) #convert to cidr
   
    logical = get_logical_interface(logical_interface) \
                        if get_logical_interface(logical_interface) is not None \
                        else _logical_interface(logical_interface)
        
    engine = IPS.create(name, mgmt_ip, mgmt_network, 
                        log_server=None,
                        mgmt_interface=mgmt_interface,
                        inline_interface=inline_interface,
                        logical_interface=logical,
                        dns=dns)
    
    element = SMCElement.factory(href=engine.href, 
                                 json=engine.engine_json) 
    result = common_api.create(element)
    
    #if result and fw_license:
    #    bind_license(name)
        
    return result     
    
def l3interface(name, ipaddress, ip_network, interface_id):
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
        engine.add_l3_interface(ipaddress, ip_network, interface_id=interface_id)
        element = SMCElement.factory(href=engine.href, 
                                    json=engine.engine_json,
                                    etag=engine.etag)
        return common_api.update(element)
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
    :return: href upon success otherwise None
    """  
    try:
        engine = Node(name).load()
        engine.add_inline_interface(logical_interface=logical_interface, 
                                    interface_id=interface_id)
        element = SMCElement.factory(href=engine.href, 
                                    json=engine.engine_json,
                                    etag=engine.etag)
        return common_api.update(element)
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
    :return: href upon success otherwise None
    """
    
    entry_href = smc.search.element_entry_point('logical_interface')   
    logical_int = LogicalInterface(name, entry_href,
                                   comment=comment)
      
    return common_api.create(logical_int.create()) 

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
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s.%(funcName)s: %(message)s')
    
    from pprint import pprint
    import time
    start_time = time.time()
    
    #smc.remove.element('erika')
    #host = host('erika', '1.2.3.4')
    ##########
    #interface 5, 6.6.6.6
    #smc.remove.element('myapi-testrun')
    
    #now load
    #engine = Node('myapi-testrun').load()    
    #smc.remove.element('kiley-test')    
    #smc.remove.element('regergserhatehtsrhs')
    
    #host = host('henrydavid', '1.1.1.1')
    #if not host.href:
    #    print "Creating henry failed: %s" % host.msg
    print LogicalInterface('mytest-api').create()
    #print log.create()
    #element = SMCElement.factory(name='test')
    
    """@type engine: Node"""
    #engine = Node('testips').load()
    #engine.inline_interface_add('9-10', 'http://172.18.1.150:8082/6.0/elements/logical_interface/1')
    #engine.capture_interface_add('10', 'http://172.18.1.150:8082/6.0/elements/logical_interface/1')
    #engine.physical_interface_add('124.124.124.124', '124.124.124.0/24', '124')
    #engine.blacklist_add('1.1.1.1/32', '0.0.0.0/0', 3600)
    #pprint(engine.interface())
    #pprint(engine.physical_interface_del('Interface 54'))
    #pprint(engine.blacklist_show())
    #pprint(engine.engine_links)
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
    int = {u'aggregate_mode': u'none',
 u'arp_entry': [],
 u'cvi_mode': u'none',
 u'dhcp_server_on_interface': {u'default_lease_time': 7200,
                               u'dhcp_range_per_node': []},
 u'interface_id': u'66',
 u'interfaces': [{u'single_node_interface': {u'address': u'66.66.66.66',
                                             u'auth_request': False,
                                             u'auth_request_source': False,
                                             u'automatic_default_route': False,
                                             u'backup_for_web_access': False,
                                             u'backup_heartbeat': False,
                                             u'backup_mgt': False,
                                             u'dynamic': False,
                                             u'igmp_mode': u'none',
                                             u'network_value': u'66.66.66.0/24',
                                             u'nicid': u'66',
                                             u'nodeid': 1,
                                             u'outgoing': False,
                                             u'pppoa': False,
                                             u'pppoe': False,
                                             u'pppoe_password': u'*****',
                                             u'primary_for_web_access': False,
                                             u'primary_heartbeat': False,
                                             u'primary_mgt': False,
                                             u'relayed_by_dhcp': False,
                                             u'reverse_connection': False,
                                             u'vrrp': False,
                                             u'vrrp_id': -1,
                                             u'vrrp_priority': -1}}],
 u'log_moderation': [{u'burst': 1000, u'log_event': u'1', u'rate': 100},
                     {u'log_event': u'2'}],
 u'managed_address_flag': False,
 u'mtu': -1,
 u'other_configuration_flag': False,
 u'qos_limit': -1,
 u'qos_mode': u'no_qos',
 u'router_advertisement': False,
 u'syn_mode': u'default',
 u'sync_parameter': {u'full_sync_interval': 5000,
                     u'heartbeat_group_ip': u'224.0.0.221',
                     u'incr_sync_interval': 50,
                     u'statesync_group_ip': u'224.0.0.222',
                     u'sync_mode': u'sync_all',
                     u'sync_security': u'sign'},
 u'virtual_engine_vlan_ok': False,
 u'vlanInterfaces': []}
    
    #pprint(smc.elements.interfaces.l3_interface('1.2.3.4', '1.2.3.0/24', '15').json)
    
    #interface = smc.elements.interfaces.l3_interface('1.2.3.4', '1.2.3.0/24', '15').json
    
    #element = SMCElement.factory(href='http://172.18.1.150:8082/6.0/elements/single_fw/3922/physical_interface', 
    #                            json=interface.get('physical_interface'))
    #print common_api.create(element)
    #print engine.initial_contact()
    #print "Engine export: %s" %  engine.export()
    
    #pprint(engine.snapshot())
    #engine.generate_snapshot('/Users/davidlepage/snapshot.xml')

    #print engine.generate_snapshot()
    
    
    #engine = IPS.create('myips', '1.2.2.2', '1.2.2.0/24')
    #element = SMCElement.factory(href=engine.href, json=engine.engine_json)
    #common_api.create(element)

    #engine.add_capture_interface(interface_id='6')
    #engine.update()
    #print "type: %s" % engine.node_type
    #pprint(engine.appliance_status('ngf-1035'))
    
    #print engine.go_online()
   #print engine.lock_offline(node='ngf-1065')
    #print engine.reboot(node='ngf-1065')
    #pprint(vars(engine))
    #pprint(engine.status())
    #print engine.cluster_mode
    #pprint(engine.appliance_status(node='ngf-1065'))
    #pprint(engine.status())
    #pprint(engine.node())
    #pprint(engine.appliance_status())
    #for msg in engine.refresh():
    #    print msg
        
    #pprint(engine.status())    
    #pprint(engine.appliance_status())
    #pprint(engine.antispoofing())
    #pprint(engine.alias_resolving())
    #pprint(engine.snapshot())
    #pprint(engine.node())
    #pprint(engine.routing_monitoring())
    
    
    #web_api.session.http_get('http://172.18.1.150:8082/6.0/progress/YWE1ZGY5YWE1YzQxYzg1MTo0MjM4YWY4ZToxNTVjMjRjOWNlYTotYzlj/result', 
    #                         stream=True)
    #"""@type engine: Node"""
    #engine = Node('henbo').load()
    
    
    
    
   
    

    
    #print "type: %s" % type(engine)
    #engine.add_inline_interface(interface_id='1-2')
    #print engine.update()
    
    #element = smc.elements.element.SMCElement.factory(href=engine.href, json=engine.engine_json, etag=engine.etag)
    #print "Firewall created at: %s" % common_api.update(element)
    
    
    #engine = Node('henry').load()
    #engine.add_inline_interface(interface_id='50-51')
    #element = smc.elements.element.SMCElement.factory(href=engine.href, json=engine.engine_json, etag=engine.etag)
    #print "IPS created at: %s" % common_api.update(element)
    
   
    
    
    
    #engine.l2interface(interface_id='9-10')
    #element = smc.elements.element.SMCElement.factory(href=engine.href, json=engine.engine_json,
    #                                                  etag=engine.etag)
    #print "IPS interface created at: %s" % common_api.update(element)
    
    #engine = Node('henry').load()
    #engine.add_l3_interface('67.67.67.67', '67.67.67.0/24', interface_id='15')
    #element = smc.elements.element.SMCElement.factory(href=engine.href, json=engine.engine_json,
    #                                                  etag=engine.etag)
    #print "Firewall Interface created at: %s" % common_api.update(element)
    #engine.add_inline_interface(interface_id='20-21')
    #print "Firewall Interface created at: %s" % common_api.update(element)
    
    '''
    engine = Layer3Firewall('henry').load()
    
    #Engine level commands
    engine.physical_interface()
    engine.tunnel_interface()
    engine.modem_interface()
    engine.adsl_interface()
    engine.wireless_interface()
    engine.switch_physical_interface()
    engine.interface()
    engine.node()
    engine.alias_resolving()
    engine.routing_monitoring()
    engine.internal_gateway()
    engine.antispoofing()
    engine.snapshot()
    engine.interface()
    engine.refresh()
    engine.upload()
    engine.add_route()
    engine.blacklist()
    engine.blacklist_flush()
    engine.generate_snapshot()
    engine.export()
    engine.routing()
    
    #Node level commands
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
    '''
    #smc.remove.element('mylayer2-test')
    #print single_layer2('mylayer2-test', '172.18.1.254', '172.18.1.0/24', dns=['5.5.5.5'], fw_license=True)
    
    '''
    smc.remove.element('testl2')
    log = smc.search.get_first_log_server()
    engine = Layer2Firewall.create('testl2', '1.1.1.1', '1.1.1.0/24', log)
    href = smc.search.element_entry_point('single_layer2')
    element = smc.elements.element.SMCElement.factory(href=href, json=engine)
    print "Layer2 Firewall engine created at: %s" % common_api.create(element)
    
    engine = Layer2Firewall('testl2').load()
    engine.add_inline_interface(interface_id='15-16')
    engine.add_capture_interface(interface_id='6', logical_interface='apitool')
    element = smc.elements.element.SMCElement.factory(href=engine.href, json=engine.engine_json,
                                                      etag=engine.etag)
    print "Firewall Interface created at: %s" % common_api.update(element)
    '''


    '''
    smc.remove.element('testfw')
    log = smc.search.get_first_log_server()
    engine = Layer3Firewall.create('testfw', '1.2.3.4', '1.2.3.0/24', log, mgmt_interface=4)
    href = smc.search.element_entry_point('single_fw')
    element = smc.elements.element.SMCElement.factory(href=href, json=engine)
    print "Layer3 Firewall engine created at: %s" % common_api.create(element)
    '''
    '''
    #Test Layer2
    smc.remove.element('layer2')
    log = smc.search.get_first_log_server()   
    engine = Layer2Firewall.create('layer2', '172.18.1.254', '172.18.1.0/24', log, dns=['5.5.5.5'])
    href = smc.search.element_entry_point('single_layer2')
    element = smc.elements.element.SMCElement.factory(href=href, json=engine)
    print "Layer2 Firewall engine created at: %s" % common_api.create(element)
    
    engine = Layer2Firewall('layer2').load()
    pprint(engine.engine_json)
    
    engine.add_inline_interface(logical_interface='apitool', interface_id='6-7')
    pprint(engine.engine_json)
    element = smc.elements.element.SMCElement.factory(href=engine.href, json=engine.engine_json, etag=engine.etag)
    print "Layer2 Firewall interface created at: %s" % common_api.update(element)
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
