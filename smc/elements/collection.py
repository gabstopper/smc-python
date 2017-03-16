"""
Collection module allows for search queries against the SMC API to retrieve
element data.

Each describe function allows two possible (optional) parameters:

* name: search for (str or list of str)
* exact_match: True|False, whether to match exactly on name field

Each function returns a list of objects based on the specified element type. Most
elements will return a list of type :py:class:`smc.base.model.Element`. 
Element is a generic container class with helper methods for elements, such as 
:py:func:`smc.base.model.Element.describe` to view the elements raw contents.

.. seealso:: :py:class:`smc.base.model.Element`

All return element types (regardless of type) will have the following attributes as
metadata::

    href: href location of the element in SMC
    type: type of element
    name: name of element

Some additional generic search examples follow...
    ::
    
        import smc.elements.collection
    
To search for all host objects::

    for host in describe_host():
        print(host.name, host.href)
        
To search only for a host with name 'test'::

    for host in describe_host(name='test'):
        print(host.href)

To search for all hosts with 'test' in the name::

    for host in describe_host(name=['test'], exact_match=False):
        print(host)
        
It may be useful to do a wildcard search for an element type and view the entire
object info::

    for host in describe_network(name=['1.1.1.0'], exact_match=False):
        print(host.name, host.describe()) #returned Element

Modify a specific Element type by changing the name::

    for host in describe_host(name=['myhost']):
        if host:
            host.modify_attribute(name='mynewname')   
            
It is also possible to use wildcards when searching, without setting the 
exact_match=False flag. For example::

    for x in describe_host(name=['TOR*']):
        print(x.describe())
        
    for y in describe_host(name=['TOR'], exact_match=False):
        print(y)
        
Both will work, however the first option will only find items starting with TOR, whereas
the second option could find items such as 'DHCP Broadcast OriginaTOR', etc.

This module is generated dynamically based on SMC API entry points mounted at
the http://<smc>/api/elements node.

    :param str|list name: str name or list of names to retrieve
    :param boolean exact_match: True|False, whether to match specifically on name field
           or do a wildcard search (default: True)
    :return: list return type determined by describe method
"""
from smc import session
import smc.elements.network as network
import smc.base.model as element
import smc.core.engine as engine
from smc.api.common import fetch_json_by_href, fetch_href_by_name
from smc.base.model import lookup_class

def min_smc_version(arg_version):
    """
    Check the function supports the minimum version of SMC
    specified in the decorator. For example, @smc_version(6.1) 
    specifies to require version 6.1 or greater. This is meant for
    functions returning a list. If not right version, return []
    """
    def original_func(f):
        def wrapped_f(*args, **kwargs):
            if session.api_version >= arg_version:
                return f(*args, **kwargs)
            else:
                return []
        return wrapped_f
    return original_func

def describe_sub_ipv6_fw_policy(name=None, exact_match=True):
    """ 
    Describe sub_ipv6_fw_policy entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('sub_ipv6_fw_policy', name, exact_match)

def describe_ids_alert(name=None, exact_match=True):
    """ 
    Describe ids_alert entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('ids_alert', name, exact_match)

def describe_fw_alert(name=None, exact_match=True):
    """ 
    Describe fw_alert entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('fw_alert', name, exact_match)

def describe_application_not_specific_tag(name=None, exact_match=True):
    """ 
    Describe application_not_specific_tag entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('application_not_specific_tag', name, exact_match)

def describe_virtual_ips(name=None, exact_match=True):
    """ 
    Describe virtual_ips entries on the SMC
    
    :return: :py:class:`smc.core.engine.Engine` 
    """
    return generic_list_builder('virtual_ips', name, exact_match, engine.Engine)

'''
def describe_ssl_vpn_portal_pages(name=None, exact_match=True):
    """ 
    Describe ssl_vpn_portal_pages entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('ssl_vpn_portal_pages', name, exact_match)
'''

def describe_os_specific_tag(name=None, exact_match=True):
    """ 
    Describe os_specific_tag entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('os_specific_tag', name, exact_match)

def describe_eia_application_usage_group_tag(name=None, exact_match=True):
    """ 
    Describe eia_application_usage_group_tag entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('eia_application_usage_group_tag', name, exact_match)

def describe_external_bgp_peer(name=None, exact_match=True):
    """ 
    Describe external_bgp_peer entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('external_bgp_peer', name, exact_match)

def describe_local_cluster_cvi_alias(name=None, exact_match=True):
    """ 
    Describe local_cluster_cvi_alias entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('local_cluster_cvi_alias', name, exact_match,
                                network.Alias)

def describe_ssl_vpn_service_profile(name=None, exact_match=True):
    """ 
    Describe ssl_vpn_service_profile entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('ssl_vpn_service_profile', name, exact_match)

def describe_active_directory_server(name=None, exact_match=True):
    """ 
    Describe active_directory_server entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('active_directory_server', name, exact_match)

def describe_eia_golden_image_tag(name=None, exact_match=True):
    """ 
    Describe eia_golden_image_tag entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('eia_golden_image_tag', name, exact_match)

def describe_situation_tag(name=None, exact_match=True):
    """ 
    Describe situation_tag entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('situation_tag', name, exact_match)

def describe_client_gateway(name=None, exact_match=True):
    """ 
    Describe client_gateway entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('client_gateway', name, exact_match)

def describe_api_client(name=None, exact_match=True):
    """ 
    Describe api_client entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('api_client', name, exact_match)

def describe_tls_match_situation(name=None, exact_match=True):
    """ 
    Describe tls_match_situation entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('tls_match_situation', name, exact_match)

def describe_ssl_vpn_policy(name=None, exact_match=True):
    """ 
    Describe ssl_vpn_policy entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('ssl_vpn_policy', name, exact_match)

