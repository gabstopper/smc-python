from copy import deepcopy
import smc.actions.search as search
from smc.elements.helpers import find_link_by_name
from smc.elements.element import SMCElement, ContactAddress

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
        for key, value in kwargs.iteritems():
            setattr(self, key, value) 
    
    def modify_attribute(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)
    
    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, 'interface_id={}'\
                           .format(self.interface_id))
        
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
        for key, value in kwargs.iteritems():
            setattr(self, key, value)

    def modify_attribute(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)
    
    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, 'interface_id={}'\
                           .format(self.interface_id))
        
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
        for key, value in kwargs.iteritems():
            setattr(self, key, value)
    
    def modify_attribute(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)
    
    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, 'interface_id={}'\
                           .format(self.interface_id))

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
        for key, value in kwargs.iteritems():
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
        return "%s(%r)" % (self.__class__.__name__, 'interface_id={}'\
                           .format(self.interface_id))

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
        for key, value in kwargs.iteritems():
            setattr(self, key, value)
    
    def modify_attribute(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)
    
    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, 'interface_id={}'\
                           .format(self.interface_id))

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
        for key, value in kwargs.iteritems():
            setattr(self, key, value)

    def modify_attribute(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)
    
    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, 'interface_id={}'\
                           .format(self.interface_id))
            
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
        for key, value in kwargs.iteritems():
            setattr(self, key, value)

class TunnelInterface(object):
    """
    TunnelInterface
    This interface type represents a tunnel interface that is typically used for
    route based VPN traffic.
    The top level interface type is defined as 'tunnel_interface' but the nested
    nodes under the interfaces attribute will be single_node_interface for single l3,
    cluster_virtual_interface for a tunnel intf with only a CVI or node_interface for 
    a cluster using only NDI's. Tunnel interfaces are only available on layer 3 engines.
    """
    name = 'tunnel_interface'
    
    def __init__(self, interface_id=None, href=None, name=None,
                 **kwargs):
        self.interface_id = interface_id
        self.href = href
        self.name = name
        self.data = {'interface_id': interface_id,
                     'interfaces': []}
        for key, value in kwargs.iteritems():
            self.data.update({key: value})
    
    def add_single_node_interface(self, tunnel_id, address, network_value, 
                                  nodeid=1,
                                  zone_ref=None, **kwargs):
        """
        Creates a tunnel interface with sub-type single_node_interface. This is
        to be used for single layer 3 firewall instances.
        
        :param int tunnel_id: the tunnel id for the interface, used as nicid also
        :param str address: ip address of interface
        :param str network_value: network cidr for interface
        :param int nodeid: nodeid, used only for clusters
        :param str zone_ref: zone reference for interface
        """
        intf = SingleNodeInterface(tunnel_id, address, network_value, **kwargs)
        self.data.update(interface_id=tunnel_id,
                         interfaces=[{SingleNodeInterface.name: vars(intf)}],
                         zone_ref=zone_ref)
    
    def add_cluster_virtual_interface(self, tunnel_id, address, network_value,
                                      zone_ref=None, **kwargs):
        """
        Add tunnel interface as a CVI only interface for clustered engines. 
        This provides a single CVI interface for defining the tunnel interface. This 
        may be useful to ensure failover is available for active/standby engines and load 
        balancing for active/active. If not using NDI's on a tunnel, the default IP for 
        outgoing traffic will be used for protocols like IGMP Proxy and dynamic routing.
        
        :param int tunnel_id: id for this tunnel interface
        :param str address: ip address for tunnel cvi
        :param str network_value: network cidr for address
        :param str zone_ref: zone reference for interface (optional)
        """
        intf = ClusterVirtualInterface(tunnel_id, address, network_value)
        self.data.update(interface_id=tunnel_id,
                         interfaces=[{ClusterVirtualInterface.name: vars(intf)}],
                         zone_ref=zone_ref)
    
    def add_cluster_virtual_and_node_interfaces(self, tunnel_id, address, 
                                                          network_value, nodes,
                                                          zone_ref=None,
                                                          **kwargs):
        """
        Add a CVI and Node Dedicated Interfaces to Tunnel Interface. 
        
        Building a tunnel interface with CVI and NDI::
        
            engine.tunnel_interface.add_cluster_virtual_and_node_interfaces(
                    tunnel_id=1055, 
                    address='77.77.77.77', 
                    network_value='77.77.77.0/24', 
                    nodes=[{'address':'77.77.77.78', 'network_value':'77.77.77.0/24', 'nodeid':1},
                           {'address':'77.77.77.79', 'network_value': '77.77.77.0/24', 'nodeid':2}])
        
        :param int tunnel_id: id for this tunnel interface
        :param str address: ip address for tunnel cvi
        :param str network_value: network cidr for address
        :param list nodes: dict of nodes {address, network_value, nodeid}
        :param str zone_ref: zone reference for interface (optional) 
        """
        intf = ClusterVirtualInterface(tunnel_id, address, network_value)
        interfaces=[]
        interfaces.append({ClusterVirtualInterface.name: vars(intf)})
        for node in nodes:
            intf = NodeInterface(interface_id=tunnel_id, 
                                 address=node.get('address'), 
                                 network_value=node.get('network_value'),
                                 nodeid=node.get('nodeid'))
            interfaces.append({NodeInterface.name: vars(intf)})
        self.data.update(interface_id=tunnel_id,
                         interfaces=interfaces,
                         zone_ref=zone_ref)
    
    def load(self):
        """
        Get latest json, mostly used by internal methods
        """
        result = search.element_by_href_as_smcresult(self.href)
        self.etag = result.etag
        self.data.update(**result.json)
    
    def all(self):
        """
        Return all meta information for physical interfaces on this engine.
        This provides a simple mechanism to obtain the correct interface in case
        a modification is required::
        
            for x in engine.tunnel_interface.all():
                if x.name.endswith('2000'):
                    print x.describe()
        """
        interfaces=[]
        for intf in search.element_by_href_as_json(self.href):
            interfaces.append(TunnelInterface(name=intf.get('name'),
                                              href=intf.get('href')))
        return interfaces

    def describe(self):
        """
        Describe the physical interface json
        
            for intf in engine.physical_interface.all():
                if intf.name.startswith('Interface 0'):
                    pprint(intf.describe())
        """
        self.load()
        return self.data
            
    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, 'name={}'\
                           .format(self.name))

