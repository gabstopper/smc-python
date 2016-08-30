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
import smc.actions.search
from smc.elements.element import logical_intf_helper, \
    TCPService, EthernetService, ICMPService, ICMPIPv6Service, ServiceGroup,\
    TCPServiceGroup, UDPServiceGroup, UDPService, IPServiceGroup, IPService, Host, \
    AdminUser, zone_helper, SMCElement
import smc.api.web
from smc.elements.engines import Node, Layer3Firewall, Layer2Firewall, IPS, Layer3VirtualEngine, FirewallCluster,\
    MasterEngine, AWSLayer3Firewall, Engine, VirtualResource
    
from smc.api.web import SMCResult
from smc.api.exceptions import SMCException
from smc.elements.interfaces import VlanInterface, PhysicalInterface, TunnelInterface, NodeInterface,\
    SingleNodeInterface
from smc.elements.vpn import VPNPolicy, ExternalGateway, ExternalEndpoint, VPNProfile
from smc.elements.collections import describe_fw_policies,\
    describe_address_ranges, describe_vpn_profiles, describe_networks,\
    describe_hosts, describe_external_gateways, describe_virtual_fws


logger = logging.getLogger(__name__)

def host(name, ipaddress, secondary_ip=[], comment=None):
    """ Create host object
      
    :param name: name, must be unique
    :param ipaddress: ip address of host
    :param secondary_ip[] (optional): additional IP for host
    :param comment (optional)
    :return: href upon success otherwise None
    """   
    return smc.elements.element.Host(name, ipaddress, 
                                    secondary_ip=secondary_ip, 
                                    comment=comment).create()

def iprange(name, addr_range, comment=None):
    """ Create iprange object

    :param name: name for object
    :param addr_range: ip address range, i.e. 1.1.1.1-1.1.1.10
    :param comment (optional)
    :return: href upon success otherwise None
    """   
    addr = addr_range.split('-') #just verify each side is valid ip addr
    if len(addr) == 2: #has two parts
        return smc.elements.element.AddressRange(name, addr_range,
                                                 comment=comment).create()   
       
def router(name, ipaddress, secondary_ip=None, comment=None):
    """ Create router element

    :param name: name for object
    :param ipaddress: ipv4 address
    :param comment (optional)
    :return: href upon success otherwise None
    """     
    return smc.elements.element.Router(name, ipaddress,
                                       secondary_ip=secondary_ip,
                                       comment=comment).create()

def network(name, ip_network, comment=None):
    """ Create network element
 
    :param name: name for object
    :param ip_network: ipv4 address in cidr or full netmask format (1.1.1.1/24, or 1.1.1.0/255.255.0.0)
    :param comment (optional)
    :return: href upon success, or None
    """
    return smc.elements.element.Network(name, ip_network,
                                        comment=comment).create()

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
            found_member = smc.actions.search.element_href(m)
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
    result = Layer3Firewall.create(name, mgmt_ip, mgmt_network, 
                                   mgmt_interface=mgmt_interface,
                                   domain_server_address=dns)
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
    result = Layer2Firewall.create(name, mgmt_ip, mgmt_network, 
                                   mgmt_interface=mgmt_interface,
                                   inline_interface=inline_interface,
                                   logical_interface=logical_intf_helper(logical_interface),
                                   domain_server_address=dns)
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
    result = IPS.create(name, mgmt_ip, mgmt_network, 
                        mgmt_interface=mgmt_interface,
                        inline_interface=inline_interface,
                        logical_interface=logical_intf_helper(logical_interface),
                        domain_server_address=dns)
    return result
   