def describe_category_group_tag(name=None, exact_match=True):
    """ 
    Describe category_group_tag entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('category_group_tag', name, exact_match)

def describe_vpn_profile(name=None, exact_match=True):
    """ 
    Describe vpn_profile entries on the SMC
    
    :return: :py:class:`smc.vpn.elements.VPNProfile` 
    """
    return generic_list_builder('vpn_profile', name, exact_match)

def describe_appliance_information(name=None, exact_match=True):
    """ 
    Describe appliance_information entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('appliance_information', name, exact_match)

def describe_ipv6_access_list(name=None, exact_match=True):
    """ 
    Describe ipv6_access_list entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('ipv6_access_list', name, exact_match)

def describe_single_layer2(name=None, exact_match=True):
    """ 
    Describe single_layer2 entries on the SMC
    
    :return: :py:class:`smc.core.engine.Engine` 
    """
    return generic_list_builder('single_layer2', name, exact_match, engine.Engine)

def describe_community_access_list(name=None, exact_match=True):
    """ 
    Describe community_access_list entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('community_access_list', name, exact_match)


def describe_ei_executable(name=None, exact_match=True):
    """ 
    Describe ei_executable entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('ei_executable', name, exact_match)

def describe_application_risk_tag(name=None, exact_match=True):
    """ 
    Describe application_risk_tag entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('application_risk_tag', name, exact_match)

def describe_ssl_vpn_web_service(name=None, exact_match=True):
    """ 
    Describe ssl_vpn_web_service entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('ssl_vpn_web_service', name, exact_match)

def describe_gateway_settings(name=None, exact_match=True):
    """ 
    Describe gateway_settings entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('gateway_settings', name, exact_match)

def describe_authentication_service(name=None, exact_match=True):
    """ 
    Describe authentication_service entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('authentication_service', name, exact_match)

def describe_expression(name=None, exact_match=True):
    """ 
    Describe expression entries on the SMC
    
    :return: :py:class:`smc.elements.network.Expression` 
    """
    return generic_list_builder('expression', name, exact_match)

def describe_ei_application_situation(name=None, exact_match=True):
    """ 
    Describe ei_application_situation entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('ei_application_situation', name, exact_match)

def describe_os_not_specific_tag(name=None, exact_match=True):
    """ 
    Describe os_not_specific_tag entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('os_not_specific_tag', name, exact_match)

def describe_route_map(name=None, exact_match=True):
    """ 
    Describe route_map entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('route_map', name, exact_match)

def describe_vss_container(name=None, exact_match=True):
    """ 
    Describe vss_container entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('vss_container', name, exact_match)

def describe_local_cluster_ndi_for_ipv6_only_alias(name=None, exact_match=True):
    """ 
    Describe local_cluster_ndi_for_ipv6_only_alias entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('local_cluster_ndi_for_ipv6_only_alias', name, exact_match,
                                network.Alias)

def describe_internal_user_domain(name=None, exact_match=True):
    """ 
    Describe internal_user_domain entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('internal_user_domain', name, exact_match)

def describe_ipv6_prefix_list(name=None, exact_match=True):
    """ 
    Describe ipv6_prefix_list entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('ipv6_prefix_list', name, exact_match)

def describe_report_template(name=None, exact_match=True):
    """ 
    Describe report_template entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('report_template', name, exact_match)

def describe_external_ldap_user_group(name=None, exact_match=True):
    """ 
    Describe external_ldap_user_group entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('external_ldap_user_group', name, exact_match)

def describe_valid_vpn_dhcp_servers_alias(name=None, exact_match=True):
    """ 
    Describe valid_vpn_dhcp_servers_alias entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('valid_vpn_dhcp_servers_alias', name, exact_match,
                                network.Alias)

def describe_auth_server_user_domain(name=None, exact_match=True):
    """ 
    Describe auth_server_user_domain entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('auth_server_user_domain', name, exact_match)

def describe_sub_ipv4_fw_policy(name=None, exact_match=True):
    """ 
    Describe sub_ipv4_fw_policy entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('sub_ipv4_fw_policy', name, exact_match)

def describe_fw_template_policy(name=None, exact_match=True):
    """ 
    Describe fw_template_policy entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('fw_template_policy', name, exact_match)

def describe_ea_server(name=None, exact_match=True):
    """ 
    Describe ea_server entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('ea_server', name, exact_match)

def describe_extended_community_access_list(name=None, exact_match=True):
    """ 
    Describe extended_community_access_list entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('extended_community_access_list', name, exact_match)

def describe_atd_server(name=None, exact_match=True):
    """ 
    Describe atd_server entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('atd_server', name, exact_match)

def describe_interface_nic_x_ip_alias(name=None, exact_match=True):
    """ 
    Describe interface_nic_x_ip_alias entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('interface_nic_x_ip_alias', name, exact_match,
                                network.Alias)

def describe_user_response(name=None, exact_match=True):
    """ 
    Describe user_response entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('user_response', name, exact_match)

def describe_ssl_vpn_portal(name=None, exact_match=True):
    """ 
    Describe ssl_vpn_portal entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('ssl_vpn_portal', name, exact_match)

def describe_data_context(name=None, exact_match=True):
    """ 
    Describe data_context entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('data_context', name, exact_match)

def describe_eia_executable_user_tag(name=None, exact_match=True):
    """ 
    Describe eia_executable_user_tag entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('eia_executable_user_tag', name, exact_match)

def describe_interface_nic_x_net_alias(name=None, exact_match=True):
    """ 
    Describe interface_nic_x_net_alias entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('interface_nic_x_net_alias', name, exact_match,
                                network.Alias)

def describe_application_usage_group_tag(name=None, exact_match=True):
    """ 
    Describe application_usage_group_tag entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('application_usage_group_tag', name, exact_match)

