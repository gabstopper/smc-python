"""
BGP Module representing BGP settings for Stonesoft NGFW layer 3 engines. BGP can be
enabled and run on either single/cluster layer 3 firewalls or virtual FW's.

For adding BGP configurations, several steps are required:

* Enable BGP on the engine and specific the BGP Profile
* Create or locate an existing OSPFArea to be used
* Modify the routing interface and add the BGP Peering

Enable BGP on an existing engine using the default BGP system profile::

    engine.enable_bgp(
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
    
    engine.disable_bgp()

Finding profiles or elements can also be done through collections::

    >>> list(BGPProfile.objects.all())
    [BGPProfile(name=Default BGP Profile)]
        
    >>> list(ExternalBGPPeer.objects.all())
    [ExternalBGPPeer(name=bgp-02), ExternalBGPPeer(name=Amazon AWS), ExternalBGPPeer(name=bgp-01)]

The BGP relationship can be represented as::

    Engine --uses an--> (BGP Profile --and--> Autonomous System --and--> Announced Networks)
    Engine Routing --uses-an--> BGP Peering --has-a--> External BGP Peer

Only Layer3Firewall and Layer3VirtualEngine types can support running BGP.

.. seealso:: :py:class:`smc.core.engines.Layer3Firewall` and 
             :py:class:`smc.core.engines.Layer3VirtualEngine`
             
"""
from smc.base.model import Element, ElementCreator
from smc.base.util import element_resolver


class AutonomousSystem(Element):
    """
    Autonomous System for BGP routing. AS is a required setting when
    enabling BGP on an engine and specifies a unique identifier for
    routing communications. 
    """
    typeof = 'autonomous_system'

    def __init__(self, name, **meta):
        super(AutonomousSystem, self).__init__(name, **meta)
        pass

    @classmethod
    def create(cls, name, as_number, comment=None):
        """
        Create an AS to be applied on the engine BGP configuration. An
        AS is a required parameter when creating an ExternalBGPPeer.

        :param str name: name of this AS
        :param int as_number: AS number preferred
        :param str comment: optional string comment
        :return: instance with meta
        :rtype: AutonomousSystem
        """
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

    def __init__(self, name, **meta):
        super(BGPProfile, self).__init__(name, **meta)
        pass

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

        :return list of tuple (subnet, distance)
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
    """
    typeof = 'external_bgp_peer'

    def __init__(self, name, **meta):
        super(ExternalBGPPeer, self).__init__(name, **meta)
        pass

    @classmethod
    def create(cls, name, neighbor_as_ref, neighbor_ip,
               neighbor_port=179):
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
                'neighbor_port': neighbor_port}

        neighbor_as_ref = element_resolver(neighbor_as_ref)

        json.update(neighbor_as=neighbor_as_ref)

        return ElementCreator(cls, json)

    @property
    def neighbor_as(self):
        """
        AutonomousSystem for this external BGP peer

        :return: :class:`~AutonomousSystem` element
        """
        return Element.from_href(self.data.get('neighbor_as'))

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

    """
    typeof = 'bgp_peering'

    def __init__(self, name, **meta):
        super(BGPPeering, self).__init__(name, **meta)
        pass

    @classmethod
    def create(cls, name, connection_profile_ref=None,
               md5_password=None, local_as_option='not_set',
               max_prefix_option='not_enabled', send_community='no',
               connected_check='disabled', orf_option='disabled',
               next_hop_self=True, override_capability=False,
               dont_capability_negotiate=False, remote_private_as=False,
               route_reflector_client=False, soft_reconfiguration=True,
               ttl_option='disabled'):
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
                'ttl_option': ttl_option}

        if md5_password:
            json.update(md5_password=md5_password)

        if not connection_profile_ref:
            connection_profile_ref = \
                BGPConnectionProfile('Default BGP Connection Profile')

        connection_profile_ref = element_resolver(connection_profile_ref)

        json.update(connection_profile=connection_profile_ref)

        return ElementCreator(cls, json)

    @property
    def connection_profile(self):
        """
        BGP Connection Profile used by this BGP Peering.

        :return: :class:`~BGPConnectionProfile`
        """
        return Element.from_href(self.data.get('connection_profile'))


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

    def __init__(self, name, **meta):
        super(BGPConnectionProfile, self).__init__(name, **meta)
        pass

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
