"""
Dynamic Routing can be enabled on devices configured in FW/VPN mode.
Configuring dynamic routing consists of enabling the routing protocol
on the engine and adding the routing elements on the interfaces at the
engine routing level.
    
For adding OSPF configurations, several steps are required:

* Enable OSPF on the engine and specific the OSPF Profile
* Create or locate an existing OSPFArea to be used
* Modify the routing interface and add the OSPFArea

Enable OSPF on an existing engine using the default OSPF system profile::

    engine.enable_ospf()
    
Create an OSPFArea using the default OSPF Interface Setting profile::

    OSPFArea.create(name='customOSPFArea')

Add OSPF area to an interface routing configuration (add to nicid '0')::

    interface = engine.routing.get(0)
    interface.add_ospf_area(area)
                
Disable OSPF on an engine::
    
    engine.disable_ospf()

Finding profiles or elements can also be done through collections::

    >>> list(Search('ospfv2_profile').objects.all())
    [OSPFProfile(name=Default OSPFv2 Profile)]
        
    >>> list(Search('ospfv2_area').objects.all())
    [OSPFArea(name=area0)]

The OSPF relationship can be represented as::

    Engine --uses an--> OSPF Profile --has-a--> OSPF Domain Setting
    Engine Routing --uses-an--> OSPF Area --has-a--> OSPF Interface Setting

Only Layer3Firewall and Layer3VirtualEngine types can support running OSPF.

.. seealso:: :py:class:`smc.core.engines.Layer3Firewall` and 
             :py:class:`smc.core.engines.Layer3VirtualEngine`

"""
from smc.base.model import Element, ElementCreator
from smc.base.util import element_resolver