def describe_report_design(name=None, exact_match=True):
    """ 
    Describe report_design entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('report_design', name, exact_match)

def describe_tcp_service(name=None, exact_match=True):
    """ 
    Describe tcp_service entries on the SMC
    
    :return: :py:class:`smc.elements.service.TCPService` 
    """
    return generic_list_builder('tcp_service', name, exact_match)

def describe_bgp_connection_profile(name=None, exact_match=True):
    """ 
    Describe bgp_connection_profile entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('bgp_connection_profile', name, exact_match)

def describe_rpc_service_group(name=None, exact_match=True):
    """ 
    Describe rpc_service_group entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('rpc_service_group', name, exact_match)

def describe_web_portal_user(name=None, exact_match=True):
    """ 
    Describe web_portal_user entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('web_portal_user', name, exact_match)

def describe_dns_server(name=None, exact_match=True):
    """ 
    Describe dns_server entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('dns_server', name, exact_match)

def describe_ea_user_domain(name=None, exact_match=True):
    """ 
    Describe ea_user_domain entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('ea_user_domain', name, exact_match)

def describe_inspection_situation(name=None, exact_match=True):
    """ 
    Describe inspection_situation entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('inspection_situation', name, exact_match)

def describe_auth_method(name=None, exact_match=True):
    """ 
    Describe auth_method entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('auth_method', name, exact_match)

def describe_local_cluster_dyn_interface_alias(name=None, exact_match=True):
    """ 
    Describe local_cluster_dyn_interface_alias entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('local_cluster_dyn_interface_alias', name, exact_match,
                                network.Alias)

def describe_application_situation(name=None, exact_match=True):
    """ 
    Describe application_situation entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('application_situation', name, exact_match)

def describe_single_fw(name=None, exact_match=True):
    """ 
    Describe single_fw entries on the SMC
    
    :return: :py:class:`smc.core.engine.Engine` 
    """
    return generic_list_builder('single_fw', name, exact_match, engine.Engine)

def describe_as_path_access_list(name=None, exact_match=True):
    """ 
    Describe as_path_access_list entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('as_path_access_list', name, exact_match)

def describe_tacacs_server(name=None, exact_match=True):
    """ 
    Describe tacacs_server entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('tacacs_server', name, exact_match)

def describe_correlation_situation(name=None, exact_match=True):
    """ 
    Describe correlation_situation entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('correlation_situation', name, exact_match)

def describe_valid_vpn_dhcp_enabled_interface_addresses_alias(name=None, exact_match=True):
    """ 
    Describe valid_vpn_dhcp_enabled_interface_addresses_alias entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('valid_vpn_dhcp_enabled_interface_addresses_alias', name, 
                                exact_match, network.Alias)

def describe_qos_class(name=None, exact_match=True):
    """ 
    Describe qos_class entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('qos_class', name, exact_match)

def describe_dhcp_server(name=None, exact_match=True):
    """ 
    Describe dhcp_server entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('dhcp_server', name, exact_match)

def describe_netlink(name=None, exact_match=True):
    """ 
    Describe netlink entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('netlink', name, exact_match)

def describe_application_group_tag(name=None, exact_match=True):
    """ 
    Describe application_group_tag entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('application_group_tag', name, exact_match)

def describe_tls_certificate_request(name=None, exact_match=True):
    """ 
    Describe tls_certificate_request entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('tls_certificate_request', name, exact_match)

def describe_sub_ipv4_layer2_policy(name=None, exact_match=True):
    """ 
    Describe sub_ipv4_layer2_policy entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('sub_ipv4_layer2_policy', name, exact_match)

def describe_auth_server_user_group(name=None, exact_match=True):
    """ 
    Describe auth_server_user_group entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('auth_server_user_group', name, exact_match)

def describe_user_identification_agent(name=None, exact_match=True):
    """ 
    Describe user_identification_agent entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('user_identification_agent', name, exact_match)

def describe_alert(name=None, exact_match=True):
    """ 
    Describe alert entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('alert', name, exact_match)

def describe_mac_address(name=None, exact_match=True):
    """ 
    Describe mac_address entries on the SMC
    
    :return: :py:class:`smc.elements.network.MacAddress` 
    """
    return generic_list_builder('mac_address', name, exact_match)

def describe_tcp_service_group(name=None, exact_match=True):
    """ 
    Describe tcp_service_group entries on the SMC
    
    :return: :py:class:`smc.elements.group.TCPServiceGroup` 
    """
    return generic_list_builder('tcp_service_group', name, exact_match)

def describe_report_file(name=None, exact_match=True):
    """ 
    Describe report_file entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('report_file', name, exact_match)

def describe_ssl_vpn_sso_domain(name=None, exact_match=True):
    """ 
    Describe ssl_vpn_sso_domain entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('ssl_vpn_sso_domain', name, exact_match)

#def describe_vulnerability_tag(name=None, exact_match=True):
#    """ 
#    Describe vulnerability_type entries on the SMC
#    
#    :return: :py:class:`smc.base.model.Element` 
#    """
#    return generic_list_builder('vulnerability_type', name, exact_match)

def describe_icmp_service(name=None, exact_match=True):
    """ 
    Describe icmp_service entries on the SMC
    
    :return: :py:class:`smc.elements.service.ICMPService` 
    """
    return generic_list_builder('icmp_service', name, exact_match)

