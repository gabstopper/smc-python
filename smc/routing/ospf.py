"""
Dynamic Routing can be enabled on devices configured in FW/VPN mode.
Configuring dynamic routing consists of enabling the routing protocol
on the engine and adding the routing elements on the interfaces at the
engine routing level.
Adding static routes can be done directly against the engine by using::

    engine = Engine('myengine).load()
    engine.add_route(gw, network)
    
For adding OSPF configurations, several steps are required:

* Enable OSPF on the engine and specific the OSPF Profile
* Create or locate an existing OSPFArea to be used
* Modify the routing interface and add and the OSPFArea

To use default profiles, these can be obtained by describe_xx methods::

    for profile in describe_ospfv2_profile():
        print profile.name, profile.href
        
    for area in describe_ospfv2_area():
        print area.name, area.href

General Rules:

OSPFProfile is applied at the engine and has an OSPFDomainSetting reference:
    
    *OSPFProfile --> OSPFDomainSetting*
    
OSPFArea is applied to an engine routing node and has an OSPFInterfaceSetting
reference:
    *OSPFArea --> OSPFInterfaceSetting*

OSPFArea with message-digest authentication also has a OSPFKeyChain reference:
    
    *OSPFArea --> OSPFKeyChain & OSPFInterfaceSetting*

Layer3Firewall and Layer3VirtualEngine types can enable OSPF during creation.

.. seealso:: :py:class:`smc.core.engines.Layer3Firewall` and 
             :py:class:`smc.core.engines.Layer3VirtualEngine`

Example of enabling OSPF on an existing engine::

    engine.modify_attribute(dynamic_routing={
                    'ospfv2':{
                        'enabled': True,
                        'ospfv2_profile_ref': 
                        'http://172.18.1.150:8082/6.1/elements/ospfv2_profile/2'}})
                    
Disable OSPF on an engine::
    
    engine.modify_attribute(dynamic_routing={'ospfv2':{'enabled': False}})

See each class definition for more examples on creating the element types.

.. note:: Not all advanced settings are implemented   
"""
import smc.actions.search as search
from smc.api.common import SMCRequest
from smc.elements.element import ElementLocator

class OSPFArea(object):
    """
    OSPFArea is an element that identifies general settings for an
    OSPF configuration applied to a routing node. The OSPFArea has a 
    reference to an OSPFInterfaceSetting and is required when
    creating.
    
    Create an OSPFArea and use a custom OSPFInterfaceSetting element::
    
        ospf = OSPFInterfaceSetting('myospf')
        OSPFArea.create(name='customOSPFArea', 
                        interface_settings_ref=ospf.href, 
                        area_id=3)
    
    Adding ospf_virtual_links_endpoints (interface_settings_ref is optional)::
    
        OSPFArea.create(
            name='ospf', 
            interface_settings_ref=intf, 
            area_id=3,
            ospfv2_virtual_links_endpoints_container=
                [{'interface_settings_ref': 
                    'http://172.18.1.150:8082/6.1/elements/ospfv2_interface_settings/8',
                  'router_id_endpoint_A': '192.168.1.1',
                  'router_id_endpoint_B': '192.168.1.254'},
                 {'router_id_endpoint_A': '172.18.1.254',
                  'router_id_endpoint_B': '172.18.1.200'}])

    When using ABR substitute rules, there are 3 actions, 'aggregate', 'not_advertise'
    and 'substitute_with'. All references required are of type 
    :py:class:`smc.elements.element.Network`. These elements can either be created or
    retrieved using describe_xx methods, or by getting the resource directly.
    
    Example of creating an OSPF area and using ABR settings::
    
        OSPFArea.create(
                name='area_with_abr', 
                interface_settings_ref=intf, 
                area_id=1, 
                ospf_abr_substitute_container=[
                    {'subnet_ref': 'http://172.18.1.150:8082/6.1/elements/network/143',
                     'substitute_ref': 'http://172.18.1.150:8082/6.1/elements/network/1547',
                     'substitute_type': 'substitute_with'},
                    {'subnet_ref': 'http://172.18.1.150:8082/6.1/elements/network/979',
                     'substitute_type': 'aggregate'}])
    """
    typeof = 'ospfv2_area'
    href = ElementLocator()
    
    def __init__(self, name, meta=None):
        self._name = name
        self.meta = meta

    @property
    def name(self):
        return self._name

    @classmethod
    def create(cls, name, interface_settings_ref, area_id=1, 
               area_default_cost=100, area_type='normal',
               outbound_filters_ref=None, inbound_filters_ref=None, 
               shortcut_capable_area=False,
               ospfv2_virtual_links_endpoints_container=None,
               ospf_abr_substitute_container=None):
        """
        Create a new OSPF Area
        
        :param str name: name of OSPFArea configuration
        :param str interface_settings_ref: reference to :py:class:`.OSPFInterfaceSetting`
        :param str name: area id
        :param int area_default_cost: default cost for this area
        :param str area_type: normal|stub|not_so_stubby|totally_stubby|
               totally_not_so_stubby
        :param str outbound_filters_ref: reference to 
               :py:class:`~smc.routing.access_list.IPAccessList`
        :param str inbound_filters_ref: reference to
               :py:class:`~smc.routing.access_list.IPAccessList`
        :param shortcut_capable_area: True|False
        :param list ospfv2_virtual_links_endpoints_container: virtual link endpoints
        :param list ospf_abr_substitute_container: substitute types: 
               |aggregate|not_advertise|substitute_with
        :return: :py:class:`smc.api.web.SMCResult`
        """
        json={'name': name,
              'area_id': area_id,
              'area_type': area_type,
              'inbound_filters_ref': inbound_filters_ref,
              'interface_settings_ref': interface_settings_ref,
              'ospf_abr_substitute_container': ospf_abr_substitute_container,
              'ospfv2_virtual_links_endpoints_container': 
                                    ospfv2_virtual_links_endpoints_container,
              'outbound_filters_ref': outbound_filters_ref,
              'shortcut_capable_area': shortcut_capable_area}
        
        href = search.element_entry_point(cls.typeof)
        return SMCRequest(href=href,
                          json=json).create()

