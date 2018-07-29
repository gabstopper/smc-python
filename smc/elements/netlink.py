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

Creating Multilink's require that you first have StaticNetlink or DynamicNetlink
elements. Once you have this created, you can create a multilink in a two step
process.

First create the multilink members specifying the created netlinks. A multilink
member encapsulates the creation process and collects the required information for
each netlink such as ip_range to use for source NAT (static netlink only) and
the network role::

    member = MultilinkMember.create(
        StaticNetlink('netlink1'), ip_range='1.1.1.1-1.1.1.2', netlink_role='active')
        
    member1 = MultilinkMember.create(
        StaticNetlink('netlink2'), ip_range='2.1.1.1-2.1.1.2', netlink_role='standby')

Then create the multilink specifying the multilink members::
    
        Multilink.create(name='internet', multilink_members=[member, member1])

.. seealso:: :class:`~Multilink`    
"""
from smc.base.model import Element, ElementCreator, ElementCache, ElementRef,\
    ElementList
from smc.base.util import element_resolver
from smc.core.general import RankedDNSAddress


class StaticNetlink(Element):
    """
    A Static Netlink is applied to an interface to provide an alternate
    route to a destination. It is typically used when you have fixed IP
    interfaces versus using DHCP (use a Dynamic NetLink).
    
    :ivar Router,Engine gateway: gateway for this netlink. Should be
        the 'next hop' element associated with the netlink
    :ivar list(Network) network: list of networks associated with this
        netlink
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
    gateway = ElementRef('gateway_ref')
    network = ElementList('ref')

    @classmethod
    def create(cls, name, gateway, network, input_speed=None,
               output_speed=None, domain_server_address=None,
               provider_name=None, probe_address=None,
               standby_mode_period=3600, standby_mode_timeout=30,
               active_mode_period=5, active_mode_timeout=1, comment=None):
        """
        Create a new StaticNetlink to be used as a traffic handler.

        :param str name: name of netlink Element
        :param gateway_ref: gateway to map this netlink to. This can be an element
            or str href.
        :type gateway_ref: Router,Engine
        :param list ref: network/s associated with this netlink.
        :type ref: list(str,Element)
        :param int input_speed: input speed in Kbps, used for ratio-based
            load-balancing
        :param int output_speed: output speed in Kbps,  used for ratio-based
            load-balancing
        :param list domain_server_address: dns addresses for netlink. Engine
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
    def update_or_create(cls, with_status=False, **kwargs):
        """
        Update or create static netlink. DNS entry differences are not
        resolved, instead any entries provided will be the final state
        for this netlink. If the intent is to add/remove DNS entries
        you can use the :meth:`~domain_server_address` method to add
        or remove.
        
        :raises CreateElementFailed: failed creating element
        :return: element instance by type or 3-tuple if with_status set
        """
        dns_address = kwargs.pop('domain_server_address', [])
        element, updated, created = super(StaticNetlink, cls).update_or_create(
            with_status=True, defer_update=True, **kwargs)
        if not created:
            if dns_address:
                new_entries = RankedDNSAddress([])
                new_entries.add(dns_address)
                element.data.update(domain_server_address=new_entries.entries)
                updated = True
        if updated:
            element.update()
        if with_status:
            return element, updated, created
        return element

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
    def networks(self):
        return self.network


class DynamicNetlink(Element):
    """
    A Dynamic Netlink is automatically created when an interface is using
    DHCP to obtain it's network address. It is also possible to manually
    create a dynamic netlink.
    
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
    :ivar bool learn_dns_automatically: whether to obtain the DNS server
        address from the DHCP lease
    """
    typeof = 'dynamic_netlink'
    
    @classmethod
    def create(cls, name, input_speed=None, learn_dns_automatically=True,
               output_speed=None, provider_name=None, probe_address=None,
               standby_mode_period=3600, standby_mode_timeout=30,
               active_mode_period=5, active_mode_timeout=1, comment=None):
        """
        Create a Dynamic Netlink.

        :param str name: name of netlink Element
        :param int input_speed: input speed in Kbps, used for ratio-based
            load-balancing
        :param int output_speed: output speed in Kbps,  used for ratio-based
            load-balancing
        :param bool learn_dns_automatically: whether to obtain DNS automatically
            from the DHCP interface
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
        :raises CreateElementFailed: failure to create netlink with reason
        :rtype: DynamicNetlink

        .. note:: To monitor the status of the network links, you must define
                  at least one probe IP address.
        """
        json = {'name': name,
                'input_speed': input_speed,
                'output_speed': output_speed,
                'probe_address': probe_address,
                'nsp_name': provider_name,
                'comment': comment,
                'standby_mode_period': standby_mode_period,
                'standby_mode_timeout': standby_mode_timeout,
                'active_mode_period': active_mode_period,
                'active_mode_timeout': active_mode_timeout,
                'learn_dns_server_automatically': learn_dns_automatically}

        return ElementCreator(cls, json)
    

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
            StaticNetlink('netlink1'), ip_range='1.1.1.1-1.1.1.2', netlink_role='active')
        
        member1 = MultilinkMember.create(
            StaticNetlink('netlink2'), ip_range='2.1.1.1-2.1.1.2', netlink_role='standby')

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
        
        :param StaticNetlink,DynamicNetlink netlink: StaticNetlink element
        :param str ip_range: ip range for source NAT on this netlink
        :param str netlink_role: the role for this netlink, `active` or
            `standby`
        :raises CreateElementFailed: failure to create multilink
        :rtype: Multilink
        """
        multilink_members = []
        for member in netlinks:
            m = {'ip_range': member.get('ip_range', '0.0.0.0'),
                 'netlink_role': member.get('netlink_role', 'active')}
            netlink = member.get('netlink')
            m.update(netlink_ref=netlink.href)
            if netlink.typeof == 'netlink':
                m.update(network_ref=netlink.data.get('ref')[0])
            multilink_members.append(m)
        
        return cls.create(name, multilink_members, **kwargs)
    
    @classmethod
    def update_or_create(cls, with_status=False, **kwargs):
        element, updated, created = super(Multilink, cls).update_or_create(
            with_status=True, defer_update=True, **kwargs)
        if not created:
            multilink_members = kwargs.pop('multilink_members', [])
            if multilink_members:
                if set(multilink_members) ^ set(element.members):
                    element.data['multilink_member'] = multilink_members    
                    updated = True
        if updated:
            element.update()
        if with_status:
            return element, updated, created
        return element
            
    @property
    def members(self):
        """
        Multilink members associated with this multilink. This provides a
        a reference to the existing netlinks and their member settings.
        
        :rtype: MultilinkMember
        """
        return [MultilinkMember(mm) for mm in self.multilink_member]


