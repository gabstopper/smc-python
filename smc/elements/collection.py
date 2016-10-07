"""
Collection module allows for search queries against the SMC API to retrieve
element data.

Each describe function allows two possible (optional) parameters:

* name: search parameter (can be any value)
* exact_match: True|False, whether to match exactly on name field

Each function returns a list of objects based on the specified element type. Most
elements will return a list of SMCElements. This will be the case for container classes
that do not have class level methods. These elements do not require 'load' be called
before fully initializing the configuration.

All return element types (regardless of type) will have the following attributes as
metadata::

    href: href location of the element in SMC
    type: type of element
    name: name of element

Describe functions that return specific element types, such as Engine, require that
the load() method be called in order to initialize the data set and available methods for
that class. 

For example, find a specific engine by type, load and run a node level command::

    for fw in describe_single_fws(): #returns type Engine
        if fw.name == 'myfw':
            engine = fw.load()
            for node in engine.nodes:
                node.appliance_status()
                node.reboot()

Elements that return type SMCElement have methods available to SMCElement class

.. seealso:: :py:class:`smc.elements.element.SMCElement`

Some additional generic search examples follow...

    import smc.elements.collection as collection
    
To search for all host objects::

    for host in describe_hosts():
        print host
        
To search only for a host name 'test'::

    for host in describe_hosts(name=['test']):
        print host

To search for all hosts with 'test' in the name::

    for host in describe_hosts(name=['test'], exact_match=False):
        print host
        
It may be useful to do a wildcard search for an element type and view the entire
object info::

    for host in describe_networks(name=['1.1.1.0'], exact_match=False):
        print host.name, host.describe() #returned SMCElement

Modify a specific SMCElement type by changing the name::

    for host in describe_hosts(name=['myhost']):
        if host:
            host.modify_attribute(name='mynewname')   
            
It is also possible to use wildcards when searching for a specific host, without
setting the exact_match=False flag. For example::

    for x in describe_hosts(name=['TOR*']):
        print x.describe()
        
    for y in describe_hosts(name=['TOR'], exact_match=False):
        print y
        
Both will work, however the first option will only find items starting with TOR*, whereas
the second option could find items such as 'DHCP Broadcast OriginaTOR', etc.
"""
from smc import session
from smc.elements.element import SMCElement, Meta, IPList
from smc.elements.user import AdminUser
from smc.core.engines import Engine
from smc.elements.vpn import ExternalGateway, VPNPolicy
from smc.elements.system import System
from smc.api.common import fetch_json_by_href, fetch_href_by_name
from smc.elements.servers import ManagementServer, LogServer
from smc.elements.policy import FirewallPolicy

"""        
Policy Elements

Policy elements describe pre-configured Firewall, IPS or Layer 2 Policies, 
along with templates. Each policy type is based on a best practice template.
When creating a policy, a policy template is required as well
"""
def describe_fw_policies(name=None, exact_match=True):
    """
    Describe all layer 3 firewall policies
    
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('fw_policy', name, exact_match, FirewallPolicy)

def describe_fw_template_policies(name=None, exact_match=True):
    """
    Describe all layer 3 firewall policy templates
    
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('fw_template_policy', name, exact_match)

def describe_ips_policies(name=None, exact_match=True):
    """
    Describe all IPS policies
    
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('ips_policy', name, exact_match)

def describe_ips_template_policies(name=None, exact_match=True):
    """
    Describe all IPS policy templates
    
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('ips_template_policy', name, exact_match)

def describe_layer2_policies(name=None, exact_match=True):
    """
    Describe Layer 2 Firewall policies
    
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('layer2_policy', name, exact_match)

def describe_layer2_template_policies(name=None, exact_match=True):
    """
    Describe Layer 2 Firewall policy templates
    
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('layer2_template_policy', name, exact_match)

def describe_inspection_policies(name=None, exact_match=True):
    """
    Describe Inspection policies
    
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('inspection_template_policy', name, exact_match)

def describe_sub_ipv6_fw_policies(name=None, exact_match=True):
    """
    Describe IPv6 Layer 3 Firewall sub policies
    
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('sub_ipv6_fw_policy', name, exact_match)

def describe_sub_ipv4_fw_policies(name=None, exact_match=True):
    """
    Describe IPv4 Layer 3 Firewall sub policies
    
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('sub_ipv4_fw_policy', name, exact_match)

def describe_sub_ipv4_layer2_policies(name=None, exact_match=True):
    """
    Describe Layer 2 IPv4 Firewall sub policies
    
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('sub_ipv4_layer2_policy', name, exact_match)

