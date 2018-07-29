"""
BGP Module representing BGP settings for Stonesoft NGFW layer 3 engines. BGP can be
enabled and run on either single/cluster layer 3 firewalls or virtual FW's.

For adding BGP configurations, several steps are required:

* Enable BGP on the engine and specify the BGP Profile
* Create or use an existing OSPFArea to be used
* Modify the routing interface and add the BGP Peering

Enable BGP on an existing engine using the default BGP system profile::

    engine.bgp.enable(
        autonomous_system=AutonomousSystem('myAS')
        announced_networks=[Network('172.18.1.0/24'), Network('1.1.1.0/24')])
    
Create a BGP Peering using the default BGP Connection Profile::

    BGPPeering.create(name='mypeer')
    
Add the BGP Peering to the routing interface::

    interface = engine.routing.get(0)
    interface.add_bgp_peering(
        BGPPeering('mypeer'), 
        ExternalBGPPeer('neighbor'))
                
Disable BGP on an engine::
    
    engine.bgp.disable()

Finding profiles or elements can also be done through collections::

    >>> list(BGPProfile.objects.all())
    [BGPProfile(name=Default BGP Profile)]
        
    >>> list(ExternalBGPPeer.objects.all())
    [ExternalBGPPeer(name=bgp-02), ExternalBGPPeer(name=Amazon AWS), ExternalBGPPeer(name=bgp-01)]

The BGP relationship can be represented as::

    Engine --uses an--> (BGP Profile --and--> Autonomous System --and--> Announced Networks)
    Engine Routing --uses-an--> BGP Peering --has-a--> External BGP Peer

Only Layer3Firewall and Layer3VirtualEngine types can support running BGP.

.. seealso:: :class:`smc.core.engines.Layer3Firewall` and 
             :class:`smc.core.engines.Layer3VirtualEngine`
             
"""
from smc.base.model import Element, ElementCreator, ElementCache,\
    ElementRef
from smc.base.util import element_resolver
from smc.routing.ospf import OSPF


class DynamicRouting(object):
    """
    Dynamic Routing element node. Encapsulates antispoofing networks
    to be added for dynamic routing protocols as well as references
    to OSPF and BGP configurations.
    """
    def __init__(self, engine):
        self.data = engine.data.get('dynamic_routing', {})
        
    @property
    def antispoofing_networks(self):
        return [Element.from_href(network)
            for network in self.data.get('antispoofing_ne_ref', [])]
    
    def update_antispoofing(self, networks=None):
        """
        Pass a list of networks to update antispoofing networks with.
        You can clear networks by providing an empty list. If networks
        are provided but already exist, no update is made.
        
        :param list networks: networks, groups or hosts for antispoofing
        :rtype: bool
        """
        if not networks and len(self.data.get('antispoofing_ne_ref')):
            self.data.update(antispoofing_ne_ref=[])
            return True
        _networks = element_resolver(networks)
        if set(_networks) ^ set(self.data.get('antispoofing_ne_ref')):
            self.data.update(antispoofing_ne_ref=_networks)
            return True
        return False

    @property
    def bgp(self):
        """
        Reference to BGP configuration
        
        :rtype: BGP
        """
        return BGP(self.data.get('bgp', {}))
        
    @property
    def ospf(self):
        """
        Reference to OSPF configuration
        
        :rtype: OSPF
        """
        return OSPF(self.data.get('ospfv2', {}))


