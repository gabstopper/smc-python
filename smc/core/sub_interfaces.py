"""
Module provides an interface to sub-interfaces on an engine. A 'top level' interface
is linked from the engine and will be PhysicalInterface, TunnelInterface, etc. Within
the top level interface, there are sub-interface configurations that identify the
basic settings such as ip address, network, administrative settings etc. These are
not called directly but used as a reference to the top level interface.
"""

class ClusterVirtualInterface(object):
    """
    ClusterVirtualInterface
    These interfaces (CVI) are used on cluster devices and applied to layer 3
    interfaces. They specify a 'VIP' (or shared IP) to be used for traffic load
    balancing or high availability. Each engine will still also have a 'node' 
    interface for communication to/from the engine itself.
    """
    typeof = 'cluster_virtual_interface'
    
    def __init__(self, data):
        self.data = data
    
    @classmethod
    def create(cls, interface_id, address, network_value, 
               **kwargs):
        """
        :param int interface_id: nic id to use for physical interface
        :param str address: address of CVI
        :param str network_value: network for CVI
        :return: dict
        """
        data = {'address': address,
                'network_value':network_value,
                'nicid': interface_id,
                'auth_request': False}
    
        for k, v in kwargs.items():
            data.update({k: v})
   
        return cls(data)
    
    def __call__(self):
        return {'cluster_virtual_interface': self.data}
    
    @property
    def address(self):
        """
        IP Address of this CVI
        
        :param str value: ip address
        :return: str
        """
        return self.data.get('address')
    
    @address.setter
    def address(self, value):
        self.data['address'] = value
        
    @property
    def auth_request(self):
        """
        The IP address of the selected interface is used when an engine
        contacts an external authentication server and it is also displayed 
        (by default) to end-users in Telnet-based authentication. This option 
        does not affect the routing of the connection with the authentication 
        server. The IP address is used only as a parameter inside the 
        authentication request payload to give a name to the request sender. 

        There must be one and only one Interface used for auth request.
        
        :param boolean value: enable/disable      
        :return: boolean
        """
        return self.data.get('auth_request')
    
    @auth_request.setter
    def auth_request(self, value):
        self.data['auth_request'] = value
        
    @property
    def igmp_mode(self):
        """
        Read-only IGMP mode (upstream/downstream/None)
        
        :return: str
        """
        return self.data.get('igmp_mode')
    
    @property
    def network_value(self):
        """
        Network cidr for this interface
        
        :param str value: network cidr, i.e. 1.1.1.0/24
        :return: str
        """
        return self.data.get('network_value')
    
    @network_value.setter
    def network_value(self, value):
        self.data['network_value'] = value
    
    @property
    def nicid(self):
        """
        Nicid for this interface
        
        :param str value: nic id as string
        :return: str
        """
        return self.data.get('nicid')
    
    @nicid.setter
    def nicid(self, value):
        self.data['nicid'] = value
    
    @property
    def relayed_by_dhcp(self):
        """
        Read-only DHCP relay setting.
        
        When the parent Physical Interface uses DHCP Relay,
        there must be one and only one Interface relayed by 
        DHCP.
        
        :return: boolean
        """
        return self.data.get('relayed_by_dhcp')
    
    def __getattr__(self, attr):
        return None

    def __repr__(self):
        return '{0}(address={1})'.format(self.__class__.__name__, 
                                         self.address)
        