#
def describe_sub_ipv4_ips_policies(name=None, exact_match=True):
    """
    Describe IPS IPv4 sub policies
    
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('sub_ipv4_ips_policy', name, exact_match)

def describe_file_filtering_policies(name=None, exact_match=True):
    """
    Describe File Filtering policies
    
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('file_filtering_policy', name, exact_match)

""" 
Engine Elements
"""
def describe_single_fws(name=None, exact_match=True):
    """
    Describe Single Layer 3 Firewalls
    
    :return: list :py:class:`smc.core.engines.Engine`
    """
    return generic_list_builder('single_fw', name, exact_match, klazz=Engine)
    
def describe_fw_clusters(name=None, exact_match=True):
    """
    Describe Layer 3 FW Clusters
    
    :return: list :py:class:`smc.core.engines.Engine`
    """
    return generic_list_builder('fw_cluster', name, exact_match, klazz=Engine)
        
def describe_single_layer2_fws(name=None, exact_match=True):
    """
    Describe Single Layer 2 Firewalls
    
    :return: list :py:class:`smc.core.engines.Engine`
    """
    return generic_list_builder('single_layer2', name, exact_match, klazz=Engine)
    
def describe_layer2_clusters(name=None, exact_match=True):
    """
    Describe Layer 2 Firewall Clusters
    
    :return: list :py:class:`smc.core.engines.Engine`
    """
    return generic_list_builder('layer2_cluster', name, exact_match, klazz=Engine)
    
def describe_single_ips(name=None, exact_match=True):
    """
    Describe Single IPS engines
    
    :return: list :py:class:`smc.core.engines.Engine`
    """
    return generic_list_builder('single_ips', name, exact_match, klazz=Engine)
    
def describe_ips_clusters(name=None, exact_match=True):
    """
    Describe IPS engine clusters
    
    :return: list :py:class:`smc.core.engines.Engine`
    """
    return generic_list_builder('ips_cluster', name, exact_match, klazz=Engine)
    
def describe_master_engines(name=None, exact_match=True):
    """
    Describe Master Engines
    
    :return: list :py:class:`smc.core.engines.Engine`
    """
    return generic_list_builder('master_engine', name, exact_match, klazz=Engine)
    
def describe_virtual_fws(name=None, exact_match=True):
    """
    Describe Virtual FW engines
    
    Example of retrieving all registered virtual fw's, looking for a
    specific engine, then checking the status of the node::
    
        for fw in describe_virtual_fws():
            print fw
            if fw.name == 've-7':
                engine = fw.load()
                for node in engine.nodes:
                    node.appliance_status()
    
    :return: list :py:class:`smc.core.engines.Engine`
    """
    return generic_list_builder('virtual_fw', name, exact_match, klazz=Engine)
    
def describe_virtual_ips(name=None, exact_match=True):
    """
    Describe Virtual IPS engines
    
    :return: list :py:class:`smc.core.engines.Engine`
    """
    return generic_list_builder('virtual_ips', name, exact_match, klazz=Engine)

""" 
Server and Engine Elements
"""

def describe_log_servers(name=None, exact_match=True):
    """
    Describe available Log Servers
    
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('log_server', name, exact_match, LogServer)

def describe_management_servers(name=None, exact_match=False):
    """
    Describe available Management Servers
    
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('mgt_server', name, exact_match, ManagementServer)

def describe_locations(name=None, exact_match=False):
    """
    Describe available locations
    
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('location')

def describe_update_packages():
    """
    Show all available update packages on SMC
    
    :return list :py:class:`smc.elements.system.UpdatePackage`
    """
    system = System().load()
    return system.update_package()

def describe_engine_upgrades():
    """
    Show all engine level upgrades available
    
    :return list :py:class:`smc.elements.system.EngineUpgrade`
    """
    system = System().load()
    return system.engine_upgrade()    

"""
Domains
"""
def describe_admin_domains(name=None, exact_match=True):
    return generic_list_builder('admin_domain', name, exact_match)

"""
Administration
"""
def describe_admin_users(name=None, exact_match=True):
    return generic_list_builder('admin_user', name, exact_match, AdminUser)

def describe_access_control_lists(name=None, exact_match=True):
    return generic_list_builder('access_control_list', name, exact_match)

"""
Interface Elements
"""
#
def describe_interface_zones(name=None, exact_match=True):
    """
    Describe available interface zones
    See :py:class:`smc.elements.element.Zone` for more info
    
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('interface_zone', name, exact_match)