def l3interface(name, ipaddress, ip_network, interfaceid):
    """ Add L3 interface for single FW
       
    :param l3fw: name of firewall to add interface to
    :param ip: ip of interface
    :param network: network for ip
    :param interface_id: interface_id to use
    :return: href upon success otherwise None
    """    
    try:
        engine = Engine(name).load()
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
        engine = Engine(name).load()
        
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
    #smc.api.web.session.login('http://172.18.1.150:8082', 'EiGpKD4QxlLJ25dbBEp20001', timeout=60)
    
    logging.getLogger()
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s.%(funcName)s: %(message)s')
    
    from smc.api.session import session
    session.login(url='http://172.18.1.150:8082', api_key='EiGpKD4QxlLJ25dbBEp20001', timeout=60)
    import smc.elements.collections as collections
    import smc.actions.remove
    from pprint import pprint
    import time
    start_time = time.time()
    
    #import smc.elements.policy
    """@type policy: FirewallPolicy"""
    #policy = smc.elements.policy.FirewallPolicy('api-test-policy').load()
    #print policy.ipv4_rule.create('erika6 rule', ['any'], ['any'], ['any'], 'allow')
    #for rule in policy.ipv4_rule.ipv4_rules:
    #    print "rule: %s" % rule

    """@type engine: Node"""
    engine = Engine('aws-02').load()
    for node in engine.nodes:
        print node.name, node.node_type
    #pprint(vars(engine))
    
    '''
    for gw in collections.describe_external_gateways():
        if gw.name == 'externalgw':
            g = gw.load()
            pprint(vars(g))
            for endpoint in g.external_endpoint:
                pprint(vars(endpoint))
    '''
    
        
    #for site in engine.internal_gateway.vpn_site.all():
    #    print site
    #    site.load()
    #    site.modify_attribute(site_element=[site_network])
    #    pprint(vars(site.element))
    #for x in describe_vpn_profiles():
    #    if x.name == 'iOS Suite':
    #        pprint(smc.actions.search.element_by_href_as_json(x.href))
    
    
    #vpn = VPNPolicy('myVPN').load()
    #print vpn.name, vpn.vpn_profile
    #vpn.open()
    #pprint(vars(vpn))
    #pprint(vpn.central_gateway_node())
    #vpn.add_central_gateway(engine.internal_gateway.href)
    #vpn.add_satellite_gateway(engine.internal_gateway.href)
    #vpn.save()
    #vpn.close()
    
    #from smc.elements.policy import FirewallPolicy
    #policy = FirewallPolicy('newpolicy').load()
    
    #print "template: %s" % policy.template
    #print "file filtering: %s" % policy.file_filtering_policy
    #print "inspection policy: %s" % policy.inspection_policy
    #for x in policy.fw_ipv4_access_rules:
    #    x.delete()
    
    #policy = FirewallPolicy.create(name='smcpython',
    #                               template_policy='Firewall Inspection Template') 
    #print(smc.actions.search.element_href('foonetwork'))
    #engine = Engine('aws-02').load()
    
    #pprint(vars(engine.internal_gateway))
    #for site in engine.internal_gateway.vpn_site:
    #    pprint(vars(site))
   
   
    #pprint(collections.describe_sub_ipv6_fw_policies())
    

    #for host in describe_hosts(name=['duh']):
    #    h = host.load()
    #    h.modify_attribute(name='kiley', address='1.1.2.2')
    
   
    '''
    for site in engine.internal_gateway.vpn_site:
        r = smc.actions.search.element_by_href_as_smcresult(site.href) 
        s = vars(site)
        s.get('site_element').append('http://172.18.1.150:8082/6.0/elements/network/9822')
        pprint(s)
        print SMCElement(href=site.href,
                         json=s,
                         etag=r.etag).update()
    '''
    '''
    myservices = [v
               for item in smc.actions.search.element_href_by_batch(['HTTP', 'HTTPS'], 'tcp_service')
               for k, v in item.iteritems()
               if v]
    
    mysources = [v
               for item in smc.actions.search.element_href_by_batch(['foonetwork', 'amazon-linux'])
               for k, v in item.iteritems()
               if v]
    
    mydestinations = ['any']
    
    policy.ipv4_rule.create(name='myrule', 
                            sources=mysources,
                            destinations=mydestinations, 
                            services=myservices, 
                            action='permit')
    
    for rule in policy.fw_ipv4_access_rules:
        print rule
    '''   
    #my_destinations = ['any']
    #my_services = smc.actions.search.element_href_by_batch(['HTTP', 'HTTPS'])
    #print my_services
    
    #print('ipv4 access rule')
    #pprint(smc.actions.search.element_by_href_as_json('http://172.18.1.150:8082/6.0/elements/fw_policy/244/fw_ipv4_access_rule'))
    #print "Query vpn sites"
    #pprint(ext_gw.vpn_site())
    #print "example vpn site detail"
    #pprint(smc.actions.search.element_by_href_as_json('http://172.18.1.150:8082/6.0/elements/external_gateway/1702/vpn_site/1723'))
    #print "gateway setting ref: "
    #pprint(smc.actions.search.element_by_href_as_json('http://172.18.1.150:8082/6.0/elements/external_gateway/1702'))
    
    
    
    #DEFAULT_NAT
    #Default NAT address alias
    #pprint(smc.actions.search.element_by_href_as_json('http://172.18.1.150:8082/6.0/elements/default_nat_address_alias'))
    #Leads to get the actual values
    #pprint(smc.actions.search.element_by_href_as_json('http://172.18.1.150:8082/6.0/elements/default_nat_address_alias/133'))
    #Then call resolve link
    #pprint(smc.actions.search.element_by_href_as_json('http://172.18.1.150:8082/6.0/elements/default_nat_address_alias/133/resolve'))
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
    
    #print "Number of GET calls: %s" % smc.api.web.session.http_get.calls
    #print "Number of GET calls: %s" % smc.api.session.session.logout()  
    #smc.api.web.session.logout()
    session.logout()
