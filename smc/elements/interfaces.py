from copy import deepcopy

class NodeInterface(object):
    """
    Node Interface
    Node dedicated interface (NDI) is used on specific engine types and represents an interface
    used for management (ips and layer 2 engines), or non-traffic type interfaces. For 
    Layer 2 Firewall/IPS these are used as individual interfaces. On clusters, these are
    used to define the node specific address for each node member (wrapped in a cluster
    virtual interface).
    
    :param int interfaceid: interface id
    :param str address: ip address of the interface
    :param str network_value: network/netmask, i.e. x.x.x.x/24
    :param int nodeid: for clusters, used to identify the node number
    """
    name = 'node_interface'
    
    def __init__(self, interface_id=None, address=None, network_value=None,
                 nodeid=1, **kwargs):
        self.address = address
        self.network_value = network_value
        self.nicid = interface_id
        self.auth_request = False
        self.backup_heartbeat = False
        self.nodeid = nodeid
        self.outgoing = False
        self.primary_mgt = False
        self.primary_heartbeat = False
        for key, value in kwargs.items():
            setattr(self, key, value) 
    
    def modify_attribute(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)
    
    def __repr__(self):
        return "%s(%r)" % (self.__class__, 'interface_id={}'.format(\
                                 self.interface_id))
class SingleNodeInterface(object):
    """
    SingleNodeInterface
    This interface is used by single node Layer 3 Firewalls. This type of interface
    can be a management interface as well as a non-management routed interface.
    
    :param int interface_id: interface id
    :param str address: address of this interface
    :param str network_value: network of this interface in cidr x.x.x.x/24
    :param int nodeid: if a cluster, identifies which node this is for
    """
    name = 'single_node_interface'

    def __init__(self, interface_id=None, address=None, network_value=None,
                 nodeid=1, **kwargs):
        self.address = address
        self.auth_request = False
        self.auth_request_source = False
        self.primary_heartbeat = False
        self.backup_heartbeat = False
        self.backup_mgt = False
        self.dynamic = False
        self.network_value = network_value
        self.nicid = interface_id
        self.nodeid = nodeid
        self.outgoing = False
        self.primary_mgt = False
        for key, value in kwargs.items():
            setattr(self, key, value)

    def modify_attribute(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)
    
    def __repr__(self):
        return "%s(%r)" % (self.__class__, 'interface_id={}'.format(\
                                 self.interface_id))
class ClusterVirtualInterface(object):
    """
    ClusterVirtualInterface
    These interfaces (CVI) are used on cluster devices and applied to layer 3
    interfaces. They specify a 'VIP' (or shared IP) to be used for traffic load
    balancing or high availability. Each engine will still also have a 'node' 
    interface for communication to/from the engine itself.
    
    :param str address: address of CVI
    :param str network_value: network for CVI
    :param int nicid: nic id to use for physical interface
    """
    name = 'cluster_virtual_interface'
    
    def __init__(self, interface_id=None, address=None, 
                 network_value=None, **kwargs):
        self.address = address
        self.network_value = network_value
        self.nicid = interface_id
        self.auth_request = False
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def modify_attribute(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)
    
    def __repr__(self):
        return "%s(%r)" % (self.__class__, 'interface_id={}'.format(\
                                 self.interface_id))
class InlineInterface(object):
    """
    InlineInterface
    This interface type is used on layer 2 or IPS related engines. It requires
    that you specify two interfaces to be part of the inline pair. These interfaces
    do not need to be sequential. It is also possible to add VLANs and zones to the
    inline interfaces.
    
    See :py:class:`PhysicalInterface` for methods related to adding VLANs
    
    :param str interface_id: two interfaces, i.e. '1-2', '4-5', '7-10', etc
    :param str logical_ref: logical interface reference
    :param str zone_ref: reference to zone, set on second inline pair
    
    The logical interface reference needs to be unique for inline and capture interfaces
    when they are applied on the same engine.
    """
    name = 'inline_interface'
    
    def __init__(self, interface_id=None, logical_interface_ref=None, 
                 zone_ref=None, **kwargs):
        self.failure_mode = 'normal'
        self.inspect_unspecified_vlans = True
        self.nicid = interface_id
        self.logical_interface_ref = logical_interface_ref
        self.zone_ref = zone_ref
        for key, value in kwargs.items():
            setattr(self, key, value)
            
    def add_vlan(self, vlan_id):
        try:
            first, last = self.nicid.split('-')
            self.nicid = first + '.' + str(vlan_id) + '-' + last + '.' + str(vlan_id)
        except ValueError:
            pass
    
    def modify_attribute(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)
    
    def __repr__(self):
        return "%s(%r)" % (self.__class__, 'interface_id={}'.format(\
                                 self.interface_id))
