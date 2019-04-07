"""
.. versionchanged:: 0.7.0

Collections classes for interfaces provide searching and methods to simplify
creation based on interface types.

You can iterate any interface type by specifying the type::
    
    >>> for interface in engine.tunnel_interface:
    ...   interface
    ... 
    TunnelInterface(name=Tunnel Interface 1008)
    TunnelInterface(name=Tunnel Interface 1003)
    TunnelInterface(name=Tunnel Interface 1000)

Or iterate all interfaces which will also return their types::
    
    >>> for interface in engine.interface:
    ...   interface
    ... 
    Layer3PhysicalInterface(name=Interface 3)
    TunnelInterface(name=Tunnel Interface 1000)
    Layer3PhysicalInterface(name=Interface 61)
    Layer3PhysicalInterface(name=Interface 56)
    Layer3PhysicalInterface(name=Interface 15)
    Layer2PhysicalInterface(name=Interface 7 (Capture))
    ModemInterfaceDynamic(name=Modem 0)
    TunnelInterface(name=Tunnel Interface 1030)
    SwitchPhysicalInterface(name=Switch 0)
    ...        
    
Accessing interface methods for creating interfaces can also be done in multiple
ways. The simplest is to use an engine reference to use this collection. The engine
reference specifies the type of interface and indicates how it will be created
for the engine. 

For example, creating an interface on a virtual engine::
    
    engine.virtual_physical_interface.add_layer3_interface(
        interface_id=1,
        address='14.14.14.119',
        network_value='14.14.14.0/24',
        comment='my comment',
        zone_ref='myzone')
    
The helper methods use the interface API to create the interface that is then
submitted to the engine.
You can optionally create the interface manually using the API which provides more
customization capabilities.

Example of creating a VirtualPhysicalInterface for a virtual engine manually::

    payload = {'comment': 'comment on this interface',
               'interfaces': [{'nodes': [{'address': '13.13.13.13', 'network_value': '13.13.13.0/24'}]}]}
     
    vinterface = VirtualPhysicalInterface(interface_id=1, **payload)
    
Pass this to update_or_create in the event that you want to potentially modify an existing
interface should the same interface ID exist::

    engine.virtual_physical_interface.update_or_create(vinterface)

Or create a new interface (this will fail if the interface exists)::

    engine.add_interface(vinterface)

Collections also provide a simple helper when you want to provide a pre-configured interface
and apply an update_or_create logic. In the update or create case, if the interface exists
any fields that have changed will be updated. If the interface does not exist it is created.
Provide `with_status` to obtain the interface and status of the operation. The update or 
create will return a tuple of (Interface, modified, created), where created and modified are
booleans indicating the operations performed::

    >>> from smc.core.engine import Engine
    >>> from smc.core.interfaces import Layer3PhysicalInterface
    >>> engine = Engine('myfw')
    >>> interface = engine.interface.get(0)
    >>> interface
    Layer3PhysicalInterface(name=Interface 0)
    >>> interface.addresses
    [(u'11.11.11.11', u'11.11.11.0/24', u'0')]
    >>> myinterface = Layer3PhysicalInterface(interface_id=0,
    interfaces=[{'nodes': [{'address': '66.66.66.66', 'network_value': '66.66.66.0/24'}]}], comment='changed today')
    ...
    >>> interface, modified, created = engine.physical_interface.update_or_create(myinterface)
    >>> interface
    Layer3PhysicalInterface(name=Interface 0)
    >>> modified
    True
    >>> created
    False
    >>> interface.addresses
    [(u'66.66.66.66', u'66.66.66.0/24', u'0')]
    >>> interface.comment
    u'changed today'

"""
from smc.core.interfaces import TunnelInterface, \
   InterfaceEditor, Layer3PhysicalInterface,\
    ClusterPhysicalInterface, Layer2PhysicalInterface, VirtualPhysicalInterface,\
    SwitchPhysicalInterface
from smc.core.sub_interfaces import LoopbackClusterInterface, LoopbackInterface
from smc.base.structs import BaseIterable
from smc.api.exceptions import UnsupportedInterfaceType, InterfaceNotFound


def get_all_loopbacks(engine):
    """
    Get all loopback interfaces for a given engine
    """
    data = []
    if 'fw_cluster' in engine.type:
        for cvi in engine.data.get('loopback_cluster_virtual_interface', []): 
            data.append(
                LoopbackClusterInterface(cvi, engine))
    for node in engine.nodes:
        for lb in node.data.get('loopback_node_dedicated_interface', []):
            data.append(LoopbackInterface(lb, engine))
    return data


