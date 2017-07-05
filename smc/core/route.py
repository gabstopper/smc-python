"""
Route module encapsulates functions related to static routing and
related configurations on NGFW.
When retrieving routing, it is done from the engine context.

For example, retrieve all routing for an engine in context::

    >>> engine = Engine('sg_vm')
    >>> for route_node in engine.routing.all():
    ...   print(route_node)
    ...
    Routing(name=Interface 0,level=interface)
    Routing(name=Interface 1,level=interface)
    Routing(name=Interface 2,level=interface)
    Routing(name=Tunnel Interface 2000,level=interface)
    Routing(name=Tunnel Interface 2001,level=interface)

Routing nodes are nested, starting with the interface level. If nested
routes exist, you can iterate a given interface to get specific information::

    >>> interface = engine.routing.get(1)
    >>> for routes in interface.all():
    ...   print(routes)
    ...
    Routing(name=network-10.0.0.0/24,level=network)
    ...
    >>> for networks in interface.all():
    ...   networks
    ...   for gateways in networks.all():
    ...     print gateways, gateways.ip
    ...
    Routing(name=network-172.18.1.0/24,level=network)
    Routing(name=asus-wireless,level=gateway) 172.18.1.200

If BGP, OSPF or a Traffic Handler (netlink) needs to be added to an interface
that has multiple IP addresses assigned and you want to bind to only one, you
can provide the ``network`` parameter to ``add_`` methods. The network can be
obtained for an interface::

    >>> engine = Engine('sg_vm')
    >>> rnode = engine.routing.get(0)
    >>> for routes in rnode:
    ...   routes, routes.ip
    ... 
    (Routing(name=network-172.18.1.0/24,level=network), '172.18.1.0/24')

Then add using::

    >>> engine = Engine('sg_vm')
    >>> rnode = engine.routing.get(0)
    >>> rnode.add_traffic_handler(StaticNetlink('foo'), network='172.18.1.0/24')

.. note:: Not specifying ``network`` will bind OSPF, BGP or the Traffic Handler
    to all address assigned.

Adding a basic static route can be done from the engine directly if it is a
simple source network to destination route::

    engine.add_route(gateway='192.168.1.254/32', network='172.18.1.0/24')

The route gateway will be mapped to an interface with an address range in
the 192.168.1.x network automatically.
    
For more complex static routes such as ones that may use group elements, use
the routing node::

    >>> engine = Engine('ve-1')
    >>> itf = engine.routing.get(0)
    >>> itf.add_static_route(Router('tmprouter'), destination=[Group('routegroup')])

.. seealso:: :meth:`.Routing.add_static_route`
    
Routing node nesting can be represented as::

    interface
        | --> network
                |
                --> gateway

.. note::
    Adding OSPF and BGP is done at the interface level, however can still be applied only to a
    specific network if desired.
    
When changing are made to a routing node, i.e. adding OSPF, BGP, Netlink's, the configuration
is updated immediately.
"""
from collections import namedtuple
from smc.base.model import SubElement, SimpleElement
from smc.base.util import element_resolver