class InlineInterface(object):
    """
    InlineInterface
    This interface type is used on layer 2 or IPS related engines. It requires
    that you specify two interfaces to be part of the inline pair. These interfaces
    do not need to be sequential. It is also possible to add VLANs and zones to the
    inline interfaces.
    The logical interface reference needs to be unique for inline and capture interfaces
    when they are applied on the same engine.
    """
    typeof = 'inline_interface'
    
    def __init__(self, data):
        self.data = data
    
    @classmethod
    def create(cls, interface_id, logical_interface_ref, 
               zone_ref=None, **kwargs):
        """
        :param str interface_id: two interfaces, i.e. '1-2', '4-5', '7-10', etc
        :param str logical_ref: logical interface reference
        :param str zone_ref: reference to zone, set on second inline pair
        :return: dict
        """
        data = {'failure_mode': 'normal',
                'inspect_unspecified_vlans': True,
                'nicid': interface_id,
                'logical_interface_ref': logical_interface_ref,
                'zone_ref': zone_ref}
    
        for k, v in kwargs.items():
            data.update({k: v})
    
        return cls(data)
    
    def __call__(self):
        return {'inline_interface': self.data}

    @property
    def inspect_unspecified_vlans(self):
        """
        Deselect this option to make the IPS engine ignore traffic from
        VLANs that are not included in the IPS engine interface config.
        
        :param boolean value: enable/disable
        :return: boolean
        """
        return self.data.get('inspect_unspecified_vlans')
    
    @inspect_unspecified_vlans.setter
    def inspect_unspecified_vlans(self, value):
        self.data['inspect_unspecified_vlans'] = value
    
    @property
    def logical_interface_ref(self):
        """
        Select the Logical Interface for inspection.
        You cannot use the same Logical Interface element for both
        Inline and Capture Interfaces on the same IPS engine. 
        Required.
        
        :param str value: string href of logical interface
        :return: str
        """
        return self.data.get('logical_interface_ref')
    
    @logical_interface_ref.setter
    def logical_interface_ref(self, value):
        self.data['logical_interface_ref'] = value
    
    @property
    def failure_mode(self):
        """
        Select how traffic to the Inline Interface is handled if the 
        IPS engine goes offline. There are two options: 'bypass' or 
        'normal'.
        
        Using the Bypass mode requires the IPS appliance to 
        have a fail-open network interface card. If the ports
        that represent the pair of Inline Interfaces on the 
        appliance cannot fail open, the policy installation 
        fails on the IPS engine. 
        
        :param str value: normal or bypass
        :return: str
        """
        return self.data.get('failure_mode')
    
    @failure_mode.setter
    def failure_mode(self, value):
        self.data['failure_mode'] = value
    
    @property
    def nicid(self):
        """
        Get nicid's for this inline interface. For inline interfaces
        this will be specified as a string using the 'first-last' 
        interfaces. For example, '1-2', '5-6' (interfaces 5 and 6).
        
        :param str nicid: interfaces used for inline pair
        :return: str
        """
        return self.data.get('nicid')
    
    @nicid.setter
    def nicid(self, value):
        self.data['nicid'] = value
    
    @property
    def virtual_second_mapping(self):
        return self.data.get('virtual_second_mapping')
    
    @virtual_second_mapping.setter
    def virtual_second_mapping(self, value):
        self.data['virtual_second_mapping'] = value
    
    @property
    def vlan_id(self):
        """
        Returns a string representation of VLANs for this inline interface
        
        :return: str
        """
        nicids = self.nicid.split('-')
        if nicids:
            u = set()
            for vlan in nicids:
                u.add(vlan.split('.')[-1])
        return '-'.join(u)       
    
    @property
    def zone_ref(self):
        """
        Select the network Zone to which the second interface belongs. 
        Not Required. Should be the href of zone (not name).
        
        :param str value: string href of zone
        :return: str
        """
        return self.data.get('zone_ref')
    
    @zone_ref.setter
    def zone_ref(self, value):
        self.data['zone_ref'] = value
    
    def __getattr__(self, attr):
        return None
    
    def __repr__(self):
        return '{0}(nicid={1})'.format(self.__class__.__name__, 
                                       self.nicid)