class LoopbackCollection(BaseIterable):
    """
    An loopback collection provides top level search capabilities
    to iterate or get loopback interfaces from a given engine.
    
    All loopback interfaces can be fetched from the engine::
    
        >>> engine = Engine('dingo')
        >>> for lb in engine.loopback_interface:
        ...   lb
        ... 
        LoopbackInterface(address=172.20.1.1, nodeid=1, rank=1)
        LoopbackInterface(address=172.31.1.1, nodeid=1, rank=2)
    
    Or directly from the nodes::
    
        >>> for node in engine.nodes:
        ...   for lb in node.loopback_interface:
        ...     lb
        ... 
        LoopbackInterface(address=172.20.1.1, nodeid=1, rank=1)
        LoopbackInterface(address=172.31.1.1, nodeid=1, rank=2)
    
    """
    def __init__(self, engine):
        self._engine = engine
        loopbacks = get_all_loopbacks(engine)
        super(LoopbackCollection, self).__init__(loopbacks)
    
    def get(self, address):
        """
        Get a loopback address by it's address. Find all loopback addresses
        by iterating at either the node level or the engine::
        
            loopback = engine.loopback_interface.get('127.0.0.10')
        
        :param str address: ip address of loopback
        :raises InterfaceNotFound: invalid interface specified
        :rtype: LoopbackInterface
        """
        loopback = super(LoopbackCollection, self).get(address=address)
        if loopback:
            return loopback
        raise InterfaceNotFound('Loopback address specified was not found')
    
    def __getattr__(self, key):
        # Dispatch to instance methods but only for adding interfaces.
        # Makes this work: engine.loopback_interface.add
        if key.startswith('add_'):
            if 'fw_cluster' not in self._engine.type:
                return getattr(LoopbackInterface(None, self._engine), key)
            else: # Cluster
                return getattr(LoopbackClusterInterface(None, self._engine), key)
        raise AttributeError('Cannot proxy to given method: %s for the '
            'following engine type: %s' % (key, self._engine.type))
        

class InterfaceCollection(BaseIterable):
    """
    An interface collection provides top level search capabilities
    to iterate or get interfaces of the specified type. This also
    delegates all 'add' methods of an interface to the interface type
    specified. Collections are returned from an engine reference and
    not called directly.
    
    For example, you can use this to obtain all interfaces of a given
    type from an engine::
    
        >>> for interface in engine.interface.all():
        ...   print(interface.name, interface.addresses)
        ('Tunnel Interface 2001', [('169.254.9.22', '169.254.9.20/30', '2001')])
        ('Tunnel Interface 2000', [('169.254.11.6', '169.254.11.4/30', '2000')])
        ('Interface 2', [('192.168.1.252', '192.168.1.0/24', '2')])
        ('Interface 1', [('10.0.0.254', '10.0.0.0/24', '1')])
        ('Interface 0', [('172.18.1.254', '172.18.1.0/24', '0')])
            
    Or only physical interface types::
    
        for interface in engine.physical_interfaces:
            print(interface)
    
    Get switch interfaces and associated port groups::
    
        for interface in engine.switch_physical_interface:
            print(interface, interface.port_groups)
            
    Get a specific interface directly::
        
        engine.interface.get(10)
    
    Switch interface direct fetching must include the 'SWP_' prefix as well.
    To get switch interface 0::
    
        engine.interface.get('SWP_0')
    
    You can also get port groups directly similar to fetching VLANs::
    
        engine.switch_physical_interface.get('SWP_0.1')
    
    Or use delegation to create interfaces::
        
        engine.physical_interface.add(2)
        engine.physical_interface.add_layer3_interface(....)
        ...

    .. note:: This can raise UnsupportedInterfaceType for unsupported engine
        types based on the interface context.
    """
    def __init__(self, engine, rel='interfaces'):
        self._engine = engine
        self._rel = rel
        self.href = engine.get_relation(rel, UnsupportedInterfaceType)
        # Pass the interface iterator to the top level iterator
        super(InterfaceCollection, self).__init__(InterfaceEditor(engine))
        
    def get(self, interface_id):
        """
        Get the interface by id, if known. The interface is retrieved from
        the top level Physical or Tunnel Interface. If the interface is an
        inline interface, you can specify only one of the two inline pairs and
        the same interface will be returned.
        
        If interface type is unknown, use engine.interface for retrieving::

            >>> engine = Engine('sg_vm')
            >>> intf = engine.interface.get(0)
            >>> print(intf, intf.addresses)
            (PhysicalInterface(name=Interface 0), [('172.18.1.254', '172.18.1.0/24', '0')])
        
        Get an inline interface::
        
            >>> intf = engine.interface.get('2-3')

        .. note:: For the inline interface example, you could also just specify
            '2'  or '3' and the fetch will return the pair.
        
        :param str,int interface_id: interface ID to retrieve
        :raises InterfaceNotFound: invalid interface specified
        :return: interface object by type (Physical, Tunnel, VlanInterface)
        """
        return self.items.get(interface_id)

    def __iter__(self):
        for interface in super(InterfaceCollection, self).__iter__():
            if self._rel != 'interfaces': 
                if interface.typeof == self._rel: 
                    yield interface
            else:
                yield interface
    
    def __len__(self):
        return sum(1 for _ in self)
    
    def __contains__(self, interface_id):
        try:
            return self.get(interface_id)
        except InterfaceNotFound:
            return False
    
    def update_or_create(self, interface):
        """
        Collections class update or create method that can be used as a
        shortcut to updating or creating an interface. The interface must
        first be defined and provided as the argument. The interface method
        must have an `update_interface` method which resolves differences and
        adds as necessary.
        
        :param Interface interface: an instance of an interface type, either
            PhysicalInterface, TunnelInterface or SwitchPhysicalInterface
        :raises EngineCommandFailed: Failed to create new interface
        :raises UpdateElementFailed: Failure to update element with reason
        :rtype: tuple
        :return: A tuple with (Interface, modified, created), where created and
            modified are booleans indicating the operations performed
        """
        created, modified = (False, False)
        try:
            intf = self._engine.interface.get(
                interface.interface_id)
            interface, updated = intf.update_interface(interface)
            if updated:
                modified = True
        except InterfaceNotFound:
            self._engine.add_interface(interface)
            interface = self._engine.interface.get(interface.interface_id)
            created = True
        
        return interface, modified, created


