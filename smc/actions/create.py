# -*- coding: utf-8 -*- 
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
from smc.core.engines import Layer3Firewall, Layer2Firewall, IPS,\
    Layer3VirtualEngine
from smc.core.engine import Engine
from smc.elements.user import AdminUser
from smc.elements.helpers import logical_intf_helper, zone_helper,\
    location_helper
from smc.core.interfaces import PhysicalInterface
from smc.api.exceptions import SMCException, NodeCommandFailed,\
    SMCOperationFailure, CreateEngineFailed
from smc.elements.collection import describe_vpn_certificate_authority,\
    describe_protocols, describe_hosts, describe_countries, describe_single_fws,\
    describe_virtual_fws, describe_vpn_policies, describe_groups,\
    describe_address_ranges, describe_ip_lists, describe_master_engines,\
    describe_external_gateways, describe_logical_interfaces,\
    describe_admin_users, describe_access_control_lists, describe_fw_policies,\
    describe_log_servers, describe_management_servers, describe_locations
from smc.elements.vpn import VPNCertificate, VPNPolicy, ExternalGateway
from smc.elements.element import SMCElement, Host, Group, Network, IPList, Location
#from smc.deploy.aws import AWSProvision
from smc.api.common import fetch_json_by_href, fetch_json_by_name,\
    fetch_href_by_name, SMCRequest
from smc.api.web import SMCResult
from smc.core.node import Node
from smc.elements.policy import FirewallPolicy
from smc.elements.servers import LogServer, ManagementServer

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
        engine = Engine(name).load()
              
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
        engine = Engine(name).load()
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
        engine = Engine(name).load()
        return engine.blacklist(src, dst, duration)
    
    except SMCException, e:
        logger.error("Exception during blacklist: %s" % e)

def blacklist_flush(name):
    """ Flush entire blacklist for node name
    
    :param name: name of node or cluster to remove blacklist
    :return: None, or message if failure
    """
    try:
        engine = Engine(name).load()
        print engine.blacklist_flush()
    
    except SMCException, e:
        logger.error("Exception during blacklist: %s" % e)
            
def bind_license(name):
    engine = Engine(name).load()
    return engine.bind_license()
    
def unbind_license(name):
    engine = Engine(name).load()
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

def mask_convertor(netmask):
    return sum([bin(int(x)).count('1') for x in netmask.split('.')])

class RequestMock(object):
    def __init__(self, 
                 text='{"details":["Element name test is already used."],\
                 "message":"Impossible to store the element test.",\
                 "status":"0"}',
                 headers={'content-type': 'application/json'}):
        self.status_code = 200
        self.headers = headers
        self.text = text
        
