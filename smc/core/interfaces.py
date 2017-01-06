from copy import deepcopy
import smc.actions.search as search
from smc.base.util import find_link_by_name
from smc.base.model import Meta, prepared_request

def NodeInterface(interface_id, address, network_value,
                  nodeid=1, **kwargs):
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
    :return: dict
    """
    intf = {'address': address,
            'network_value': network_value,
            'nicid': interface_id,
            'auth_request': False,
            'backup_heartbeat': False,
            'nodeid': nodeid,
            'outgoing': False,
            'primary_mgt': False,
            'primary_heartbeat': False}
    
    for k, v in kwargs.items():
        intf.update({k: v})
    return {'node_interface': intf}

    
def SingleNodeInterface(interface_id, address, network_value, 
                            nodeid=1, **kwargs):
    """
    SingleNodeInterface
    This interface is used by single node Layer 3 Firewalls. This type of interface
    can be a management interface as well as a non-management routed interface.
    
    :param int interface_id: interface id
    :param str address: address of this interface
    :param str network_value: network of this interface in cidr x.x.x.x/24
    :param int nodeid: if a cluster, identifies which node this is for
    :return: dict
    """
    intf = {'address': address,
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
        intf.update({k: v})
    return {'single_node_interface': intf}


def ClusterVirtualInterface(interface_id, address, 
                            network_value, **kwargs):
    """
    ClusterVirtualInterface
    These interfaces (CVI) are used on cluster devices and applied to layer 3
    interfaces. They specify a 'VIP' (or shared IP) to be used for traffic load
    balancing or high availability. Each engine will still also have a 'node' 
    interface for communication to/from the engine itself.
    
    :param str address: address of CVI
    :param str network_value: network for CVI
    :param int nicid: nic id to use for physical interface
    :return: dict
    """
    intf = {'address': address,
            'network_value':network_value,
            'nicid': interface_id,
            'auth_request': False}
    
    for k, v in kwargs.items():
        intf.update({k: v})
    return {'cluster_virtual_interface': intf}


def InlineInterface(interface_id, logical_interface_ref, 
                    zone_ref=None, **kwargs):
    """
    InlineInterface
    This interface type is used on layer 2 or IPS related engines. It requires
    that you specify two interfaces to be part of the inline pair. These interfaces
    do not need to be sequential. It is also possible to add VLANs and zones to the
    inline interfaces.
    The logical interface reference needs to be unique for inline and capture interfaces
    when they are applied on the same engine.
    
    See :py:class:`PhysicalInterface` for methods related to adding VLANs
    
    :param str interface_id: two interfaces, i.e. '1-2', '4-5', '7-10', etc
    :param str logical_ref: logical interface reference
    :param str zone_ref: reference to zone, set on second inline pair
    :return: dict
    """
    intf = {'failure_mode': 'normal',
            'inspect_unspecified_vlans': True,
            'nicid': interface_id,
            'logical_interface_ref': logical_interface_ref,
            'zone_ref': zone_ref}
    
    for k, v in kwargs.items():
        intf.update({k: v})
    return {'inline_interface': intf}

def add_vlan_to_inline(inline_intf, vlan_id):
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
            nicid = '{}.{}-{}.{}'.format(first, str(vlan_id), last, str(vlan_id))
        except ValueError:
            pass
    vals.update(nicid=nicid)
    return inline_intf


def CaptureInterface(interface_id, logical_interface_ref, **kwargs):
    """ 
    Capture Interface (SPAN)
    This is a single physical interface type that can be installed on either
    layer 2 or IPS engine roles. It enables the NGFW to capture traffic on
    the wire without actually blocking it (although blocking is possible).
    
    :param int interfaceid: the interface id
    :param str logical_ref: logical interface reference, must be unique from 
           inline intfs
    :return: dict
    """
    intf = {'inspect_unspecified_vlans': True,
            'logical_interface_ref': logical_interface_ref,
            'nicid': interface_id}
    
    for k, v in kwargs.items():
        intf.update({k: v})
    return {'capture_interface': intf}


def DHCPInterface(interface_id, dynamic_index=1, nodeid=1,
                  **kwargs):
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
    :param dynamic_index: DHCP index (when using multiple DHCP interfaces)
    :return: dict
    """
    intf = {'auth_request': False,
            'outgoing': False,
            'dynamic': True,
            'dynamic_index': dynamic_index,
            'nicid': interface_id,
            'nodeid': nodeid,
            'primary_mgt': False,
            'automatic_default_route': False,
            'reverse_connection': False}
    
    for k, v in kwargs.items():
        intf.update({k: v})
    return {'single_node_interface': intf}