class SwitchInterfaceCollection(InterfaceCollection):
    """
    SwitchInterfaceCollection provides an interface to retrieving existing
    interfaces and helper methods to shortcut the creation of a switch.
    Note that switch interfaces are only supported on specific engine types
    and require that the top level switch is created and port groups are
    created (although you can use one single port group for the entire
    switch configuration.
    
    Get specific switch interfaces assigned on the given engine::
    
        for interface in engine.switch_physical_interface:
            print(interface, interface.port_groups)
    
    You can also retrieve a switch directly by referencing it using the
    switch interface id. Switch interfaces will always have a name starting
    with 'SWP_'. For example, SWP_0 specifies physical switch port 0::
    
        engine.switch_physical_interface.get('SWP_0')
    
    You can also get port_group_interfaces directly::
    
        engine.switch_physical_interface.get('SWP_0.1')
    
    Or iterate through the port_group_interface collection::
    
        interface = engine.switch_physical_interface.get('SWP_0')
        for port_group in interface.port_group_interface:
            ...
    """
    def __init__(self, engine):
        super(SwitchInterfaceCollection, self).__init__(engine, 'switch_physical_interface')
        
    def add_switch_interface(self, interface_id, appliance_switch_module='110',
                        comment=None, **kwargs):
        """
        In case of Switch Physical/Port Group interfaces, the interface ID must
        be prefixed by "SWP_". For example, for switch ID 1 and Port Group ID 1.2
        you must enter SWP_1 for the switch and SWP_1.2 for the Port Group.
        
        :param str interface_id: Name of the interface, must be prefixed with
            'SWP_'
        :param str appliance_switch_module: appliance switch module which specifies
            the hardware module (default: '110')
        :param str comment: optional comment
        :param dict kwargs: optional kwargs conforming to the port group dict
            format if port groups need to be created
        :raises EngineCommandFailed: failure during creation
        :return: None
        """
        interface = SwitchPhysicalInterface(engine=self._engine,
            interface_id=interface_id, appliance_switch_module=appliance_switch_module,
            comment=comment, **kwargs)
        self._engine.add_interface(interface)
    
    def add_port_group_interface(self, interface_id, port_group_id, interface_ports,
                interfaces=None, zone_ref=None):
        """
        Add a port group to an existing switch physical interface. If the switch
        port should have an address assigned, use the following format::
        
            engine.switch_physical_interface.add_port_group_interface('SWP_1', 1, [1],
                    interfaces=[{'nodes': [{'address': '12.12.12.12',
                                            'network_value': '12.12.12.0/24',
                                            'nodeid': 1}]}])
        
        To create a generic switch port group without IP addresses assigned with port
        group ID 1 and using physical port numbers 2,3,4,5::
        
            engine.switch_physical_interface.add_port_group_interface('SWP_1', 1, [2,3,4,5])
        
        .. note:: If the port group ID exists, this method will modify the existing port
            group with the specified settings
        
        :param str interface_id: The top level switch, naming convention should be
            SWP_0, SWP_1, etc.
        :param int port_group_id: Port group number encapsulating switch port/s
        :param list interface_ports: list of interface ports to add to this port
            group. If the port group.
        :param list interfaces: list of interface node definitions if the switch port
            should have IP address/es assigned
        :param str zone_ref: zone reference, can be name, href or Zone, will be
            created if it doesn't exist
        :raises InterfaceNotFound: invalid switch interface_id specified
        :return: None
        """
        switch = self._engine.interface.get(interface_id)
        switch_port = {'interface_id': '{}.{}'.format(switch.interface_id, port_group_id),
            'switch_physical_interface_port': [{'switch_physical_interface_port_number': port} 
                for port in interface_ports], 'zone_ref': zone_ref}
        switch_port.update(interfaces=interfaces if interfaces else [])
        interface = {'interface_id': switch.interface_id, 'port_group_interface': [switch_port]}
        switch.update_interface(SwitchPhysicalInterface(**interface))

        