def describe_cis_server(name=None, exact_match=True):
    """ 
    Describe cis_server entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('cis_server', name, exact_match)

def describe_dynamic_interface_alias(name=None, exact_match=True):
    """ 
    Describe dynamic_interface_alias entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('dynamic_interface_alias', name, exact_match,
                                network.Alias)

def describe_service_group(name=None, exact_match=True):
    """ 
    Describe service_group entries on the SMC
    
    :return: :py:class:`smc.elements.group.ServiceGroup` 
    """
    return generic_list_builder('service_group', name, exact_match)

def describe_local_cluster_alias(name=None, exact_match=True):
    """ 
    Describe local_cluster_alias entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('local_cluster_alias', name, exact_match,
                                network.Alias)

def describe_interface_zone(name=None, exact_match=True):
    """ 
    Describe interface_zone entries on the SMC
    
    :return: :py:class:`smc.elements.network.Zone` 
    """
    return generic_list_builder('interface_zone', name, exact_match)

def describe_internal_user(name=None, exact_match=True):
    """ 
    Describe internal_user entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('internal_user', name, exact_match)

def describe_url_category_risk_tag(name=None, exact_match=True):
    """ 
    Describe url_category_risk_tag entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('url_category_risk_tag', name, exact_match)

def describe_udp_service_group(name=None, exact_match=True):
    """ 
    Describe udp_service_group entries on the SMC
    
    :return: :py:class:`smc.elements.group.UDPServiceGroup` 
    """
    return generic_list_builder('udp_service_group', name, exact_match)

def describe_vpn(name=None, exact_match=True):
    """ 
    Describe vpn entries on the SMC
    
    :return: :py:class:`smc.vpn.policy.VPNPolicy` 
    """
    return generic_list_builder('vpn', name, exact_match)

def describe_valid_dhcp_servers_alias(name=None, exact_match=True):
    """ 
    Describe valid_dhcp_servers_alias entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('valid_dhcp_servers_alias', name, exact_match,
                                network.Alias)

def describe_ospfv2_area(name=None, exact_match=True):
    """ 
    Describe ospfv2_area entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('ospfv2_area', name, exact_match)

def describe_address_range(name=None, exact_match=True):
    """ 
    Describe address_range entries on the SMC
    
    :return: :py:class:`smc.elements.network.AddressRange` 
    """
    return generic_list_builder('address_range', name, exact_match)

def describe_eia_application_category_tag(name=None, exact_match=True):
    """ 
    Describe eia_application_category_tag entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('eia_application_category_tag', name, exact_match)

def describe_tls_signing_certificate_authority(name=None, exact_match=True):
    """ 
    Describe tls_signing_certificate_authority entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('tls_signing_certificate_authority', name, exact_match)

def describe_local_cluster_ndi_for_hb_alias(name=None, exact_match=True):
    """ 
    Describe local_cluster_ndi_for_hb_alias entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('local_cluster_ndi_for_hb_alias', name, exact_match,
                                network.Alias)

def describe_fw_cluster(name=None, exact_match=True):
    """ 
    Describe fw_cluster entries on the SMC
    
    :return: :py:class:`smc.core.engine.Engine` 
    """
    return generic_list_builder('fw_cluster', name, exact_match, engine.Engine)

def describe_domain_name(name=None, exact_match=True):
    """ 
    Describe domain_name entries on the SMC
    
    :return: :py:class:`smc.elements.network.DomainName` 
    """
    return generic_list_builder('domain_name', name, exact_match)

def describe_bgp_profile(name=None, exact_match=True):
    """ 
    Describe bgp_profile entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('bgp_profile', name, exact_match)

def describe_rpc_service(name=None, exact_match=True):
    """ 
    Describe rpc_service entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('rpc_service', name, exact_match)

def describe_web_authentication_page(name=None, exact_match=True):
    """ 
    Describe web_authentication_page entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('web_authentication_page', name, exact_match)

def describe_ips_template_policy(name=None, exact_match=True):
    """ 
    Describe ips_template_policy entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('ips_template_policy', name, exact_match)

def describe_tls_profile(name=None, exact_match=True):
    """ 
    Describe tls_profile entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('tls_profile', name, exact_match)

def describe_tools_profile(name=None, exact_match=True):
    """ 
    Describe tools_profile entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('tools_profile', name, exact_match)

def describe_external_gateway(name=None, exact_match=True):
    """ 
    Describe external_gateway entries on the SMC
    
    :return: :py:class:`smc.vpn.elements.ExternalGateway` 
    """
    return generic_list_builder('external_gateway', name, exact_match)

def describe_epo(name=None, exact_match=True):
    """ 
    Describe epo entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('epo', name, exact_match)

def describe_logging_profile(name=None, exact_match=True):
    """ 
    Describe logging_profile entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('logging_profile', name, exact_match)

def describe_outbound_multilink(name=None, exact_match=True):
    """ 
    Describe outbound_multilink entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('outbound_multilink', name, exact_match)

def describe_ip_access_list(name=None, exact_match=True):
    """ 
    Describe ip_access_list entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('ip_access_list', name, exact_match)

def describe_log_server(name=None, exact_match=True):
    """ 
    Describe log_server entries on the SMC
    
    :return: :py:class:`smc.elements.servers.LogServer` 
    """
    return generic_list_builder('log_server', name, exact_match)

def describe_icmp_ipv6_service(name=None, exact_match=True):
    """ 
    Describe icmp_ipv6_service entries on the SMC
    
    :return: :py:class:`smc.elements.service.ICMPIPv6Service` 
    """
    return generic_list_builder('icmp_ipv6_service', name, exact_match)

def describe_virtual_fw(name=None, exact_match=True):
    """ 
    Describe virtual_fw entries on the SMC
    
    :return: :py:class:`smc.core.engine.Engine` 
    """
    return generic_list_builder('virtual_fw', name, exact_match, engine.Engine)