class CaptureInterface(object):
    """ 
    Capture Interface (SPAN)
    This is a single physical interface type that can be installed on either
    layer 2 or IPS engine roles. It enables the NGFW to capture traffic on
    the wire without actually blocking it (although blocking is possible).
    """
    typeof = 'capture_interface'
    
    def __init__(self, data):
        self.data = data
 
    @classmethod
    def create(cls, interface_id, logical_interface_ref, **kwargs):
        """
        :param int interface_id: the interface id
        :param str logical_ref: logical interface reference, must be unique from 
               inline intfs
        :return: dict
        """
        data = {'inspect_unspecified_vlans': True,
                'logical_interface_ref': logical_interface_ref,
                'nicid': interface_id}
    
        for k, v in kwargs.items():
            data.update({k: v})
    
        return cls(data)
    
    def __call__(self):
        return {'capture_interface': self.data}
    
    @property
    def inspect_unspecified_vlans(self):
        """
        Deselect this option to make the IPS engine ignore traffic from
        VLANs that are not included in the IPS engine interface config.
        
        :param boolean value: enable/disable
        :return: boolean
        """
        return self.data.get('inspect_unspecified_vlans')
    
    @inspect_unspecified_vlans.setter
    def inspect_unspecified_vlans(self, value):
        self.data['inspect_unspecified_vlans'] = value
    
    @property
    def logical_interface_ref(self):
        """
        Select the Logical Interface for inspection.
        You cannot use the same Logical Interface element for both
        Inline and Capture Interfaces on the same IPS engine. 
        Required.
        
        :param str value: logical interface href
        :return: str
        """
        return self.data.get('logical_interface_ref')
    
    @logical_interface_ref.setter
    def logical_interface_ref(self, value):
        self.data['logical_interface_ref'] = value
    
    @property
    def reset_interface_nicid(self):
        """
        Select the Reset Interface to specify the interface through 
        which TCP connection resets are sent when Reset responses are
        used in your IPS policy. Not Required.
        
        :param int value: int value of nicid when resets are used
        :return: int
        """
        return self.data.get('reset_interface_nicid')
    
    @reset_interface_nicid.setter
    def reset_interface_nicid(self, value):
        self.data['reset_interface_nicid'] = value
    
    @property
    def nicid(self):
        """
        Nicid for this interface
        
        :param str value: nicid value
        :return: str
        """
        return self.data.get('nicid')
    
    @nicid.setter
    def nicid(self, value):
        self.data['nicid'] = value
    
    def __getattr__(self, attr):
        return None

    def __repr__(self):
        return '{0}(nicid={1})'.format(self.__class__.__name__, 
                                       self.nicid)
        