class TunnelInterfaceCollection(InterfaceCollection):
    """
    TunnelInterface Collection provides an interface to retrieving existing
    interfaces and helper methods to shortcut the creation of an interface.
    """
    def __init__(self, engine):
        super(TunnelInterfaceCollection, self).__init__(engine, 'tunnel_interface')

    def add_cluster_virtual_interface(self, interface_id, cluster_virtual=None,
                    network_value=None, nodes=None, zone_ref=None, comment=None):
        """
        Add a tunnel interface on a clustered engine. For tunnel interfaces
        on a cluster, you can specify a CVI only, NDI interfaces, or both.
        This interface type is only supported on layer 3 firewall engines.
        ::

            Add a tunnel CVI and NDI:

            engine.tunnel_interface.add_cluster_virtual_interface(
                interface_id_id=3000,
                cluster_virtual='4.4.4.1',
                network_value='4.4.4.0/24',
                nodes=nodes)

            Add tunnel NDI's only:

            engine.tunnel_interface.add_cluster_virtual_interface(
                interface_id=3000,
                nodes=nodes)

            Add tunnel CVI only:

            engine.tunnel_interface.add_cluster_virtual_interface(
                interface_id=3000,
                cluster_virtual='31.31.31.31',
                network_value='31.31.31.0/24',
                zone_ref='myzone')

        :param str,int interface_id: tunnel identifier (akin to interface_id)
        :param str cluster_virtual: CVI ipaddress (optional)
        :param str network_value: CVI network; required if ``cluster_virtual`` set
        :param list nodes: nodes for clustered engine with address,network_value,nodeid
        :param str zone_ref: zone reference, can be name, href or Zone
        :param str comment: optional comment
        :raises EngineCommandFailed: failure during creation
        :return: None
        """
        interfaces = [{'cluster_virtual': cluster_virtual, 'network_value': network_value,
                       'nodes': nodes if nodes else []}]
        interface = {'interface_id': interface_id, 'interfaces': interfaces,
            'zone_ref': zone_ref, 'comment': comment}
        
        tunnel_interface = TunnelInterface(**interface)
        self._engine.add_interface(tunnel_interface)
        
    def add_layer3_interface(self, interface_id, address=None, network_value=None,
                             zone_ref=None, comment=None):
        """
        Creates a tunnel interface with sub-type single_node_interface. This is
        to be used for single layer 3 firewall instances.
        
        .. note:: If no address or network_value is provided, an unconfigured tunnel
            interface will be created

        :param str,int interface_id: the tunnel id for the interface, used as nicid also
        :param str address: ip address of interface
        :param str network_value: network cidr for interface; format: 1.1.1.0/24
        :param str zone_ref: zone reference for interface can be name, href or Zone
        :param str comment: optional comment
        :raises EngineCommandFailed: failure during creation
        :return: None
        """
        interfaces = [{'nodes': [{'address': address, 'network_value': network_value}]}] \
            if address and network_value else []
        interface = {'interface_id': interface_id, 'interfaces': interfaces,
            'zone_ref': zone_ref, 'comment': comment}
        tunnel_interface = TunnelInterface(**interface)
        self._engine.add_interface(tunnel_interface)