def describe_logical_interfaces(name=None, exact_match=True):
    """
    Describe available logical interfaces (used for Capture / Inline interfaces)
    See :py:class:`smc.elements.element.LogicalInterface` for more info
    
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('logical_interface', name, exact_match)

"""
Network Elements
"""    
def describe_hosts(name=None, exact_match=True):
    """
    Describe host objects
    See :py:class:`smc.elements.element.Host` for more info
    
    :param list name: Name of host object (optional)
    :param exact_match: Do exact match against name field (default True)
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('host', name, exact_match)

def describe_tcp_services(name=None, exact_match=True):
    """
    Describe available TCP Services
    See :py:class:`smc.elements.element.TCPService` for more info
    
    :param list name: Name of host object (optional)
    :param exact_match: Do exact match against name field (default True)
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('tcp_service', name, exact_match)

def describe_tcp_service_groups(name=None, exact_match=True):
    """
    Describe TCP Service Groups
    See :py:class:`smc.elements.element.TCPServiceGroup` for more info
    
    :param list name: Name of host object (optional)
    :param exact_match: Do exact match against name field (default True)
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('tcp_service_group', name, exact_match)

def describe_icmp_services(name=None, exact_match=True):
    """
    Describe ICMP Services
    See :py:class:`smc.elements.element.ICMPService` for more info
    
    :param list name: Name of host object (optional)
    :param exact_match: Do exact match against name field (default True)
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('icmp_service', name, exact_match)

def describe_service_groups(name=None, exact_match=True):
    """
    Describe Service Groups
    See :py:class:`smc.elements.element.ServiceGroup` for more info
    
    :param list name: Name of host object (optional)
    :param exact_match: Do exact match against name field (default True)
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('service_group', name, exact_match)

def describe_udp_service_groups(name=None, exact_match=True):
    """
    Describe UDP Service Groups
    See :py:class:`smc.elements.element.UDPServiceGroup` for more info
    
    :param list name: Name of host object (optional)
    :param exact_match: Do exact match against name field (default True)
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('udp_service_group', name, exact_match)

def describe_address_ranges(name=None, exact_match=True):
    """
    Describe Address Range network elements
    See :py:class:`smc.elements.element.AddressRange` for more info
    
    :param list name: Name of host object (optional)
    :param exact_match: Do exact match against name field (default True)
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('address_range', name, exact_match)

def describe_domain_names(name=None, exact_match=True):
    """
    Describe Domain Name network elements
    See :py:class:`smc.elements.element.DomainName` for more info
    
    :param list name: Name of host object (optional)
    :param exact_match: Do exact match against name field (default True)
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('domain_name', name, exact_match)

def describe_rpc_services(name=None, exact_match=True):
    """
    Describe RPC Service network elements
    
    :param list name: Name of host object (optional)
    :param exact_match: Do exact match against name field (default True)
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('rpc_service', name, exact_match)

def describe_icmp_ipv6_services(name=None, exact_match=True):
    """
    Describe ICMP ipv6 service elements
    See :py:class:`smc.elements.element.ICMPIPv6Service` for more info
    
    :param list name: Name of host object (optional)
    :param exact_match: Do exact match against name field (default True)
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('icmp_ipv6_service', name, exact_match)

def describe_icmp_service_groups(name=None, exact_match=True):
    """
    Describe ICMP Service Groups
    
    :param list name: Name of host object (optional)
    :param exact_match: Do exact match against name field (default True)
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('icmp_service_group', name, exact_match)

def describe_ip_services(name=None, exact_match=True):
    """
    Describe IP Service network elements
    See :py:class:`smc.elements.element.IPService` for more info
    
    :param list name: Name of host object (optional)
    :param exact_match: Do exact match against name field (default True)
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('ip_service', name, exact_match)

def describe_protocols(name=None, exact_match=True):
    """
    Describe Protocol network elements
    See :py:class:`smc.elements.element.Protocol` for more info
    
    :param list name: Name of host object (optional)
    :param exact_match: Do exact match against name field (default True)
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('protocol', name, exact_match)

def describe_routers(name=None, exact_match=True):
    """
    Describe Router network elements
    See :py:class:`smc.elements.element.Router` for more info
    
    :param list name: Name of host object (optional)
    :param exact_match: Do exact match against name field (default True)
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('router', name, exact_match)

def describe_groups(name=None, exact_match=True):
    """
    Describe Group network elements
    See :py:class:`smc.elements.element.Group` for more info
    
    :param list name: Name of host object (optional)
    :param exact_match: Do exact match against name field (default True)
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('group', name, exact_match)

