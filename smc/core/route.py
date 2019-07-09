"""
Route module encapsulates functions related to static routing and
related configurations on NGFW.
When retrieving routing, it is done from the engine context.

For example, retrieve all routing for an engine in context::

    >>> engine = Engine('sg_vm')
    >>> for route_node in engine.routing:
    ...   print(route_node)
    ...
    Routing(name=Interface 0,level=interface)
    Routing(name=Interface 1,level=interface)
    Routing(name=Interface 2,level=interface)
    Routing(name=Tunnel Interface 2000,level=interface)
    Routing(name=Tunnel Interface 2001,level=interface)

Routing nodes are nested, starting with the engine level. 
Routing node nesting is made up of 'levels' and can be
represented as a tree::

    engine (root)
        |
        --> interface
                | 
                --> network
                        |
                        --> gateway
                                |
                                --> any

You can get a representation of the routing or antispoofing tree nodes
by calling as_tree::

    >>> print(engine.routing.as_tree())
    Routing(name=myfw,level=engine_cluster)
    --Routing(name=Interface 0,level=interface)
    ----Routing(name=network-1.1.1.0/24,level=network)
    ------Routing(name=mypeering,level=gateway)
    ------Routing(name=mynetlink,level=gateway)
    --------Routing(name=router-1.1.1.1,level=any)
    ------Routing(name=mystatic,level=gateway)
    --Routing(name=Interface 1,level=interface)
    ----Routing(name=network-10.10.10.0/24,level=network)
    ------Routing(name=anotherpeering,level=gateway)
    --Routing(name=Tunnel Interface 1000,level=interface)
    ----Routing(name=network-2.2.2.0/24,level=network)
    --Routing(name=Tunnel Interface 1001,level=interface)
    --Routing(name=Interface 2,level=interface)
    ----Routing(name=Network (IPv4),level=network)
    ------Routing(name=dynamic_netlink-myfw-Interface 2,level=gateway)
    --------Routing(name=Any network,level=any)

If nested routes exist, you can iterate a given node to get specific
information::

    >>> interface = engine.routing.get(1)
    >>> for routes in interface:
    ...   print(routes)
    ...
    Routing(name=network-10.0.0.0/24,level=network)
    ...
    >>> for networks in interface:
    ...   networks
    ...   for gateways in networks:
    ...     print gateways, gateways.ip
    ...
    Routing(name=network-172.18.1.0/24,level=network)
    Routing(name=asus-wireless,level=gateway) 172.18.1.200

If BGP, OSPF or a Traffic Handler (netlink) need to be added to an interface
that has multiple IP addresses assigned and you want to bind to only one, you
can provide the ``network`` parameter to ``add_`` methods. The network can be
obtained for an interface::

    >>> engine = Engine('sg_vm')
    >>> interface0 = engine.routing.get(0)
    >>> for network in interface0:
    ...   network, network.ip
    ... 
    (Routing(name=network-172.18.1.0/24,level=network), '172.18.1.0/24')

Then add using::

    >>> engine = Engine('sg_vm')
    >>> interface0 = engine.routing.get(0)
    >>> interface0.add_traffic_handler(StaticNetlink('foo'), network='172.18.1.0/24')

.. note:: If the ``network`` keyword is omitted and the interface has multiple
    IP addresses assigned, this will bind OSPF, BGP or the Traffic Handler
    to all address assigned.

Adding a basic static route can be done from the engine directly if it is a
simple source network to destination route::

    engine.add_route(gateway='192.168.1.254/32', network='172.18.1.0/24')

The route gateway will be mapped to an interface with an address range in
the 192.168.1.x network automatically.
    
For more complex static routes such as ones that may use group elements, use
the routing node::

    >>> engine = Engine('ve-1')
    >>> interface0 = engine.routing.get(0)
    >>> interface0.add_static_route(Router('tmprouter'), destination=[Group('routegroup')])

When a routing gateway is added to an IPv6 network, the gateway is validated before
adding. For example, if you have a single interface that has both an IPv4 and IPv6
address assigned, a static route using a Router gateway with only an IPv4 address will
only bind to the IPv4 network. In this case, you can optionally add both an IPv4 and
IPv6 to the router element, or run this operation for each network respectively.

.. seealso:: :meth:`.Routing.add_static_route`

.. note:: When changing are made to a routing node, i.e. adding OSPF, BGP, Netlink's, the
    configuration is updated immediately without calling .update()
"""
import collections
from smc.base.model import SubElement, Element, ElementCache
from smc.base.util import element_resolver
from smc.api.exceptions import InterfaceNotFound, ModificationAborted
from smc.base.structs import SerializedIterable