if __name__ == '__main__':

    import time
    start_time = time.time()
    from smc import session
    from pprint import pprint
    logging.getLogger()
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s.%(funcName)s: %(message)s')
 
    #session.login(url='http://172.18.1.150:8082', api_key='EiGpKD4QxlLJ25dbBEp20001', timeout=60)
    session.login(url='http://172.18.1.25:8082', api_key='gxJ8WugtuNB5ztvl7HUz0001', timeout=120)

    #print fetch_json_by_name('ĂĂĂĂrdvark')
    #pprint(session.cache.get_all_entry_points())
    
    """@type engine: Engine"""
    #engine = Engine('i-*').load()
    
    #for e in engine.export(wait_for_finish=True):
    #    print e
    #print engine
    #pprint(engine.permissions())
    
    host = Host('host1')
    print host.describe()
    
    #####################BUG - doesnt filter properly
    #for locations in describe_locations():
    #    print locations
    #####################BUG - doesn't find location using location as filter
    #location = Location('mylocation')
    #print location.href
    #for location in describe_locations():
    #    print location
    
    group = Group('silva')
    for member in group.obtain_members():
        e = smc.actions.search.element_name_and_type_by_href(member)
        print e
        print "Name: %s, Type: %s" % (e[0].decode('utf-8'), e[1])
    

    #pprint(smc.actions.search.search_unused())
    #pprint(smc.actions.search.search_duplicate())
    #pprint(smc.actions.search.element_by_href_as_json('http://172.18.1.25:8082/6.1/elements/access_control_list/5'))
    #host = Host('blahblah', '1.1.1.1').redirected()
    #pprint(smc.actions.search.element_by_href_as_json('http://172.18.1.25:8082/6.1/elements/admin_user/4'))
    
    #pprint(session.cache.get_element_filters())
    
    '''
    func_template = """def describe_%s(): print("blah")"""
    for x in session.element_filters:
        if x == 'alias': 
            print "EXECUTING"
            #exec(func_template % x)
            exec("""def describe_alias(): print ('2')""")
    
    #func_template = """def describe_field_%d(): print(%d)"""
    #for x in range(1, 11): 
    #    exec(func_template % (x, x))
    '''
    
    #smc.actions.search.element_by_href_as_json('http://172.18.1.25:8082/6.1/elements/single_fw/776')
    #print fetch_href_by_name('ĂĂĂĂrdvark')
    #smc.actions.search.element_as_json('2ĂĂĂĂrdvark')
    #result = Host('Curaçao34', '22.22.22.22').create()
    #engine = Layer3Firewall.create(name='ĂĂĂĂrdvark36', 
    #                                   mgmt_ip='1.1.1.1', 
    #                                   mgmt_network='1.1.1.0/24')
    #pprint(engine.json)
    #engine = Engine('ĂĂĂĂrdvark2').load()
    #engine = Layer3Firewall.create(name='ĂĂĂĂrdvark2',
    #                               mgmt_ip='1.1.1.1',
    #                               mgmt_network='1.1.1.0/24')   

    #engine = Engine('ĂĂĂĂhfefeĂĂĂĂĂĂĂĂĂwfefwef').load()
    #print engine.rename('ĂĂĂĂĂĂĂĂĂĂĂwfefwef')
        #print smc.actions.search.element_as_json('¥¥¥test')
    
    #pprint(engine.json)
    #print engine
    
    #print engine
    #for engine in describe_virtual_fws():
    #    print engine
    

    #for country in describe_countries():
    #    print country
    #for x in describe_countries():
    #    print x
    
    #import smc.elements.policy
    """@type policy: FirewallPolicy"""
    #policy = smc.elements.policy.FirewallPolicy('api-test-policy').load()
    #print policy.ipv4_rule.create('erika6 rule', ['any'], ['any'], ['any'], 'allow')
    #for rule in policy.ipv4_rule.ipv4_rules:
    #    print "rule: %s" % rule
    from smc.elements.other import ContactAddress
    from smc.elements.user import AdminUser
    from smc.core.engine import Engine
    from smc.actions import search
    
    #engine = Engine('i-1*').load()
    #print engine.json
    
    #print Layer3Firewall.create_with_template(cfg)
    #print mask_convertor('255.255.191.0')
    #engine.rename('kooky')
    #print engine.node()
    
    #pprint(search.element_by_href_as_json('http://172.18.1.25:8082/6.1/elements/single_fw/684/firewall_node/685/certificate_info'))    
    #print engine.internal_gateway.generate_certificate(cert)
    
    #organization, common_name, signature_algorithm,
    #             public_key_algorithm, public_key_length=2056, country=None,
    #             organization_unit=None, state_province=None, locality=None,
    #             certificate_authority_ref=None
                 
    #pprint(search.element_entry_point('vpn_certificate_authority'))
    #pprint(search.element_by_href_as_json('http://172.18.1.25:8082/6.1/elements/vpn_certificate_authority'))
    #print engine.internal_gateway.gateway_certificate_request()
    #print engine.internal_gateway.generate_certificate()
    
    #pprint(engine.antispoofing())
    #for interface in engine.physical_interface.all():
    #    print interface.describe()
                    
    #for domain in collection.describe_admin_domains():
    #    pprint(vars(domain))
    #    pprint(smc.actions.search.element_by_href_as_json('http://172.18.1.25:8082/6.1/elements/admin_domain/1'))
    
    
    #engine = Engine('mcafee').load()
    #pprint(engine.json)
     
    
    #href = smc.actions.search.element_href('sg_vm')

    #from smc.api.common import fetch_href_by_name
    #pprint(fetch_href_by_name('mcafee', exact_match=False).json)
    
    #pprint(smc.actions.search.element_info_as_json('mcafee2'))
    
    '''    
    for interface in engine.interface.all():
        if interface.name == 'Interface 0':
            #interface.add_contact_address('52.206.156.102', location_helper('Internet'), engine.etag)
            #interface.add_contact_address('123.123.123.123', location_helper('DMZ'), engine.etag)
            #pprint(interface.contact_addresses)
            #interface._sub_interface()
            print interface.sub_interface()
    '''
    #pprint(smc.actions.search.element_by_href_as_json('http://172.18.1.25:8082/6.1/elements/address_range/0'))
   
    #vpn = VPNPolicy('Amazon*').load()
    #pprint(vpn.describe())
    #request = SMCRequest(href='http://172.18.1.25:8082/elements/blah', json={})
    #result = getattr(smc.api.common, 'create')(request)
    #result = getattr(request, 'create')()
    #print result
    
    ###CONTACT ADDRESS ON INTERFACE
    '''
    for loc in describe_locations():
        if loc.name == 'mydmz':
            location=loc.href
            
    for x in engine.interface.all():
        if x.name == 'Interface 0':
            print "Adding to href : %s" % loc.href
            x.add_contact_address('2.2.2.2', location, engine.etag)
    '''
    #pprint(smc.actions.search.element_by_href_as_json('http://172.18.1.25:8082/6.1/elements/ip_list/12/ip_address_list'))
   
    
    """@type engine: Node""" #aws-02 node 1
    #engine = Engine('elyse').load()
    #pprint(engine.json)
    #for intf in engine.interface.all():
    #    if intf.name == 'Interface 0':
    #        pprint(intf.describe())
    #        intf.add_contact_address('5.5.5.5', location_helper('dmz'))
    #pprint(smc.actions.search.element_by_href_as_json('http://172.18.1.25:8082/6.1/elements/single_fw/687/physical_interface/2/interface/2/contact_addresses'))
   
    #smc.actions.remove.element('elyse')
    
    #tunnel = TunnelInterface()
    #tunnel.add_cluster_virtual_interface(5000, '52.52.52.52', '52.52.52.0/24')
    #Works for single node - 
    #tunnel.add_single_node_interface(1005, '10.10.10.5', '10.10.10.0/24')
    #pprint(tunnel.data)
        
        
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
   
   
    #pprint(collection.describe_sub_ipv6_fw_policies())
    

    #for host in describe_hosts(name=['duh']):
    #    h = host.load()
    #    h.modify_attribute(name='kiley', address='1.1.2.2')
    
   
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