class PhysicalInterfaceCollection(InterfaceCollection):
    """
    PhysicalInterface Collection provides an interface to retrieving existing
    interfaces and helper methods to shortcut the creation of an interface.
    """
    def __init__(self, engine):
        super(PhysicalInterfaceCollection, self).__init__(engine, 'physical_interface')
    
    def add(self, interface_id, virtual_mapping=None,
            virtual_resource_name=None, zone_ref=None, comment=None):
        """
        Add single physical interface with interface_id. Use other methods
        to fully add an interface configuration based on engine type.
        Virtual mapping and resource are only used in Virtual Engines.

        :param str,int interface_id: interface identifier
        :param int virtual_mapping: virtual firewall id mapping
               See :class:`smc.core.engine.VirtualResource.vfw_id`
        :param str virtual_resource_name: virtual resource name
               See :class:`smc.core.engine.VirtualResource.name`
        :raises EngineCommandFailed: failure creating interface
        :return: None
        """
        interface = Layer3PhysicalInterface(engine=self._engine,
            interface_id=interface_id, zone_ref=zone_ref,
            comment=comment, virtual_resource_name=virtual_resource_name,
            virtual_mapping=virtual_mapping)
        
        return self._engine.add_interface(interface)
    
    def add_capture_interface(self, interface_id, logical_interface_ref,
            inspect_unspecified_vlans=True, zone_ref=None, comment=None):
        """
        Add a capture interface. Capture interfaces are supported on
        Layer 2 FW and IPS engines.
        
        ..note::
            Capture interface are supported on Layer 3 FW/clusters for NGFW engines
            version >= 6.3 and SMC >= 6.3.
        
        :param str,int interface_id: interface identifier
        :param str logical_interface_ref: logical interface name, href or LogicalInterface.
            If None, 'default_eth' logical interface will be used.
        :param str zone_ref: zone reference, can be name, href or Zone
        :raises EngineCommandFailed: failure creating interface
        :return: None

        See :class:`smc.core.sub_interfaces.CaptureInterface` for more information
        """
        capture = {'interface_id': interface_id, 'interface': 'capture_interface',
            'logical_interface_ref': logical_interface_ref, 'inspect_unspecified_vlans':
            inspect_unspecified_vlans, 'zone_ref': zone_ref, 'comment': comment}
        
        interface = Layer2PhysicalInterface(engine=self._engine, **capture)
        return self._engine.add_interface(interface)

    def add_layer3_interface(self, interface_id, address, network_value,
                             zone_ref=None, comment=None, **kw):
        """
        Add a layer 3 interface on a non-clustered engine.
        For Layer 2 FW and IPS engines, this interface type represents
        a layer 3 routed (node dedicated) interface. For clusters, use the
        cluster related methods such as :func:`add_cluster_virtual_interface`

        :param str,int interface_id: interface identifier
        :param str address: ip address
        :param str network_value: network/cidr (12.12.12.0/24)
        :param str zone_ref: zone reference, can be name, href or Zone
        :param kw: keyword arguments are passed to the sub-interface during
            create time. If the engine is a single FW, the sub-interface type
            is :class:`smc.core.sub_interfaces.SingleNodeInterface`. For all
            other engines, the type is :class:`smc.core.sub_interfaces.NodeInterface`
            For example, pass 'backup_mgt=True' to enable this interface as the
            management backup.
        :raises EngineCommandFailed: failure creating interface
        :return: None

        .. note::
            If an existing ip address exists on the interface and zone_ref is
            provided, this value will overwrite any previous zone definition.
        """
        interfaces = {'interface_id': interface_id, 'interfaces':
            [{'nodes': [{'address': address, 'network_value': network_value}]}],
            'zone_ref': zone_ref, 'comment': comment}
        interfaces.update(kw)
        
        if 'single_fw' in self._engine.type: # L2FW / IPS
            interfaces.update(interface='single_node_interface')
    
        try:
            interface = self._engine.interface.get(interface_id)
            interface._add_interface(**interfaces)
            return interface.update()
            
        except InterfaceNotFound:
            interface = Layer3PhysicalInterface(**interfaces)
            return self._engine.add_interface(interface)
    
    def add_layer3_vlan_interface(self, interface_id, vlan_id, address=None,
        network_value=None, virtual_mapping=None, virtual_resource_name=None,
        zone_ref=None, comment=None, **kw):
        """
        Add a Layer 3 VLAN interface. Optionally specify an address and network if
        assigning an IP to the VLAN. This method will also assign an IP address to
        an existing VLAN, or add an additional address to an existing VLAN. This
        method may commonly be used on a Master Engine to create VLANs for virtual
        firewall engines.
        
        Example of creating a VLAN and passing kwargs to define a DHCP server
        service on the VLAN interface::
        
            engine = Engine('engine1')
            engine.physical_interface.add_layer3_vlan_interface(interface_id=20, vlan_id=20,
                address='20.20.20.20', network_value='20.20.20.0/24', comment='foocomment',
                dhcp_server_on_interface={
                    'default_gateway': '20.20.20.1',
                    'default_lease_time': 7200,
                    'dhcp_address_range': '20.20.20.101-20.20.20.120',
                    'dhcp_range_per_node': [],
                    'primary_dns_server': '8.8.8.8'})
        
        :param str,int interface_id: interface identifier
        :param int vlan_id: vlan identifier
        :param str address: optional IP address to assign to VLAN
        :param str network_value: network cidr if address is specified. In
            format: 10.10.10.0/24.
        :param str zone_ref: zone to use, by name, href, or Zone
        :param str comment: optional comment for VLAN level of interface
        :param int virtual_mapping: virtual engine mapping id
               See :class:`smc.core.engine.VirtualResource.vfw_id`
        :param str virtual_resource_name: name of virtual resource
               See :class:`smc.core.engine.VirtualResource.name`
        :param dict kw: keyword arguments are passed to top level of VLAN interface,
            not the base level physical interface. This is useful if you want to
            pass in a configuration that enables the DHCP server on a VLAN for example.
        :raises EngineCommandFailed: failure creating interface
        :return: None
        """
        interfaces = {'nodes': [{'address': address, 'network_value': network_value}] if address
            and network_value else [], 'zone_ref': zone_ref, 'virtual_mapping': virtual_mapping,
            'virtual_resource_name': virtual_resource_name, 'comment': comment}
        interfaces.update(**kw)
        _interface = {'interface_id': interface_id, 'interfaces': [interfaces]}
        
        if 'single_fw' in self._engine.type: # L2FW / IPS
            _interface.update(interface='single_node_interface')
        
        try:
            interface = self._engine.interface.get(interface_id)
            vlan = interface.vlan_interface.get(vlan_id)
            # Interface exists, so we need to update but check if VLAN already exists
            if vlan is None:
                interfaces.update(vlan_id=vlan_id)
                interface._add_interface(**_interface)
            else:
                _interface.update(interface_id='{}.{}'.format(interface_id, vlan_id))
                vlan._add_interface(**_interface)
            return interface.update()
   
        except InterfaceNotFound:
            interfaces.update(vlan_id=vlan_id)
            interface = Layer3PhysicalInterface(**_interface)
            return self._engine.add_interface(interface)
            
    def add_layer3_cluster_interface(self, interface_id, cluster_virtual=None,
            network_value=None, macaddress=None, nodes=None, cvi_mode='packetdispatch',
            zone_ref=None, comment=None, **kw):
        """
        Add cluster virtual interface. A "CVI" interface is used as a VIP
        address for clustered engines. Providing 'nodes' will create the
        node specific interfaces. You can also add a cluster address with only
        a CVI, or only NDI's.
        
        Add CVI only:: 
             
            engine.physical_interface.add_cluster_virtual_interface(
                interface_id=30,
                cluster_virtual='30.30.30.1',
                network_value='30.30.30.0/24', 
                macaddress='02:02:02:02:02:06')
        
        Add NDI's only:: 
 
            engine.physical_interface.add_cluster_virtual_interface( 
                interface_id=30, 
                nodes=nodes) 
        
        Add CVI and NDI's::
        
            engine.physical_interface.add_cluster_virtual_interface(
                cluster_virtual='5.5.5.1',
                network_value='5.5.5.0/24',
                macaddress='02:03:03:03:03:03',
                nodes=[{'address':'5.5.5.2', 'network_value':'5.5.5.0/24', 'nodeid':1},
                       {'address':'5.5.5.3', 'network_value':'5.5.5.0/24', 'nodeid':2}])

        .. versionchanged:: 0.6.1
            Renamed from add_cluster_virtual_interface
        
        :param str,int interface_id: physical interface identifier
        :param str cluster_virtual: CVI address (VIP) for this interface
        :param str network_value: network value for VIP; format: 10.10.10.0/24
        :param str macaddress: mandatory mac address if cluster_virtual and
            cluster_mask provided
        :param list nodes: list of dictionary items identifying cluster nodes
        :param str cvi_mode: packetdispatch is recommended setting
        :param str zone_ref: zone reference, can be name, href or Zone
        :param kw: key word arguments are valid NodeInterface sub-interface
            settings passed in during create time. For example, 'backup_mgt=True'
            to enable this interface as the management backup.
        :raises EngineCommandFailed: failure creating interface
        :return: None
        """
        interfaces = [{'nodes': nodes if nodes else [],
            'cluster_virtual': cluster_virtual, 'network_value': network_value}]
        try:
            interface = self._engine.interface.get(interface_id)
            interface._add_interface(interface_id, interfaces=interfaces)
            return interface.update()
    
        except InterfaceNotFound:
        
            interface = ClusterPhysicalInterface(
                engine=self._engine,
                interface_id=interface_id,
                interfaces=interfaces,
                cvi_mode=cvi_mode if macaddress else 'none',
                macaddress=macaddress,
                zone_ref=zone_ref, comment=comment, **kw)

            return self._engine.add_interface(interface)
            
    def add_layer3_vlan_cluster_interface(self, interface_id, vlan_id,
            nodes=None, cluster_virtual=None, network_value=None, macaddress=None,
            cvi_mode='packetdispatch', zone_ref=None, comment=None, **kw):
        """
        Add IP addresses to VLANs on a firewall cluster. The minimum params
        required are ``interface_id`` and ``vlan_id``.
        To create a VLAN interface with a CVI, specify ``cluster_virtual``,
        ``cluster_mask`` and ``macaddress``.

        To create a VLAN with only NDI, specify ``nodes`` parameter.

        Nodes data structure is expected to be in this format::

            nodes=[{'address':'5.5.5.2', 'network_value':'5.5.5.0/24', 'nodeid':1},
                   {'address':'5.5.5.3', 'network_value':'5.5.5.0/24', 'nodeid':2}]

        :param str,int interface_id: interface id to assign VLAN.
        :param str,int vlan_id: vlan identifier
        :param list nodes: optional addresses for node interfaces (NDI's). For a cluster,
            each node will require an address specified using the nodes format.
        :param str cluster_virtual: cluster virtual ip address (optional). If specified, cluster_mask
            parameter is required
        :param str network_value: Specifies the network address, i.e. if cluster virtual is 1.1.1.1,
            cluster mask could be 1.1.1.0/24.
        :param str macaddress: (optional) if used will provide the mapping from node interfaces
            to participate in load balancing.
        :param str cvi_mode: cvi mode for cluster interface (default: packetdispatch)
        :param zone_ref: zone to assign, can be name, str href or Zone
        :param dict kw: keyword arguments are passed to top level of VLAN interface,
            not the base level physical interface. This is useful if you want to
            pass in a configuration that enables the DHCP server on a VLAN for example.
        :raises EngineCommandFailed: failure creating interface
        :return: None

        .. note::
            If the ``interface_id`` specified already exists, it is still possible
            to add additional VLANs and interface addresses.
        """
        interfaces = {'nodes': nodes if nodes else [],
            'cluster_virtual': cluster_virtual, 'network_value': network_value}
        interfaces.update(**kw)
        _interface = {'interface_id': interface_id, 'interfaces': [interfaces],
            'macaddress': macaddress, 'cvi_mode': cvi_mode if macaddress else 'none',
            'zone_ref': zone_ref, 'comment': comment}
        
        try:
            interface = self._engine.interface.get(interface_id)
            vlan = interface.vlan_interface.get(vlan_id)
            # Interface exists, so we need to update but check if VLAN already exists
            if vlan is None:
                interfaces.update(vlan_id=vlan_id)
                interface._add_interface(**_interface)
            else:
                for k in ('macaddress', 'cvi_mode'):
                    _interface.pop(k)
                _interface.update(interface_id='{}.{}'.format(interface_id, vlan_id))
                vlan._add_interface(**_interface)
                
            return interface.update()
        
        except InterfaceNotFound:

            interfaces.update(vlan_id=vlan_id)
            interface = ClusterPhysicalInterface(**_interface)
            return self._engine.add_interface(interface)
    
    def add_inline_interface(self, interface_id, second_interface_id,
        logical_interface_ref=None, vlan_id=None, second_vlan_id=None, zone_ref=None,
        second_zone_ref=None, failure_mode='normal', comment=None, **kw):
        """
        Add an inline interface pair. This method is only for IPS or L2FW engine
        types.
        
        :param str interface_id: interface id of first interface
        :param str second_interface_id: second interface pair id
        :param str, href logical_interface_ref: logical interface by href or name
        :param str vlan_id: vlan ID for first interface in pair
        :param str second_vlan_id: vlan ID for second interface in pair
        :param str, href zone_ref: zone reference by name or href for first interface
        :param str, href second_zone_ref: zone reference by nae or href for second interface
        :param str failure_mode: normal or bypass
        :param str comment: optional comment
        :raises EngineCommandFailed: failure creating interface
        :return: None
        """
        interface_spec = {'interface_id': interface_id, 'second_interface_id': second_interface_id,
            'interface': kw.get('interface') if self._engine.type in ('single_fw', 'fw_cluster')
            else 'inline_interface'}
        
        _interface = {'logical_interface_ref': logical_interface_ref,
            'failure_mode': failure_mode, 'zone_ref': zone_ref, 'second_zone_ref': second_zone_ref,
            'comment': comment}
        
        vlan = {'vlan_id': vlan_id, 'second_vlan_id': second_vlan_id}
        
        try:
            inline_id = '{}-{}'.format(interface_id, second_interface_id)
            interface = self._engine.interface.get(inline_id)
            _interface.update(vlan)
            interface_spec.update(interfaces=[_interface])
            interface._add_interface(**interface_spec)
            return interface.update()
            
        except InterfaceNotFound:
            _interface.update(interfaces=[vlan])
            interface_spec.update(_interface)
            interface = Layer2PhysicalInterface(**interface_spec)
            return self._engine.add_interface(interface)
                
    def add_inline_ips_interface(self, interface_id, second_interface_id,
        logical_interface_ref=None, vlan_id=None, failure_mode='normal',
        zone_ref=None, second_zone_ref=None, comment=None):
        """
        .. versionadded:: 0.5.6
            Using an inline interface on a layer 3 FW requires SMC and engine
            version >= 6.3.
            
        An inline IPS interface is a new interface type for Layer 3 NGFW
        engines version >=6.3. Traffic passing an Inline IPS interface will
        have a access rule default action of Allow. Inline IPS interfaces are
        bypass capable. When using bypass interfaces and NGFW is powered off,
        in an offline state or overloaded, traffic is allowed through without
        inspection regardless of the access rules.
        
        If the interface does not exist and a VLAN id is specified, the logical
        interface and zones will be applied to the top level physical interface.
        If adding VLANs to an existing inline ips pair, the logical and zones
        will be applied to the VLAN.
        
        :param str interface_id: first interface in the interface pair
        :param str second_interface_id: second interface in the interface pair
        :param str logical_interface_ref: logical interface name, href or LogicalInterface.
            If None, 'default_eth' logical interface will be used.
        :param str vlan_id: optional VLAN id for first interface pair
        :param str failure_mode: 'normal' or 'bypass' (default: normal).
            Bypass mode requires fail open interfaces.
        :param zone_ref: zone for first interface in pair, can be name,
            str href or Zone
        :param second_zone_ref: zone for second interface in pair, can be name,
            str href or Zone
        :param str comment: comment for this interface
        :raises EngineCommandFailed: failure creating interface
        :return: None
        
        .. note:: Only a single VLAN is supported on this inline pair type
        """
        _interface = {'interface_id': interface_id, 'second_interface_id': second_interface_id,
            'logical_interface_ref': logical_interface_ref, 'failure_mode': failure_mode,
            'zone_ref': zone_ref, 'second_zone_ref': second_zone_ref, 'comment': comment,
            'interface': 'inline_ips_interface', 'vlan_id': vlan_id}
        
        return self.add_inline_interface(**_interface)
    
    def add_inline_l2fw_interface(self, interface_id, second_interface_id,
            logical_interface_ref=None, vlan_id=None, zone_ref=None,
            second_zone_ref=None, comment=None):
        """
        .. versionadded:: 0.5.6
            Requires NGFW engine >=6.3 and layer 3 FW or cluster
        
        An inline L2 FW interface is a new interface type for Layer 3 NGFW
        engines version >=6.3. Traffic passing an Inline Layer 2 Firewall
        interface will have a default action in access rules of Discard.
        Layer 2 Firewall interfaces are not bypass capable, so when NGFW is
        powered off, in an offline state or overloaded, traffic is blocked on
        this interface.
        
        If the interface does not exist and a VLAN id is specified, the logical
        interface and zones will be applied to the top level physical interface.
        If adding VLANs to an existing inline ips pair, the logical and zones
        will be applied to the VLAN.
        
        :param str interface_id: interface id; '1-2', '3-4', etc
        :param str logical_interface_ref: logical interface name, href or LogicalInterface.
            If None, 'default_eth' logical interface will be used.
        :param str vlan_id: optional VLAN id for first interface pair
        :param str vlan_id2: optional VLAN id for second interface pair
        :param zone_ref_intf1: zone for first interface in pair, can be name,
            str href or Zone
        :param zone_ref_intf2: zone for second interface in pair, can be name,
            str href or Zone
        :raises EngineCommandFailed: failure creating interface
        :return: None
        
        .. note:: Only a single VLAN is supported on this inline pair type
        """
        _interface = {'interface_id': interface_id, 'second_interface_id': second_interface_id,
            'logical_interface_ref': logical_interface_ref, 'failure_mode': 'normal',
            'zone_ref': zone_ref, 'second_zone_ref': second_zone_ref, 'comment': comment,
            'interface': 'inline_l2fw_interface', 'vlan_id': vlan_id}
    
        return self.add_inline_interface(**_interface)
    
    def add_dhcp_interface(self, interface_id, dynamic_index, zone_ref=None,
            vlan_id=None, comment=None):
        """
        Add a DHCP interface on a single FW

        :param int interface_id: interface id
        :param int dynamic_index: index number for dhcp interface
        :param bool primary_mgt: whether to make this primary mgt
        :param str zone_ref: zone reference, can be name, href or Zone
        :raises EngineCommandFailed: failure creating interface
        :return: None

        See :class:`~DHCPInterface` for more information
        """
        _interface = {'interface_id': interface_id, 'interfaces': [{'nodes': [
            {'dynamic': True, 'dynamic_index': dynamic_index}], 'vlan_id': vlan_id}],
            'comment': comment, 'zone_ref': zone_ref}
        
        if 'single_fw' in self._engine.type:
            _interface.update(interface='single_node_interface')
        
        try:
            interface = self._engine.interface.get(interface_id)
            vlan = interface.vlan_interface.get(vlan_id)
            # Interface exists, so we need to update but check if VLAN already exists
            if vlan is None:
                interface._add_interface(**_interface)
                interface.update()
                
        except InterfaceNotFound:
            interface = Layer3PhysicalInterface(**_interface)
            return self._engine.add_interface(interface)
        
    def add_cluster_interface_on_master_engine(self, interface_id, macaddress,
            nodes, zone_ref=None, vlan_id=None, comment=None):
        """
        Add a cluster address specific to a master engine. Master engine
        clusters will not use "CVI" interfaces like normal layer 3 FW clusters,
        instead each node has a unique address and share a common macaddress.
        Adding multiple addresses to an interface is not supported with this
        method.

        :param str,int interface_id: interface id to use
        :param str macaddress: mac address to use on interface
        :param list nodes: interface node list
        :param bool is_mgmt: is this a management interface
        :param zone_ref: zone to use, by name, str href or Zone
        :param vlan_id: optional VLAN id if this should be a VLAN interface
        :raises EngineCommandFailed: failure creating interface
        :return: None
        """
        _interface = {'interface_id': interface_id, 'macaddress': macaddress,
            'interfaces': [{'nodes': nodes if nodes else [], 'vlan_id': vlan_id}],
            'zone_ref': zone_ref, 'comment': comment}
        
        try:
            interface = self._engine.interface.get(interface_id)
            vlan = interface.vlan_interface.get(vlan_id)
            # Interface exists, so we need to update but check if VLAN already exists
            if vlan is None:
                interface._add_interface(**_interface)
                interface.update()
                
        except InterfaceNotFound:
            interface = Layer3PhysicalInterface(**_interface)
            return self._engine.add_interface(interface)
        