def flush_parent_cache(node):
    """
    Flush parent cache will recurse back up the tree and
    wipe the cache from each parent node reference on the
    given element. This allows the objects to be reused
    and a clean way to force the object to update itself
    if attributes or methods are referenced after update.
    """
    if node._parent is None:
        node._del_cache()
        return
    node._del_cache()
    flush_parent_cache(node._parent)


class RoutingTree(SubElement):
    """
    RoutingTree is the base class for both Routing and Antispoofing nodes.
    This provides a commmon API for operations that affect how routing table
    and antispoofing operate.
    """
    def __init__(self, data=None, **meta):
        super(RoutingTree, self).__init__(**meta)
        if data is not None:
            self.data = ElementCache(data)
    
    def __iter__(self):
        for node in self.data[self.typeof]:
            data = ElementCache(node)
            yield(self.__class__(
                    href=data.get_link('self'),
                    type=self.__class__.__name__,
                    data=node,
                    parent=self))
    
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

        :return: nic identifier
        :rtype: str
        """
        return self.data.get('nic_id')

    @property
    def dynamic_nicid(self):
        """
        NIC id for this dynamic interface
        
        :return: nic identifier, if this is a DHCP interface
        :rtype: str or None
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
    
    @property
    def related_element_type(self):
        """
        .. versionadded:: 0.6.0
            Requires SMC version >= 6.4
            
        Related element type defines the 'type' of element at this
        routing or antispoofing node level.
        
        :rtype: str
        """
        if 'related_element_type' in self.data:
            return self.data.get('related_element_type')
        return None if self.dynamic_nicid or (self.nicid and '.' in self.nicid) else \
            Element.from_href(self.data.get('href')).typeof # pre-6.4
        
    def as_tree(self, level=0):
        """
        Display the routing tree representation in string
        format
        
        :rtype: str
        """
        ret = '--' * level + repr(self) + '\n'
        for routing_node in self:
            ret += routing_node.as_tree(level+1)
        return ret
    
    def get(self, interface_id):
        """
        Obtain routing configuration for a specific interface by
        ID.

        .. note::
            If interface is a VLAN, you must use a str to specify the
            interface id, such as '3.13' (interface 3, VLAN 13)

        :param str,int interface_id: interface identifier
        :raises InterfaceNotFound: invalid interface for engine
        :return: Routing element, or None if not found
        :rtype: Routing
        """
        for interface in self:
            if interface.nicid == str(interface_id) or \
                interface.dynamic_nicid == str(interface_id):
                return interface
        raise InterfaceNotFound('Specified interface {} does not exist on '
            'this engine.'.format(interface_id))
    
    def delete(self):
        super(RoutingTree, self).delete()
        flush_parent_cache(self._parent)
        
    def update(self):
        super(RoutingTree, self).update()
        flush_parent_cache(self._parent)
    
    def all(self):
        """
        Return all routes for this engine.

        :return: current route entries as :class:`.Routing` element
        :rtype: list
        """
        return [node for node in self]

    def __str__(self):
        return '{}(name={},level={},type={})'.format(
            self.__class__.__name__, self.name, self.level, self.related_element_type)

    def __repr__(self):
        return str(self)