def load_decorator(method):
    print "Called with: %s" % method     
    def inner(instance): 
        print "inner with: %s" % instance
        if not instance.data.get('link'):
            print "Load data"
            result = search.element_by_href_as_smcresult(instance.href)
            print result
            instance.etag = result.etag
            instance.data.update(**result.json)
        else: 
            method(instance) 
        return inner
        
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
    
    def __init__(self, interface_id=None, href=None, name=None,
                 **kwargs):
        self.interface_id = interface_id
        self.href = href
        self.name = name
        self.data = {
                'interface_id': interface_id,
                'interfaces': [],
                'vlanInterfaces': [],
                'zone_ref': None }
                     
        for key, value in kwargs.iteritems():
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
    
    def add_contact_address(self, address, location, engine_etag):
        """
        Add a contact address to this physical interface
        
        :param address: ip address of contact address
        :param locatino: location ref for contact address
        :param engine_etag: etag for engine, required for update
        
        You can obtain the engine_etag after loading the engine and by
        the etag property. 
        If the contact address should be the default contact address, you
        can obtain that using location_helper('Default')::
        
            for interface in self.engine.interface.all():
                if interface.name == 'Interface 0':
                    location = location_helper('Default')
                    interface.add_contact_address(elastic_ip, location, self.engine.etag)
        """
        self.load()
        href = find_link_by_name('contact_addresses', self.data.get('link'))
        existing = search.element_by_href_as_json(href)        
        if existing:
            existing.get('contact_addresses').append({'address': address,
                                                      'dynamic': False, 
                                                      'location': location})
        else:
            existing = {'contact_addresses': [{'address': address,
                                               'dynamic': False, 
                                               'location': location}]}
        return SMCElement(href=href, json=existing, 
                          etag=engine_etag).update()
    
    @property
    def contact_addresses(self):
        if not self.data.get('link'):
            self.load()
        return search.element_by_href_as_json(
                    find_link_by_name('contact_addresses', 
                                      self.data.get('link')))
        
    def load(self):
        """
        Get latest json, mostly used by internal methods
        """
        result = search.element_by_href_as_smcresult(self.href)
        self.etag = result.etag
        self.data.update(**result.json)
        
    def modify_attribute(self, **kwargs):
        """ 
        Modify interface attributes
        Currently only modifies the nested sub-interfaces, i.e. single_node_interface,
        node_interface, etc.
        """
        for interface in self.data.get('interfaces'):
            for _k, v in interface.iteritems():
                v.update(kwargs)

    def all(self):
        """
        Return all meta information for physical interfaces on this engine.
        This provides a simple mechanism to obtain the correct interface in case
        a modification is required::
        
            for interface in engine.physical_interface.all():
                if interface.name.startswith('Interface 0'):
                    print interface.describe()
        """
        interfaces=[]
        for intf in search.element_by_href_as_json(self.href):
            interfaces.append(PhysicalInterface(name=intf.get('name'),
                                                href=intf.get('href')))
        return interfaces

    def describe(self):
        """
        Describe the physical interface json
        
            for intf in engine.physical_interface.all():
                if intf.name.startswith('Interface 0'):
                    pprint(intf.describe())
        """
        self.load()
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
        if self.href:
            #called from within engine context
            return SMCElement(href=self.href, json=self.data).create()
        #else don't add, just build json
    
    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, 'name={}'\
                           .format(self.name))
        
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
    
    def __init__(self, interface_id=None, **kwargs):
        PhysicalInterface.__init__(self, interface_id, **kwargs)
        pass