class OSPFInterfaceSetting(object):
    """
    OSPF Interface Setting indicate specific configurations that are
    applied to the interface and OSPF Area configuration, including
    authentication.
    
    If you require non-default settings applied to your interface
    OSPF instance, you can create a custom interface profile::
    
        OSPFInterfaceSetting.create(name='myprofile', 
                                    dead_interval=30, 
                                    hello_interval=5)
                                                 
    When using authentication on interface settings, there are two types,
    password authentication (plain text) or message digest. 
    
    When specifying an authentication_type='password', the password parameter
    must be provided. 
    
    When specifying authentication_type='message_digest', the key_chain_ref
    parameter must be specified.
    """ 
    typeof = 'ospfv2_interface_settings'
    href = ElementLocator()
    
    def __init__(self, name, meta=None):
        self._name = name
        self.meta= meta
    
    @property
    def name(self):
        return self._name
    
    @classmethod
    def create(cls, name, dead_interval=40, hello_interval=10, 
               hello_interval_type='normal', dead_multiplier=1,
               mtu_mismatch_detection=True, retransmit_interval=5,
               router_priority=1, transmit_delay=1,
               authentication_type=None, password=None,
               key_chain_ref=None):
        """
        Create custom OSPF interface settings profile
        
        :param str name: name of interface settings
        :param int dead_interval: in seconds
        :param str hello_interval: in seconds
        :param str hello_interval_type: |normal|fast_hello
        :param int dead_multipler: fast hello packet multipler
        :param boolean mtu_mismatch_detection: True|False
        :param int retransmit_interval: in seconds
        :param int router_priority: set priority
        :param int transmit_delay: in seconds
        :param str authentication_type: password|message_digest
        :param str password: max 8 chars (required when 
               authentication_type='password')
        :param str key_chain_ref: reference to key chain (required when 
               authentication_type='message_digest')
        :return: :py:class:`smc.api.web.SMCResult`
        """
        json={'name': name,
              'authentication_type': authentication_type,
              'password': password,
              'key_chain_ref': key_chain_ref,
              'dead_interval': dead_interval,
              'dead_multiplier': dead_multiplier,
              'hello_interval': hello_interval,
              'hello_interval_type': hello_interval_type,
              'mtu_mismatch_detection': mtu_mismatch_detection,
              'retransmit_interval': retransmit_interval,
              'router_priority': router_priority,
              'transmit_delay': transmit_delay}
        
        href = search.element_entry_point(cls.typeof)
        return SMCRequest(href=href,
                          json=json).create()
                      
class OSPFKeyChain(object):
    """
    OSPF Key Chain is used for authenticating OSPFv2 packets. If required,
    create a key chain and specify authentication in the OSPFInterfaceSetting
    referencing this element.
    
    Is message-digest authentication is required on an OSPFInterfaceSetting, 
    first create the key chain and use the reference to create the ospf 
    interface profile::
    
        key_chain = OSPFKeyChain('secure-keychain') #obtain resource
        OSPFInterfaceSetting.create(name='authenicated-ospf', 
                                    authentication_type='message_digest', 
                                    key_chain_ref=key_chain.href)
    """
    typeof = 'ospfv2_key_chain'
    href = ElementLocator()
    
    def __init__(self, name, meta=None):
        self._name = name
        self.meta = meta
    
    @property
    def name(self):
        return self._name

    @classmethod
    def create(cls, name, key_chain_entry):
        """
        Create a key chain with list of keys
        
        Key_chain_entry format is::
        
            [{'key': 'xxxx', 'key_id': 1-255, 'send_key': True|False}]
        
        :param str name: Name of key chain
        :param list key_chain_entry: list of key chain entries
        :return: :py:class:`smc.qpi.web.SMCResult`
        """
        key_chain_entry = [] if key_chain_entry is None else key_chain_entry
        json={'name': name,
              'ospfv2_key_chain_entry': key_chain_entry}
        
        href = search.element_entry_point(cls.typeof)
        return SMCRequest(href=href,
                          json=json).create()