class BGP(object):
    """
    BGP represents the BGP configuration on a given engine. An
    instance is returned from an engine reference::
    
        engine = Engine('myengine')
        engine.dynamic_routing.bgp.status
        engine.dynamic_routing.bgp.announced_networks
        ...
    
    When making changes to the BGP configuration, any methods
    called that change the configuration also require that
    engine.update() is called once changes are complete. This way
    you can make multiple changes without refreshing the engine cache.
    
    For example, adding advertised networks to the configuration::
    
        engine.dynamic_routing.bgp.update_configuration(announced_network=[Network('foo')])
        engine.update()
    
    :ivar AutonomousSystem autonomous_system: AS reference for this BGP configuration
    :ivar BGPProfile profile: BGP profile reference for this configuration
    """
    autonomous_system = ElementRef('bgp_as_ref')
    profile = ElementRef('bgp_profile_ref')
    
    def __init__(self, data=None):
        self.data = data if data else ElementCache()

    @property
    def router_id(self):
        """
        Get the router ID for this BGP configuration. If None, then
        the ID will use the interface IP.
        
        :return: str or None
        """
        return self.data.get('router_id')
    
    @property
    def status(self):
        """
        Is BGP enabled on this engine.
        
        :rtype: bool
        """
        return self.data.get('enabled')
    
    def disable(self):
        """
        Disable BGP on this engine.

        :return: None
        """
        self.data.update(    
            enabled=False,
            announced_ne_setting=[])
    
    def enable(self, autonomous_system, announced_networks,
               router_id=None, bgp_profile=None):
        """
        Enable BGP on this engine. On master engine, enable BGP on the
        virtual firewall. When adding networks to `announced_networks`, the
        element types can be of type :class:`smc.elements.network.Host`,
        :class:`smc.elements.network.Network` or :class:`smc.elements.group.Group`.
        If passing a Group, it must have element types of host or network.
        
        Within announced_networks, you can pass a 2-tuple that provides an optional
        :class:`smc.routing.route_map.RouteMap` if additional policy is required
        for a given network.
        ::

            engine.dynamic_routing.bgp.enable(
                autonomous_system=AutonomousSystem('aws_as'),
                announced_networks=[Network('bgpnet'),Network('inside')],
                router_id='10.10.10.10')

        :param str,AutonomousSystem autonomous_system: provide the AS element
            or str href for the element
        :param str,BGPProfile bgp_profile: provide the BGPProfile element or
            str href for the element; if None, use system default
        :param list announced_networks: list of networks to advertise via BGP
            Announced networks can be single networks,host or group elements or
            a 2-tuple with the second tuple item being a routemap element
        :param str router_id: router id for BGP, should be an IP address. If not
            set, automatic discovery will use default bound interface as ID.
        :raises ElementNotFound: OSPF, AS or Networks not found
        :return: None
        
        .. note:: For arguments that take str or Element, the str value should be
            the href of the element.
        """
        autonomous_system = element_resolver(autonomous_system)
    
        bgp_profile = element_resolver(bgp_profile) or \
            BGPProfile('Default BGP Profile').href
        
        announced = self._unwrap(announced_networks)
        
        self.data.update(
            enabled=True,
            bgp_as_ref=autonomous_system,
            bgp_profile_ref=bgp_profile,
            announced_ne_setting=announced,
            router_id=router_id)
    
    def update_configuration(self, **kwargs):
        """
        Update configuration using valid kwargs as defined in
        the enable constructor.
        
        :param dict kwargs: kwargs to satisfy valid args from `enable`
        :rtype: bool
        """
        updated = False
        if 'announced_networks' in kwargs:
            kwargs.update(announced_ne_setting=kwargs.pop('announced_networks'))
        if 'bgp_profile' in kwargs:
            kwargs.update(bgp_profile_ref=kwargs.pop('bgp_profile'))
        if 'autonomous_system' in kwargs:
            kwargs.update(bgp_as_ref=kwargs.pop('autonomous_system'))
        
        announced_ne = kwargs.pop('announced_ne_setting', None)
        
        for name, value in kwargs.items():
            _value = element_resolver(value)
            if self.data.get(name) != _value:
                self.data[name] = _value
                updated = True
        
        if announced_ne is not None:
            s = self.data.get('announced_ne_setting')
            ne = self._unwrap(announced_ne)
            
            if len(announced_ne) != len(s) or not self._equal(ne, s):
                self.data.update(announced_ne_setting=ne)
                updated = True
            
        return updated    
    
    def _equal(self, dict1, dict2):
        _s = {entry.get('announced_ne_ref'): entry.get('announced_rm_ref')
              for entry in dict1}
        _d = {entry.get('announced_ne_ref'): entry.get('announced_rm_ref')
              for entry in dict2}
        return len({k:_s[k] for k in _s if k not in _d or _d.get(k) != _s[k]}) == 0
    
    def _unwrap(self, network):
        _announced = []
        for net in network:
            d = dict()
            if isinstance(net, tuple):
                _network, _routemap = net
                d.update(announced_ne_ref=_network.href)
                if _routemap:
                    d.update(announced_rm_ref=_routemap.href)
                _announced.append(d)
                continue
            d.update(announced_ne_ref=net.href)
            _announced.append(d)
        return _announced
    
    @property
    def announced_networks(self):
        """
        Show all announced networks for the BGP configuration.
        Returns tuple of advertised network, routemap. Route
        map may be None.
        ::
        
            for advertised in engine.bgp.advertisements:
                net, route_map = advertised
        
        :return: list of tuples (advertised_network, route_map).
        """
        return [(Element.from_href(ne.get('announced_ne_ref')),
                 Element.from_href(ne.get('announced_rm_ref')))
                 for ne in self.data.get('announced_ne_setting')]
        
    