class CaptureInterface(object):
    """ 
    Capture Interface (SPAN)
    This is a single physical interface type that can be installed on either
    layer 2 or IPS engine roles. It enables the NGFW to capture traffic on
    the wire without actually blocking it (although blocking is possible).
    
    :param int interfaceid: the interface id
    :param str logical_ref: logical interface reference, must be unique from 
    inline intfs
    """
    name = 'capture_interface'
    
    def __init__(self, interface_id=None, logical_interface_ref=None, **kwargs):
        self.inspect_unspecified_vlans = True
        self.logical_interface_ref = logical_interface_ref
        self.nicid = interface_id
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def modify_attribute(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)
    
    def __repr__(self):
        return "%s(%r)" % (self.__class__, 'interface_id={}'.format(\
                                 self.interface_id))
class DHCPInterface(object):
    """
    DHCP Interface
    This interface is typically applied on remote devices that require
    a dynamic IP address. The dynamic index specifies which interface
    index is used for the DHCP interface. This would be important if you had
    multiple DHCP interfaces on a single engine.
    The interface ID identifies which physical interface DHCP will be associated
    with.
    
    .. note:: When the DHCP interface will be the primary mgt interface, you must
    create a secondary physical interface and set auth_request=True. 
    
    :param interface_id: interface to use for DHCP
    :param dynamic_index: DHCP index (when using multiple DHCP interfaces 
    """
    name = 'single_node_interface'
    
    def __init__(self, interface_id=None, dynamic_index=1, nodeid=1,
                 **kwargs):
        self.auth_request = False
        self.outgoing = False
        self.dynamic = True
        self.dynamic_index = dynamic_index
        self.nicid = interface_id
        self.nodeid = nodeid
        self.primary_mgt = False
        self.automatic_default_route = False
        self.reverse_connection = False
        for key, value in kwargs.items():
            setattr(self, key, value)

    def modify_attribute(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)
    
    def __repr__(self):
        return "%s(%r)" % (self.__class__, 'interface_id={}'.format(\
                                 self.interface_id))
            
class VlanInterface(object):
    """ 
    VLAN Interface 
    These interfaces can be applied on all engine types but will be bound to
    being on a physical interface. VLAN's can be applied to layer 3 routed
    interfaces as well as inline interfaces.
    
    :param int interface_id: id of interface to assign VLAN to
    :param int vlan_id: ID of vlan
    :param int virtual_mapping: The interface ID for the virtual engine. Virtual engine
           interface mapping starts numbering at 0 by default, which means you must
           account for interfaces used by master engine
    :param str virtual_resource_name: Name of virtual resource for this VLAN if a VE
    """
    def __init__(self, interface_id=None, vlan_id=None,
                 virtual_mapping=None,
                 virtual_resource_name=None,
                 zone_ref=None, **kwargs):
        self.interface_id = str(interface_id) + '.' + str(vlan_id)
        self.virtual_mapping = virtual_mapping
        self.virtual_resource_name = virtual_resource_name
        self.interfaces = []
        self.zone_ref = zone_ref
        for key, value in kwargs.items():
            setattr(self, key, value)

class TunnelInterface(object):
    def __init__(self, interface_id=None, **kwargs):
        self.interface_id = None
        self.interfaces = []
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def add(self, address, network_value, nicid):
        pass
            
    def __repr__(self):
        return "%s(%r)" % (self.__class__, 'interface_id={}'.format(\
                                 self.interface_id))
        
