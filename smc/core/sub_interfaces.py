"""
Module provides an interface to sub-interfaces on an engine. A 'top level' interface
is linked from the engine and will be PhysicalInterface, TunnelInterface, etc. Within
the top level interface, there are sub-interface configurations that identify the
basic settings such as ip address, network, administrative settings etc. These are
not called directly but used as a reference to the top level interface.
All sub interfaces are type dict. 
"""

from smc.base.structs import NestedDict, BaseIterable
from smc.api.exceptions import EngineCommandFailed


def get_sub_interface(typeof):
    if typeof in clsmembers:
        return clsmembers[typeof]

    
class SubInterfaceCollection(BaseIterable):
    """
    A Sub Interface collection for non-VLAN interfaces.
    """
    def __init__(self, interface):
        data = [clsmembers.get(kind)(data)
                for intf in interface.data.get('interfaces', [])
                for kind, data in intf.items()]
        super(SubInterfaceCollection, self).__init__(data)
        

class SubInterface(NestedDict):
    def __init__(self, data):
        super(SubInterface, self).__init__(data=data)
    
    def change_interface_id(self, interface_id):
        """
        Generic change interface ID for VLAN interfaces that are not
        Inline Interfaces (non-VLAN sub interfaces do not have an
        interface_id field).
        
        :param str, int interface_id: interface ID value
        """
        _, second = self.nicid.split('.')
        self.update(nicid='{}.{}'.format(str(interface_id), second))
    
    def change_vlan_id(self, vlan_id):
        """
        Change a VLAN id
        
        :param str vlan_id: new vlan
        """
        first, _ = self.nicid.split('.')
        self.update(nicid='{}.{}'.format(first, str(vlan_id)))
    
    def __getattr__(self, key):
        return self.get(key)

            
class ClusterVirtualInterface(SubInterface):
    """
    These interfaces (CVI) are used on cluster devices and applied to layer 3
    interfaces. They specify a 'VIP' (or shared IP) to be used for traffic load
    balancing or high availability. Each engine will still also have a 'node'
    interface for communication to/from the engine itself.
    The following getter/setter properties are available:

    :ivar str address: address of the CVI
    :ivar boolean auth_request: interface for authentication requests (only 1)
    :ivar str network_value: network address for interface, i.e. 1.1.1.0/24
    :ivar int nicid: nic interface identifier
    :ivar boolean relayed_by_dhcp: is the interface using DHCP
    :ivar str igmp_mode: IGMP mode (upstream/downstream/None)

    """
    typeof = 'cluster_virtual_interface'

    def __init__(self, data):
        super(ClusterVirtualInterface, self).__init__(data)
            
    @classmethod
    def create(cls, interface_id, address, network_value,
               **kwargs):
        """
        :param int interface_id: nic id to use for physical interface
        :param str address: address of CVI
        :param str network_value: network for CVI
        :rtype: ClusterVirtualInterface
        """
        data = {'address': address,
                'network_value': network_value,
                'nicid': str(interface_id),
                'auth_request': False}

        for k, v in kwargs.items():
            data.update({k: v})

        return cls(data)

    @property
    def vlan_id(self):
        """
        VLAN ID for this interface, if any
        
        :return: VLAN identifier
        :rtype: str
        """
        nicid = self.nicid
        if nicid:
            v = nicid.split('.')
            if len(v) > 1:
                return nicid.split('.')[1]

    def __repr__(self):
        if self.vlan_id:
            return '{0}(address={1}, vlan_id={2})'.format(
                self.__class__.__name__, self.address, self.vlan_id)
        else:
            return '{0}(address={1})'.format(
                self.__class__.__name__, self.address)