class VirtualPhysicalInterfaceCollection(InterfaceCollection):
    """
    PhysicalInterface Collection provides an interface to retrieving existing
    interfaces and helper methods to shortcut the creation of an interface.
    """
    def __init__(self, engine):
        super(VirtualPhysicalInterfaceCollection, self).__init__(engine,
            'virtual_physical_interface')    
    
    def add_layer3_interface(self, interface_id, address, network_value,
                             zone_ref=None, comment=None, **kw):
        """
        Add a layer 3 interface on a virtual engine.

        :param str,int interface_id: interface identifier
        :param str address: ip address
        :param str network_value: network/cidr (12.12.12.0/24)
        :param str zone_ref: zone reference, can be name, href or Zone
        :param kw: keyword arguments are passed are any value attribute values of
            type :class:`smc.core.sub_interfaces.NodeInterface`
        :raises EngineCommandFailed: failure creating interface
        :return: None

        .. note::
            If an existing ip address exists on the interface and zone_ref is
            provided, this value will overwrite any previous zone definition.
        """
        interfaces = {'interface_id': interface_id, 'interfaces':
            [{'nodes': [{'address': address, 'network_value': network_value}]}],
            'zone_ref': zone_ref, 'comment': comment}
        interfaces.update(kw)
        
        try:
            interface = self._engine.interface.get(interface_id)
            interface._add_interface(**interfaces)
            return interface.update()
            
        except InterfaceNotFound:
            interface = VirtualPhysicalInterface(**interfaces)
            return self._engine.add_interface(interface)
        
    def add_tunnel_interface(self, interface_id, address, network_value,
                             zone_ref=None, comment=None):
        """
        Creates a tunnel interface for a virtual engine.

        :param str,int interface_id: the tunnel id for the interface, used as nicid also
        :param str address: ip address of interface
        :param str network_value: network cidr for interface; format: 1.1.1.0/24
        :param str zone_ref: zone reference for interface can be name, href or Zone
        :raises EngineCommandFailed: failure during creation
        :return: None
        """
        interfaces = [{'nodes': [{'address': address, 'network_value': network_value}]}]
        interface = {'interface_id': interface_id, 'interfaces': interfaces,
            'zone_ref': zone_ref, 'comment': comment}
        tunnel_interface = TunnelInterface(**interface)
        self._engine.add_interface(tunnel_interface)
    