def describe_filter_expression_tag(name=None, exact_match=True):
    """ 
    Describe filter_expression_tag entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('filter_expression_tag', name, exact_match)

def describe_match_expression(name=None, exact_match=True):
    """ 
    Describe match_expression entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('match_expression', name, exact_match)

def describe_mgt_server(name=None, exact_match=True):
    """ 
    Describe mgt_server entries on the SMC
    
    :return: :py:class:`smc.elements.servers.ManagementServer` 
    """
    return generic_list_builder('mgt_server', name, exact_match)

def describe_probing_profile(name=None, exact_match=True):
    """ 
    Describe probing_profile entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('probing_profile', name, exact_match)

def describe_ip_prefix_list(name=None, exact_match=True):
    """ 
    Describe ip_prefix_list entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('ip_prefix_list', name, exact_match)

def describe_valid_vpn_dhcp_address_pools_alias(name=None, exact_match=True):
    """ 
    Describe valid_vpn_dhcp_address_pools_alias entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('valid_vpn_dhcp_address_pools_alias', name, exact_match,
                                network.Alias)

def describe_tls_cryptography_suite_set(name=None, exact_match=True):
    """ 
    Describe tls_cryptography_suite_set entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('tls_cryptography_suite_set', name, exact_match)

def describe_logical_interface(name=None, exact_match=True):
    """ 
    Describe logical_interface entries on the SMC
    
    :return: :py:class:`smc.elements.other.LogicalInterface` 
    """
    return generic_list_builder('logical_interface', name, exact_match)

def describe_situation_group_tag(name=None, exact_match=True):
    """ 
    Describe situation_group_tag entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('situation_group_tag', name, exact_match)

def describe_log_servers_alias(name=None, exact_match=True):
    """ 
    Describe log_servers_alias entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('log_servers_alias', name, exact_match,
                                network.Alias)

def describe_server_pool(name=None, exact_match=True):
    """ 
    Describe server_pool entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('server_pool', name, exact_match)

def describe_ea_method(name=None, exact_match=True):
    """ 
    Describe ea_method entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('ea_method', name, exact_match)

def describe_vulnerability_impact_tag(name=None, exact_match=True):
    """ 
    Describe vulnerability_impact_tag entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('vulnerability_impact_tag', name, exact_match)

def describe_trusted_ca_tag(name=None, exact_match=True):
    """ 
    Describe trusted_ca_tag entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('trusted_ca_tag', name, exact_match)

def describe_ospfv2_key_chain(name=None, exact_match=True):
    """ 
    Describe ospfv2_key_chain entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('ospfv2_key_chain', name, exact_match)

def describe_local_cluster_ndi_only_alias(name=None, exact_match=True):
    """ 
    Describe local_cluster_ndi_only_alias entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('local_cluster_ndi_only_alias', name, exact_match,
                                network.Alias)

def describe_radius_server(name=None, exact_match=True):
    """ 
    Describe radius_server entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('radius_server', name, exact_match)

def describe_web_portal_server(name=None, exact_match=True):
    """ 
    Describe web_portal_server entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('web_portal_server', name, exact_match)

def describe_vpn_certificate_authority(name=None, exact_match=True):
    """ 
    Describe vpn_certificate_authority entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('vpn_certificate_authority', name, exact_match)

def describe_ospfv2_profile(name=None, exact_match=True):
    """ 
    Describe ospfv2_profile entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('ospfv2_profile', name, exact_match)

def describe_access_control_list(name=None, exact_match=True):
    """ 
    Describe access_control_list entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('access_control_list', name, exact_match)

def describe_url_situation(name=None, exact_match=True):
    """ 
    Describe url_situation entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('url_situation', name, exact_match)

def describe_tls_server_credentials(name=None, exact_match=True):
    """ 
    Describe tls_server_credentials entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('tls_server_credentials', name, exact_match)

def describe_application_specific_tag(name=None, exact_match=True):
    """ 
    Describe application_specific_tag entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('application_specific_tag', name, exact_match)

def describe_icmp_service_group(name=None, exact_match=True):
    """ 
    Describe icmp_service_group entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('icmp_service_group', name, exact_match)

def describe_external_ldap_user(name=None, exact_match=True):
    """ 
    Describe external_ldap_user entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('external_ldap_user', name, exact_match)

def describe_ospfv2_interface_settings(name=None, exact_match=True):
    """ 
    Describe ospfv2_interface_settings entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('ospfv2_interface_settings', name, exact_match)

def describe_query_data_filter(name=None, exact_match=True):
    """ 
    Describe query_data_filter entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('query_data_filter', name, exact_match)

def describe_ip_service(name=None, exact_match=True):
    """ 
    Describe ip_service entries on the SMC
    
    :return: :py:class:`smc.elements.service.IPService` 
    """
    return generic_list_builder('ip_service', name, exact_match)

def describe_file_filtering_compatibility_tag(name=None, exact_match=True):
    """ 
    Describe file_filtering_compatibility_tag entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('file_filtering_compatibility_tag', name, exact_match)

def describe_filter_expression(name=None, exact_match=True):
    """ 
    Describe filter_expression entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('filter_expression', name, exact_match)

def describe_application_tag(name=None, exact_match=True):
    """ 
    Describe application_tag entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('application_tag', name, exact_match)

def describe_qos_policy(name=None, exact_match=True):
    """ 
    Describe qos_policy entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('qos_policy', name, exact_match)

def describe_layer2_template_policy(name=None, exact_match=True):
    """ 
    Describe layer2_template_policy entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('layer2_template_policy', name, exact_match)

def describe_external_ldap_user_domain(name=None, exact_match=True):
    """ 
    Describe external_ldap_user_domain entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('external_ldap_user_domain', name, exact_match)

