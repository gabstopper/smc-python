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

    engine.ospf.enable()
    
Create an OSPFArea using the default OSPF Interface Setting profile::

    OSPFArea.create(name='customOSPFArea')

Add OSPF area to an interface routing configuration (add to nicid '0')::

    interface = engine.routing.get(0)
    interface.add_ospf_area(area)
                
Disable OSPF on an engine::
    
    engine.ospf.disable()

Finding profiles or elements can also be done through collections::

    >>> list(OSPFProfile.objects.all())
    [OSPFProfile(name=Default OSPFv2 Profile)]
        
    >>> list(OSPFArea.objects.all())
    [OSPFArea(name=area0)]

The OSPF relationship can be represented as::

    Engine --uses an--> OSPF Profile --has-a--> OSPF Domain Setting
    Engine Routing --uses-an--> OSPF Area --has-a--> OSPF Interface Setting

Only Layer3Firewall and Layer3VirtualEngine types can support running OSPF.

.. seealso:: :py:class:`smc.core.engines.Layer3Firewall` and 
             :py:class:`smc.core.engines.Layer3VirtualEngine`

"""
from smc.base.model import Element, ElementCreator, ElementCache, ElementRef
from smc.base.util import element_resolver


class OSPF(object):
    """
    OSPF configuration on the engine. Access through an engine reference::
        
        engine.dynamic_routing.ospf.status
        engine.dynamic_rotuing.ospf.enable(....)
        
    When making changes to the OSPF configuration, any methods
    called that change the configuration also require that
    engine.update() is called once changes are complete. This way
    you can make multiple changes without refreshing the engine cache.
    
    :ivar OSPFProfile profile: OSPFProfile reference for this engine
    """
    profile = ElementRef('ospfv2_profile_ref')
    
    def __init__(self, data=None):
        self.data = data if data else ElementCache()
    
    @property
    def router_id(self):
        """
        Get the router ID for this OSPF configuration. If None, then
        the ID will use the interface IP.
        
        :return: str or None
        """
        return self.data.get('router_id')
    
    @property
    def status(self):
        """
        Is OSPF enabled on this engine.
        
        :rtype: bool
        """
        return self.data.get('enabled')
    
    def disable(self):
        """
        Disable OSPF on this engine.

        :return: None
        """
        self.data.update(
            enabled=False)

    def enable(self, ospf_profile=None, router_id=None):
        """
        Enable OSPF on this engine. For master engines, enable
        OSPF on the virtual firewall.

        Once enabled on the engine, add an OSPF area to an interface::

            engine.dynamic_routing.ospf.enable()
            interface = engine.routing.get(0)
            interface.add_ospf_area(OSPFArea('myarea'))

        :param str,OSPFProfile ospf_profile: OSPFProfile element or str
            href; if None, use default profile
        :param str router_id: single IP address router ID
        :raises ElementNotFound: OSPF profile not found
        :return: None
        """
        ospf_profile = element_resolver(ospf_profile) if ospf_profile \
            else OSPFProfile('Default OSPFv2 Profile').href

        self.data.update(
            enabled=True,
            ospfv2_profile_ref=ospf_profile,
            router_id=router_id)
    
    def update_configuration(self, **kwargs):
        """
        Update the OSPF configuration using kwargs that match the
        `enable` constructor.
        
        :param dict kwargs: keyword arguments matching enable constructor.
        :return: whether change was made
        :rtype: bool
        """
        updated = False
        if 'ospf_profile' in kwargs:
            kwargs.update(ospfv2_profile_ref=kwargs.pop('ospf_profile'))
        for name, value in kwargs.items():
            _value = element_resolver(value)
            if self.data.get(name) != _value:
                self.data[name] = _value
                updated = True
        return updated


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
    
    :ivar OSPFInterfaceSetting interface_settings_ref: reference to the OSPFInterfaceSetting
        element
    """
    typeof = 'ospfv2_area'
    interface_settings_ref = ElementRef('interface_settings_ref')

    @classmethod
    def create(cls, name, interface_settings_ref=None, area_id=1,
               area_type='normal', outbound_filters=None,
               inbound_filters=None, shortcut_capable_area=False,
               ospfv2_virtual_links_endpoints_container=None,
               ospf_abr_substitute_container=None, comment=None, **kwargs):
        """
        Create a new OSPF Area

        :param str name: name of OSPFArea configuration
        :param str,OSPFInterfaceSetting interface_settings_ref: an OSPFInterfaceSetting
            element or href. If None, uses the default system profile
        :param str name: area id
        :param str area_type: \|normal\|stub\|not_so_stubby\|totally_stubby\|
               totally_not_so_stubby
        :param list outbound_filters: reference to an IPAccessList and or IPPrefixList.
            You can only have one outbound prefix or access list
        :param list inbound_filters: reference to an IPAccessList and or IPPrefixList.
            You can only have one outbound prefix or access list
        :param shortcut_capable_area: True|False
        :param list ospfv2_virtual_links_endpoints_container: virtual link endpoints
        :param list ospf_abr_substitute_container: substitute types: 
               \|aggregate\|not_advertise\|substitute_with
        :param str comment: optional comment
        :raises CreateElementFailed: failed to create with reason
        :rtype: OSPFArea
        """
        interface_settings_ref = element_resolver(interface_settings_ref) or \
            OSPFInterfaceSetting('Default OSPFv2 Interface Settings').href
        
        if 'inbound_filters_ref' in kwargs:
            inbound_filters = kwargs.get('inbound_filters_ref')
        
        if 'outbound_filters_ref' in kwargs:
            outbound_filters = kwargs.get('outbound_filters_ref')
        
        json = {'name': name,
                'area_id': area_id,
                'area_type': area_type,
                'comment': comment,
                'inbound_filters_ref': element_resolver(inbound_filters),
                'interface_settings_ref': interface_settings_ref,
                'ospf_abr_substitute_container': ospf_abr_substitute_container,
                'ospfv2_virtual_links_endpoints_container':
                    ospfv2_virtual_links_endpoints_container,
                'outbound_filters_ref': element_resolver(outbound_filters),
                'shortcut_capable_area': shortcut_capable_area}

        return ElementCreator(cls, json)

    @classmethod
    def update_or_create(cls, filter_key=None, with_status=False, **kwargs):
        if 'inbound_filters' in kwargs:
            kwargs.update(inbound_filters_ref=
                element_resolver(kwargs.pop('inbound_filters')))
        if 'outbound_filters' in kwargs:
            kwargs.update(outbound_filters_ref=
                element_resolver(kwargs.pop('outbound_filters')))
        return super(OSPFArea, cls).update_or_create(filter_key, with_status, **kwargs)

    @property
    def inbound_filters(self):
        """
        Inbound filters attached to this OSPF Area. Filters can be type
        IPPrefixList or IPAccessList
        
        :rtype: list
        """
        return [Element.from_href(filt)
            for filt in self.data.get('inbound_filters_ref', [])]
    
    @property
    def outbound_filters(self):
        """
        Outbound filters attached to this OSPF Area. Filters can be type
        IPPrefixList or IPAccessList
        
        :rtype: list
        """
        return [Element.from_href(filt)
            for filt in self.data.get('outbound_filters_ref', [])]


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
    key_chain_ref = ElementRef('key_chain_ref')

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
        json = {'name': name,
                'authentication_type': authentication_type,
                'password': password,
                'key_chain_ref': element_resolver(key_chain_ref),
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
        key_chain_entry = key_chain_entry or []
        json = {'name': name,
                'ospfv2_key_chain_entry': key_chain_entry}

        return ElementCreator(cls, json)


def _format_redist_entry(redistribution_entry):
    for entry in redistribution_entry:
        _filter = entry.pop('filter', None)
        if _filter and _filter.typeof == 'ip_access_list':
            entry.update(
                filter_type='access_list',
                redistribution_filter_ref=_filter.href)
        elif _filter and _filter.typeof == 'route_map':
            entry.update(
                filter_type='route_map_policy',
                redistribution_rm_ref=_filter.href)
        if not 'metric_type' in entry:
            entry.update(
                metric_type='external_1')
    return redistribution_entry

    
class OSPFProfile(Element):
    """
    An OSPF Profile contains administrative distance and redistribution 
    settings. An OSPF Profile is set on the engine element when enabling
    OSPF.

    These settings are always in effect:

    * No autosummary

    Example of creating an OSPFProfile with the default domain profile::

        OSPFProfile.create(name='myospf')

    .. note:: Enable OSPF on engine using engine.ospf.enable()
    
    :ivar int external_distance: external distance metric
    :ivar int inter_distance: inter distance metric
    :ivar int intra_distance: intra distance metric
    :ivar int default_metric: set a default metric for all unset areas
    :ivar list redistribution_entry: settings for static, connected, etc
    :ivar OSPFDomainSetting domain_settings_ref: OSPF Domain Settings profile
        used for this OSPF Profile
    """
    typeof = 'ospfv2_profile'
    domain_settings_ref = ElementRef('domain_settings_ref')

    @classmethod
    def create(cls, name, domain_settings_ref=None, external_distance=110,
               inter_distance=110, intra_distance=110, redistribution_entry=None,
               default_metric=None, comment=None):
        """
        Create an OSPF Profile.
        
        If providing a list of redistribution entries, provide in the following
        dict format: 
        
        {'enabled': boolean, 'metric_type': 'external_1' or 'external_2',
         'metric': 2, 'type': 'kernel'}
        
        Valid types for redistribution entries are: kernel, static, connected, bgp,
        and default_originate.
        
        You can also provide a 'filter' key with either an IPAccessList or RouteMap
        element to use for further access control on the redistributed route type.
        If metric_type is not provided, external_1 (E1) will be used. 
        
        An example of a redistribution_entry would be::
        
            {u'enabled': True,
             u'metric': 123,
             u'metric_type': u'external_2',
             u'filter': RouteMap('myroutemap'),
             u'type': u'static'}

        :param str name: name of profile
        :param str,OSPFDomainSetting domain_settings_ref: OSPFDomainSetting 
            element or href
        :param int external_distance: route metric (E1-E2)
        :param int inter_distance: routes learned from different areas (O IA)
        :param int intra_distance: routes learned from same area (O)
        :param list redistribution_entry: how to redistribute the OSPF routes.
        :raises CreateElementFailed: create failed with reason
        :rtype: OSPFProfile
        """
        json = {'name': name,
                'external_distance': external_distance,
                'inter_distance': inter_distance,
                'intra_distance': intra_distance,
                'default_metric': default_metric,
                'comment': comment}
        
        if redistribution_entry:
            json.update(redistribution_entry=
                _format_redist_entry(redistribution_entry))

        domain_settings_ref = element_resolver(domain_settings_ref) or \
            OSPFDomainSetting('Default OSPFv2 Domain Settings').href

        json.update(domain_settings_ref=domain_settings_ref)

        return ElementCreator(cls, json)
        
    @classmethod
    def update_or_create(cls, filter_key=None, with_status=False, **kwargs):
        if 'redistribution_entry' in kwargs:
            kwargs.update(redistribution_entry=_format_redist_entry(
                kwargs.pop('redistribution_entry', [])))
        return super(OSPFProfile, cls).update_or_create(filter_key, with_status, **kwargs)


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