def as_dotted(dotted_str):
    """
    Implement RFC 5396 to support 'asdotted' notation for BGP AS numbers.
    Provide a string in format of '1.10', '65000.65015' and this will return
    a 4-byte decimal representation of the AS number.
    Get the binary values for the int's and pad to 16 bits if necessary
    (values <255). Concatenate the first 2 bytes with second 2 bytes then
    convert back to decimal. The maximum for low and high order values is
    65535 (i.e. 65535.65535).
    
    :param str dotted_str: asdotted notation for BGP ASN
    :rtype: int
    """
    #max_asn = 4294967295 (65535 * 65535)
    if '.' not in dotted_str:
        return dotted_str
    max_byte = 65535
    left, right = map(int, dotted_str.split('.'))
    if left > max_byte or right > max_byte:
        raise ValueError('The max low and high order value for '
            'a 32-bit ASN is 65535')
    binval = "{0:016b}".format(left)
    binval += "{0:016b}".format(right)
    return int(binval, 2)


class AutonomousSystem(Element):
    """
    Autonomous System for BGP routing. AS is a required setting when
    enabling BGP on an engine and specifies a unique identifier for
    routing communications. 
    """
    typeof = 'autonomous_system'

    @classmethod
    def create(cls, name, as_number, comment=None):
        """
        Create an AS to be applied on the engine BGP configuration. An
        AS is a required parameter when creating an ExternalBGPPeer. You
        can also provide an AS number using an 'asdot' syntax::
        
            AutonomousSystem.create(name='myas', as_number='200.600')

        :param str name: name of this AS
        :param int as_number: AS number preferred
        :param str comment: optional string comment
        :raises CreateElementFailed: unable to create AS
        :raises ValueError: If providing AS number in dotted format and
            low/high order bytes are > 65535.
        :return: instance with meta
        :rtype: AutonomousSystem
        """
        as_number = as_dotted(str(as_number))
        json = {'name': name,
                'as_number': as_number,
                'comment': comment}

        return ElementCreator(cls, json)

    @property
    def as_number(self):
        """
        The AS Number for this autonomous system

        :return: AS number
        :rtype: int
        """
        return int(self.data.get('as_number'))
    
    @classmethod
    def update_or_create(cls, with_status=False, **kwargs):
        if '.' in str(kwargs.get('as_number')):
            kwargs.update(as_number=int(as_dotted(kwargs['as_number'])))
        return super(AutonomousSystem, cls).update_or_create(
            with_status=with_status, **kwargs)
    