def describe_protocol(name=None, exact_match=True):
    """ 
    Describe protocol entries on the SMC
    
    :return: :py:class:`smc.elements.service.Protocol` 
    """
    return generic_list_builder('protocol', name, exact_match)

def describe_router(name=None, exact_match=True):
    """ 
    Describe router entries on the SMC
    
    :return: :py:class:`smc.elements.network.Router` 
    """
    return generic_list_builder('router', name, exact_match)

def describe_sub_ipv4_ips_policy(name=None, exact_match=True):
    """ 
    Describe sub_ipv4_ips_policy entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('sub_ipv4_ips_policy', name, exact_match)

def describe_default_nat_address_alias(name=None, exact_match=True):
    """ 
    Describe default_nat_address_alias entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('default_nat_address_alias', name, exact_match,
                                network.Alias)

def describe_admin_domain(name=None, exact_match=True):
    """ 
    Describe admin_domain entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('admin_domain', name, exact_match)

def describe_file_type(name=None, exact_match=True):
    """ 
    Describe file_type entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('file_type', name, exact_match)

def describe_host(name=None, exact_match=True):
    """ 
    Describe host entries on the SMC
    
    :return: :py:class:`smc.elements.network.Host` 
    """
    return generic_list_builder('host', name, exact_match)

def describe_mlc_user_agent(name=None, exact_match=True):
    """ 
    Describe mlc_user_agent entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('mlc_user_agent', name, exact_match)

def describe_trusted_update_certificate(name=None, exact_match=True):
    """ 
    Describe trusted_update_certificate entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('trusted_update_certificate', name, exact_match)

def describe_auth_server(name=None, exact_match=True):
    """ 
    Describe auth_server entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('auth_server', name, exact_match)

def describe_dynamic_netlink(name=None, exact_match=True):
    """ 
    Describe dynamic_netlink entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('dynamic_netlink', name, exact_match)

def describe_group(name=None, exact_match=True):
    """ 
    Describe group entries on the SMC
    
    :return: :py:class:`smc.elements.group.Group` 
    """
    return generic_list_builder('group', name, exact_match)

def describe_dhcp_enabled_interface_addresses_alias(name=None, exact_match=True):
    """ 
    Describe dhcp_enabled_interface_addresses_alias entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('dhcp_enabled_interface_addresses_alias', name, exact_match,
                                network.Alias)

def describe_vss_context(name=None, exact_match=True):
    """ 
    Describe vss_context entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('vss_context', name, exact_match)

def describe_hardware_tag(name=None, exact_match=True):
    """ 
    Describe hardware_tag entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('hardware_tag', name, exact_match)

def describe_fw_policy(name=None, exact_match=True):
    """ 
    Describe fw_policy entries on the SMC
    
    :return: :py:class:`smc.elements.policy.FirewallPolicy` 
    """
    return generic_list_builder('fw_policy', name, exact_match)

def describe_ips_policy(name=None, exact_match=True):
    """ 
    Describe ips_policy entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('ips_policy', name, exact_match)

def describe_smtp_server(name=None, exact_match=True):
    """ 
    Describe smtp_server entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('smtp_server', name, exact_match)

def describe_category_tag(name=None, exact_match=True):
    """ 
    Describe category_tag entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('category_tag', name, exact_match)

def describe_layer2_cluster(name=None, exact_match=True):
    """ 
    Describe layer2_cluster entries on the SMC
    
    :return: :py:class:`smc.core.engine.Engine` 
    """
    return generic_list_builder('layer2_cluster', name, exact_match, engine.Engine)

def describe_bgp_peering(name=None, exact_match=True):
    """ 
    Describe bgp_peering entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('bgp_peering', name, exact_match)

def describe_ethernet_service(name=None, exact_match=True):
    """ 
    Describe ethernet_service entries on the SMC
    
    :return: :py:class:`smc.elements.service.EthernetService` 
    """
    return generic_list_builder('ethernet_service', name, exact_match)

def describe_admin_user(name=None, exact_match=True):
    """ 
    Describe admin_user entries on the SMC
    
    :return: :py:class:`smc.elements.user.AdminUser` 
    """
    return generic_list_builder('admin_user', name, exact_match)

def describe_local_cluster_ndi_for_mgt_alias(name=None, exact_match=True):
    """ 
    Describe local_cluster_ndi_for_mgt_alias entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('local_cluster_ndi_for_mgt_alias', name, exact_match,
                                network.Alias)

def describe_mgt_servers_alias(name=None, exact_match=True):
    """ 
    Describe mgt_servers_alias entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('mgt_servers_alias', name, exact_match,
                                network.Alias)

def describe_application_usage_tag(name=None, exact_match=True):
    """ 
    Describe application_usage_tag entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('application_usage_tag', name, exact_match)

def describe_layer2_policy(name=None, exact_match=True):
    """ 
    Describe layer2_policy entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('layer2_policy', name, exact_match)

def describe_single_ips(name=None, exact_match=True):
    """ 
    Describe single_ips entries on the SMC
    
    :return: :py:class:`smc.core.engine.Engine` 
    """
    return generic_list_builder('single_ips', name, exact_match, engine.Engine)

def describe_auth_server_user(name=None, exact_match=True):
    """ 
    Describe auth_server_user entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('auth_server_user', name, exact_match)