class InlineInterface(SubInterface):
    """
    InlineInterface
    This interface type is used on layer 2 or IPS related engines. It requires
    that you specify two interfaces to be part of the inline pair. These interfaces
    do not need to be sequential. It is also possible to add VLANs and zones to the
    inline interfaces.
    The logical interface reference needs to be unique for inline and capture interfaces
    when they are applied on the same engine.

    :ivar boolean inspect_unspecified_vlans: promiscuous SPAN on unspecified VLANs
    :ivar str logical_interface_ref (required): logical interface to use, by href
    :ivar str failure_mode: normal or bypass
    :ivar str nicid: interfaces for inline pair, for example, '4.50-5.55', '5-6'
    :ivar str vlan_id: vlan identifier for interface
    :ivar str zone_ref (optional): zone for second interface in pair
    """
    typeof = 'inline_interface'

    def __init__(self, data):
        super(InlineInterface, self).__init__(data)

    @classmethod
    def create(cls, interface_id, logical_interface_ref,
            second_interface_id=None, zone_ref=None, **kwargs):
        """
        :param str interface_id: two interfaces, i.e. '1-2', '4-5', '7-10', etc
        :param str logical_ref: logical interface reference
        :param str zone_ref: reference to zone, set on second inline pair
        :rtype: dict
        """
        data = {'inspect_unspecified_vlans': True,
                'nicid': '{}-{}'.format(str(interface_id), str(second_interface_id)) if 
                    second_interface_id else str(interface_id),
                'logical_interface_ref': logical_interface_ref,
                'zone_ref': zone_ref}

        for k, v in kwargs.items():
            data.update({k: v})

        return cls(data)
    
    def change_vlan_id(self, vlan_id):
        """
        Change a VLAN id for an inline interface.
        
        :param str vlan_id: New VLAN id. Can be in format '1-2' or
            a single numerical value. If in '1-2' format, this specifies
            the vlan ID for the first inline interface and the rightmost
            for the second.
        :return: None
        """
        first, second = self.nicid.split('-')
        firstintf = first.split('.')[0]
        secondintf = second.split('.')[0]
        newvlan = str(vlan_id).split('-')
        self.update(nicid='{}.{}-{}.{}'.format(
            firstintf, newvlan[0], secondintf, newvlan[-1]))

    def change_interface_id(self, newid):
        """
        Change the inline interface ID. The current format is
        nicid='1-2', where '1' is the top level interface ID (first),
        and '2' is the second interface in the pair. Consider the existing
        nicid in case this is a VLAN.
        
        :param str newid: string defining new pair, i.e. '3-4'
        :return: None
        """
        try:
            newleft, newright = newid.split('-')
        except ValueError:
            raise EngineCommandFailed('You must provide two parts when changing '
                'the interface ID on an inline interface, i.e. 1-2.')
        first, second = self.nicid.split('-')
        if '.' in first and '.' in second:
            firstvlan = first.split('.')[-1]
            secondvlan = second.split('.')[-1]
            self.update(nicid='{}.{}-{}.{}'.format(
                newleft, firstvlan, newright, secondvlan))
        else:
            # Top level interface or no VLANs
            self.update(nicid=newid)
    
    @property
    def vlan_id(self):
        """
        VLAN ID for this interface, if any
        
        :return: VLAN identifier
        :rtype: str
        """
        nicids = self.nicid.split('-')
        if nicids:
            u = []
            for vlan in nicids:
                if vlan.split('.')[-1] not in u:
                    u.append(vlan.split('.')[-1])
            return '-'.join(u)

    def __repr__(self):
        return '{0}(nicid={1})'.format(
            self.__class__.__name__, self.nicid)


class InlineIPSInterface(InlineInterface):
    """
    An Inline IPS Interface is a new interface type introduced
    in SMC version 6.3. This interface type is the same as a
    normal IPS interface except that it is applied on a Layer 3
    Firewall.
    
    .. versionadded:: 0.5.6
        Requires SMC 6.3.
    """
    typeof = 'inline_ips_interface'
    
    def __init__(self, data):
        super(InlineIPSInterface, self).__init__(data)
    

class InlineL2FWInterface(InlineInterface):
    """
    An Inline L2FW Interface is a new interface type introduced
    in SMC version 6.3. This interface type is the a layer 2 FW
    interface on a layer 3 firewall. By default this interface
    type does not support bypass mode and will discard on overload.
    
    .. versionadded:: 0.5.6
        Requires SMC 6.3.
    """
    typeof = 'inline_l2fw_interface'
    
    def __init__(self, data):
        super(InlineL2FWInterface, self).__init__(data)
    
    @classmethod
    def create(cls, interface_id, logical_interface_ref,
            second_interface_id=None, zone_ref=None, **kwargs):
        kwargs.pop('failure_mode', None)
        return super(InlineL2FWInterface, cls).create(
            interface_id, logical_interface_ref, second_interface_id,
            zone_ref=zone_ref, **kwargs)
        