class BGPProfile(Element):
    """
    A BGP Profile specifies settings specific to an engine level BGP
    configuration. A profile specifies engine specific settings such
    as distance, redistribution, and aggregation and port.

    These settings are always in effect:

    * BGP version 4/4+
    * No autosummary
    * No synchronization
    * Graceful restart

    Example of creating a custom BGP Profile with default administrative
    distances and custom subnet distances::

        Network.create(name='inside', ipv4_network='1.1.1.0/24')
        BGPProfile.create(
            name='bar',
            internal_distance=100,
            external_distance=200,
            local_distance=50,
            subnet_distance=[(Network('inside'), 100)])  
    """
    typeof = 'bgp_profile'

    @classmethod
    def create(cls, name, port=179, external_distance=20, internal_distance=200,
               local_distance=200, subnet_distance=None):
        """
        Create a custom BGP Profile

        :param str name: name of profile
        :param int port: port for BGP process
        :param int external_distance: external administrative distance; (1-255)
        :param int internal_distance: internal administrative distance (1-255)
        :param int local_distance: local administrative distance (aggregation) (1-255)
        :param list subnet_distance: configure specific subnet's with respective distances
        :type tuple subnet_distance: (subnet element(Network), distance(int))
        :raises CreateElementFailed: reason for failure
        :return: instance with meta
        :rtype: BGPProfile
        """
        json = {'name': name,
                'external': external_distance,
                'internal': internal_distance,
                'local': local_distance,
                'port': port}

        if subnet_distance:
            d = [{'distance': distance, 'subnet': subnet.href}
                 for subnet, distance in subnet_distance]
            json.update(distance_entry=d)

        return ElementCreator(cls, json)

    @property
    def port(self):
        """
        Specified port for BGP

        :return: value of BGP port
        :rtype: int
        """
        return self.data.get('port')

    @property
    def external_distance(self):
        """
        External administrative distance (eBGP)

        :return: distance setting
        :rtype: int
        """
        return self.data.get('external')

    @property
    def internal_distance(self):
        """
        Internal administrative distance (iBGP)

        :return: internal distance setting
        :rtype: int
        """
        return self.data.get('internal')

    @property
    def local_distance(self):
        """
        Local administrative distance (aggregation)

        :return: local distance setting
        :rtype: int
        """
        return self.data.get('local')

    @property
    def subnet_distance(self):
        """
        Specific subnet administrative distances

        :return: list of tuple (subnet, distance)
        """
        return [(Element.from_href(entry.get('subnet')), entry.get('distance'))
                for entry in self.data.get('distance_entry')]


class ExternalBGPPeer(Element):
    """
    An External BGP represents the AS and IP settings for a remote
    BGP peer. Creating a BGP peer requires that you also pre-create
    an :class:`~AutonomousSystem` element::

        AutonomousSystem.create(name='neighborA', as_number=500)
        ExternalBGPPeer.create(name='name', 
                               neighbor_as_ref=AutonomousSystem('neighborA'),
                               neighbor_ip='1.1.1.1')
    
    :ivar AutonomousSystem neighbor_as: AS for this external BGP peer
    """
    typeof = 'external_bgp_peer'
    neighbor_as = ElementRef('neighbor_as')

    @classmethod
    def create(cls, name, neighbor_as, neighbor_ip,
               neighbor_port=179, comment=None):
        """
        Create an external BGP Peer. 

        :param str name: name of peer
        :param str,AutonomousSystem neighbor_as_ref: AutonomousSystem
            element or href. 
        :param str neighbor_ip: ip address of BGP peer
        :param int neighbor_port: port for BGP, default 179.
        :raises CreateElementFailed: failed creating
        :return: instance with meta
        :rtype: ExternalBGPPeer
        """
        json = {'name': name,
                'neighbor_ip': neighbor_ip,
                'neighbor_port': neighbor_port,
                'comment': comment}

        neighbor_as_ref = element_resolver(neighbor_as)
        json.update(neighbor_as=neighbor_as_ref)

        return ElementCreator(cls, json)

    @property
    def neighbor_ip(self):
        """
        IP address of the external BGP Peer

        :return: ipaddress of external bgp peer
        :rtype: str
        """
        return self.data.get('neighbor_ip')

    @property
    def neighbor_port(self):
        """
        Port used for neighbor AS

        :return: neighbor port
        :rtype: int
        """
        return self.data.get('neighbor_port')


