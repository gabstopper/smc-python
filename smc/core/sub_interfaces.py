"""
Module provides an interface to sub-interfaces on an engine. A 'top level' interface
is linked from the engine and will be PhysicalInterface, TunnelInterface, etc. Within
the top level interface, there are sub-interface configurations that identify the
basic settings such as ip address, network, administrative settings etc. These are
not called directly but used as a reference to the top level interface.
"""
from smc.base.util import element_resolver
from smc.base.model import SubDict
from smc.api.exceptions import EngineCommandFailed


def get_sub_interface(typeof):
    if typeof in clsmembers:
        return clsmembers[typeof]


def all_interfaces(data):
    """
    Return a list of subinterfaces based on the interface
    list.
    """
    return [get_sub_interface(kind)(value)
            for interface in data
            for kind, value in interface.items()]
        

class SubInterface(object):
    def __init__(self, data):
        self.__dict__ = data

    @property
    def data(self):
        return {self.typeof: self.__dict__}
    
    def __getattr__(self, _):
        return None


class LoopbackInterface(SubDict):
    """
    A Loopback interface can be assigned to any layer 3 routed engine, single
    firewall, virtual firewall or cluster firewall.
    
    Any IP address that is not used to route traffic on another interface can
    be used as a loopback IP address. Loopback IP addresses are not connected
    to any physical interface and they do not create connectivity to any
    network.
    
    Some common rules for loopback addresses:
    
    * You can add several loopback IP addresses on a given layer 3 firewall
    * Any IP address that is not already used on another Physical or VLAN
      Interface in the same firewall can be used as a loopback IP address.
    * The same IP address can be used as a loopback IP address and as the IP
      address of a Tunnel Interface.
    * Loopback IP addresses can be used as the Identity for Authentication
      Requests, the Source for Authentication Requests, and the Default IP
      Address for Outgoing Traffic.
    
    """
    def __init__(self, data, **kw):
        self._parent = kw.pop('parent', None)
        super(LoopbackInterface, self).__init__(data=data)
        
    def delete(self):
        if isinstance(self, LoopbackClusterVirtualInterface):
            engine = self._parent
            engine.data[LoopbackClusterVirtualInterface.typeof] = \
                [lb for lb in engine.loopback_cluster_virtual_interface
                 if lb.get('address') != self.address]
            engine.update()
        else: 
            node = self._parent
            if len(node._engine.nodes) == 1:
                node.data[LoopbackNodeInterface.typeof] = \
                    [lb for lb in node.loopback_node_dedicated_interface
                     if lb.get('address') != self.address]
                node.update()
            else: 
                # For cluster loopbacks, deleting a single loopback
                # will also delete the peer member entries by the rank
                # field. In case delete is done in a loop, check that
                # the loopback exists in the engine reference or noop
                if any(lb for n in node._engine.nodes
                       for lb in n.loopback_node_dedicated_interface
                       if lb.get('address') == self.address):
                        
                    nodes = []
                    for _node in node._engine.nodes:
                        _node.data[LoopbackNodeInterface.typeof] = \
                            [lb for lb in _node.loopback_node_dedicated_interface
                             if lb.get('rank') != self.rank]
                        nodes.append({_node.type: _node.data})
            
                    node._engine.data['nodes'] = nodes
                    node._engine.update()        
                
    def add(self, address, nodeid=1, ospf_area=None, **kwargs):
        """
        Add a loopback interface to a single node engine. 
        
        :param str address: IP for loopback
        :param str network_value: network cidr for address
        :param str nodeid: nodeid for this engine. Will always
            be 1.
        :param str ospf_area: optional OSPF area for this loopback
        :raises EngineCommandFailed: failed creating loopback
        """
        if len(self._engine.nodes) == 1:
            lb = LoopbackNodeInterface.create(
                address, nodeid, ospf_area, **kwargs)
            
            node = self._engine.nodes[0]
            if LoopbackNodeInterface.typeof in node.data:
                node.data[LoopbackNodeInterface.typeof].append(lb)
            else:
                node.data.update(
                    {LoopbackNodeInterface.typeof: [lb]})
            
            node.update()
        
        else:
            raise EngineCommandFailed('Engine has multiple nodes, use '
                'add_to_cluster_nodes when adding loopback interfaces '
                'to clusters, or add a loopback CVI')
            
    def add_to_cluster_nodes(self, nodes, ospf_area=None):
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
    
    def add_cluster_virtual(self, address, igmp_mode=None, ospf_area=None,
            auth_request=False, relayed_by_dhcp=False, **kw):
        """
        Add a loopback interface as a cluster virtual loopback. This enables
        the loopback to 'float' between cluster members. Otherwise assign a
        unique loopback address per cluster node.
        
        """
        lb = LoopbackClusterVirtualInterface.create(
            address, igmp_mode=igmp_mode, ospf_area=ospf_area,
            auth_request=auth_request, relayed_by_dhcp=relayed_by_dhcp,
            **kw)
        
        if getattr(self._engine, LoopbackClusterVirtualInterface.typeof):
            self._engine.data[LoopbackClusterVirtualInterface.typeof].append(lb)
        else:
            self._engine.data.update(
                {LoopbackClusterVirtualInterface.typeof: [lb]})
        
        self._engine.update()

                