class CaptureInterface(SubInterface):
    """
    Capture Interface (SPAN)
    This is a single physical interface type that can be installed on either
    layer 2 or IPS engine roles. It enables the NGFW to capture traffic on
    the wire without actually blocking it (although blocking is possible).

    :ivar boolean inspect_unspecified_vlans: promiscuous SPAN on unspecified VLANs
    :ivar str logical_interface_ref (required): logical interface to use, by href
    :ivar int reset_interface_nicid: if sending passive RST back, interface id to use
    :ivar str,int nicid: nicid for this capture interface
    """
    typeof = 'capture_interface'

    def __init__(self, data):
        super(CaptureInterface, self).__init__(data)
        
    @classmethod
    def create(cls, interface_id, logical_interface_ref, **kw):
        """
        :param int interface_id: the interface id
        :param str logical_ref: logical interface reference, must be unique from
               inline intfs
        :rtype: dict
        """
        data = {'inspect_unspecified_vlans': True,
                'logical_interface_ref': logical_interface_ref,
                'nicid': str(interface_id)}
        
        if 'reset_interface_nicid' in kw:
            data.update(reset_interface_nicid=kw.get('reset_interface_nicid'))

        return cls(data)

    @property
    def vlan_id(self):
        if '.' in self.nicid:
            return self.nicid.split('.')[-1]

    def __repr__(self):
        return '{0}(nicid={1})'.format(
            self.__class__.__name__, self.nicid)


class NodeInterface(SubInterface):
    """
    Node Interface
    Node dedicated interface (NDI) is used on specific engine types and represents
    an interface used for management (IPS and layer 2 engines), or as normal layer
    3 interfaces such as on a layer 3 firewall cluster.

    For Layer 2 Firewall/IPS these are used as individual interfaces. On clusters,
    these are used to define the node specific address for each node member, along
    with a cluster virtual interface.

    :ivar str address: ip address of this interface
    :ivar str network_value: network for this interface, i.e. 1.1.1.0/24
    :ivar str or int nicid: nic interface id
    :ivar int nodeid: node identifier for interface (in a cluster, each node will be unique)
    :ivar boolean outgoing: This option defines the IP address that the nodes use if they
        have to initiate connections (system communications, ping, etc.) through an interface that
        has no Node Dedicated IP Address. In Firewall Clusters, you must select an interface that has an
        IP address defined for all nodes.
    :ivar boolean primary_heartbeat: Whether interface is the primary heartbeat interface for
        communications between the nodes. It is recommended that you use a Physical Interface, not
        a VLAN Interface. It is also recommended that you do not direct any other traffic
        through this interface.
    :ivar boolean primary_mgt: Is it the Primary Control Interface for Management Server contact.
        There must be one and only one Primary Control Interface
    :ivar boolean auth_request: whether to specify this interface as interface for authentication
        requests. Should be set on interface acting as management
    :ivar boolean auth_request_source: If the authentication requests are sent to an external
        authentication server over VPN, select an interface with a Node Dedicated IP address that
        you want use for the authentication requests
    :ivar boolean reverse_connection: Reverse connection enables engine to contact SMC
        versus other way around
    :ivar str vlan_id: VLAN id for interface if assigned
    :ivar boolean backup_mgt: Whether interface is a backup control interface that is used if the
        primary control interface is not available
    :ivar boolean backup_heartbeat: Whether the interface is a backup heartbeat.
        It is not mandatory to configure a backup heartbeat interface.
    :ivar boolean dynamic: Whether this is a DHCP interface
    :ivar int dynamic_index: The dynamic index of the DHCP interface. The value is between
        1 and 16. Only used when 'dynamic' is set to True.
    :ivar str igmp_mode: IGMP mode (upstream/downstream/None)
    :ivar boolean vrrp: Enable VRRP
    :ivar str vrrp_address: IP address if VRRP is enabled
    :ivar int vrrp_id: The VRRP ID. Required only for VRRP mode
    :ivar int vrrp_priority: The VRRP Priority. Required only for VRRP mode
    """
    typeof = 'node_interface'

    def __init__(self, data):
        super(NodeInterface, self).__init__(data)

    @classmethod
    def create(cls, interface_id, address, network_value,
               nodeid=1, **kwargs):
        """
        :param int interface_id: interface id
        :param str address: ip address of the interface
        :param str network_value: network/netmask, i.e. x.x.x.x/24
        :param int nodeid: for clusters, used to identify the node number
        :rtype: dict
        """
        data = {'address': address,
                'network_value': network_value,
                'nicid': str(interface_id),
                'auth_request': False,
                'backup_heartbeat': False,
                'nodeid': nodeid,
                'outgoing': False,
                'primary_mgt': False,
                'primary_heartbeat': False}

        for k, v in kwargs.items():
            data.update({k: v})

        return cls(data)
    
    @property
    def vlan_id(self):
        """
        VLAN ID for this interface, if any
        
        :return: VLAN identifier
        :rtype: str
        """
        nicid = self.nicid
        #if nicid:
        if nicid and not nicid.startswith('SWP_'): # Ignore switch physical interface
            v = nicid.split('.')
            if len(v) > 1:
                return nicid.split('.')[1]

    def __repr__(self):
        if self.vlan_id:
            return '{0}(address={1}, vlan_id={2})'.format(
                self.__class__.__name__, self.address, self.vlan_id)
        elif self.dynamic_index:
            return '{0}(address=DHCP, dynamic_index={1})'.format(
                self.__class__.__name__, self.dynamic_index)
        else:
            return '{0}(address={1})'.format(
                self.__class__.__name__, self.address)