def describe_ethernet_services(name=None, exact_match=True):
    """
    Describe Ethernet Service network elements
    See :py:class:`smc.elements.element.EthernetService` for more info
    
    :param list name: Name of host object (optional)
    :param exact_match: Do exact match against name field (default True)
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('ethernet_service', name, exact_match)

def describe_udp_services(name=None, exact_match=True):
    """
    Describe UDP Service network elements
    See :py:class:`smc.elements.element.UDPService` for more info
    
    :param list name: Name of host object (optional)
    :param exact_match: Do exact match against name field (default True)
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('udp_service', name, exact_match)

def describe_networks(name=None, exact_match=True):
    """
    Describe Networks network elements
    See :py:class:`smc.elements.element.Network` for more info
    
    :param list name: Name of host object (optional)
    :param exact_match: Do exact match against name field (default True)
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('network', name, exact_match)

def describe_ip_service_groups(name=None, exact_match=True):
    """
    Describe IP Service Groups
    See :py:class:`smc.elements.element.IPServiceGroup` for more info
    
    :param list name: Name of host object (optional)
    :param exact_match: Do exact match against name field (default True)
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('ip_service_group', name, exact_match)

def describe_ethernet_service_groups(name=None, exact_match=True):
    """
    Describe Ethernet Service Groups
    
    :param list name: Name of host object (optional)
    :param exact_match: Do exact match against name field (default True)
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('ethernet_service_group', name, exact_match)

def describe_ip_lists(name=None, exact_match=True):
    """
    Describe IP Lists
    
    :param list name: Name of host object (optional)
    :param exact_match: Do exact match against name field (default True)
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    if session.api_version >= 6.1:
        return generic_list_builder('ip_list', name, exact_match, IPList)
    else:
        return []

def describe_countries(name=None, exact_match=True):
    """
    Describe countries
    """
    if session.api_version >= 6.1:
        return generic_list_builder('country', name, exact_match)
    else:
        return []

"""
VPN Elements
"""
def describe_vpn_policies(name=None, exact_match=True):
    """
    Show all VPN policies configured
    
    Find a specific VPN policy, load and check specific setting::
    
        for x in collections.describe_vpn_policies():
            if x.name == 'myVPN':
                policy = x.load()
                policy.open()
                print policy.central_gateway_node()
                policy.close()

    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('vpn', name, exact_match, klazz=VPNPolicy)

def describe_vpn_profiles(name=None, exact_match=True):
    """
    Show all VPN Profiles
    VPN Profiles are used by VPN Policy and define phase 1
    and phase 2 properties for VPN configurations
    
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('vpn_profile', name, exact_match)

def describe_external_gateways(name=None, exact_match=True):
    """ 
    Show External Gateways. External gateways are non-SMC
    managed endpoints used as a VPN peer
    
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('external_gateway', name, exact_match, 
                                klazz=ExternalGateway)

def describe_gateway_settings(name=None, exact_match=True):
    """
    Show Gateway Setting profiles 
    Gateway settings are applied at the engine level and
    define available crypto settings. Generally these settings
    do not need to be changed
    
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('gateway_settings', name, exact_match)

def describe_client_gateways(name=None, exact_match=True):
    """
    Client Gateway profile
    These are global configurations for the VPN Client which could be 
    used in VPN Policy
    
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('client_gateway', name, exact_match)

def describe_vpn_certificate_authority(name=None, exact_match=True):
    """
    Return VPN certificate authority used for internal gateway's
    
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    return generic_list_builder('vpn_certificate_authority', name, exact_match)
  
def generic_list_builder(typeof, name=None, exact_match=True, klazz=None):
    """
    Build the query to SMC based on parameters
    
    Each constructor that has a describe function must have two arguments, 
    name=None, meta=None. This is because some top level classes require name.
    If the resource does not have a top level api entry point, it will be
    referenced by the linked resource using meta only.
    
    Before the META data is returned, the dict values are encoded to utf-8 to
    support unicode chars.
    
    :param list name: Name of host object (optional)
    :param exact_match: Do exact match against name field (default True)
    :return: list :py:class:`smc.elements.element.SMCElement`
    """
    if not klazz:
        klazz = SMCElement
    result=[]
    if not name:
        lst = fetch_json_by_href(
                    session.cache.get_entry_href(typeof)).json
        if lst:
            for item in lst:
                result.append(klazz(name=item.get('name'), 
                                    meta=Meta(**item)))
    else: #Filter provided
        for element in name:
            for item in fetch_href_by_name(element, 
                                           filter_context=typeof, 
                                           exact_match=exact_match).json:
                result.append(klazz(name=item.get('name'),
                                    meta=Meta(**item)))
    return result