class Interface(object):
    def __init__(self, **kwargs):
        """
        Interface is a container class used to display all interfaces for
        an engine, along with their types. This is convenient to enumerate
        all interfaces by type as an engine could have multiple interface
        types, i.e. physical, and tunnel, inline and capture, etc. and you
        may not know exactly which ones. :py:function:`all` will return the
        interface by class, or a generic interface object is interface is not 
        yet implemented.
        
        :ivar href: interface href link
        :ivar name: interface name
        :ivar type: interface type
        """
        for k, v in kwargs.iteritems():
            setattr(self, k, v)

    def delete(self):
        import smc.api.common
        return smc.api.common.delete(self.href)
    
    def all(self):
        """
        Return all interfaces for this engine. This will be an Interface
        object that provides the 3 attributes, href, name and type.
        
        :return: list :py:class:smc.elements.interfaces.Interface`
        """
        interfaces=[]
        for interface in search.element_by_href_as_json(self.href):
            intf_type = interface.get('type')
            if intf_type == PhysicalInterface.name:
                interfaces.append(PhysicalInterface(name=interface.get('name'),
                                                    href=interface.get('href')))
            elif intf_type == VirtualPhysicalInterface.name:
                interfaces.append(VirtualPhysicalInterface(name=interface.get('name'),
                                                           href=interface.get('href')))
            elif intf_type == TunnelInterface.name:
                interfaces.append(TunnelInterface(name=interface.get('name'),
                                                  href=interface.get('href')))
            else:
                interfaces.append(Interface(**interface))
        return interfaces
           
    def __repr__(self):
        try:
            return "%s(%r)" % (self.__class__.__name__, 'name={},type={}'\
                               .format(self.name, self.type))
        except AttributeError:
            return "%s" % self.__class__.__name__