def VlanInterface(interface_id, vlan_id,
                 virtual_mapping=None,
                 virtual_resource_name=None,
                 zone_ref=None, **kwargs):
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
    :return: dict
    """
    interface_id = '{}.{}'.format(str(interface_id), str(vlan_id))
    intf = {'interface_id': interface_id,
            'virtual_mapping': virtual_mapping,
            'virtual_resource_name': virtual_resource_name,
            'interfaces': [],
            'zone_ref': zone_ref}
    return intf


def commit(method):
    """
    If metadata doesn't exist, this is because an Engine is 
    being created and a direct call to SMC is not required.
    Interface info is stored in data attribute.
    """
    def decorated(self, *args, **kwargs):
        method(self, *args, **kwargs)
        if not self.href:
            return self.data
        else:
            return prepared_request(href=self.href, 
                                    json=self.data).create()
    return decorated  


class Interface(object):
    """
    Top level representation of all interface types
    """
    def __init__(self, meta=None):
        self.meta = meta
    
    def delete(self):
        return prepared_request(href=self.href).delete()
    
    def describe(self):
        """
        Display the interface json information, including sub interfaces
        
        :return: dict of interface json
        """
        return search.element_by_href_as_json(self.href)

    def contact_addresses(self):
        """
        View the contact address/es for this physical interface.
        The displayed output is in json format. Use :meth:`~add_contact_address`
        to add a new contact address to the interface.
        
        :return: dict of contact addresses
        """
        return search.element_by_href_as_json(
                    find_link_by_name('contact_addresses', self.link))
    
    def add_contact_address(self, contact_address, engine_etag):
        """
        Add a contact address to this physical interface
        Contact address is the return of 
        :py:func:`smc.elements.other.prepare_contact_address`.
        
        :param contact_address: :py:func:`smc.elements.other.prepare_contact_address`
        :param engine_etag: etag for engine, required for update
        
        You can obtain the engine_etag after loading the engine and by
        the etag property. 
        If the contact address should be the default contact address, you
        can obtain that using location_helper. Assuming the engine has a 
        location set of 'Internet'::
        
            engine = Engine('testfw').load()
            for interface in engine.interface.all():
                if interface.name == 'Interface 0':
                    contact_address = prepare_contact_address('53.2.4.3', 'Default')
                    interface.add_contact_address(contact_address, engine.etag)
        
        """
        href = find_link_by_name('contact_addresses', self.link)
        existing = search.element_by_href_as_json(href)
        if existing:
            existing.get('contact_addresses').append(
                            contact_address.get('contact_addresses')[0])
        else:
            existing = contact_address

        return prepared_request(href=href, json=existing, 
                                etag=engine_etag).update()

    def modify_interface(self, interface, values):
        """
        Modify sub-interface attributes. 
        
        :param interface: sub-interface dict (SingleNodeInterface, etc)
        :param values: dict to update
        :return: sub-interface dict
        """
        for typeof, val in interface.items():
            print("Modifying interface: %s, %s, with: %s" % (typeof, val, values))
            val.update(values)
        return interface
    
    def all(self):
        return [type(self)(meta=Meta(**intf))
                for intf in search.element_by_href_as_json(self.href)]
    
    @property
    def name(self):
        return self.meta.name if self.meta else None

    @property
    def href(self):
        return self.meta.href if self.meta else None
    
    @property
    def link(self):
        if self.href:
            result = search.element_by_href_as_json(self.href)
            return result.get('link')
        else:
            raise AttributeError('You must access interface information through '
                                 'an engine reference.')
            
    def __repr__(self):
        return '{0}(name={1})'.format(self.__class__.__name__, self.meta.name)
        
    
class TunnelInterface(Interface):
    """
    TunnelInterface
    This interface type represents a tunnel interface that is typically used for
    route based VPN traffic.
    The top level interface type is defined as 'tunnel_interface' but the nested
    nodes under the interfaces attribute will be single_node_interface for single l3,
    cluster_virtual_interface for a tunnel intf with only a CVI or node_interface for 
    a cluster using only NDI's. Tunnel interfaces are only available on layer 3 engines.
    """
    typeof = 'tunnel_interface'
    
    def __init__(self, meta=None, **kwargs):
        Interface.__init__(self, meta)
        self.data = {'interface_id': None,
                     'interfaces': []}

    @commit
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
                         interfaces=[intf],
                         zone_ref=zone_ref)
       
    @commit
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
        cvi = ClusterVirtualInterface(tunnel_id, address, network_value)
        self.data.update(interface_id=tunnel_id,
                         interfaces=[cvi],
                         zone_ref=zone_ref)

    @commit
    def add_cluster_virtual_and_node_interfaces(self, tunnel_id, address, 
                                                network_value, nodes,
                                                zone_ref=None, **kwargs):
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
        cvi = ClusterVirtualInterface(tunnel_id, address, network_value)
        interfaces=[]
        interfaces.append(cvi)
        for node in nodes:
            ndi = NodeInterface(interface_id=tunnel_id, 
                                address=node.get('address'), 
                                network_value=node.get('network_value'),
                                nodeid=node.get('nodeid'))
            interfaces.append(ndi)
        self.data.update(interface_id=tunnel_id,
                         interfaces=interfaces,
                         zone_ref=zone_ref)


class PhysicalInterface(Interface):
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
        ....
        
    When making changes, the etag used should be the top level engine etag.
    """
    typeof = 'physical_interface'
    
    def __init__(self, meta=None, **kwargs):
        Interface.__init__(self, meta)
        self.data = {
                'interface_id': None,
                'interfaces': [],
                'vlanInterfaces': [],
                'zone_ref': None }
                     
        for key, value in kwargs.items():
            self.data.update({key: value})
    
    @commit    
    def add(self, interface_id, virtual_mapping=None, 
            virtual_resource_name=None):
        """ 
        Add single physical interface with interface_id. Use other methods
        to fully add an interface configuration based on engine type
        
        :param int interface_id: interface id
        :param int virtual_mapping: virtual firewall mapping
               See :py:class:`smc.core.engine.VirtualResource.vfw_id`
        :param str virtual_resource_name: virtual resource name
               See :py:class:`smc.core.engine.VirtualResource.name`
        :return: :py:class:`smc.api.web.SMCResult`
        """
        self.data.update(interface_id=interface_id,
                         virtual_mapping=virtual_mapping,
                         virtual_resource_name=virtual_resource_name)
    
    @commit      
    def add_single_node_interface(self, interface_id, address, network_value, 
                                  zone_ref=None, is_mgmt=False, **kwargs):
        """
        Adds a single node interface to engine in context
        
        :param int interface_id: interface id
        :param str address: ip address
        :param str network_value: network cidr
        :param str zone_ref: zone reference
        :param boolean is_mgmt: should management be enabled
        :return: :py:class:`smc.api.web.SMCResult`
        
        See :py:class:`~SingleNodeInterface` for more information
        """
        intf = SingleNodeInterface(interface_id, address, network_value, 
                                   **kwargs)
        if is_mgmt:
            intf = self.modify_interface(intf, {'auth_request': True,
                                                'outgoing': True,
                                                'primary_mgt': True})    
        self.data.update(interface_id=interface_id,
                         interfaces=[intf],
                         zone_ref=zone_ref)
 
    @commit
    def add_node_interface(self, interface_id, address, network_value,
                           zone_ref=None, nodeid=1, is_mgmt=False, 
                           **kwargs):
        """
        Add a node interface to engine
        
        :param int interface_id: interface identifier
        :param str address: ip address
        :param str network_value: network cidr
        :param str zone_ref: zone reference
        :param int nodeid: node identifier, used for cluster nodes
        :param boolean is_mgmt: enable management
        :return: :py:class:`smc.api.web.SMCResult`
        
        See :py:class:`~NodeInterface` for more information 
        """
        ndi = NodeInterface(interface_id, address, network_value, 
                             nodeid=nodeid, **kwargs)
        if is_mgmt:
            ndi = self.modify_interface(ndi, {'outgoing': True,
                                              'primary_mgt': True})
            
        self.data.update(interface_id=interface_id,
                         interfaces=[ndi],
                         zone_ref=zone_ref)

    @commit
    def add_capture_interface(self, interface_id, logical_interface_ref, 
                              zone_ref=None, **kwargs):
        """
        Add a capture interface
        
        :param int interface_id: interface identifier
        :param str logical_interface_ref: logical interface reference
        :param str zone_ref: zone reference
        :return: :py:class:`smc.api.web.SMCResult`
        
        See :py:class:`~CaptureInterface` for more information 
        """
        intf = CaptureInterface(interface_id, logical_interface_ref, 
                                **kwargs)
        self.data.update(interface_id=interface_id,
                         interfaces=[intf],
                         zone_ref=zone_ref)

    @commit    
    def add_inline_interface(self, interface_id, logical_interface_ref, 
                             zone_ref_intf1=None,
                             zone_ref_intf2=None):
        """
        Add an inline interface pair
        
        :param int interface_id: interface identifier
        :param str logical_interface_ref: logical interface reference
        :param zone_ref_intf1: zone for inline interface 1
        :param zone_ref_intf2: zone for inline interface 2
        :return: :py:class:`smc.api.web.SMCResult`
        
        See :py:class:`~InlineInterface` for more information  
        """
        inline_intf = InlineInterface(interface_id, 
                                      logical_interface_ref=logical_interface_ref,
                                      zone_ref=zone_ref_intf2) #second intf zone
        self.data.update(interface_id=interface_id.split('-')[0],
                         interfaces=[inline_intf],
                         zone_ref=zone_ref_intf1)

    @commit
    def add_dhcp_interface(self, interface_id, dynamic_index, 
                           primary_mgt=False, zone_ref=None, nodeid=1):
        """
        Add a DHCP interface
        
        :param int interface_id: interface id
        :param int dynamic_index: index number for dhcp interface
        :param boolean primary_mgt: whether to make this primary mgt
        :param str zone_ref: zone reference for interface
        :param int nodeid: node identifier
        :return: :py:class:`smc.api.web.SMCResult`
        
        See :py:class:`~DHCPInterface` for more information 
        """ 
        dhcp = DHCPInterface(interface_id,
                             dynamic_index,
                             nodeid=nodeid)
        if primary_mgt:
            dhcp = self.modify_interface(dhcp, {'primary_mgt': True,
                                                'reverse_connection': True,
                                                'automatic_default_route': True})

        self.data.update(interface_id=interface_id,
                         interfaces=[dhcp],
                         zone_ref=zone_ref)
  
    @commit
    def add_cluster_virtual_interface(self, interface_id, cluster_virtual, 
                                      cluster_mask, macaddress, nodes, 
                                      cvi_mode='packetdispatch', 
                                      zone_ref=None, is_mgmt=False):
        """
        Add cluster virtual interface
        
        :param int interface_id: physical interface identifier
        :param int cluster_virtual: CVI address (VIP) for this interface
        :param str cluster_mask: network cidr
        :param str macaddress: required mac address for this CVI
        :param list nodes: list of dictionary items identifying cluster nodes
        :param str cvi_mode: packetdispatch is recommended setting
        :param str zone_ref: if present, is promoted to top level physical interface
        :param boolean is_mgmt: default False, should this be management enabled
        :return: :py:class:`smc.api.web.SMCResult`
        
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
        cvi = ClusterVirtualInterface(interface_id, cluster_virtual, cluster_mask)
        if is_mgmt:
            cvi = self.modify_interface(cvi, {'auth_request': True})
        
        interfaces=[]
        interfaces.append(cvi)
        
        for node in nodes:
            ndi = NodeInterface(interface_id=interface_id, 
                                address=node.get('address'), 
                                network_value=node.get('network_value'),
                                nodeid=node.get('nodeid'))
            if is_mgmt:
                ndi = self.modify_interface(ndi, {'primary_mgt': True,
                                                  'outgoing': True,
                                                  'primary_heartbeat': True})
            interfaces.append(ndi)
        self.data.update(cvi_mode=cvi_mode,
                         macaddress=macaddress,
                         interface_id=interface_id,
                         interfaces=interfaces,
                         zone_ref=zone_ref)
    
    @commit
    def add_cluster_interface_on_master_engine(self, interface_id,
                                               macaddress, nodes, 
                                               is_mgmt=False,
                                               zone_ref=None, **kwargs):
        """
        Add a cluster address specific to a master engine. Master engine 
        clusters will not use "CVI" interfaces like normal layer 3 FW clusters, 
        instead each node has a unique address and share a common macaddress.
        
        :param int interface_id: interface id to use
        :param str macaddress: mac address to use on interface
        :param list nodes: interface node list
        :param boolean is_mgmt: is this a management interface
        :param zone_ref: zone to use, if any
        """
        interfaces=[]
        for node in nodes:
            ndi = NodeInterface(interface_id=interface_id, 
                                address=node.get('address'), 
                                network_value=node.get('network_value'),
                                nodeid=node.get('nodeid'))
            if is_mgmt:
                ndi = self.modify_interface(ndi, {'primary_mgt': True,
                                                  'outgoing': True,
                                                  'primary_heartbeat': True})
            interfaces.append(ndi)
        
        self.data.update(interface_id=interface_id,
                         interfaces=interfaces,
                         macaddress=macaddress,
                         zone_ref=zone_ref)

    @commit          
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
        :return: :py:class:`smc.api.web.SMCResult`
        
        See :py:class:`~SingleNodeInterface` for more information 
        """
        vlan = VlanInterface(interface_id, vlan_id, zone_ref=zone_ref)
        sni = SingleNodeInterface(vlan.get('interface_id'), address, network_value)
        vlan.get('interfaces').append(sni)
        self.data.update(interface_id=interface_id,
                         vlanInterfaces=[vlan])
 
    @commit
    def add_vlan_to_node_interface(self, interface_id, vlan_id, 
                                   virtual_mapping=None, virtual_resource_name=None,
                                   zone_ref=None):
        """
        Add vlan to node interface. Creates interface if it doesn't exist.
        
        :param int interface_id: interface identifier
        :param int vlan_id: vlan identifier
        :param int virtual_mapping: virtual engine mapping id
               See :py:class:`smc.core.engine.VirtualResource.vfw_id`
        :param str virtual_resource_name: name of virtual resource
               See :py:class:`smc.core.engine.VirtualResource.name`
        :return: :py:class:`smc.api.web.SMCResult`
        
        See :py:class:`~NodeInterface` for more information 
        """
        vlan = VlanInterface(interface_id, vlan_id, 
                             virtual_mapping,
                             virtual_resource_name,
                             zone_ref)
        self.data.update(interface_id=interface_id,
                         vlanInterfaces=[vlan])
   
    @commit    
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
        :return: :py:class:`smc.api.web.SMCResult`
        
        See :py:class:`~InlineInterface` for more information 
        """
        #TODO: Unique VLAN per inline  
        first_intf = interface_id.split('-')[0]
        vlan = VlanInterface(first_intf, vlan_id, zone_ref=zone_ref_intf1)
        inline_intf = InlineInterface(interface_id, 
                                      logical_interface_ref,
                                      zone_ref=zone_ref_intf2)
        copied_intf = deepcopy(inline_intf)
        vlan.get('interfaces').append(add_vlan_to_inline(inline_intf, vlan_id))
          
        self.data.update(interfaces=[copied_intf],
                         vlanInterfaces=[vlan],
                         interface_id=first_intf)

    
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
    typeof = 'virtual_physical_interface'
    
    def __init__(self, meta=None, **kwargs):
        PhysicalInterface.__init__(self, meta, **kwargs)
        pass

                    
class InterfaceEnum(object):
    def __init__(self, meta):
        self.meta = meta
        
    def all(self):
        """
        Return all interfaces for this engine. This will be an Interface
        object that provides the 3 attributes, href, name and type.
        
        :return: list :py:class:smc.elements.interfaces.Interface`
        """
        interfaces=[]
        intf_map = interface_map()
        for interface in search.element_by_href_as_json(self.meta.href):
            intf_type = interface.get('type')
            if intf_map.get(intf_type):
                interfaces.append(intf_map[intf_type](meta=Meta(**interface)))
            else:
                interfaces.append(type(self)(meta=Meta(**interface)))
        return interfaces


def interface_map():
    """
    Map helper to get interface class by typeof attribute
    """
    import inspect, sys
    intf_map = dict((klazz.typeof, klazz) 
                    for _, klazz in inspect.getmembers(sys.modules[__name__])
                    if inspect.isclass(klazz) and hasattr(klazz, 'typeof'))
    return intf_map