class Routing(RoutingTree):
    """
    Routing represents the Engine routing configuration and provides the
    ability to view and add features to routing nodes such as OSPF.
    """
    typeof = 'routing_node'
        
    def __init__(self, data=None, **meta):
        self._parent = meta.pop('parent', None)
        super(Routing, self).__init__(data, **meta)
    
    @property
    def routing_node_element(self):
        """
        A routing node element will reference the element used to represent
        the node (i.e. router, host, network, netlink, bgp peering, etc).
        Although the routing node already resolves the element and provides
        the `ip` property to obtain the address/network, use this property
        to obtain access to modifying the element itself::
        
            >>> interface0 = engine.routing.get(0)
            >>> for networks in interface0:
            ...   for gateway in networks:
            ...     gateway.routing_node_element
            ... 
            Router(name=router-1.1.1.1)
            StaticNetlink(name=mystatic)
            BGPPeering(name=anotherpeering)
            BGPPeering(name=mypeering)
            >>> 
        """
        return from_meta(self)
    
    @property
    def bgp_peerings(self):
        """
        BGP Peerings applied to a routing node. This can be called from
        the engine, interface or network level. Return is a tuple
        of (interface, network, bgp_peering). This simplifies viewing
        and removing BGP Peers from the routing table::
        
            >>> for bgp in engine.routing.bgp_peerings:
            ...   bgp
            ... 
            (Routing(name=Interface 0,level=interface,type=physical_interface),
             Routing(name=network-1.1.1.0/24,level=network,type=network),
             Routing(name=mypeering,level=gateway,type=bgp_peering))
            (Routing(name=Interface 1,level=interface,type=physical_interface),
             Routing(name=network-2.2.2.0/24,level=network,type=network),
             Routing(name=mypeering,level=gateway,type=bgp_peering))
        
        .. seealso:: :meth:`~netlinks` and :meth:`~ospf_areas` for obtaining
            other routing element types
        
        :rtype: tuple(Routing)
        """
        return gateway_by_type(self, 'bgp_peering')
    
    @property
    def netlinks(self):
        """
        Netlinks applied to a routing node. This can be called
        from the engine, interface or network level. Return is a
        tuple of (interface, network, netlink). This simplifies
        viewing and removing Netlinks from the routing table::
        
            >>> interface = engine.routing.get(1)
            >>> for static_netlink in interface.netlinks:
            ...   interface, network, netlink = static_netlink
            ...   netlink
            ...   netlink.delete()
            ... 
            Routing(name=mylink,level=gateway,type=netlink)
            
        .. seealso:: :meth:`~bgp_peerings` and :meth:`~ospf_areas` for obtaining
            other routing element types
        
        :rtype: tuple(Routing)
        """
        return gateway_by_type(self, 'netlink')
    
    @property
    def ospf_areas(self):
        """
        OSPFv2 areas applied to a routing node. This can be called from
        the engine, interface or network level. Return is a tuple
        of (interface, network, bgp_peering). This simplifies viewing
        and removing BGP Peers from the routing table::
        
            >>> for ospf in engine.routing.ospf_areas:
            ...   ospf
            ... 
            (Routing(name=Interface 0,level=interface,type=physical_interface),
             Routing(name=network-1.1.1.0/24,level=network,type=network),
             Routing(name=area10,level=gateway,type=ospfv2_area))
        
        .. seealso:: :meth:`~bgp_peerings` and :meth:`~netlinks` for obtaining
            other routing element types
        
        :rtype: tuple(Routing)
        """
        return gateway_by_type(self, 'ospfv2_area')
            
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
                netlink_gw=[Router('myrtr'), Host('myhost')],
                network='172.18.1.0/24')
            
        :param StaticNetlink,Multilink netlink: netlink element
        :param list(Element) netlink_gw: list of elements that should be destinations
            for this netlink. Typically these may be of type host, router, group, server,
            network or engine. 
        :param str network: if network specified, only add OSPF to this network on interface
        :raises UpdateElementFailed: failure updating routing
        :raises ModificationAborted: Change must be made at the interface level
        :raises ElementNotFound: ospf area not found
        :return: Status of whether the route table was updated
        :rtype: bool
        """
        routing_node_gateway = RoutingNodeGateway(netlink,
            destinations=[] if not netlink_gw else netlink_gw)
        return self._add_gateway_node('netlink', routing_node_gateway, network)

    def add_ospf_area(self, ospf_area, ospf_interface_setting=None, network=None,
                      communication_mode='not_forced', unicast_ref=None):
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

        .. note:: If unicast is specified, you must also provide a unicast_ref
                  of element type Host to identify the remote host. If no
                  unicast_ref is provided, this is skipped

        :param OSPFArea ospf_area: OSPF area instance or href
        :param OSPFInterfaceSetting ospf_interface_setting: used to override the
            OSPF settings for this interface (optional)
        :param str network: if network specified, only add OSPF to this network
            on interface
        :param str communication_mode: not_forced|point_to_point|passive|unicast
        :param Element unicast_ref: Element used as unicast gw (required for unicast)
        :raises ModificationAborted: Change must be made at the interface level
        :raises UpdateElementFailed: failure updating routing
        :raises ElementNotFound: ospf area not found
        :return: Status of whether the route table was updated
        :rtype: bool
        """
        communication_mode = communication_mode.lower()
        destinations=[] if not ospf_interface_setting else [ospf_interface_setting]
        if communication_mode == 'unicast' and unicast_ref:
            destinations.append(unicast_ref)
        routing_node_gateway = RoutingNodeGateway(
            ospf_area, communication_mode=communication_mode,
            destinations=destinations)
        return self._add_gateway_node('ospfv2_area', routing_node_gateway, network)

    def add_bgp_peering(self, bgp_peering, external_bgp_peer=None,
                        network=None):
        """
        Add a BGP configuration to this routing interface. 
        If the interface has multiple ip addresses, all networks will receive
        the BGP peering by default unless the ``network`` parameter is
        specified.
        
        Example of adding BGP to an interface by ID::

            interface = engine.routing.get(0)
            interface.add_bgp_peering(
                BGPPeering('mypeer'),
                ExternalBGPPeer('neighbor'))

        :param BGPPeering bgp_peering: BGP Peer element
        :param ExternalBGPPeer,Engine external_bgp_peer: peer element or href
        :param str network: if network specified, only add OSPF to this network
            on interface
        :raises ModificationAborted: Change must be made at the interface level
        :raises UpdateElementFailed: failed to add BGP
        :return: Status of whether the route table was updated
        :rtype: bool
        """
        destination = [external_bgp_peer] if external_bgp_peer else []
        routing_node_gateway = RoutingNodeGateway(bgp_peering,
            destinations=destination)
        return self._add_gateway_node('bgp_peering', routing_node_gateway, network)

    def add_static_route(self, gateway, destination, network=None):
        """
        Add a static route to this route table. Destination can be any element
        type supported in the routing table such as a Group of network members.
        Since a static route gateway needs to be on the same network as the
        interface, provide a value for `network` if an interface has multiple
        addresses on different networks.
        ::

            >>> engine = Engine('ve-1')
            >>> itf = engine.routing.get(0)
            >>> itf.add_static_route(
                    gateway=Router('tmprouter'),
                    destination=[Group('routegroup')])
        
        :param Element gateway: gateway for this route (Router, Host)
        :param Element destination: destination network/s for this route.
        :type destination: list(Host, Router, ..)
        :raises ModificationAborted: Change must be made at the interface level
        :raises UpdateElementFailed: failure to update routing table
        :return: Status of whether the route table was updated
        :rtype: bool
        """
        routing_node_gateway = RoutingNodeGateway(gateway,
            destinations=destination)     
        return self._add_gateway_node('router', routing_node_gateway, network)

    def add_dynamic_gateway(self, networks):
        """
        A dynamic gateway object creates a router object that is 
        attached to a DHCP interface. You can associate networks with
        this gateway address to identify networks for routing on this
        interface.
        ::
        
            route = engine.routing.get(0)
            route.add_dynamic_gateway([Network('mynetwork')])
        
        :param list Network: list of network elements to add to
            this DHCP gateway
        :raises ModificationAborted: Change must be made at the interface level
        :raises UpdateElementFailed: failure to update routing table
        :return: Status of whether the route table was updated
        :rtype: bool
        """
        routing_node_gateway = RoutingNodeGateway(dynamic_classid='gateway',
            destinations=networks or [])
        return self._add_gateway_node('dynamic_netlink', routing_node_gateway)
    
    def _add_gateway_node_on_tunnel(self, routing_node_gateway):
        """
        Add a gateway node on a tunnel interface. Tunnel interface elements
        are attached to the interface level and not directly nested under
        the networks node.
        
        :param RouteNodeGateway routing_node_gateway: routing node gateway instance
        :return: Whether a change was made or not
        :rtype: bool
        """
        modified = False
        peering = [next_hop for next_hop in self
            if next_hop.routing_node_element == routing_node_gateway.routing_node_element]
        if not peering:
            self.data.setdefault('routing_node', []).append( 
                routing_node_gateway)
            modified = True
        # Have peering
        else:
            peers = [node.routing_node_element for peer in peering
                for node in peer]
            for destination in routing_node_gateway.destinations:
                if destination not in peers:
                    peering[0].data.setdefault('routing_node', []).append(
                        {'level': 'any', 'href': destination.href,
                         'name': destination.name})
                    modified = True
        if modified:
            self.update()
        return modified

    def _add_gateway_node(self, gw_type, routing_node_gateway, network=None):
        """
        Add a gateway node to existing routing tree. Gateways are only added if
        they do not already exist. If they do exist, check the destinations of
        the existing gateway and add destinations that are not already there.
        A current limitation is that if a gateway doesn't exist and the
        destinations specified do not have IP addresses that are valid, they
        are still added (i.e. IPv4 gateway with IPv6 destination is considered
        invalid).
        
        :param Routing self: the routing node, should be the interface routing node
        :param str gw_type: type of gateway, i.e. netlink, ospfv2_area, etc
        :param RoutingNodeGateway route_node_gateway: gateway element
        :param str network: network to bind to. If none, all networks
        :return: Whether a change was made or not
        :rtype: bool
        """
        if self.level != 'interface':
            raise ModificationAborted('You must make this change from the '
                'interface routing level. Current node: {}'.format(self))
        
        if self.related_element_type == 'tunnel_interface':
            return self._add_gateway_node_on_tunnel(routing_node_gateway)
        
        # Find any existing gateways
        routing_node = list(gateway_by_type(self, type=gw_type, on_network=network))
        
        _networks = [netwk for netwk in self if netwk.ip == network] if network is \
            not None else list(self)
        
        # Routing Node Gateway to add as Element
        gateway_element_type = routing_node_gateway.routing_node_element
        
        modified = False
        for network in _networks:
            # Short circuit for dynamic interfaces
            if getattr(network, 'dynamic_classid', None):
                network.data.setdefault('routing_node', []).append(
                        routing_node_gateway)
                modified = True
                break
            
            # Used for comparison to 
            this_network_node = network.routing_node_element
            
            if routing_node and any(netwk for _intf, netwk, gw in routing_node
                if netwk.routing_node_element == this_network_node and
                gateway_element_type == gw.routing_node_element):
                
                # A gateway exists on this network
                for gw in network:
                    if gw.routing_node_element == gateway_element_type:
                        existing_dests = [node.routing_node_element for node in gw]
                        for destination in routing_node_gateway.destinations:
                            is_valid_destination = False
                            if destination not in existing_dests:
                                dest_ipv4, dest_ipv6 = _which_ip_protocol(destination)
                                if len(network.ip.split(':')) > 1: # IPv6
                                    if dest_ipv6:
                                        is_valid_destination = True
                                else:
                                    if dest_ipv4:
                                        is_valid_destination = True
                
                                if is_valid_destination:
                                    gw.data.setdefault('routing_node', []).append(
                                        {'level': 'any', 'href': destination.href,
                                         'name': destination.name})
                                    modified = True
        
            else: # Gateway doesn't exist
                gw_ipv4, gw_ipv6 = _which_ip_protocol(gateway_element_type) # ipv4, ipv6 or both
                if len(network.ip.split(':')) > 1:
                    if gw_ipv6:
                        network.data.setdefault('routing_node', []).append(
                            routing_node_gateway)
                        modified = True
                else: # IPv4
                    if gw_ipv4:
                        network.data.setdefault('routing_node', []).append(
                            routing_node_gateway) 
                        modified = True

        if modified:
            self.update()
        return modified    
                 
    def remove_route_gateway(self, element, network=None):
        """
        Remove a route element by href or Element. Use this if you want to
        remove a netlink or a routing element such as BGP or OSPF. Removing
        is done from within the routing interface context.
        ::
        
            interface0 = engine.routing.get(0)
            interface0.remove_route_gateway(StaticNetlink('mynetlink'))
            
        Only from a specific network on a multi-address interface::
        
            interface0.remove_route_gateway(
                StaticNetlink('mynetlink'),
                network='172.18.1.0/24')
        
        :param str,Element element: element to remove from this routing node
        :param str network: if network specified, only add OSPF to this
            network on interface
        :raises ModificationAborted: Change must be made at the interface level
        :raises UpdateElementFailed: failure to update routing table
        :return: Status of whether the entry was removed (i.e. or not found)
        :rtype: bool
        """
        if self.level not in ('interface',):
            raise ModificationAborted('You must make this change from the '
                'interface routing level. Current node: {}'.format(self))
        
        node_changed = False
        element = element_resolver(element)
        for network in self:
            # Tunnel Interface binds gateways to the interface
            if network.level == 'gateway' and network.data.get('href') == element:
                network.delete()
                node_changed = True
                break
            for gateway in network:
                if gateway.data.get('href') == element:
                    gateway.delete()
                    node_changed = True
        return node_changed


