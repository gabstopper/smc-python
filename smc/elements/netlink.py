"""
NetLink elements are used to represent alternative routes that lead to the
same destination IP addresses.

NetLinks usually represent Internet connections, but can be used for other
communications links as well.

You can use a single Router if a single route is enough for routing traffic
to a network through an interface or an aggregated link. If you want to create
separate routes for traffic to a network through two or more interfaces, you
must use NetLinks.

To use traffic handlers, you must first create the netlink type required, then
add this to the engine routing node.

Creating a static netlink element::

    StaticNetlink.create(
        name='netlink',
        gateway=Router('routerfoo'),
        network=[Network('mynetwork')],
        domain_server_address=['8.8.8.8', '8.8.4.4'],
        probe_address=['1.1.1.254'],
        comment='foobar')

Add the netlink to the desired routing interface::

    engine = Engine('vm')
    rnode = engine.routing.get(0) #interface 0
    rnode.add_traffic_handler(
        netlink=StaticNetlink('mynetlink'),
        netlink_gw=[Router('myrtr')])

.. seealso:: :class:`smc.core.route.Routing.add_traffic_handler`

"""
from smc.base.model import Element, ElementCreator
from smc.base.util import element_resolver
from smc.api.exceptions import MissingRequiredInput, ElementNotFound,\
    CreateElementFailed
from smc.core.general import RankedDNSAddress
from smc.base.structs import NestedDict