class Routing(SubElement):
    """
    Routing represents the Engine routing configuration and provides the
    ability to view and add features to routing nodes such as OSPF.
    """
    def __init__(self, data=None, **meta):
        super(Routing, self).__init__(**meta)
        if data is not None:
            self.data = SimpleElement(**data)
            
    def __iter__(self):
        for node in self.data['routing_node']:
            data = SimpleElement(**node)
            yield(Routing(
                    href=data.get_link('self'),
                    data=node))

    @property
    def name(self):
        """
        Interface name / ID for routing level

        :return: name of routing node
        :rtype: str
        """
        return self.data.get('name')

    @property
    def nicid(self):
        """
        NIC id for this interface

        :return str nic identifier
        """
        return self.data.get('nic_id')

    @property
    def dynamic_nicid(self):
        """
        NIC id for this dynamic interface
        
        :return str nic identifier
        """
        return self.data.get('dynamic_nicid')
    
    @property
    def ip(self):
        """
        IP network / host for this route

        :return: IP address of this routing level
        :rtype: str
        """
        return self.data.get('ip')

    @property
    def level(self):
        """
        Routing nodes have multiple 'levels' where routes can
        be nested. Most routes are placed at the interface level.
        This setting can mostly be ignored, but provides an
        informative view of how the route is nested.

        :return: routing node level (interface,network,gateway,any)
        :rtype: str
        """
        return self.data.get('level')

    def get(self, interface_id):
        """
        Obtain routing configuration for a specific interface by
        ID.

        .. note::
            If interface is a VLAN, you must use a str to specify the
            interface id, such as '3.13' (interface 3, VLAN 13)

        :param str,int interface_id: interface identifier
        :return: Routing element, or None if not found
        :rtype: Routing
        """
        for interface in iter(self):
            if interface.nicid == str(interface_id) or \
                interface.dynamic_nicid == str(interface_id):
                return interface     

    def add_traffic_handler(self, netlink, netlink_gw=None, network=None):
        """
        Add a traffic handler to a routing node. A traffic handler can be
        either a static netlink or a multilink traffic handler. If ``network``
        is not specified and the interface has multiple IP addresses, the 
        traffic handler will be added to all ipv4 addresses.
        
        Add a pre-defined netlink to the route table of interface 0::
        
            engine = Engine('vm')
            rnode = engine.routing.get(0)
            rnode.add_traffic_handler(StaticNetlink('mynetlink'))
        
        Add a pre-defined netlink only to a specific network on an interface
        with multiple addresses. Specify a netlink_gw for the netlink::
        
            rnode = engine.routing.get(0)
            rnode.add_traffic_handler(
                StaticNetlink('mynetlink'),
                netlink_gw=Router('myrtr'),
                network='172.18.1.0/24')
            
        :param StaticNetlink,Multilink netlink: netlink element
        :param Element netlink_gw: gateway for the netlink element. Can be
            None if no gateway is needed. Element type is typically of type
            :class:`smc.elements.network.Router`.
        :param str network: if network specified, only add OSPF to this network on interface
        :raises EngineCommandFailed: failure updating routing
        :raises ElementNotFound: ospf area not found
        :return: None
        """
        netlink = {
            'href': netlink.href,
            'level': 'gateway',
            'routing_node': [],
            'name': netlink.name}
        
        if netlink_gw:
            netlink_gateway = {
                'level': 'any',
                'href': netlink_gw.href,
                'name': netlink_gw.name}
        
            netlink['routing_node'].append(netlink_gateway)
    
        self._bind_to_ipv4_network(network, netlink)
        self.update()
        
    def add_ospf_area(self, ospf_area,
                      communication_mode='NOT_FORCED',
                      unicast_ref=None,
                      network=None):
        """
        Add OSPF Area to this routing node.

        Communication mode specifies how the interface will interact with the
        adjacent OSPF environment. Please see SMC API documentation for more
        in depth information on each option.

        If the interface has multiple networks nested below, all networks
        will receive the OSPF area by default unless the ``network`` parameter
        is specified. OSPF cannot be applied to IPv6 networks.

        Example of adding an area to interface routing node::

            area = OSPFArea('area0') #obtain area resource

            #Set on routing interface 0
            interface = engine.routing.get(0)
            interface.add_ospf_area(area)

        .. note:: If UNICAST is specified, you must also provide a unicast_ref
                  to identify the remote host

        :param OSPFArea ospf_area: OSPF area instance or href
        :param str communication_mode: NOT_FORCED|POINT_TO_POINT|PASSIVE|UNICAST
        :param Element unicast_ref: Element used as unicast gw (required for UNICAST)
        :param str network: if network specified, only add OSPF to this network
            on interface
        :raises EngineCommandFailed: failure updating routing
        :raises ElementNotFound: ospf area not found
        :return: None
        """
        communication_mode = communication_mode.upper()
        node = {
            'href': ospf_area.href,
            'communication_mode': communication_mode,
            'level': 'gateway',
            'routing_node': [],
            'name': ospf_area.name}
        
        if communication_mode == 'UNICAST':
            # Need a destination ref, add to sub routing_node
            node['routing_node'].append({
                'href': unicast_ref.href,
                'level': 'any',
                'name': unicast_ref.name})

        self._bind_to_ipv4_network(network, node)
        self.update()

    def add_bgp_peering(self, bgp_peering, external_bgp_peer,
                        network=None):
        """
        Add a BGP configuration to this routing interface. 
        If the interface has multiple ipaddresses, all networks will receive
        the BGP peering by default unless the ``network`` parameter is
        specified.
        
        Example of adding BGP to an interface by ID::

            interface = engine.routing.get(0)
            interface.add_bgp_peering(
                BGPPeering('mypeer'),
                ExternalBGPPeer('neighbor'))

        :param BGPPeering bgp_peering: BGP Peer element
        :param ExternalBGPPeer external_bgp_peer: peer element or href
        :param str network: if network specified, only add OSPF to this network
            on interface
        :raises UpdateElementFailed: failed to add BGP
        :return: None
        """
        bgp = {
            'href': bgp_peering.href,
            'level': 'gateway',
            'routing_node': [],
            'name': bgp_peering.name}

        external_peer = {
            'href': external_bgp_peer.href,
            'level': 'any',
            'name': external_bgp_peer.name}
        
        bgp['routing_node'].append(external_peer)
        
        self._bind_to_ipv4_network(network, bgp)
        self.update()

    def add_static_route(self, gateway, destination,
                         network=None):
        """
        Add a static route to this route table. Destination can be any element
        type supported in the routing table such as a Group of network members.
        ::

            >>> engine = Engine('ve-1')
            >>> itf = engine.routing.get(0)
            >>> itf.add_static_route(
                    gateway=Router('tmprouter'),
                    destination=[Group('routegroup')])
        
        :param Element gateway: gateway for this route (Router, Host)
        :param Element destination: destination network/s for this route.
        :type destination: list(Host, Router, ..)
        :raises UpdateElementFailed: failure to update routing table
        :return: None
        """
        route = {
            'href': gateway.href,
            'level': 'gateway',
            'routing_node': [],
            'name': gateway.name}
        
        for dest in destination:
            route['routing_node'].append({
                'href': dest.href,
                'level': 'any',
                'name': dest.name})            
        
        self._bind_to_ipv4_network(network, route)
        self.update()
    
    def add_dynamic_gateway(self, networks):
        """
        A dynamic gateway object is a router that is attached to
        a DHCP interface. You can associate networks with this gateway
        address to identify networks on this interface.
        ::
        
            route = engine.routing.get(0)
            route.add_dynamic_gateway([Network('mynetwork')])
        
        :param list Network: list of network elements to add to
            this gateway
        :return: None
        """
        route = {
            'dynamic_classid': 'gateway',
            'level': 'gateway',
            'routing_node': []}
        
        for network in networks:
            route['routing_node'].append({
                'href': network.href,
                'level': 'any',
                'name': network.name})
        
        for networks in iter(self):
            networks.data['routing_node'].append(route)
        
        self.update()
            
    def _bind_to_ipv4_network(self, network, element):
        for networks in iter(self):
            if len(networks.ip.split(':')) == 1:  # Skip IPv6
                if network is not None:  # Only place on specific network
                    if networks.ip == network:
                        networks.data['routing_node'].append(element)
                else:
                    networks.data['routing_node'].append(element)
                        
    def remove_route_element(self, element, network=None):
        """
        Remove a route element by href or Element. Use this if you want to
        remove a netlink or a routing element such as BGP or OSPF. Removing
        is done from within the routing interface context.
        ::
        
            rnode = engine.routing.get(0)
            rnode.remove_route_element(StaticNetlink('mynetlink'))
            
        Only from a specific network on a multi-address interface::
        
            rnode.remove_route_element(
                StaticNetlink('mynetlink'),
                network='172.18.1.0/24')
        
        :param str,Element element: element to remove from this routing node
        :param str network: if network specified, only add OSPF to this
            network on interface
        :raises UpdateElementFailed: failed to remove route element
        :return: None
        """
        element = element_resolver(element)
        routing_node = []
        for networks in iter(self):
            if network is not None:
                if networks.ip != network:
                    routing_node.append(networks.data)
                else:
                    rnode = [gw for gw in networks.data['routing_node']
                             if gw.get('href') != element]
                    networks.data['routing_node'] = rnode
                    routing_node.append(networks.data)          
            else:
                rnode = [gw for gw in networks.data['routing_node']
                         if gw.get('href') != element]
                networks.data['routing_node'] = rnode
                routing_node.append(networks.data)
            
        self.data['routing_node'] = routing_node
        self.update()
                    
    def all(self):
        """
        Return all routes for this engine.

        :return: current route entries as :class:`.Routing` element
        :rtype: list
        """
        return [node for node in iter(self)]

    def __str__(self):
        return '{0}(name={1},level={2})'.format(
            self.__class__.__name__, self.name, self.level)

    def __repr__(self):
        return str(self)