class PhysicalInterface(object):
    """
    Physical Interfaces on NGFW. This represents the following base configuration for
    the following interface types:
        * Single Node Interface
        * Node Interface
        * Capture Interface
        * Inline Interface
        * Cluster Virtual Interface
        * Virtual Physical Interface (used on Virtual Engines)
        * DHCP Interface
        
    This should be used to add interfaces to an engine after it has been created.
    First get the engine context by loading the engine then get the engine property for 
    physical interface::
        
        engine = Engine('myfw').load()
        engine.physical_interface.add_single_node_interface(.....)
        engine.physical_interface.add(5) #single unconfigured physical interface
        engine.physical_interface.add_node_interface(....)
        engine.physical_interface.add_inline_interface('5-6', ....)
    """
    name = 'physical_interface'
    
    def __init__(self, interface_id=None, **kwargs):
        self.data = {
                'interface_id': interface_id,
                'interfaces': [],
                'vlanInterfaces': [],
                'zone_ref': None }
                     
        for key, value in kwargs.items():
            if key == 'callback':
                self.callback = value
            else:
                self.data.update({key: value})
    
    def add(self, interface_id):
        """ 
        Add single physical interface with interface_id. Use other methods
        to fully add an interface configuration based on engine type
        
        :param int interface_id: interface id
        :return: SMCResult
        """
        self.data.update(interface_id=interface_id)
        return self._make()
          
    def add_single_node_interface(self, interface_id, address, network_value, 
                                  zone_ref=None, is_mgmt=False, **kwargs):
        """
        Adds a single node interface to engine in context
        
        :param int interface_id: interface id
        :param str address: ip address
        :param str network_value: network cidr
        :param str zone_ref: zone reference
        :param boolean is_mgmt: should management be enabled
        :return: SMCResult
        
        See :py:class:`SingleNodeInterface` for more information 
        """
        intf = SingleNodeInterface(interface_id, address, network_value, **kwargs)
        if is_mgmt:
            intf.modify_attribute(auth_request=True, outgoing=True,
                                  primary_mgt=True)
        self.data.update(interface_id=interface_id,
                         interfaces=[{SingleNodeInterface.name: vars(intf)}],
                         zone_ref=zone_ref)
        return self._make()
 
    def add_node_interface(self, interface_id, address, network_value,
                           zone_ref=None, nodeid=1, is_mgmt=False, **kwargs):
        """
        Add a node interface to engine
        
        :param int interface_id: interface identifier
        :param str address: ip address
        :param str network_value: network cidr
        :param str zone_ref: zone reference
        :param int nodeid: node identifier, used for cluster nodes
        :param boolean is_mgmt: enable management
        :return: SMCResult
        
        See :py:class:`NodeInterface` for more information 
        """
        intf = NodeInterface(interface_id, address, network_value, nodeid=nodeid,
                             **kwargs)
        if is_mgmt:
            intf.modify_attribute(primary_mgt=True, outgoing=True)
        self.data.update(interface_id=interface_id, 
                         interfaces=[{NodeInterface.name: vars(intf)}],
                         zone_ref=zone_ref)
        return self._make()
   
    def add_capture_interface(self, interface_id, logical_interface_ref, 
                              zone_ref=None, **kwargs):
        """
        Add a capture interface
        
        :param int interface_id: interface identifier
        :param str logical_interface_ref: logical interface reference
        :param str zone_ref: zone reference
        :return: SMCResult
        
        See :py:class:`CaptureInterface` for more information 
        """
        intf = CaptureInterface(interface_id, logical_interface_ref, **kwargs)
        self.data.update(interface_id=interface_id,
                         interfaces=[{CaptureInterface.name: vars(intf)}],
                         zone_ref=zone_ref)
        return self._make()
        
    def add_inline_interface(self, interface_id, logical_interface_ref, 
                             zone_ref_intf1=None,
                             zone_ref_intf2=None):
        """
        Add an inline interface pair
        
        :param int interface_id: interface identifier
        :param str logical_interface_ref: logical interface reference
        :param zone_ref_intf1: zone for inline interface 1
        :param zone_ref_intf2: zone for inline interface 2
        :return: SMCResult
        
        See :py:class:`InlineInterface` for more information  
        """
        inline_intf = InlineInterface(interface_id, 
                                      logical_interface_ref=logical_interface_ref,
                                      zone_ref=zone_ref_intf2) #second intf zone
        self.data.update(interface_id=interface_id.split('-')[0],
                         interfaces=[{InlineInterface.name: vars(inline_intf)}],
                         zone_ref=zone_ref_intf1)
        return self._make()
    
    def add_dhcp_interface(self, interface_id, dynamic_index, 
                           primary_mgt=False, zone_ref=None, nodeid=1):
        """
        Add a DHCP interface
        
        :param int interface_id: interface id
        :param int dynamic_index: index number for dhcp interface
        :param boolean primary_mgt: whether to make this primary mgt
        :param str zone_ref: zone reference for interface
        :param int nodeid: node identifier
        :return: SMCResult
        
        See :py:class:`DHCPInterface` for more information 
        """ 
        dhcp = DHCPInterface(interface_id,
                             dynamic_index,
                             nodeid=nodeid)
        if primary_mgt:
            dhcp.modify_attribute(primary_mgt=True,
                                  reverse_connection=True,
                                  automatic_default_route=True)
        self.data.update(interface_id=interface_id,
                         interfaces=[{DHCPInterface.name: vars(dhcp)}],
                         zone_ref=zone_ref)
        return self._make()
    
    def add_cluster_virtual_interface(self, interface_id, cluster_virtual, 
                                      cluster_mask, 
                                      macaddress, nodes, 
                                      zone_ref=None, is_mgmt=False):
        """
        Add cluster virtual interface
        
        :param int interface_id: physical interface identifier
        :param int cluster_virtual: CVI address (VIP) for this interface
        :param str cluster_mask: network cidr
        :param str macaddress: required mac address for this CVI
        :param list nodes: list of dictionary items identifying cluster nodes
        :param str zone_ref: if present, is promoted to top level physical interface
        :param boolean is_mgmt: default False, should this be management enabled
        :return: SMCResult
        
        Adding a cluster virtual to an existing engine would look like::
        
            physical.add_cluster_virtual_interface(
                    cluster_virtual='5.5.5.1', 
                    cluster_mask='5.5.5.0/24', 
                    macaddress='02:03:03:03:03:03', 
                    nodes=[{'address':'5.5.5.2', 'network_value':'5.5.5.0/24', 'nodeid':1},
                           {'address':'5.5.5.3', 'network_value':'5.5.5.0/24', 'nodeid':2},
                           {'address':'5.5.5.4', 'network_value':'5.5.5.0/24', 'nodeid':3}],
                    zone_ref=zone_helper('Heartbeat'))
        """
        self.data.setdefault('cvi_mode', 'packetdispatch')
        self.data.setdefault('macaddress', macaddress)
         
        cvi = ClusterVirtualInterface(interface_id, cluster_virtual, cluster_mask)
        if is_mgmt:
            cvi.modify_attribute(auth_request=True)
        
        interfaces=[]
        interfaces.append({ClusterVirtualInterface.name: vars(cvi)})
        
        for node in nodes:
            intf = NodeInterface(interface_id=interface_id, 
                                 address=node.get('address'), 
                                 network_value=node.get('network_value'),
                                 nodeid=node.get('nodeid'))
            if is_mgmt:
                intf.modify_attribute(primary_mgt=True, outgoing=True,
                                      primary_heartbeat=True)
            interfaces.append({NodeInterface.name: vars(intf)})
        self.data.update(interface_id=interface_id,
                         interfaces=interfaces,
                         zone_ref=zone_ref)
        return self._make()
          
    def add_vlan_to_single_node_interface(self, interface_id, address, 
                                          network_value, vlan_id, 
                                          zone_ref=None):
        """
        Add a vlan to single node interface. Will create interface if it 
        doesn't exist
        
        :param int interface_id: interface identifier
        :param str address: ip address
        :param str network_value: network cidr
        :param int vlan_id: vlan identifier 
        :param str zone_ref: zone reference
        :return: SMCResult
        
        See :py:class:`SingleNodeInterface` for more information 
        """
        vlan = VlanInterface(interface_id, vlan_id, zone_ref=zone_ref)
        node = SingleNodeInterface(vlan.interface_id, address, network_value)
        vlan.interfaces.append({SingleNodeInterface.name: vars(node)})
        self.data.update(interface_id=interface_id,
                         vlanInterfaces=[vars(vlan)])
        return self._make()
    
    def add_vlan_to_node_interface(self, interface_id, vlan_id, 
                                   virtual_mapping=None, virtual_resource_name=None,
                                   zone_ref=None):
        """
        Add vlan to existing node interface
        
        :param int interface_id: interface identifier
        :param int vlan_id: vlan identifier
        :param int virtual_mapping: virtual engine mapping id
        :param str virtual_resource_name: name of virtual resource
        :return: SMCResult
        
        See :py:class:`NodeInterface` for more information 
        """
        vlan = VlanInterface(interface_id, vlan_id, 
                             virtual_mapping,
                             virtual_resource_name,
                             zone_ref)
        self.data.update(interface_id=interface_id,
                         vlanInterfaces=[vars(vlan)])
        return self._make()
        
    def add_vlan_to_inline_interface(self, interface_id, vlan_id, 
                                     logical_interface_ref=None,
                                     zone_ref_intf1=None,
                                     zone_ref_intf2=None):
        """
        Add a vlan to inline interface, will create inline if it doesn't exist
        
        :param str interface_id: interfaces for inline pair, '1-2', '5-6'
        :param int vlan_id: vlan identifier
        :param str logical_interface_ref: logical interface reference to use
        :param str zone_ref_intf1: zone for inline interface 1
        :param str zone_ref_intf2: zone for inline interface 2
        :return: SMCResult
        
        See :py:class:`InlineInterface` for more information 
        """     
        first_intf = interface_id.split('-')[0]
        vlan = VlanInterface(first_intf, vlan_id, zone_ref=zone_ref_intf1)
        inline_intf = InlineInterface(interface_id, 
                                      logical_interface_ref,
                                      zone_ref=zone_ref_intf2)
        copied_intf = deepcopy(inline_intf) #copy as ref data will change
        inline_intf.add_vlan(vlan_id)
        #add embedded inline interface to physical interface vlanInterfaces list
        vlan.interfaces.append({InlineInterface.name: vars(inline_intf)})

        self.data.update(interfaces=[{InlineInterface.name: vars(copied_intf)}],
                         vlanInterfaces=[vars(vlan)],
                         interface_id=first_intf)
        return self._make()
    
    def modify_attribute(self, **kwds):
        """ Not fully implemented """
        for k, v in kwds.iteritems():
            if k in self.data:
                print "K is in self.data"
                self.data.update({k:v})
    
    def modify_interface(self, interface_type, **kwds):
        """ Modify interface
        
        :param interface_type: single_node_interface, node_interface, etc
        :param kwargs: dict of key value, i.e. {'backup_heartbeat': True}
        """ 
        intf = self.data.get('interfaces')[0].get(interface_type)
        for k, v in kwds.iteritems():
            if k in intf:
                intf[k] = v

    def describe_interface(self):
        return self.data
            
    def _make(self):
        """
        If callback attribute doesn't exist, this is because an Engine is 
        being created. The callback should be an SMCElement used to 
        reference the http href for submitting the json. For engines being 
        created, the engine json is compiled directly. This should only 
        execute in the try block when the engine is already in context and 
        operator is adding more interfaces by accessing the property 
        :py:class:`smc.elements.engines.Engine.physical_interface`
        """
        try:
            self.callback.json = self.data
            return self.callback.create()
        except AttributeError:
            pass
    
    def __repr__(self):
        return "%s(%r)" % (self.__class__, 'interface_id={}'.format(\
                                 self.data.get('interface_id')))
        