class SingleNodeInterface(NodeInterface):
    """
    SingleNodeInterface
    This interface is used by single node Layer 3 Firewalls. This type of interface
    can be a management interface as well as a non-management routed interface.

    :ivar bool dynamic: is this interface a dynamic DHCP interface
    :ivar int dynamic_index: dynamic interfaces index value
    :ivar boolean automatic_default_route: Flag to know if the dynamic default route will
        be automatically created for this dynamic interface. Used in DHCP interfaces only
    """
    typeof = 'single_node_interface'

    def __init__(self, data):
        super(SingleNodeInterface, self).__init__(data)

    @classmethod
    def create(cls, interface_id, address=None, network_value=None,
               nodeid=1, **kw):
        """
        :param int interface_id: interface id
        :param str address: address of this interface
        :param str network_value: network of this interface in cidr x.x.x.x/24
        :param int nodeid: if a cluster, identifies which node this is for
        :rtype: dict
        """
        data = {'address': address,
                'auth_request': False,
                'auth_request_source': False,
                'primary_heartbeat': False,
                'backup_heartbeat': False,
                'backup_mgt': False,
                'dynamic': False,
                'network_value': network_value,
                'nicid': str(interface_id),
                'nodeid': nodeid,
                'outgoing': False,
                'primary_mgt': False}
        
        for k, v in kw.items():
            data.update({k: v})
        
        if 'dynamic' in kw and kw['dynamic'] is not None:
            for key in ('address', 'network_value'):
                data.pop(key, None)
            if data['primary_mgt']: # Have to set auth_request to a different interface for DHCP
                data['auth_request'] = False
            
            if data.get('dynamic_index', None) is None:
                data['dynamic_index'] = 1
            elif data.get('automatic_default_route') is None:
                data.update(automatic_default_route=True)
        
        return cls(data)