class RoutingNodeGateway(Routing):
    def __init__(self, element=None, level='gateway', **kwargs):
        self.destinations = kwargs.pop('destinations', [])
        self.data = ElementCache(kwargs)
        self.data.update(
            level=level,
            routing_node=[])

        if element:
            self.data.update(
                href=element.href,
                name=element.name)
                #related_element_type=element.typeof)
        
        for destination in self.destinations:
            self.data['routing_node'].append(
                {'href': destination.href,
                 'name': destination.name,
                 'level': 'any'})


class Antispoofing(RoutingTree):
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
    typeof = 'antispoofing_node'
    
    def __init__(self, data=None, **meta):
        self._parent = meta.pop('parent', None)
        super(Antispoofing, self).__init__(data, **meta)

    @property
    def autogenerated(self):
        """
        Was the entry auto generated by a route entry or
        added manually as an override
        
        :rtype: bool
        """
        return self.data.get('auto_generated') == 'true'

    @property
    def validity(self):
        """
        Enabled or disabled antispoofing entry

        :return: validity of this entry (enable,disable,absolute)
        :rtype: str
        """
        return self.data.get('validity')
    
    def add(self, element):
        """
        Add an entry to this antispoofing node level.
        Entry can be either href or network elements specified
        in :py:class:`smc.elements.network`
        ::

            if0 = engine.antispoofing.get(0)
            if0.add(Network('foonet'))

        :param Element element: entry to add, i.e. Network('mynetwork'), Host(..)
        :raises CreateElementFailed: failed adding entry
        :raises ElementNotFound: element entry specified not in SMC
        :return: whether entry was added
        :rtype: bool
        """
        if self.level == 'interface':
            for network in self:
                if from_meta(network) == element:
                    return False
        
            self.data['antispoofing_node'].append({
                'antispoofing_node': [],
                'auto_generated': 'false',
                'href': element.href,
                'level': self.level,
                'validity': 'enable',
                'name': element.name})

            self.update()
            return True
        return False
    
    def __len__(self):
        return len(self.data.get('antispoofing_node', []))
    
    def remove(self, element):
        """
        Remove a specific user added element from the antispoofing tables of
        a given interface. This will not remove autogenerated or system level
        entries.
        
        :param Element element: element to remove
        :return: remove element if it exists and return bool
        :rtype: bool
        """
        if self.level == 'interface':
            len_before_change = len(self)
            _nodes = []
            for network in self:
                if from_meta(network) != element:
                    _nodes.append(network.data)
                else:
                    if network.autogenerated: # Make sure it was user added
                        _nodes.append(network.data)
            if len(_nodes) != len_before_change:
                self.data['antispoofing_node'] = _nodes
                self.update()
                return True
        return False