class BGPPeering(Element):
    """
    BGP Peering is applied directly to an interface and defines
    basic connection settings. A BGPConnectionProfile is required
    to create a BGPPeering and if not provided, the default profile
    will be used.

    The most basic peering can simply specify the name of the peering
    and leverage the default BGPConnectionProfile::

        BGPPeering.create(name='my-aws-peer')

    :ivar BGPConnectionProfile connection_profile: BGP connection profile for this
        peering
    """
    typeof = 'bgp_peering'
    connection_profile = ElementRef('connection_profile')
    
    @classmethod
    def create(cls, name, connection_profile_ref=None,
               md5_password=None, local_as_option='not_set',
               max_prefix_option='not_enabled', send_community='no',
               connected_check='disabled', orf_option='disabled',
               next_hop_self=True, override_capability=False,
               dont_capability_negotiate=False, remote_private_as=False,
               route_reflector_client=False, soft_reconfiguration=True,
               ttl_option='disabled', comment=None):
        """
        Create a new BGPPeering configuration.

        :param str name: name of peering
        :param str,BGPConnectionProfile connection_profile_ref: required BGP
            connection profile. System default used if not provided.
        :param str md5_password: optional md5_password
        :param str local_as_option: the local AS mode. Valid options are:
            'not_set', 'prepend', 'no_prepend', 'replace_as'
        :param str max_prefix_option: The max prefix mode. Valid options are:
            'not_enabled', 'enabled', 'warning_only'
        :param str send_community: the send community mode. Valid options are:
            'no', 'standard', 'extended', 'standard_and_extended'
        :param str connected_check: the connected check mode. Valid options are:
            'disabled', 'enabled', 'automatic'
        :param str orf_option: outbound route filtering mode. Valid options are:
            'disabled', 'send', 'receive', 'both'
        :param bool next_hop_self: next hop self setting
        :param bool override_capability: is override received capabilities
        :param bool dont_capability_negotiate: do not send capabilities
        :param bool remote_private_as: is remote a private AS
        :param bool route_reflector_client: Route Reflector Client (iBGP only)
        :param bool soft_reconfiguration: do soft reconfiguration inbound
        :param str ttl_option: ttl check mode. Valid options are: 'disabled', 
            'ttl-security'
        :raises CreateElementFailed: failed creating profile
        :return: instance with meta
        :rtype: BGPPeering
        """
        json = {'name': name,
                'local_as_option': local_as_option,
                'max_prefix_option': max_prefix_option,
                'send_community': send_community,
                'connected_check': connected_check,
                'orf_option': orf_option,
                'next_hop_self': next_hop_self,
                'override_capability': override_capability,
                'dont_capability_negotiate': dont_capability_negotiate,
                'soft_reconfiguration': soft_reconfiguration,
                'remove_private_as': remote_private_as,
                'route_reflector_client': route_reflector_client,
                'ttl_option': ttl_option,
                'comment': comment}

        if md5_password:
            json.update(md5_password=md5_password)

        connection_profile_ref = element_resolver(connection_profile_ref) or \
            BGPConnectionProfile('Default BGP Connection Profile').href
    
        json.update(connection_profile=connection_profile_ref)

        return ElementCreator(cls, json)


class BGPConnectionProfile(Element):
    """
    A BGP Connection Profile will specify timer based settings and
    is used by a BGPPeering configuration.

    Create a custom profile::

        BGPConnectionProfile.create(
            name='fooprofile', 
            md5_password='12345', 
            connect_retry=200, 
            session_hold_timer=100, 
            session_keep_alive=150)        
    """
    typeof = 'bgp_connection_profile'

    @classmethod
    def create(cls, name, md5_password=None, connect_retry=120,
               session_hold_timer=180, session_keep_alive=60):
        """
        Create a new BGP Connection Profile.

        :param str name: name of profile
        :param str md5_password: optional md5 password
        :param int connect_retry: The connect retry timer, in seconds
        :param int session_hold_timer: The session hold timer, in seconds
        :param int session_keep_alive: The session keep alive timer, in seconds
        :raises CreateElementFailed: failed creating profile
        :return: instance with meta
        :rtype: BGPConnectionProfile
        """
        json = {'name': name,
                'connect': connect_retry,
                'session_hold_timer': session_hold_timer,
                'session_keep_alive': session_keep_alive}

        if md5_password:
            json.update(md5_password=md5_password)

        return ElementCreator(cls, json)

    @property
    def connect_retry(self):
        """
        The connect retry timer, in seconds

        :return: connect retry in seconds
        :rtype: int
        """
        return self.data.get('connect')

    @property
    def session_hold_timer(self):
        """
        The session hold timer, in seconds

        :return: in seconds
        :rtype: int
        """
        return self.data.get('session_hold_timer')

    @property
    def session_keep_alive(self):
        """
        The session keep alive, in seconds

        :return: in seconds
        :rtype: int
        """
        return self.data.get('session_keep_alive')
