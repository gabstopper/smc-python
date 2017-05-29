"""
Module provides an interface to sub-interfaces on an engine. A 'top level' interface
is linked from the engine and will be PhysicalInterface, TunnelInterface, etc. Within
the top level interface, there are sub-interface configurations that identify the
basic settings such as ip address, network, administrative settings etc. These are
not called directly but used as a reference to the top level interface.
"""
from collections import Sequence


class SubInterface(Sequence):
    def __init__(self, subif):
        self.subif = subif if subif is not None else []

    def __getitem__(self, i):
        intf = self.subif[i]
        for k, v in intf.items():
            return SubInterface.get_subinterface(k)(v)

    def __len__(self):
        return len(self.subif)

    @staticmethod
    def get_subinterface(typeof):
        for subif in [NodeInterface, SingleNodeInterface, ClusterVirtualInterface,
                      CaptureInterface, InlineInterface]:
            if subif.typeof == typeof:
                return subif


class LoopbackInterface(object):
    @classmethod
    def create(cls, address, network_value, **kwargs):
        data = {'address': address,
                'network_value': network_value,
                'nicid': 'Loopback Interface'}

        for k, v in kwargs.items():
            data.update({k: v})
        
        return data
            
class ClusterVirtualInterface(object):
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
        self.__dict__ = data

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
    def data(self):
        return {'cluster_virtual_interface': self.__dict__}

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
    
    def __getattr__(self, attr):
        return None

    def __repr__(self):
        if self.vlan_id:
            return '{0}(address={1}, vlan_id={2})'.format(
                self.__class__.__name__, self.address, self.vlan_id)
        else:
            return '{0}(address={1})'.format(
                self.__class__.__name__, self.address)


class InlineInterface(object):
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
        self.__dict__ = data

    @classmethod
    def create(cls, interface_id, logical_interface_ref,
               zone_ref=None, **kwargs):
        """
        :param str interface_id: two interfaces, i.e. '1-2', '4-5', '7-10', etc
        :param str logical_ref: logical interface reference
        :param str zone_ref: reference to zone, set on second inline pair
        :rtype: dict
        """
        data = {'failure_mode': 'normal',
                'inspect_unspecified_vlans': True,
                'nicid': interface_id,
                'logical_interface_ref': logical_interface_ref,
                'zone_ref': zone_ref}

        for k, v in kwargs.items():
            data.update({k: v})

        return cls(data)
        
    @property
    def data(self):
        return {'inline_interface': self.__dict__}

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

    def __getattr__(self, attr):
        return None

    def __repr__(self):
        return '{0}(nicid={1})'.format(
            self.__class__.__name__, self.nicid)


class CaptureInterface(object):
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
        self.__dict__ = data

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
    def data(self):
        return {'capture_interface': self.__dict__}

    def __getattr__(self, attr):
        return None

    def __repr__(self):
        return '{0}(nicid={1})'.format(
            self.__class__.__name__, self.nicid)


class NodeInterface(object):
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
        self.__dict__ = data

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
    def data(self):
        return {self.typeof: self.__dict__}

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

    def __getattr__(self, attr):
        return None

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
        pass

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