class VirtualPhysicalInterface(PhysicalInterface):
    """ 
    VirtualPhysicalInterface
    This interface type is used by virtual engines and has subtle differences
    to a normal interface. For a VE in layer 3 firewall, it also specifies a 
    Single Node Interface as the physical interface sub-type.
    When creating the VE, one of the interfaces must be designated as the source
    for Auth Requests and Outgoing. 
    
    :param int interface_id: interface id for this virtual interface
    :param list intfdict: dictionary representing interface information
    :param str zone_ref: zone for top level physical interface
    """
    name = 'virtual_physical_interface'
    
    def __init__(self, interface_id=None):
        PhysicalInterface.__init__(self, interface_id)
        pass

import smc.api.common
import smc.actions.search as search

class Interface(object):
    def __init__(self, **kwargs):
        """
        :ivar href: interface href link
        :ivar name: interface name
        :ivar type: interface type
        """
        for k, v in kwargs.iteritems():
            setattr(self, k, v)

    def delete(self):
        return smc.api.common.delete(self.href)
    
    def modify_attribute(self, **kwargs):
        pass
        
    @property
    def physical_interface(self):
        return PhysicalInterface()
    
    @property
    def tunnel_interface(self):
        return TunnelInterface()
    
    #lazy loaded when called
    def describe_interface(self):
        if self.type == 'physical_interface':
            return PhysicalInterface(
                    **search.element_by_href_as_json(self.href))
        elif self.type == 'tunnel_interface':
            return TunnelInterface(
                    **search.element_by_href_as_json(self.href))
            
    def __repr__(self):
        return "%s(%r)" % (self.__class__, 'name={},type={}'.format(\
                                 self.name, self.type))
        