class StaticNetlink(Element):
    """
    A Static Netlink is applied to an interface to provide an alternate
    route to a destination. It is typically used when you have fixed IP
    interfaces versus using DHCP (use a Dynamic NetLink).
    
    :ivar int input_speed: input speed in Kbps, used for ratio-based
            load-balancing
    :ivar int output_speed: output speed in Kbps,  used for ratio-based
        load-balancing
    :ivar list probe_address: list of IP addresses to use as probing
        addresses to validate connectivity
    :ivar int standby_mode_period: Specifies the probe period when
        standby mode is used (in seconds)
    :ivar int standby_mode_timeout: probe timeout in seconds
    :ivar int active_mode_period: Specifies the probe period when active
        mode is used (in seconds)
    :ivar int active_mode_timeout: probe timeout in seconds
    """
    typeof = 'netlink'

    @classmethod
    def create(cls, name, gateway, network, input_speed=None,
               output_speed=None, domain_server_address=None,
               provider_name=None, probe_address=None,
               standby_mode_period=3600, standby_mode_timeout=30,
               active_mode_period=5, active_mode_timeout=1, comment=None):
        """
        Create a new netlink. Name, gateway and network values are all
        required fields.

        :param str name: name of netlink Element
        :param gateway: gateway to map this netlink to. This can be an element
            or str href.
        :type gateway: Router,Engine
        :param list network: network/s associated with this netlink.
        :type network: list(str,Element)
        :param int input_speed: input speed in Kbps, used for ratio-based
            load-balancing
        :param int output_speed: output speed in Kbps,  used for ratio-based
            load-balancing
        :param list domain_server_address: dns addresse for netlink. Engine
            DNS can override this field
        :type dns_addresses: list(str,Element)
        :param str provider_name: optional name to identify provider for this
            netlink
        :param list probe_address: list of IP addresses to use as probing
            addresses to validate connectivity
        :type probe_ip_address: list(str)
        :param int standby_mode_period: Specifies the probe period when
            standby mode is used (in seconds)
        :param int standby_mode_timeout: probe timeout in seconds
        :param int active_mode_period: Specifies the probe period when active
            mode is used (in seconds)
        :param int active_mode_timeout: probe timeout in seconds
        :raises ElementNotFound: if using type Element parameters that are
            not found.
        :raises CreateElementFailed: failure to create netlink with reason
        :return: instance with meta
        :rtype: StaticNetlink

        .. note:: To monitor the status of the network links, you must define
                  at least one probe IP address.
        """
        json = {'name': name,
                'gateway_ref': element_resolver(gateway),
                'ref': element_resolver(network),
                'input_speed': input_speed,
                'output_speed': output_speed,
                'probe_address': probe_address,
                'nsp_name': provider_name,
                'comment': comment,
                'standby_mode_period': standby_mode_period,
                'standby_mode_timeout': standby_mode_timeout,
                'active_mode_period': active_mode_period,
                'active_mode_timeout': active_mode_timeout}

        if domain_server_address:
            r = RankedDNSAddress([])
            r.add(domain_server_address)
            json.update(domain_server_address=r.entries)
        
        return ElementCreator(cls, json)
    
    @classmethod
    def update_or_create(cls, name, with_status=False, **kwargs):
        """
        Update or create static netlink. 
        
        :param str name: name of the static netlink to update or create
        :param dict kwargs: kwargs to satisfy the `create` constructor arguments
            if the element doesn't exist or attributes to change
        :return: element instance by type or 3-tuple if with_status set
        """
        updated, created = False, False
        try:
            element = cls.get(name)
            gateway = kwargs.pop('gateway', None)
            if gateway is not None and gateway != element.gateway:
                element.gateway = gateway
                updated = True
            
            for net in kwargs.pop('network', []):
                if net not in element.network:
                    element.data['ref'].append(element_resolver(net))
                    updated = True
            
            current_dns = len(element.domain_server_address)
            element.domain_server_address.append(
                kwargs.pop('domain_server_address', []))
            if len(element.domain_server_address) != current_dns:
                updated = True

            for name, value in kwargs.items():
                if getattr(element, name, None) != value:
                    #setattr(element, name, value)
                    element.data[name] = value
                    updated = True      
            
            if updated:
                element.update()

        except ElementNotFound:
            try:
                element = cls.create(name=name, **kwargs)
                created = True
            except TypeError:
                raise CreateElementFailed('%s: %r not found and missing '
                    'constructor arguments to properly create.' %
                    (cls.__name__, name))
        
        if with_status:
            return element, updated, created
        return element

    def add_network(self, network):
        """
        Add an additional network to this netlink. The network should be 
        an element of type Network or str href. Update to this will be 
        done after calling this method.
        
        :param str,Element network: network element to add to this static
            netlink
        :raises UpdateElementFailed: if update fails
        :return: None
        """
        network = element_resolver(network)
        self.data.get('ref', []).append(network)
        self.update()
    
    @property
    def network(self):
        """
        List of networks this static netlink uses.

        :return: networks associated with this netlink, as Element
        :rtype: Element
        """
        return [self.from_href(elem) for elem in self.data.get('ref')]

    @property
    def domain_server_address(self):
        """
        Configured DNS servers for this netlink

        :return: list of DNS servers; if elements are specifed, they will
            be returned as type Element
        :rtype: RankedDNSAddress
        """
        return RankedDNSAddress(self.data.get('domain_server_address'))
    
    @property
    def gateway(self):
        """
        The gateway (engine) that this netlink is used on. You can set
        the gateway by providing an element of type Engine or Router.

        :rtype: Element
        """
        return Element.from_href(self.data.get('gateway_ref'))
    
    @gateway.setter
    def gateway(self, value):
        self.data.update(gateway_ref=element_resolver(value))
    
    @property
    def networks(self):
        return self.network

#     def __setattr__(self, name, value):
#         if name in ('_meta', '_name') or name in dir(self):
#             return super(StaticNetlink, self).__setattr__(name, value)
#         else:
#             self.data[name] = value