class NodeInterface(object):
    """
    Node Interface
    Node dedicated interface (NDI) is used on specific engine types and represents 
    an interface used for management (IPS and layer 2 engines), or as normal layer 
    3 interfaces such as on a layer 3 firewall cluster. 
    
    For Layer 2 Firewall/IPS these are used as individual interfaces. On clusters, 
    these are used to define the node specific address for each node member, along 
    with a cluster virtual interface.
    """ 
    typeof = 'node_interface'
    
    def __init__(self, data):
        self.data = data
    
    @classmethod
    def create(cls, interface_id, address, network_value,
               nodeid=1, **kwargs):
        """
        :param int interface_id: interface id
        :param str address: ip address of the interface
        :param str network_value: network/netmask, i.e. x.x.x.x/24
        :param int nodeid: for clusters, used to identify the node number
        :return: dict
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
    
    def __call__(self):
        return {self.typeof: self.data}   
    
    @property
    def address(self):
        """
        IP Address of interface
        
        :param str value: ip address of interface
        :return: str
        """
        return self.data.get('address')
    
    @address.setter
    def address(self, value):
        self.data['address'] = value
    
    @property
    def auth_request(self):
        """
        The IP address of the selected interface is used when an engine
        contacts an external authentication server and it is also displayed 
        (by default) to end-users in Telnet-based authentication. This option 
        does not affect the routing of the connection with the authentication 
        server. The IP address is used only as a parameter inside the 
        authentication request payload to give a name to the request sender. 
        
        There must be one and only one Interface used for authentication 
        requests.
        
        :param boolean value: enable/disable
        :return: boolean
        """
        return self.data.get('auth_request')
    
    @auth_request.setter
    def auth_request(self, value):
        self.data['auth_request'] = value
        
    @property
    def auth_request_source(self):
        """
        By default, the source IP address for authentication requests
        is selected according to routing. If the authentication requests 
        are sent to an external authentication server over VPN, select an 
        interface with a Node Dedicated IP address that you want use for 
        the authentication requests.
        
        :return: boolean
        """
        return self.data.get('auth_request_source')
    
    @auth_request_source.setter
    def auth_request_source(self, value):
        self.data['auth_request_source'] = value
    
    @property
    def backup_for_web_access(self):
        """
        Read-only setting for web access backup
        
        :return: boolean
        """
        return self.data.get('backup_for_web_access')
    
    @property
    def backup_mgt(self):
        """
        Whether interface is a backup control interface that is used if the 
        primary control interface is not available.
        
        :param boolean value: enable/disable
        :return: boolean
        """
        return self.data.get('backup_mgt')
    
    @backup_mgt.setter
    def backup_mgt(self, value):
        self.data['backup_mgt'] = value
    
    @property
    def backup_heartbeat(self):
        """
        Whether the interface is a backup heartbeat. 
        It is not mandatory to configure a backup heartbeat interface.
        
        :param boolean value: enable/disable
        :return: boolean 
        """
        return self.data.get('backup_heartbeat')
    
    @backup_heartbeat.setter
    def backup_heartbeat(self, value):
        self.data['backup_heartbeat'] = value
    
    @property
    def comment(self):
        """
        Comment for interface
        
        :param str value: string comment
        :return: str
        """
        return self.data.get('comment')
    
    @comment.setter
    def comment(self, value):
        self.data['comment'] = value
            
    @property
    def dynamic(self):
        """
        Whether this is a DHCP interface
        
        :param boolean value: enable/disable
        :return: boolean
        """
        return self.data.get('dynamic')
    
    @dynamic.setter
    def dynamic(self, value):
        self.data['dynamic'] = value
        
    @property
    def dynamic_index(self):
        """
        The dynamic index of the DHCP interface. The value is between 
        1 and 16. Only used when 'dynamic' is set to True.
        
        :param int value: set index for dhcp
        :return: int
        """
        if self.data.get('dynamic_index'):
            return int(self.data.get('dynamic_index'))
        
    @dynamic_index.setter
    def dynamic_index(self, value):
        self.data['dynamic_index'] = value
        
    @property
    def igmp_mode(self):
        """
        Read-only IGMP mode (upstream/downstream/None)
        
        :return: str
        """
        return self.data.get('igmp_mode')
        
    @property
    def network_value(self):
        """
        Network cidr for this interface
        
        :param str value: network cidr of interface, i.e. 1.1.1.0/24
        :return: str 
        """
        return self.data.get('network_value')
    
    @network_value.setter
    def network_value(self, value):
        self.data['network_value'] = value
    
    @property
    def nicid(self):
        """
        Nicid for this interface
        
        :param str value: nicid of interface
        :return: str
        """
        return self.data.get('nicid')
    
    @nicid.setter
    def nicid(self, value):
        self.data['nicid'] = value
    
    @property
    def nodeid(self):
        """
        The node id of the interface
        
        :param int value: node identifier for interface
        :return: int
        """
        return self.data.get('nodeid')
    
    @nodeid.setter
    def nodeid(self, value):
        self.data['nodeid'] = value
    
    @property
    def outgoing(self):
        """
        This option defines the IP address that the nodes use if they 
        have to initiate connections (system communications, ping, etc.) 
        through an interface that has no Node Dedicated IP Address. 
        In Firewall Clusters, you must select an interface that has an 
        IP address defined for all nodes. 
        
        There must be one and only one NDI defined for Outgoing.
        
        :param boolean value: enable/disable
        :return: boolean
        """
        return self.data.get('outgoing')
    
    @outgoing.setter
    def outgoing(self, value):
        self.data['outgoing'] = value

    @property
    def pppoa(self):
        """
        Read-only PPPoA mode
        This can be used with ADSL interfaces only
        
        :return: boolean
        """
        return self.data.get('pppoa')
    
    @property
    def pppoe(self):
        """
        Read-only PPPoE mode
        This can be used with Physical Interfaces or ADSL Interfaces.
        
        :return: boolean
        """ 
        return self.data.get('pppoe')
    
    @property
    def primary_for_web_access(self):
        """
        Read-only primary web configuration interface
        
        :return: boolean
        """
        return self.data.get('primary_for_web_access')
    
    @property
    def primary_heartbeat(self):
        """
        Whether interface is the primary heartbeat interface for 
        communications between the nodes. It is recommended that you 
        use a Physical Interface, not a VLAN Interface. 
        It is also recommended that you do not direct any other traffic 
        through this interface. 
        A dedicated network helps ensure reliable and secure operation.
        
        :param boolean value: enable/disable
        :return: boolean
        """
        return self.data.get('primary_heartbeat')
    
    @primary_heartbeat.setter
    def primary_heartbeat(self, value):
        self.data['primary_heartbeat'] = value
    
    @property
    def primary_mgt(self):
        """
        Is it the Primary Control Interface for Management Server contact.
        There must be one and only one Primary Control Interface.
        
        :param boolean value: enable/disable
        :return: boolean
        """
        return self.data.get('primary_mgt')
    
    @primary_mgt.setter
    def primary_mgt(self, value):
        self.data['primary_mgt'] = value
        
    @property
    def relayed_by_dhcp(self):
        """
        Read-only field indicating use of DHCP relay.

        When the parent Physical Interface uses DHCP Relay,
        there must be one and only one Interface relayed by DHCP
        
        :param boolean value: enable/disable
        :return: boolean
        """
        return self.data.get('relayed_by_dhcp')
    
    @property
    def reverse_connection(self):
        """
        Reverse connection enables engine to contact SMC
        versus other way around
        
        :param boolean value: enable/disable
        :return: boolean
        """
        return self.data.get('reverse_connection')
    
    @reverse_connection.setter
    def reverse_connection(self, value):
        self.data['reverse_connection'] = value
    
    @property
    def vlan_id(self):
        """
        Return VLAN id of this interface, or None
        
        :return: str
        """
        nicid = self.data.get('nicid')
        if nicid:
            v = nicid.split('.')
            if len(v) > 1:
                return nicid.split('.')[1]
        #Return None
        
    @property
    def vrrp(self):
        """
        Whether VRRP is enabled
        
        :param boolean value: enable/disable
        :return: boolean
        """
        return self.data.get('vrrp')
    
    @vrrp.setter
    def vrrp(self, value):
        self.data['vrrp'] = value
    
    @property
    def vrrp_address(self):
        """
        The VRRP IP Address. Required only for VRRP mode
        
        :param str value: ip address for VRRP
        :return: str
        """ 
        return self.data.get('vrrp_address')
    
    @vrrp_address.setter
    def vrrp_address(self, value):
        self.data['vrrp_address'] = value
        
    @property
    def vrrp_id(self):
        """
        The VRRP ID. Required only for VRRP mode.
        
        :param int value: id for VRRP 
        :return: int 
        """
        return self.data.get('vrrp_id')
    
    @vrrp_id.setter
    def vrrp_id(self, value):
        self.data['vrrp_id'] = value
        
    @property
    def vrrp_priority(self):
        """
        The VRRP Priority. Required only for VRRP mode
        
        :param int value: priorty value
        :return: int
        """
        return self.data.get('vrrp_priority')
    
    @vrrp_priority.setter
    def vrrp_priority(self, value):
        self.data['vrrp_priority'] = value
    
    def __getattr__(self, attr):
        return None

    def __repr__(self):
        return '{0}(address={1})'.format(self.__class__.__name__, 
                                         self.address)
        
class SingleNodeInterface(NodeInterface):
    """
    SingleNodeInterface
    This interface is used by single node Layer 3 Firewalls. This type of interface
    can be a management interface as well as a non-management routed interface.
    """
    typeof = 'single_node_interface'
    
    def __init__(self, data):
        NodeInterface.__init__(self, data)
        pass
    
    @classmethod
    def create(cls, interface_id, address, network_value, 
               nodeid=1, **kwargs):
        """
        :param int interface_id: interface id
        :param str address: address of this interface
        :param str network_value: network of this interface in cidr x.x.x.x/24
        :param int nodeid: if a cluster, identifies which node this is for
        :return: dict
        """
        data = {'address': address,
                'auth_request': False,
                'auth_request_source': False,
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
        :return: dict
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
        
    def __call__(self):
        return {self.typeof: self.data}

    @property
    def automatic_default_route(self):
        """
        Flag to know if the dynamic default route will be automatically 
        created for this dynamic interface. 
        
        Used in DHCP interfaces only
        
        :return: boolean
        """
        return self.data.get('automatic_default_route')
    
    @automatic_default_route.setter
    def automatic_default_route(self, value):
        self.data['automatic_default_route'] = value
    
    def __repr__(self):
        if self.vlan_id:
            return '{0}(name={1}, vlan_id={2})'.format(self.__class__.__name__, 
                                                       self.address,
                                                       self.vlan_id)
        else:
            return '{0}(name={1})'.format(self.__class__.__name__, self.address)

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
                nicid = '{}.{}-{}.{}'.format(first, str(vlan_id), last, str(vlan_id))
            else:
                nicid = '{}.{}-{}.{}'.format(first, str(vlan_id), last, str(vlan_id2))
        except ValueError:
            pass
    vals.update(nicid=nicid)
    return inline_intf