def from_meta(node):
    """
    Helper method that reolves a routing node to element. Rather than doing
    a lookup and fetch, the routing node provides the information to
    build the element from meta alone.
    
    :rtype: Element
    """
    # Version SMC < 6.4
    if 'related_element_type' not in node.data:
        return Element.from_href(
            node.data.get('href'))
    
    # SMC Version >= 6.4 - more efficient because it builds the
    # element by meta versus requiring a query
    return Element.from_meta(
        name=node.data.get('name'),
        type=node.related_element_type,
        href=node.data.get('href'))


def route_level(root, level):
    """
    Helper method to recurse the current node and return
    the specified routing node level.
    """
    def recurse(nodes):
        for node in nodes:
            if node.level == level:
                routing_node.append(node)
            else:
                recurse(node)

    routing_node = []
    recurse(root)
    return routing_node


def gateway_by_type(self, type=None, on_network=None):  # @ReservedAssignment
    """
    Return gateways for the specified node. You can also
    specify type to find only gateways of a specific type.
    Valid types are: bgp_peering, netlink, ospfv2_area.
    
    :param RoutingNode self: the routing node to check
    :param str type: bgp_peering, netlink, ospfv2_area
    :param str on_network: if network is specified, should be CIDR and
        specifies a filter to only return gateways on that network when
        an interface has multiple
    :return: tuple of RoutingNode(interface,network,gateway)
    :rtype: list
    """
    gateways = route_level(self, 'gateway')
    if not type:
        for gw in gateways:
            yield gw
    else:
        for node in gateways:
            #TODO: Change to type == node.related_element_type when
            # only supporting SMC >= 6.4
            if type == node.routing_node_element.typeof:
                # If the parent is level interface, this is a tunnel interface
                # where the gateway is bound to interface versus network
                parent = node._parent
                if parent.level == 'interface':
                    interface = parent
                    network = None
                else:
                    network = parent
                    interface = network._parent
                
                if on_network is not None:
                    if network and network.ip == on_network:
                        yield (interface, network, node)
                else:
                    yield (interface, network, node)