class Multilink(Element):
    """
    You can use Multi-Link to distribute outbound traffic between multiple
    network connections and to provide High Availability and load balancing
    for outbound traffic.
    
    Creating a multilink requires several steps:
    
    * Create the static netlink/s
    * Create the multilink using the netlinks
    * Add the multilink to an outbound NAT rule
    
    Create the static netlink::
    
        StaticNetlink.create(
            name='isp1', 
            gateway=Router('nexthop'),     # 10.10.0.1
            network=[Network('comcast')],  # 10.10.0.0/16
            probe_address=['10.10.0.1'])
    
    Create the multilink members based on the pre-created netlinks. A multilink
    member specifies the ip range to use for source NAT, the role (active/standby)
    and obtains the defined network from the StaticNetlink::
    
        member = MultilinkMember.create(
            StaticNetlink('netlink1'), ip_range='1.1.1.1-1.1.1.2', role='active')
        
        member1 = MultilinkMember.create(
            StaticNetlink('netlink2'), ip_range='2.1.1.1-2.1.1.2', role='standby')

    Create the multilink using the multilink members::
    
        Multilink.create(name='internet', multilink_members=[member, member1])
    

    Lastly, add a NAT rule with dynamic source nat using the multilink::
    
        policy = FirewallPolicy('outbound')
        policy.fw_ipv4_nat_rules.create(
            name='mynat',
            sources=[Network('mynetwork')],
            destinations='any',
            services='any',
            dynamic_src_nat=Multilink('internet'))
       
    .. note:: Multi-Link is supported on Single Firewalls, Firewall Clusters,
        and Virtual Firewalls                 
    """
    typeof = 'outbound_multilink'
   
    @classmethod
    def create(cls, name, multilink_members, multilink_method='rtt', retries=2,
               timeout=3600, comment=None):
        """
        Create a new multilink configuration. Multilink requires at least
        one netlink for operation, although 2 or more are recommeneded.
        
        :param str name: name of multilink
        :param list multilink_members: the output of calling
            :func:`.multilink_member` to retrieve the proper formatting for
            this sub element.
        :param str multilink_method: 'rtt' or 'ratio'. If ratio is used, each
            netlink must have a probe IP address configured and also have
            input and output speed configured (default: 'rtt')
        :param int retries: number of keep alive retries before a destination
            link is considered unavailable (default: 2)
        :param int timeout: timeout between retries (default: 3600 seconds)
        :param str comment: comment for multilink (optional)
        :raises CreateElementFailed: failure to create multilink
        :rtype: Multilink
        """
        json = {'name': name,
                'comment': comment,
                'retries': retries,
                'timeout': timeout,
                'multilink_member': multilink_members,
                'multilink_method': multilink_method}
        
        return ElementCreator(cls, json)

    @classmethod
    def create_with_netlinks(cls, name, netlinks, **kwargs):
        """
        Create a multilink with a list of StaticNetlinks. To properly create
        the multilink using this method, pass a list of netlinks with the
        following dict structure::
        
            netlinks = [{'netlink': StaticNetlink,
                         'ip_range': 1.1.1.1-1.1.1.2,
                         'netlink_role': 'active'}]
        
        The `netlink_role` can be either `active` or `standby`. The remaining
        settings are resolved from the StaticNetlink. The IP range value must
        be an IP range within the StaticNetlink's specified network.
        Use kwargs to pass any additional arguments that are supported by the
        `create` constructor.
        A full example of creating a multilink using predefined netlinks::
        
            multilink = Multilink.create_with_netlinks(
                name='mynewnetlink',
                netlinks=[{'netlink': StaticNetlink('netlink1'),
                           'ip_range': '1.1.1.2-1.1.1.3',
                           'netlink_role': 'active'},
                          {'netlink': StaticNetlink('netlink2'),
                           'ip_range': '2.1.1.2-2.1.1.3',
                           'netlink_role': 'standby'}])
        
        :param StaticNetlink netlink: StaticNetlink element
        :param str ip_range: ip range for source NAT on this netlink
        :param str netlink_role: the role for this netlink, `active` or
            `standby`
        :raises CreateElementFailed: failure to create multilink
        :rtype: Multilink
        """
        multilink_members = []
        for member in netlinks:
            m = {'ip_range': member.get('ip_range'),
                 'netlink_role': member.get('netlink_role', 'active')}
            static_netlink = member.get('netlink')
            m.update(netlink_ref=static_netlink.href,
                     network_ref=static_netlink.data.get('ref')[0])
            multilink_members.append(m)
        
        return cls.create(name, multilink_members, **kwargs)
        
    @property
    def members(self):
        """
        Multilink members associated with this multilink. This provides a
        a reference to the existing netlinks and their member settings.
        
        :rtype: MultilinkMember
        """
        return [MultilinkMember(mm) for mm in self.multilink_member]