def describe_file_filtering_policy(name=None, exact_match=True):
    """ 
    Describe file_filtering_policy entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('file_filtering_policy', name, exact_match)

def describe_udp_service(name=None, exact_match=True):
    """ 
    Describe udp_service entries on the SMC
    
    :return: :py:class:`smc.elements.service.UDPService` 
    """
    return generic_list_builder('udp_service', name, exact_match)

def describe_network(name=None, exact_match=True):
    """ 
    Describe network entries on the SMC
    
    :return: :py:class:`smc.elements.network.Network` 
    """
    return generic_list_builder('network', name, exact_match)

def describe_ips_cluster(name=None, exact_match=True):
    """ 
    Describe ips_cluster entries on the SMC
    
    :return: :py:class:`smc.core.engine.Engine` 
    """
    return generic_list_builder('ips_cluster', name, exact_match, engine.Engine)

def describe_ldap_server(name=None, exact_match=True):
    """ 
    Describe ldap_server entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('ldap_server', name, exact_match)

def describe_master_engine(name=None, exact_match=True):
    """ 
    Describe master_engine entries on the SMC
    
    :return: :py:class:`smc.core.engine.Engine` 
    """
    return generic_list_builder('master_engine', name, exact_match, engine.Engine)

def describe_tls_certificate_authority(name=None, exact_match=True):
    """ 
    Describe tls_certificate_authority entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('tls_certificate_authority', name, exact_match)

def describe_appliance_switch_module(name=None, exact_match=True):
    """ 
    Describe appliance_switch_module entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('appliance_switch_module', name, exact_match)

def describe_alias(name=None, exact_match=True):
    """ 
    Describe alias entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('alias', name, exact_match, network.Alias)

def describe_ip_service_group(name=None, exact_match=True):
    """ 
    Describe ip_service_group entries on the SMC
    
    :return: :py:class:`smc.elements.group.IPServiceGroup` 
    """
    return generic_list_builder('ip_service_group', name, exact_match)

def describe_http_proxy(name=None, exact_match=True):
    """ 
    Describe http_proxy entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('http_proxy', name, exact_match)

def describe_auth_servers_alias(name=None, exact_match=True):
    """ 
    Describe auth_servers_alias entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('auth_servers_alias', name, exact_match,
                                network.Alias)

def describe_virtual_fwlayer2(name=None, exact_match=True):
    """ 
    Describe virtual_fwlayer2 entries on the SMC
    
    :return: :py:class:`smc.core.engine.Engine` 
    """
    return generic_list_builder('virtual_fwlayer2', name, exact_match, engine.Engine)

def describe_ethernet_service_group(name=None, exact_match=True):
    """ 
    Describe ethernet_service_group entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('ethernet_service_group', name, exact_match)

def describe_eia_user_domain(name=None, exact_match=True):
    """ 
    Describe eia_user_domain entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('eia_user_domain', name, exact_match)

def describe_gateway_profile(name=None, exact_match=True):
    """ 
    Describe gateway_profile entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('gateway_profile', name, exact_match)

def describe_inspection_template_policy(name=None, exact_match=True):
    """ 
    Describe inspection_template_policy entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('inspection_template_policy', name, exact_match)

def describe_ospfv2_domain_settings(name=None, exact_match=True):
    """ 
    Describe ospfv2_domain_settings entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('ospfv2_domain_settings', name, exact_match)