def _which_ip_protocol(element):
    """
    Validate the protocol addresses for the element. Most elements can
    have an IPv4 or IPv6 address assigned on the same element. This
    allows elements to be validated and placed on the right network.
    
    :return: boolean tuple
    :rtype: tuple(ipv4, ipv6)
    """
    try:
        if element.typeof in ('host', 'router'):
            return getattr(element, 'address', False), getattr(element, 'ipv6_address', False)
        elif element.typeof == 'netlink':
            gateway = element.gateway
            if gateway.typeof == 'router':
                return getattr(gateway, 'address', False), getattr(gateway, 'ipv6_address', False)
            # It's an engine, return true
        elif element.typeof == 'network':
            return getattr(element, 'ipv4_network', False), getattr(element, 'ipv6_network', False)
    except AttributeError:
        pass
    # Always return true so that the calling function assumes the element
    # is valid for the routing node. This could fail when submitting but
    # we don't want to prevent adding elements yet since this could change
    return True, True


def del_invalid_routes(engine, nicids):
    """
    Helper method to run through and delete any routes that are tagged
    as invalid or to_delete by a list of nicids. Since we could have a
    list of routes, iterate from top level engine routing node to avoid
    fetch exceptions. Route list should be a list of nicids as str.
    
    :param list nicids: list of nicids
    :raises DeleteElementFailed: delete element failed with reason
    """
    nicids = map(str, nicids)
    for interface in engine.routing:
        if interface.nicid in nicids:
            if getattr(interface, 'to_delete', False): # Delete the invalid interface
                interface.delete()
                continue
        for network in interface:
            if getattr(network, 'invalid', False) or \
                getattr(network, 'to_delete', False):
                network.delete()