class LoopbackClusterInterface(ClusterVirtualInterface):
    """
    This represents the CVI Loopback IP address.
    A CVI loopback IP address is used for loopback traffic that is sent to
    the whole cluster. It is shared by all the nodes in the cluster.
    """
    typeof = 'loopback_cluster_virtual_interface'
    
    def __init__(self, data, engine=None):
        self._engine = engine
        super(LoopbackClusterInterface, self).__init__(data)
        
    @classmethod
    def create(cls, address, ospf_area=None, **kwargs):
        """
        Create a loopback interface. Uses parent constructor
        
        :rtype: LoopbackClusterInterface
        """
        return super(LoopbackClusterInterface, cls).create(
            address=address,
            network_value='{}/32'.format(address),
            interface_id='Loopback Interface',
            ospfv2_area_ref=ospf_area,
            **kwargs)
    
    def delete(self):
        """
        Delete a loopback cluster virtual interface from this engine. 
        Changes to the engine configuration are done immediately.
        
        You can find cluster virtual loopbacks by iterating at the
        engine level::
        
            for loopbacks in engine.loopback_interface:
                ...
        
        :raises UpdateElementFailed: failure to delete loopback interface
        :return: None
        """
        self._engine.data[self.typeof] = \
            [loopback for loopback in self._engine.data.get(self.typeof, [])
             if loopback.get('address') != self.address]
            
        self._engine.update()
    
    def add_node_loopback(self, nodes, ospf_area=None):
        """
        Add loopback interfaces to a cluster. When adding a loopback on a
        cluster, every cluster node must have a loopback defined or you
        can optionally configure a loopback CVI address.
        
        Nodes should be in the format::
        
            {'address': '127.0.0.10', 'nodeid': 1,
             'address': '127.0.0.11', 'nodeid': 2}
             
        :param dict nodes: nodes defintion for cluster nodes
        :param str ospf_area: optional OSPF area for this loopback
        :raises EngineCommandFailed: failed creating loopback
        """
        pass
    
    def add_cvi_loopback(self, address, ospf_area=None, **kw):
        """
        Add a loopback interface as a cluster virtual loopback. This enables
        the loopback to 'float' between cluster members. Changes are committed
        immediately.
        
        :param str address: ip address for loopback
        :param int rank: rank of this entry
        :param str,Element ospf_area: optional ospf_area to add to loopback
        :raises UpdateElementFailed: failure to save loopback address
        :return: None
        """
        lb = self.create(address, ospf_area, **kw)
       
        if self.typeof in self._engine.data:
            self._engine.data[self.typeof].append(lb.data)
        else:
            self._engine.data[self.typeof] = [lb.data]
        
        self._engine.update()
  
    def __repr__(self):
        return 'LoopbackClusterInterface(address={}, auth_request={})'.format(
            self.address, self.auth_request)
        

class LoopbackInterface(NodeInterface):
    """
    Loopback interface for a physical or virtual single firewall.
    To create a loopback interface, call from the engine node::
    
        engine.loopback_interface.add_single(...)
    """
    typeof = 'loopback_node_dedicated_interface'
    
    def __init__(self, data, engine=None):
        self._engine = engine
        super(LoopbackInterface, self).__init__(data)
        
    @classmethod
    def create(cls, address, rank=1, nodeid=1, ospf_area=None, **kwargs):
        return super(LoopbackInterface, cls).create(
            interface_id='Loopback Interface',
            #rank=rank,
            address=address,
            network_value='{}/32'.format(address),
            nodeid=nodeid,
            ospfv2_area_ref=ospf_area,
            **kwargs)
    
    def add_single(self, address, rank=1, nodeid=1, ospf_area=None, **kwargs):
        """
        Add a single loopback interface to this engine. This is used
        for single or virtual FW engines.
        
        :param str address: ip address for loopback
        :param int nodeid: nodeid to apply. Default to 1 for single FW
        :param str, Element ospf_area: ospf area href or element
        :raises UpdateElementFailed: failure to create loopback address
        :return: None
        """
        lb = self.create(address, rank, nodeid, ospf_area, **kwargs)
        self._engine.nodes[0].data[self.typeof].append(lb.data)
        self._engine.update()
    
    def delete(self):
        """
        Delete a loopback interface from this engine. Changes to the
        engine configuration are done immediately.
        
        A simple way to obtain an existing loopback is to iterate the
        loopbacks or to get by address::
        
            lb = engine.loopback_interface.get('127.0.0.10')
            lb.delete()
        
        .. warning:: When deleting a loopback assigned to a node on a cluster
            all loopbacks with the same rank will also be removed.
        
        :raises UpdateElementFailed: failure to delete loopback interface
        :return: None
        """
        nodes = []
        for node in self._engine.nodes:
            node.data[self.typeof] = \
                [lb for lb in node.loopback_node_dedicated_interface
                 if lb.get('rank') != self.rank]
            nodes.append({node.type: node.data})
        
        self._engine.data['nodes'] = nodes
        self._engine.update()
    
    def change_ipaddress(self, address):
        self.update(address=address,
                    network_value='{}/32'.format(address))

    def __repr__(self):
        return 'LoopbackInterface(address={}, nodeid={}, rank={})'.format(
            self.address, self.nodeid, self.rank)   


def inheritors(klass):
    subclasses = {}
    work = [klass]
    while work:
        parent = work.pop()
        for child in parent.__subclasses__():
            if child.typeof not in subclasses:
                subclasses[child.typeof] = child
                work.append(child)
    return subclasses

clsmembers = inheritors(SubInterface)