class LoopbackNodeInterface(LoopbackInterface):
    typeof = 'loopback_node_dedicated_interface'
    
    def __init__(self, data, **kw):
        super(LoopbackNodeInterface, self).__init__(data, **kw)
    
    @classmethod
    def create(cls, address, nodeid=1, ospf_area=None, **kwargs):
        data = {'address': address,
                'network_value': '{}/32'.format(address),
                'nicid': 'Loopback Interface',
                'ospfv2_area_ref': element_resolver(ospf_area) if \
                    ospf_area else None,
                'nodeid': nodeid }

        for k, v in kwargs.items():
            data.update({k: v})
    
        return data
           
    def __repr__(self):
        return '{}(address={}, nodeid={})'.format(
            self.__class__.__name__, self.address, self.nodeid)

        
class LoopbackClusterVirtualInterface(LoopbackInterface):
    typeof = 'loopback_cluster_virtual_interface'
    
    def __init__(self, data, **kw):
        super(LoopbackClusterVirtualInterface, self).__init__(data, **kw)
    
    @classmethod
    def create(cls, address, igmp_mode=None, ospf_area=None,
               auth_request=False, relayed_by_dhcp=False, **kw):
        
        data = {'address': address,
                'network_value': '{}/32'.format(address),
                'nicid': 'Loopback Interface',
                'ospfv2_area_ref': element_resolver(ospf_area) if ospf_area else None,
                'igmp_mode': igmp_mode,
                'auth_request': auth_request,
                'relayed_by_dhcp': relayed_by_dhcp}

        for k, v in kw.items():
            data.update({k: v})
    
        return data

    def __repr__(self):
        return '{}(address={}, auth_request={})'.format(
            self.__class__.__name__, self.address, self.auth_request)
            
'''
class LoopbackInterface(object):
    @classmethod
    def create(cls, address, network_value, **kwargs):
        data = {'address': address,
                'network_value': network_value,
                'nicid': 'Loopback Interface'}

        for k, v in kwargs.items():
            data.update({k: v})
        
        return data
'''
            
class ClusterVirtualInterface(SubInterface):
    """
    ClusterVirtualInterface
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
        :rtype: dict
        """
        data = {'address': address,
                'network_value': network_value,
                'nicid': interface_id,
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
    :ivar str nicid: interfaces for inline pair, for example, '1-2', '5-6' (interfaces 5 and 6)
    :ivar str vlan_id: vlan identifier for interface
    :ivar str zone_ref (optional): zone for second interface in pair
    """
    typeof = 'inline_interface'

    def __init__(self, data):
        super(InlineInterface, self).__init__(data)

    @classmethod
    def create(cls, interface_id, logical_interface_ref,
               zone_ref=None, **kwargs):
        """
        :param str interface_id: two interfaces, i.e. '1-2', '4-5', '7-10', etc
        :param str logical_ref: logical interface reference
        :param str zone_ref: reference to zone, set on second inline pair
        :rtype: dict
        """
        data = {'inspect_unspecified_vlans': True,
                'nicid': interface_id,
                'logical_interface_ref': logical_interface_ref,
                'zone_ref': zone_ref}

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
    def create(cls, interface_id, logical_interface_ref, **kwargs):
        """
        :param int interface_id: the interface id
        :param str logical_ref: logical interface reference, must be unique from
               inline intfs
        :rtype: dict
        """
        data = {'inspect_unspecified_vlans': True,
                'logical_interface_ref': logical_interface_ref,
                'nicid': interface_id}

        for k, v in kwargs.items():
            data.update({k: v})

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
                'nicid': interface_id,
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


class SingleNodeInterface(NodeInterface):
    """
    SingleNodeInterface
    This interface is used by single node Layer 3 Firewalls. This type of interface
    can be a management interface as well as a non-management routed interface.

    :ivar boolean automatic_default_route: Flag to know if the dynamic default route will be automatically
        created for this dynamic interface. Used in DHCP interfaces only
    """
    typeof = 'single_node_interface'

    def __init__(self, data):
        super(SingleNodeInterface, self).__init__(data)

    @classmethod
    def create(cls, interface_id, address, network_value,
               nodeid=1, **kwargs):
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
                'nicid': interface_id,
                'nodeid': nodeid,
                'outgoing': False,
                'primary_mgt': False}

        for k, v in kwargs.items():
            data.update({k: v})

        return cls(data)
        
    @classmethod
    def create_dhcp(cls, interface_id, dynamic_index=1, nodeid=1,
                    **kwargs):
        """
        The dynamic index specifies which interface index is used
        for the DHCP interface. This would be important if you had
        multiple DHCP interfaces on a single engine.
        The interface ID identifies which physical interface DHCP will
        be associated with.

        :param interface_id: interface to use for DHCP
        :param dynamic_index: DHCP index (when using multiple DHCP interfaces)
        :rtype: dict
        """
        data = {'auth_request': False,
                'outgoing': False,
                'dynamic': True,
                'dynamic_index': dynamic_index,
                'nicid': interface_id,
                'nodeid': nodeid,
                'primary_mgt': False,
                'automatic_default_route': False,
                'reverse_connection': False}

        for k, v in kwargs.items():
            data.update({k: v})

        return cls(data)


def _add_vlan_to_inline(inline_intf, vlan_id, vlan_id2=None):
    """
    Modify InlineInterface to add VLAN by ID

    :param inline_intf: InlineInterface dict
    :param str vlan_id: VLAN id
    :return: InlineInterface with VLAN configuration
    """
    for _, vals in inline_intf.items():
        nicid = vals.get('nicid')
        try:
            first, last = nicid.split('-')
            if vlan_id2 is None:
                nicid = '{}.{}-{}.{}'.format(first,
                                             str(vlan_id), last, str(vlan_id))
            else:
                nicid = '{}.{}-{}.{}'.format(first,
                                             str(vlan_id), last, str(vlan_id2))
        except ValueError:
            pass
    vals.update(nicid=nicid)
    return inline_intf


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