class MultilinkMember(NestedDict):
    """
    A multilink member represents an netlink member used on a multilink
    configuration. Multilink uses netlinks to specify settings specific
    to a connection, network, whether it should be active or standby and
    optionally QoS.
    Use this class to create mutlilink members that are required for
    creating a Multilink element.
    """
    def __init__(self, kwargs):
        super(MultilinkMember, self).__init__(data=kwargs)
    
    @property
    def ip_range(self):
        """
        Specifies the IP address range for dynamic source address
        translation (NAT) for the internal source IP addresses on the
        NetLink. Can also be set.

        :rtype: str
        """
        return self.get('ip_range')
    
    @ip_range.setter
    def ip_range(self, value):
        if '-' in value:
            self.update(ip_range=value)
    
    @property
    def netlink_role(self):
        """
        Shows whether the Netlink is active or standby.
        Active - traffic is routed through the NetLink according to the
        method you specify in the Outbound Multi-Link element properties.
        Standby - traffic is only routed through the netlink if all primary
        (active) netlinks are unavailable.
        
        :rtype: str
        """
        return self.get('netlink_role')
    
    @netlink_role.setter
    def netlink_role(self, value):
        if value in ('standby', 'active'):
            self.update(netlink_role=value)
    
    @property
    def network(self):
        """
        Specifies the Network element that represents the IP address
        space in the directly connected external network of the network
        link. Can also be set.
        
        :rtype: Network
        """
        return Element.from_href(self.get('network_ref'))
    
    @network.setter
    def network(self, value):
        self.update(network_ref=element_resolver(value))
    
    @property
    def netlink(self):
        """
        The static netlink referenced in this multilink member
        
        :rtype: StaticNetlink
        """
        return Element.from_href(self.get('netlink_ref'))

    @classmethod
    def create(cls, netlink, ip_range, role='active'):
        """
        Create a multilink member. Multilink members are added to an
        Outbound Multilink configuration and define the ip range, static
        netlink to use, and the role. This element can be passed to the
        Multilink constructor to simplify creation of the outbound multilink.
        
        :param StaticNetlink netlink: static netlink element to use as member
        :param str role: role of this netlink, 'active' or 'standby'
        :param str ip_range: the IP range for source NAT for this member. The
            IP range should be part of the defined network range used by this
            netlink.
        :raises ElementNotFound: Specified netlink could not be found
        :rtype: MultilinkMember
        """
        return cls(dict(
            netlink_ref=netlink.href,
            netlink_role=role,
            network_ref=netlink.network[0].href,
            ip_range=ip_range))
    
    def __repr__(self):
        return 'MultilinkMember(netlink={},netlink_role={},ip_range={})'.format(
            self.netlink, self.netlink_role, self.ip_range)  
    
        
def multilink_member(netlink, nat_range, netlink_network=None,
                     netlink_role='active'):
    """
    :param StaticNetlink netlink: netlink element for multilink member
    :param str nat_range: ip address range to use for NAT. This needs
        to be a range in the same network defined in the netlink
    :param str,Element netlink_network: netlink network when multiple
        networks are defined within a netlink. Only one network can be
        defined for each multilink member.
    :param str netlink_role: role for this netlink member. Values can
        be 'active' or 'standby' (default: 'active')
    :raises ElementNotFound: if provided netlink or netlink_network is
        not found.
    :return: member dict required for calling Multilink create
    :rtype: dict
    """
    member = {}
    member.update(netlink_ref=netlink.href)
    if len(netlink.networks) > 1: 
        if not netlink_network:
            raise MissingRequiredInput(
                'Netlink %r has more than one network defined. You must '
                'specify which network to use with the netlink_network '
                'parameter' % netlink.name)
        netlink_network = element_resolver(netlink_network)
        member.update(network_ref=netlink_network)
    else:
        member.update(network_ref=netlink.networks[0].href)

    member.update(ip_range=nat_range,
                  netlink_role=netlink_role)
    return member    