def routetuple(d):
    d.pop('cluster_ref', None)
    routes = namedtuple('Route', d.keys())
    return routes(**d)


class Routes(object):
    """
    Routes are represented by a query to the SMC for the
    specified engine. This represents the current routing
    table.
    Route are obtained through the following method::

        for routes in engine.routing_monitoring.all():
            print(routes)

    Routes have the following attributes:

    :ivar int src_if: The source IF of the routing entry
    :ivar int dst_if: The destination IF of the routing entry
    :ivar str route_type: Route type specifies status (Static, Connected, etc)
    :ivar str route_network: The route network address
    :ivar int route_netmask: Network mask
    :ivar str route_gateway: The route gateway address

    .. note:: Not all attributes may be present.
    """

    def __init__(self, data):
        self._data = data

    def __iter__(self):
        for route in self._data['routing_monitoring_entry']:
            yield routetuple(route)

    def all(self):
        return [r for r in iter(self)]


class Antispoofing(SubElement):
    """
    Anti-spoofing is configured by default based on
    interface networks directly attached. It is possible
    to override these settings by adding additional
    networks as valid source networks on a given
    interface.

    Antispoofing is nested similar to routes. Iterate the
    antispoofing configuration::

        for entry in engine.antispoofing.all():
            print(entry)
    """

    def __init__(self, data=None, **meta):
        super(Antispoofing, self).__init__(**meta)
        if data is not None:
            self.data = SimpleElement(**data)

    def __iter__(self):
        for node in self.data['antispoofing_node']:
            data = SimpleElement(**node)
            yield(Antispoofing(
                    href=data.get_link('self'),
                    data=node))
            
    @property
    def name(self):
        """
        Name on this node level
        """
        return self.data.get('name')

    @property
    def ip(self):
        """
        IP network / address / host of this antispoofing entry

        :return: IP Address of this antispoofing node
        :rtype: str
        """
        return self.data.get('ip')

    @property
    def level(self):
        """
        Routing nodes have multiple 'levels' where routes can
        be nested. Most routes are placed at the interface level.
        This setting can mostly be ignored, but provides an
        informative view of how the route is nested.

        :return: routing node level (interface,network,gateway,any)
        :rtype: str
        """
        return self.data.get('level')

    @property
    def validity(self):
        """
        Enabled or disabled antispoofing entry

        :return: validity of this entry (enable,disable,absolute)
        :rtype: str
        """
        return self.data.get('validity')

    @property
    def nicid(self):
        """
        NIC id for this interface

        :return str nic identifier
        """
        return self.data.get('nic_id')

    def add(self, entry):
        """
        Add an entry to this antispoofing node level.
        Entry can be either href or network elements specified
        in :py:class:`smc.elements.network`
        ::

            for entry in engine.antispoofing.all():
                if entry.name == 'Interface 0':
                    entry.add(Network('network-10.1.2.0/24'))

        :param Element entry: entry to add, i.e. Network('mynetwork'), Host(..)
        :return: None
        :raises CreateElementFailed: failed adding entry
        :raises ElementNotFound: element entry specified not in SMC
        """
        node = {
            'antispoofing_node': [],
            'auto_generated': 'false',
            'href': entry.href,
            'level': self.level,
            'validity': 'enable',
            'name': entry.name}

        self.data['antispoofing_node'].append(node)
        self.update()

    def all(self):
        return [node for node in iter(self)]

    def __str__(self):
        return '{0}(name={1},level={2})'.format(
            self.__class__.__name__, self.name, self.level)

    def __repr__(self):
        return str(self)