class OSPFProfile(object):
    """
    This element contains administrative distance and redistribution 
    settings.
    This is applied to the engine properties under Dynamic Routing.
    
    .. note:: An OSPFProfile has a one-to-one link to an OSPFDomainSetting

    Create an engine level OSPFProfile::

        ospf_domain = OSPFDomainSetting('custom') #obtain resource
        
        OSPFProfile.create(name='myospfprofile', 
                           domain_settings_ref=ospf_domain.href)
                           
    A redistribution entry specifies how routes are propogated, i.e. to BGP.
    
    An example of redistributing routes to BGP with a metric of 15::
    
        domain = OSPFDomainSetting('Default OSPFv2 Domain Settings')   
        OSPFProfile.create(name='dist-to-bgp', 
                           domain_settings_ref=domain.href, 
                           redistribution_entry=[{'enabled': True,
                                                  'filter_type': 'none',
                                                  'metric': 15,
                                                  'metric_type': 'external_1',
                                                  'type': 'bgp'}])
                            
    """
    typeof = 'ospfv2_profile'
    href = ElementLocator()
    
    def __init__(self, name, meta=None):
        self._name = name
        self.meta = meta
        
    @property
    def name(self):
        return self._name

    @classmethod
    def create(cls, name, domain_settings_ref, external_distance=110,
               inter_distance=110, intra_distance=110, 
               redistribution_entry=None):
        """
        Create an OSPFProfile
        
        :param str name: name of profile
        :param str domain_settings_ref: linked OSPFDomainSetting href
        :param int external_distance: route metric (E1-E2)
        :param int inter_distance: routes learned from different areas (O IA)
        :param int intra_distance: routes learned from same area (O)
        :param list redistribution_entry:
        :return: :py:class:`smc.api.web.SMCResult`
        """
        json={'name': name,
              'domain_settings_ref': domain_settings_ref,
              'external_distance': external_distance,
              'inter_distance': inter_distance,
              'intra_distance': intra_distance,
              'redistribution_entry': redistribution_entry}
        
        href = search.element_entry_point(cls.typeof)
        return SMCRequest(href=href,
                          json=json).create()

class OSPFDomainSetting(object):
    """
    Use this element to set the area border router (ABR) type, 
    throttle timer settings, and the max metric router link-state 
    advertisement (LSA) settings.
    
    An OSPFProfile requires a reference to an OSPFDomainSetting. The
    OSPFProfile is applied at the engine level.
    
    Create a custom OSPF Domain Setting element::
    
        OSPFDomainSetting.create(name='mydomain', 
                                 abr_type='standard', 
                                 auto_cost_bandwidth=200, 
                                 deprecated_algorithm=True)
    """
    typeof = 'ospfv2_domain_settings'
    href = ElementLocator()
    
    def __init__(self, name, meta=None):
        self._name = name
        self.meta = meta
        
    @property
    def name(self):
        return self._name

    @classmethod
    def create(cls, name, abr_type='cisco', auto_cost_bandwidth=100, 
               deprecated_algorithm=False, initial_delay=200, 
               initial_hold_time=1000, max_hold_time=10000,
               shutdown_max_metric_lsa=0, startup_max_metric_lsa=0):
        """
        Create custom Domain Settings
        
        Domain settings are referenced by an OSPFProfile
        
        :param str name: name of custom domain settings
        :param str abr_type: cisco|shortcut|standard
        :param int auto_cost_bandwidth: Mbits/s
        :param boolean deprecated_algorithm: RFC 1518 compatibility
        :param int initial_delay: in milliseconds
        :param int initial_hold_type: in milliseconds
        :param int max_hold_time: in milliseconds
        :param int shutdown_max_metric_lsa: in seconds
        :param int startup_max_metric_lsa: in seconds
        :return: :py:class:`smc.api.web.SMCResult`
        """
        json={'name': name,
              'abr_type': abr_type,
              'auto_cost_bandwidth': auto_cost_bandwidth,
              'deprecated_algorithm': deprecated_algorithm,
              'initial_delay': initial_delay,
              'initial_hold_time': initial_hold_time,
              'max_hold_time': max_hold_time,
              'shutdown_max_metric_lsa': shutdown_max_metric_lsa,
              'startup_max_metric_lsa': startup_max_metric_lsa}
        
        href = search.element_entry_point(cls.typeof)
        return SMCRequest(href=href,
                          json=json).create()