class MultilinkMember(object):
    """
    A multilink member represents an netlink member used on a multilink
    configuration. Multilink uses netlinks to specify settings specific
    to a connection, network, whether it should be active or standby and
    optionally QoS.
    Use this class to create mutlilink members that are required for
    creating a Multilink element.
    
    :ivar Network network: network element reference specifying netlink subnet
    :ivar StaticNetlink,DynamicNetlink netlink: netlink element reference
    """
    network = ElementRef('network_ref')
    netlink = ElementRef('netlink_ref')
    
    def __init__(self, kwargs):
        self.data = ElementCache(kwargs)
    
    def __eq__(self, other):
        return all([
            self.ip_range == other.ip_range,
            self.netlink_role == other.netlink_role,
            self.data.get('network_ref') == other.data.get('network_ref'),
            self.data.get('netlink_ref') == other.data.get('netlink_ref')
            ])
    
    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash((self.ip_range, self.netlink_role,
            self.data.get('network_ref'), self.data.get('netlink_ref')))
    
    @property
    def ip_range(self):
        """
        Specifies the IP address range for dynamic source address
        translation (NAT) for the internal source IP addresses on the
        NetLink. Can also be set.

        :rtype: str
        """
        return self.data.get('ip_range')
    
    @ip_range.setter
    def ip_range(self, value):
        if '-' in value:
            self.data.update(ip_range=value)
    
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
        return self.data.get('netlink_role')
    
    @netlink_role.setter
    def netlink_role(self, value):
        if value in ('standby', 'active'):
            self.data.update(netlink_role=value)

    @classmethod
    def create(cls, netlink, ip_range=None, netlink_role='active'):
        """
        Create a multilink member. Multilink members are added to an
        Outbound Multilink configuration and define the ip range, static
        netlink to use, and the role. This element can be passed to the
        Multilink constructor to simplify creation of the outbound multilink.
        
        :param StaticNetlink,DynamicNetlink netlink: static netlink element to
            use as member
        :param str ip_range: the IP range for source NAT for this member. The
            IP range should be part of the defined network range used by this
            netlink. Not required for dynamic netlink
        :param str netlink_role: role of this netlink, 'active' or 'standby'
        :raises ElementNotFound: Specified netlink could not be found
        :rtype: MultilinkMember
        """
        member_def = dict(
            netlink_ref=netlink.href,
            netlink_role=netlink_role,
            ip_range=ip_range if netlink.typeof == 'netlink' else '0.0.0.0')
        if netlink.typeof == 'netlink': # static netlink vs dynamic netlink
            member_def.update(network_ref=netlink.network[0].href)
            
        return cls(member_def)
    
    def __repr__(self):
        return 'MultilinkMember(netlink={},netlink_role={},ip_range={})'.format(
            self.netlink, self.netlink_role, self.ip_range)  