def describe_autonomous_system(name=None, exact_match=True):
    """ 
    Describe autonomous_system entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('autonomous_system', name, exact_match)

def describe_internal_user_group(name=None, exact_match=True):
    """ 
    Describe internal_user_group entries on the SMC
    
    :return: :py:class:`smc.base.model.Element` 
    """
    return generic_list_builder('internal_user_group', name, exact_match)

@min_smc_version(6.1)
def describe_sidewinder_tag(name=None, exact_match=True):
    """ 
    Describe sidewinder_tag entries on the SMC
    
    ..note :: Requires SMC API version 6.1
    
    :return: :py:class:`smc.base.model.Element`
    """
    return generic_list_builder('sidewinder_tag', name, exact_match)

@min_smc_version(6.1)
def describe_ip_list(name=None, exact_match=True):
    """ 
    Describe ip_list entries on the SMC
    
    ..note :: Requires SMC API version >= 6.1 
    
    :return: :py:class:`smc.elements.network.IPList` 
    """
    return generic_list_builder('ip_list', name, exact_match)

@min_smc_version(6.1)
def describe_ip_list_group(name=None, exact_match=True):
    """ 
    Describe ip_list_group entries on the SMC
    
    ..note :: Requires SMC API version 6.1
    
    :return: :py:class:`smc.base.model.Element`
    """
    return generic_list_builder('ip_list_group', name, exact_match)

@min_smc_version(6.1)    
def describe_url_list_application(name=None, exact_match=True):
    """ 
    Describe url_list_application entries on the SMC
    
    ..note :: Requires SMC API version >= 6.1 
    
    :return: :py:class:`smc.elements.network.URLListApplication` 
    """
    return generic_list_builder('url_list_application', name, exact_match)

@min_smc_version(6.1)
def describe_country(name=None, exact_match=True):
    """ 
    Describe country entries on the SMC
    
    ..note :: Requires SMC API version 6.1
    
    :return: :py:class:`smc.base.model.Element`
    """
    return generic_list_builder('country', name, exact_match)

@min_smc_version(6.1)
def describe_sidewinder_logging_profile(name=None, exact_match=True):
    """ 
    Describe sidewinder_logging_profile entries on the SMC
    
    ..note :: Requires SMC API version 6.1
    
    :return: :py:class:`smc.base.model.Element`
    """
    return generic_list_builder('sidewinder_logging_profile', name, exact_match)

@min_smc_version(6.1)    
def describe_url_category(name=None, exact_match=True):
    """ 
    Describe url_category entries on the SMC
    
    ..note :: Requires SMC API version 6.1
    
    :return: :py:class:`smc.base.model.Element`
    """
    return generic_list_builder('url_category', name, exact_match)

@min_smc_version(6.1)  
def describe_sidewinder_logging_profile_settings(name=None, exact_match=True):
    """ 
    Describe sidewinder_logging_profile_settings entries on the SMC
    
    ..note :: Requires SMC API version 6.1
    
    :return: :py:class:`smc.base.model.Element`
    """
    return generic_list_builder('sidewinder_logging_profile_settings', name, exact_match)

@min_smc_version(6.1)    
def describe_security_group(name=None, exact_match=True):
    """ 
    Describe security_group entries on the SMC
    
    ..note :: Requires SMC API version 6.1
    
    :return: :py:class:`smc.base.model.Element`
    """
    return generic_list_builder('security_group', name, exact_match)

@min_smc_version(6.1)
def describe_location(name=None, exact_match=True):
    """ 
    Describe location entries on the SMC
    
    ..note :: Requires SMC API version >= 6.1 
    
    :return: :py:class:`smc.elements.other.Location` 
    """
    return generic_list_builder('location', name, exact_match)

@min_smc_version(6.1)   
def describe_threatseeker_server(name=None, exact_match=True):
    """ 
    Describe threatseeker_server entries on the SMC
    
    ..note :: Requires SMC API version 6.1
    
    :return: :py:class:`smc.base.model.Element`
    """
    return generic_list_builder('threatseeker_server', name, exact_match)

@min_smc_version(6.1)    
def describe_url_category_group(name=None, exact_match=True):
    """ 
    Describe url_category_group entries on the SMC
    
    ..note :: Requires SMC API version 6.1
    
    :return: :py:class:`smc.base.model.Element`
    """
    return generic_list_builder('url_category_group', name, exact_match)

@min_smc_version(6.1)   
def describe_ip_country_group(name=None, exact_match=True):
    """ 
    Describe ip_country_group entries on the SMC
    
    ..note :: Requires SMC API version 6.1
    
    :return: :py:class:`smc.base.model.Element`
    """
    return generic_list_builder('ip_country_group', name, exact_match)

@min_smc_version(6.1)    
def describe_known_host(name=None, exact_match=True):
    """ 
    Describe known_host entries on the SMC
    
    ..note :: Requires SMC API version 6.1
    
    :return: :py:class:`smc.base.model.Element`
    """
    return generic_list_builder('known_host', name, exact_match)

@min_smc_version(6.1)    
def describe_ssh_profile(name=None, exact_match=True):
    """ 
    Describe ssh_profile entries on the SMC
    
    ..note :: Requires SMC API version 6.1
    
    :return: :py:class:`smc.base.model.Element`
    """
    return generic_list_builder('ssh_profile', name, exact_match)

@min_smc_version(6.1)    
def describe_known_host_list(name=None, exact_match=True):
    """ 
    Describe known_host_list entries on the SMC
    
    ..note :: Requires SMC API version 6.1
    
    :return: :py:class:`smc.base.model.Element`
    """
    return generic_list_builder('known_host_list', name, exact_match)

@min_smc_version(6.1) 
def describe_engines(name=None, exact_match=True):
    """
    Display all engines, regardless of engine type
    
    ..note :: Requires SMC API version 6.1
    
    :return: :py:class:`smc.core.engine.Engine`
    """
    name = name if name else '*'
    return generic_list_builder('engine_clusters', name, exact_match, engine.Engine)

@min_smc_version(6.1) 
def describe_layer2_engines(name=None, exact_match=True):
    """
    Display all layer 2 engines
    
    ..note :: Requires SMC API version 6.1
    
    :return: :py:class:`smc.core.engine.Engine`
    """
    name = name if name else '*'
    return generic_list_builder('layer2_clusters', name, exact_match, engine.Engine)

@min_smc_version(6.1) 
def describe_layer3_engines(name=None, exact_match=True):
    """
    Display all layer 3 engines
    
    ..note :: Requires SMC API version 6.1
    
    :return: :py:class:`smc.core.engine.Engine`
    """
    name = name if name else '*'
    return generic_list_builder('fw_clusters', name, exact_match, engine.Engine)

@min_smc_version(6.1) 
def describe_ips_engines(name=None, exact_match=True):
    """
    Display all IPS engines
    
    ..note :: Requires SMC API version 6.1
    
    :return: :py:class:`smc.core.engine.Engine`
    """
    name = name if name else '*'
    return generic_list_builder('ips_clusters', name, exact_match, engine.Engine)
                               
def generic_list_builder(typeof, name=None, exact_match=True, klazz=None):
    """
    Build the query to SMC based on parameters
    
    The describe function uses the Element interface and expects that the
    class takes two arguments, name and meta.

    If the resource does not have a top level api entry point, it will be
    referenced by the linked resource using meta only.
    
    :param list name: Name of host object (optional)
    :param exact_match: Do exact match against name field (default True)
    :return: list :py:class:`smc.base.model.Element`
    """
    if klazz is None:
        klazz = lookup_class(typeof)
    result = []
    if not name:
        lst = fetch_json_by_href(
                    session.cache.get_entry_href(typeof)).json
        if lst:
            for item in lst:
                result.append(klazz(name=item.get('name'),
                                    meta=element.Meta(**item)))
    else: #Filter provided
        if isinstance(name, str): # By str
            for item in fetch_href_by_name(name, filter_context=typeof,
                                           exact_match=exact_match).json:
                result.append(klazz(name=item.get('name'),
                                    meta=element.Meta(**item)))
        else: # By list
            for elements in name:
                for item in fetch_href_by_name(elements, 
                                               filter_context=typeof, 
                                               exact_match=exact_match).json:
                    result.append(klazz(name=item.get('name'),
                                        meta=element.Meta(**item)))
    return result