class OSPFArea(Element):
    """
    OSPF Area is an element that identifies general settings for an
    OSPF configuration applied to an engine routing node. The OSPFArea
    has a reference to an OSPFInterfaceSetting and is required when
    creating.

    Create a basic OSPFArea with just area id::

        OSPFArea.create(name='myarea', area_id=0)

    Create an OSPFArea and use a custom OSPFInterfaceSetting element::

        OSPFArea.create(
            name='customOSPFArea', 
            interface_settings_ref=OSPFInterfaceSetting('myospf'), 
            area_id=3)

    **Advanced example:**

    Adding ospf_virtual_links_endpoints::

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
    :py:class:`smc.elements.network.Network`. These elements can either be created or
    retrieved using collections, or by getting the resource directly.

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

    def __init__(self, name, **meta):
        super(OSPFArea, self).__init__(name, **meta)
        pass

    @classmethod
    def create(cls, name, interface_settings_ref=None, area_id=1,
               area_default_cost=100, area_type='normal',
               outbound_filters_ref=None, inbound_filters_ref=None,
               shortcut_capable_area=False,
               ospfv2_virtual_links_endpoints_container=None,
               ospf_abr_substitute_container=None):
        """
        Create a new OSPF Area

        :param str name: name of OSPFArea configuration
        :param str,OSPFInterfaceSetting interface_settings_ref: an OSPFInterfaceSetting
            element or href. If None, uses the default system profile
        :param str name: area id
        :param int area_default_cost: default cost for this area
        :param str area_type: \|normal\|stub\|not_so_stubby\|totally_stubby\|
               totally_not_so_stubby
        :param str outbound_filters_ref: reference to 
               :py:class:`~smc.routing.access_list.IPAccessList`
        :param str inbound_filters_ref: reference to
               :py:class:`~smc.routing.access_list.IPAccessList`
        :param shortcut_capable_area: True|False
        :param list ospfv2_virtual_links_endpoints_container: virtual link endpoints
        :param list ospf_abr_substitute_container: substitute types: 
               \|aggregate\|not_advertise\|substitute_with
        :raises CreateElementFailed: failed to create with reason
        :return: instance with meta
        :rtype: OSPFArea
        """
        if interface_settings_ref is None:
            interface_settings_ref = \
                OSPFInterfaceSetting('Default OSPFv2 Interface Settings').href
        else:
            interface_settings_ref = element_resolver(interface_settings_ref)

        json = {'name': name,
                'area_id': area_id,
                'area_type': area_type,
                'inbound_filters_ref': inbound_filters_ref,
                'interface_settings_ref': interface_settings_ref,
                'ospf_abr_substitute_container': ospf_abr_substitute_container,
                'ospfv2_virtual_links_endpoints_container':
                    ospfv2_virtual_links_endpoints_container,
                'outbound_filters_ref': outbound_filters_ref,
                'shortcut_capable_area': shortcut_capable_area}

        return ElementCreator(cls, json)

    @property
    def interface_settings_ref(self):
        return Element.from_href(self.data.get('interface_settings_ref'))


class OSPFInterfaceSetting(Element):
    """
    OSPF Interface Setting indicate specific configurations that are
    applied to the interface and OSPF Area configuration, including
    authentication.

    If you require non-default settings applied to your interface
    OSPF instance, you can create a custom interface profile::

        OSPFInterfaceSetting.create(
            name='myprofile', 
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

    def __init__(self, name, **meta):
        super(OSPFInterfaceSetting, self).__init__(name, **meta)
        pass

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
        :param str hello_interval_type: \|normal\|fast_hello
        :param int dead_multipler: fast hello packet multipler
        :param bool mtu_mismatch_detection: True|False
        :param int retransmit_interval: in seconds
        :param int router_priority: set priority
        :param int transmit_delay: in seconds
        :param str authentication_type: \|password\|message_digest
        :param str password: max 8 chars (required when 
               authentication_type='password')
        :param str,Element key_chain_ref: OSPFKeyChain (required when 
               authentication_type='message_digest')
        :raises CreateElementFailed: create failed with reason
        :return: instance with meta
        :rtype: OSPFInterfaceSetting
        """
        key_chain_ref = element_resolver(key_chain_ref) if key_chain_ref else None
        json = {'name': name,
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

        return ElementCreator(cls, json)


class OSPFKeyChain(Element):
    """
    OSPF Key Chain is used for authenticating OSPFv2 packets. If required,
    create a key chain and specify authentication in the OSPFInterfaceSetting
    referencing this element.

    Is message-digest authentication is required on an OSPFInterfaceSetting, 
    first create the key chain and use the reference to create the ospf 
    interface profile::

        key_chain = OSPFKeyChain('secure-keychain') #obtain resource
        OSPFInterfaceSetting.create(
            name='authenicated-ospf', 
            authentication_type='message_digest', 
            key_chain_ref=key_chain.href)
    """
    typeof = 'ospfv2_key_chain'

    def __init__(self, name, **meta):
        super(OSPFKeyChain, self).__init__(name, **meta)
        pass

    @classmethod
    def create(cls, name, key_chain_entry):
        """
        Create a key chain with list of keys

        Key_chain_entry format is::

            [{'key': 'xxxx', 'key_id': 1-255, 'send_key': True|False}]

        :param str name: Name of key chain
        :param list key_chain_entry: list of key chain entries
        :raises CreateElementFailed: create failed with reason
        :return: instance with meta
        :rtype: OSPFKeyChain
        """
        key_chain_entry = [] if key_chain_entry is None else key_chain_entry
        json = {'name': name,
                'ospfv2_key_chain_entry': key_chain_entry}

        return ElementCreator(cls, json)


class OSPFProfile(Element):
    """
    An OSPF Profile contains administrative distance and redistribution 
    settings. An OSPF Profile is set on the engine element when enabling
    OSPF.

    These settings are always in effect:

    * No autosummary

    Example of creating an OSPFProfile with the default domain profile::

        OSPFProfile.create(name='myospf')

    See :py:class:`smc.core.properties.EngineFeature.enable_ospf` for enabling 
    ospf on an existing engine.

    """
    typeof = 'ospfv2_profile'

    def __init__(self, name, **meta):
        super(OSPFProfile, self).__init__(name, **meta)
        pass

    @classmethod
    def create(cls, name, domain_settings_ref=None, external_distance=110,
               inter_distance=110, intra_distance=110):
        """
        Create an OSPF Profile

        :param str name: name of profile
        :param str,OSPFDomainSetting domain_settings_ref: OSPFDomainSetting 
            element or href
        :param int external_distance: route metric (E1-E2)
        :param int inter_distance: routes learned from different areas (O IA)
        :param int intra_distance: routes learned from same area (O)
        :raises CreateElementFailed: create failed with reason
        :return: instance with meta
        :rtype: OSPFProfile
        """
        json = {'name': name,
                'external_distance': external_distance,
                'inter_distance': inter_distance,
                'intra_distance': intra_distance}

        if not domain_settings_ref:
            domain_settings_ref = OSPFDomainSetting(
                'Default OSPFv2 Domain Settings').href
        else:
            domain_settings_ref = element_resolver(domain_settings_ref)

        json.update(domain_settings_ref=domain_settings_ref)

        return ElementCreator(cls, json)

    @property
    def external_distance(self):
        """
        External administrative distance. Between 1-255.

        :return: int distance value
        """
        return self.data.get('external_distance')

    @property
    def inter_distance(self):
        """
        Inter administrative distance. Between 1-255.

        :return: int distance value
        """
        return self.data.get('inter_distance')

    @property
    def intra_distance(self):
        """
        Intra administrative distance. Between 1-255.

        :return: int distance value
        """
        return self.data.get('intra_distance')

    @property
    def domain_settings_ref(self):
        """
        OSPF Domain Settings profile used for this OSPF Profile

        :return: :class:`~OSPFDomainSetting`
        """
        return Element.from_href(self.data.get('domain_settings_ref'))


class OSPFDomainSetting(Element):
    """
    An OSPF Domain Setting provides settings for area border router (ABR)
    type, throttle timer settings, and the max metric router link-state 
    advertisement (LSA) settings.

    An OSPF Profile requires a reference to an OSPF Domain Setting. 

    Create a custom OSPF Domain Setting element::

        OSPFDomainSetting.create(
            name='mydomain', 
            abr_type='standard', 
            auto_cost_bandwidth=200, 
            deprecated_algorithm=True)
    """
    typeof = 'ospfv2_domain_settings'

    def __init__(self, name, **meta):
        super(OSPFDomainSetting, self).__init__(name, **meta)
        pass

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
        :param bool deprecated_algorithm: RFC 1518 compatibility
        :param int initial_delay: in milliseconds
        :param int initial_hold_type: in milliseconds
        :param int max_hold_time: in milliseconds
        :param int shutdown_max_metric_lsa: in seconds
        :param int startup_max_metric_lsa: in seconds
        :raises CreateElementFailed: create failed with reason
        :return: instance with meta
        :rtype: OSPFDomainSetting
        """
        json = {'name': name,
                'abr_type': abr_type,
                'auto_cost_bandwidth': auto_cost_bandwidth,
                'deprecated_algorithm': deprecated_algorithm,
                'initial_delay': initial_delay,
                'initial_hold_time': initial_hold_time,
                'max_hold_time': max_hold_time,
                'shutdown_max_metric_lsa': shutdown_max_metric_lsa,
                'startup_max_metric_lsa': startup_max_metric_lsa}

        return ElementCreator(cls, json)