route = collections.namedtuple('Route',
        'route_network route_netmask route_gateway route_type dst_if src_if')
route.__new__.__defaults__ = (None,) * len(route._fields)

   
class Route(SerializedIterable):
    """
    Active routes obtained from a running engine.
    Obtain routes from an engine reference::
    
        >>> engine = Engine('sg_vm')
        >>> for route in engine.routing_monitoring:
        ...    route
    
    :ivar str route_network: network for this route
    :ivar int route_netmask: netmask for the route
    :ivar str route_gateway: route gateway, may be None if it's a local network only
    :ivar str route_type: status of the route
    :ivar int dst_if: destination interface index
    :ivar int src_if: source interface index
    """

    def __init__(self, data):
        routes = data.get('routing_monitoring_entry', [])
        data = [{k: v for k, v in d.items()
                 if k != 'cluster_ref'} for d in routes]
        super(Route, self).__init__(data, route)
            

policy_route = collections.namedtuple('PolicyRoute',
        'source destination gateway_ip comment')
policy_route.__new__.__defaults__ = (None,) * len(policy_route._fields)
    

class PolicyRoute(SerializedIterable):
    """
    An iterable providing an interface to policy based routing on the
    engine. 
    You must call engine.udpate() after performing an add or delete::
    
        >>> engine = Engine('myfw')
        >>> engine.policy_route
        PolicyRoute(items: 1)
        >>> for rt in engine.policy_route:
        ...   rt
        ... 
        PolicyRoute(source=u'172.18.1.0/24', destination=u'172.18.1.0/24', gateway_ip=u'172.18.1.1', comment=None)
        >>> engine.policy_route.create(source='172.18.2.0/24', destination='192.168.3.0/24', gateway_ip='172.18.2.1')
        >>> engine.update()
        'http://172.18.1.151:8082/6.4/elements/single_fw/746'
        >>> for rt in engine.policy_route:
        ...   rt
        ... 
        PolicyRoute(source=u'172.18.1.0/24', destination=u'172.18.1.0/24', gateway_ip=u'172.18.1.1', comment=None)
        PolicyRoute(source=u'172.18.2.0/24', destination=u'192.168.3.0/24', gateway_ip=u'172.18.2.1', comment=None)
        >>> engine.policy_route.delete(source='172.18.2.0/24')
        >>> engine.update()
        'http://172.18.1.151:8082/6.4/elements/single_fw/746'
        >>> for rt in engine.policy_route:
        ...   rt
        ... 
        PolicyRoute(source=u'172.18.1.0/24', destination=u'172.18.1.0/24', gateway_ip=u'172.18.1.1', comment=None)

    :ivar str source: source network/cidr for the route
    :ivar str destination: destination network/cidr for the route
    :ivar str gateway_ip: gateway IP address, must be on source network
    :ivar str comment: optional comment
    """
    def __init__(self, engine):
        data = engine.data.get('policy_route')
        super(PolicyRoute, self).__init__(data, policy_route)

    def create(self, source, destination, gateway_ip, comment=None):
        """
        Add a new policy route to the engine.
        
        :param str source: network address with /cidr
        :param str destination: network address with /cidr
        :param str gateway: IP address, must be on source network
        :param str comment: optional comment
        """
        self.items.append(dict(
            source=source, destination=destination,
            gateway_ip=gateway_ip, comment=comment))
    
    def delete(self, **kw):
        """
        Delete a policy route from the engine. You can delete using a
        single field or multiple fields for a more exact match.
        Use a keyword argument to delete a route by any valid attribute.
        
        :param kw: use valid Route keyword values to delete by exact match
        """
        delete_by = []
        for field, val in kw.items():
            if val is not None:
                delete_by.append(field)
        
        self.items[:] = [route for route in self.items
                         if not all(route.get(field) == kw.get(field)
                                    for field in delete_by)]

