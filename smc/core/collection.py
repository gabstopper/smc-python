"""
Collections classes for core based functionality like interfaces.

"""
from smc.core.interfaces import PhysicalInterface, TunnelInterface, \
    VirtualPhysicalInterface, InterfaceEditor
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
   
    Get a specific interface directly::
        
        engine.interface.get(10)
            
    Or use delegation to create interfaces::
        
        engine.physical_interface.add(2)
        engine.physical_interface.add_layer3_interface(....)
        ...

    .. note:: This can raise UnsupportedInterfaceType for unsupported engine
        types based on the interface context.
    """
    class_map = {
        PhysicalInterface.typeof: PhysicalInterface,
        TunnelInterface.typeof: TunnelInterface,
        VirtualPhysicalInterface.typeof: VirtualPhysicalInterface
        }
    
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
        :return: interface object by type (Physical, Tunnel, PhysicalVlanInterface)
        """
        return self.items.get(interface_id)

    def __iter__(self):
        for interface in super(InterfaceCollection, self).__iter__():
            if self._rel != 'interfaces': 
                if interface.typeof == self._rel: 
                    yield interface
            else:
                yield interface
    
    def update_or_create(self, interface):
        """
        Collections class update or create method that can be used as a
        shortcut to updating or creating an interface. The interface must
        first be defined and provided as the argument. The interface method
        must have an `update_interface` method which resolves differences and
        adds as necessary.
        
        :param Interface interface: an instance of an interface type, either
            PhysicalInterface or TunnelInterface
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
            self._engine.physical_interface.add_interface(
                interface)
            interface = self._engine.interface.get(interface.interface_id)
            created = True
        
        return interface, modified, created
    
    def __getattr__(self, key):
        # Dispatch to instance methods but only for adding interfaces.
        # Makes this work: engine.physical_interface.add_xxxx
        if key.startswith('add') and self.class_map.get(self._rel):
            if hasattr(self.class_map[self._rel], key):
                return getattr(self.class_map[self._rel](
                    engine=self._engine), key)
        raise AttributeError('Cannot proxy to given method: %s for the '
            'following type: %s' % (key, self._rel))

