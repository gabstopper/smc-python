"""
Interface module encapsulates interface types for security engines.
All interface have a 'top level' such as Physical or Tunnel Interface. 
These top level interfaces have certain common settings that can be 
modified such as assigning a zone.

IP addresses, netmask, management settings, VLANs, etc are part of an 
interfaces 'sub' interface. Sub interfaces can be retrieved from an engine
reference and call to :func:`~smc.core.interfaces.Interface.sub_interfaces`

The interface hierarchy resembles:

::

    Physical/Tunnel Interface
            |
        Sub Interface (SingleNodeInterface, NodeInterface, InlineInterface, etc)
            |
        Attributes (address, network_value, vlan_id, etc)

Sub interfaces are documented in :py:mod:`smc.core.sub_interfaces`.

VLANs are properties of specific interfaces and can also be retrieved by 
first getting the top level interface, and calling :func:`~smc.core.interfaces.Interface.vlan_interfaces` 
to view or modify specific aspects of a VLAN, such as addresses, etc.
"""
from copy import deepcopy
from functools import wraps
import smc.actions.search as search
from smc.base.util import find_link_by_name
from smc.base.model import Meta, prepared_request, Cache
import smc.core.sub_interfaces
from smc.api.exceptions import EngineCommandFailed
from smc.elements.other import ContactAddress
from smc.core.sub_interfaces import (NodeInterface, SingleNodeInterface, 
                                     ClusterVirtualInterface, InlineInterface,
                                     CaptureInterface, _add_vlan_to_inline)

def create(method):
    """
    If metadata doesn't exist, this is because an Engine is 
    being created and a direct call to SMC is not required.
    Interface info is stored in data attribute.
    """
    @wraps(method)
    def decorated(self, *args, **kwargs):
        method(self, *args, **kwargs)
        if not self.href: #has no location
            return self._data
        else:
            if hasattr(self, '_update'): #exit decorator
                return
            result = prepared_request(href=self.href, 
                                      json=self._data).create()
            if result.msg:
                raise EngineCommandFailed(result.msg)

    return decorated  

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
    
class InterfaceCommon(object):
    @property
    def aggregate_mode(self):
        """
        LAGG configuration for this physical interface.
        Options are HA (failover) or LB (load balancing)
        
        :param str value: 'lb' or 'ha'
        :rtype: str
        """
        return self.data.get('aggregate_mode')
        
    @aggregate_mode.setter
    def aggregate_mode(self, value):
        self.data['aggregate_mode'] = value
    
    @property
    def comment(self):
        """
        Optional comment
        
        :param str value: comment
        :return: str
        """
        return self.data.get('comment')
    
    @comment.setter
    def comment(self, value):
        self.data['comment'] = value
    
    @property
    def interface_id(self):
        """
        The Interface ID automatically maps to a physical network port
        of the same number during the initial configuration of the engine, 
        but the mapping can be changed as necessary.
        
        :param str value: interface_id
        :rtype: str
        """
        return self.data.get('interface_id')
    
    @interface_id.setter
    def interface_id(self, value):
        self.data['interface_id'] = value
    
    @property
    def mtu(self):
        """
        Set MTU on interface. Enter a value between 400-65535. 
        The same MTU is automatically applied to any VLANs 
        created under this physical interface
        
        :param int value: MTU
        :rtype: int
        """
        return self.data.get('mtu')
    
    @mtu.setter
    def mtu(self, value):
        self.data['mtu'] = value
    
    @property
    def second_interface_id(self):
        """
        The second interface in a LAGG configuration
        
        :param str value: interface_id of LAGG interface
        :rtype: str
        """
        return self.data.get('second_interface_id')
    
    @second_interface_id.setter
    def second_interface_id(self, value):
        self.data['second_interface_id'] = value

    @property
    def virtual_mapping(self):
        """
        The virtual mapping id. Required if Virtual Resource chosen.
        See :py:class:`smc.core.engine.VirtualResource.vfw_id`
        
        :param int value: vfw_id
        :rtype: int
        """
        if self.data.get('virtual_mapping'):
            return int(self.data.get('virtual_mapping'))
    
    @virtual_mapping.setter
    def virtual_mapping(self, value):
        self.data['virtual_mapping'] = value
    
    @property
    def virtual_resource_name(self):
        """
        Virtual Resource name used on Master Engine to map a virtual engine.
        See :py:class:`smc.core.engine.VirtualResource.name`
        
        :param str value: virtual resource name
        :rtype: str
        """
        return self.data.get('virtual_resource_name')
    
    @virtual_resource_name.setter
    def virtual_resource_name(self, value):
        self.data['virtual_resource_name'] = value
    
    @property
    def zone_ref(self):
        """
        Zone for this physical interface. 
        
        :param str value: href of zone, set to None to remove existing zone
        :rtype: str
        """
        return self.data.get('zone_ref')
    
    @zone_ref.setter
    def zone_ref(self, value):
        if value is None:
            self.data.pop('zone_ref', None)
        else:
            self.data['zone_ref'] = value
    
class Interface(object):
    """
    Top level representation of all base interface types. Base interface types
    are: Physical, VirtualPhysical and Tunnel Interface. All other interface
    types are considered sub-interfaces and will be used depending on the type
    of engine. For example, an Inline Interface is a Physical Interface, but can
    only be used on Layer 2 Firewall or IPS Engines. 
    
    Note that when modifying existing interface information changes can only be
    made to a single interface at once. Some changes like switching management
    interfaces is currently not supported.
    """
    def __init__(self, meta=None, **kwargs):
        self.meta = meta
        self._cache = Cache(self)
        self._engine = kwargs.get('engine') #Engine reference
   
    @property
    def data(self):
        if self.meta:
            return self._cache()[1]
        else:
            return self._data
    
    @property
    def etag(self):
        return self._cache()[0]
    
    def delete(self):
        """
        Delete this interface
        
        :raises: :py:class:`smc.api.exceptions.EngineCommandFailed`
        :return: None
        """
        result = prepared_request(href=self.href).delete()
        if result.msg:
            raise EngineCommandFailed(result.msg)
    
    def describe(self):
        """
        Display the interface json information, including sub interfaces
        
        :return: dict of interface json
        """
        return self.data

    def contact_addresses(self):
        """
        View the contact address/es for this physical interface.
        Use :meth:`~add_contact_address` to add a new contact 
        address to the interface.
        
        :return: list :py:class:`smc.elements.other.ContactAddress`
        """
        result = search.element_by_href_as_json(
                    find_link_by_name('contact_addresses', self.link))
        if result:
            return [ContactAddress(addr) for addr in result.get('contact_addresses')]
        else:
            return []
    
    def add_contact_address(self, contact_address, *args):
        """
        Add a contact address to this physical interface.
        
        Adding contact address to interface 0::
        
            engine = Engine('testfw')
            for interface in engine.interface.all():
                if interface.name == 'Interface 0':
                    addr = ContactAddress.create('13.13.13.13', location='MyLocation')
                    interface.add_contact_address(addr)
        
        :param contact_address: :py:class:`smc.elements.other.ContactAddress`
        :return: None
        :raises: :py:class:`smc.api.exceptions.EngineCommandFailed`
        """
        href = find_link_by_name('contact_addresses', self.link)
        existing = search.element_by_href_as_json(href)
        if existing:
            existing.get('contact_addresses').append(contact_address['contact_addresses'][0])
        else:
            existing = contact_address

        result = prepared_request(href=href, json=existing, 
                                  etag=self._engine.etag).update()
        if result.msg:
            raise EngineCommandFailed(result.msg)
 
    @property
    def name(self):
        """
        Name of this interface
        """
        return self.meta.name if self.meta else None

    @property
    def href(self):
        return self.meta.href if self.meta else None

    def get(self, interface_id):
        """
        Get the interface by id, if known. The interface is 
        retrieved from the top level Physical or Tunnel Interface.
        If interface type is unknown, use engine.interface
        for retrieving::
        
            engine = Engine('testfw')
            p = engine.physical_interface.get(0)
            print(p.name, p.typeof, p.address, p.network_value)
            .....
        
        :return: interface object by type (Physical, Tunnel, PhysicalVlanInterface)
        :raises: :py:class:`smc.api.exceptions.EngineCommandFailed` if interface not found
        """
        interface_id = str(interface_id)
        for interface in search.element_by_href_as_json(self.meta.href):
            intf_type = interface.get('type') #Keep type
            intf = _InterfaceFactory(intf_type)(meta=Meta(**interface),
                                                engine=self._engine)

            if intf.data.get('interface_id') == interface_id:
                return intf
        raise EngineCommandFailed('Interface id {} not found'.format(interface_id))
     
    @property
    def link(self):
        return self.data.get('link')        
    
    @property
    def has_vlan(self):
        """
        Whether this interface has VLAN interfaces
        
        :return: boolean True if vlan interfaces exist
        """
        return bool(self.data.get('vlanInterfaces'))

    def save(self):
        """
        Save this interface information back to SMC. When saving
        the interface, call save on the topmost level of the interface.
        
        Example of changing the IP address of an interface::
        
            engine = Engine('testfw')
            for intf in engine.interface.all():
                if intf.name == 'Interface 0':
                    for subif in intf.sub_interfaces():
                        if subif.address == '172.18.1.80':
                            subif.address = '172.18.1.100'
                    intf.save()

        :return: :py:class:`smc.api.web.SMCResult`
        """
        self._cache(force_refresh=True)
        return prepared_request(href=self.href, json=self.data,
                                etag=self.etag).update()

    def vlan_interfaces(self):
        """
        Access VLAN interfaces for this interface. 
        
        Retrieve interface and view vlan interfaces::
        
            engine = Engine('testfw')
            for intf in engine.interface.all():
                if intf.has_vlan:
                    print(intf.vlan_interfaces()) #Show VLANs
        
        :return: list :py:class:`smc.core.interfaces.PhysicalVlanInterface`
        """
        if self.has_vlan:
            return [PhysicalVlanInterface(vlan)
                    for vlan in self.data.get('vlanInterfaces')]
        return []
        
    def sub_interfaces(self):
        """
        Access sub interfaces with sub-interface information. Single 
        engines will typically only have 1 sub-interface, however interfaces 
        with VLANs, clusters, or multiple IP's assigned will have multiple.
        It is not required to use this method to access interface attributes.
        However, it is required to make modifications to the right interface.
        
        Retrieve interface and type, with address and network::
        
            engine = Engine('testfw')
            for intf in engine.interface.all():
                for x in intf.sub_interfaces():
                    print(x) #Show sub interfaces by type
                    if x.address == '1.1.1.1':
                        x.address = '1.1.1.5'    #Change the IP address
                intf.save() #Save to top level interface 
        
        :return: list :py:mod:`smc.core.sub_interfaces` by type
        """    
        results = []
        
        data = self.data
        def inner(data):
            if data.get('interfaces'):
                # It's an interface definition
                for intf in data['interfaces']:
                    for if_type, values in intf.items():
                        results.append(_InterfaceFactory(if_type)(values))
            elif data.get('vlanInterfaces'):
                for vlan in data.get('vlanInterfaces'):
                    inner(vlan)
            else:
                if self.typeof == TunnelInterface.typeof:
                    pass
                else: #PhysicalInterface
                    if '.' in data.get('interface_id'):
                        results.append(PhysicalVlanInterface(data))
        
        inner(data)
        return results
     
    def all(self):
        """
        Return all interfaces for this engine. This is a common entry
        point to viewing interface information.
        
        Retrieve specific information about an interface::
        
            engine = Engine('myengine')
            for x in engine.physical_interface.all():
                print(x.name, x.address, x.network_value)
            
        :return: list :py:class:`smc.elements.interfaces.Interface`
        """
        interfaces=[]
        
        for interface in search.element_by_href_as_json(self.meta.href):
            intf_type = interface.get('type')
            intf = _InterfaceFactory(intf_type)
            if intf:
                interfaces.append(intf(meta=Meta(**interface),
                                       engine=self._engine))
            else:
                interfaces.append(Interface(meta=Meta(**interface),
                                            engine=self._engine))
        return interfaces
                    
    def __iter__(self):
        if self.data.get('interfaces'):
            for intf in self.data['interfaces']:
                for if_type, values in intf.items():
                    yield _InterfaceFactory(if_type)(values)
        if self.data.get('vlanInterfaces'):
            for intf in self.data['vlanInterfaces']:
                yield PhysicalVlanInterface(intf)
        
    def __getattr__(self, name):
        return [getattr(intfs, name) for intfs in iter(self)]
        
    def __str__(self):
        return '{0}(name={1})'.format(self.__class__.__name__, self.name)
    
    def __repr__(self):
        return str(self)

   
class TunnelInterface(InterfaceCommon, Interface):
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
        Interface.__init__(self, meta, **kwargs)
        self._data = {'interface_id': None,
                      'interfaces': []}

    @create
    def add_single_node_interface(self, tunnel_id, address, network_value, 
                                  nodeid=1, zone_ref=None, **kwargs):
        """
        Creates a tunnel interface with sub-type single_node_interface. This is
        to be used for single layer 3 firewall instances.
        
        :param int tunnel_id: the tunnel id for the interface, used as nicid also
        :param str address: ip address of interface
        :param str network_value: network cidr for interface
        :param int nodeid: nodeid, used only for clusters
        :param str zone_ref: zone reference for interface
        :return: None
        :raises: :py:class:`smc.api.exceptions.EngineCommandFailed`
        """
        intf = SingleNodeInterface.create(tunnel_id, address, network_value, 
                                          **kwargs)

        if self.href: #From an engine reference
            try:
                intf_ref = self.get(tunnel_id) #Does interface already exist?
                self._data.update(intf_ref.data)
                self._data['interfaces'].append(intf())
                self._update = True
                return prepared_request(href=intf_ref.href, json=self._data,
                                        etag=intf_ref.etag).update()
            except EngineCommandFailed:
                pass
       
        self._data.update(interface_id=tunnel_id,
                          interfaces=[intf()],
                          zone_ref=zone_ref)

    @create
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
        :return: None
        :raises: :py:class:`smc.api.exceptions.EngineCommandFailed`
        """
        cvi = ClusterVirtualInterface.create(tunnel_id, address, network_value)
        self._data.update(interface_id=tunnel_id,
                          interfaces=[cvi()],
                          zone_ref=zone_ref)

    @create
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
        :return: None
        :raises: :py:class:`smc.api.exceptions.EngineCommandFailed`
        """
        cvi = ClusterVirtualInterface.create(tunnel_id, address, network_value)
        interfaces=[]
        interfaces.append(cvi())
        for node in nodes:
            ndi = NodeInterface.create(interface_id=tunnel_id, 
                                       address=node.get('address'), 
                                       network_value=node.get('network_value'),
                                       nodeid=node.get('nodeid'))
            interfaces.append(ndi())
        self._data.update(interface_id=tunnel_id,
                          interfaces=interfaces,
                          zone_ref=zone_ref)


class PhysicalInterface(InterfaceCommon, Interface):
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

        engine = Engine('myfw')
        engine.physical_interface.add_single_node_interface(.....)
        engine.physical_interface.add(5) #single unconfigured physical interface
        engine.physical_interface.add_node_interface(....)
        engine.physical_interface.add_inline_interface('5-6', ....)
        ....
        
    When making changes, the etag used should be the top level engine etag.
    """
    typeof = 'physical_interface'
    
    def __init__(self, meta=None, **kwargs):
        Interface.__init__(self, meta, **kwargs)
        self._data = {'interface_id': None,
                      'interfaces': [],
                      'vlanInterfaces': [],
                      'zone_ref': None}
    
    @create    
    def add(self, interface_id, virtual_mapping=None, 
            virtual_resource_name=None):
        """ 
        Add single physical interface with interface_id. Use other methods
        to fully add an interface configuration based on engine type.
        Virtual mapping and resource are only used in Virtual Engines.
        
        :param int interface_id: interface id
        :param int virtual_mapping: virtual firewall mapping
               See :py:class:`smc.core.engine.VirtualResource.vfw_id`
        :param str virtual_resource_name: virtual resource name
               See :py:class:`smc.core.engine.VirtualResource.name`
        :return: None
        :raises: :py:class:`smc.api.exceptions.EngineCommandFailed`
        """
        self._data.update(interface_id=interface_id,
                          virtual_mapping=virtual_mapping,
                          virtual_resource_name=virtual_resource_name)
    
    @create      
    def add_single_node_interface(self, interface_id, address, network_value, 
                                  zone_ref=None, is_mgmt=False, **kwargs):
        """
        Adds a single node interface to engine in context.
        Address can be either IPv4 or IPv6.
        
        :param int interface_id: interface id
        :param str address: ip address
        :param str network_value: network cidr
        :param str zone_ref: zone reference
        :param boolean is_mgmt: should management be enabled
        :return: None
        :raises: :py:class:`smc.api.exceptions.EngineCommandFailed`
        
        See :py:class:`smc.core.sub_interfaces.SingleNodeInterface` for more information
        """
        intf = SingleNodeInterface.create(interface_id, address, network_value, 
                                          **kwargs)
        if is_mgmt:
            intf.auth_request = True
            intf.outgoing = True
            intf.primary_mgt = True
        
        if self.href: #From an engine reference
            try:
                intf_ref = self.get(interface_id) #Does interface already exist?
                self._data.update(intf_ref.data)
                self._data['interfaces'].append(intf())
                self._update = True
                return prepared_request(href=intf_ref.href, json=self._data,
                                        etag=intf_ref.etag).update()
            except EngineCommandFailed:
                pass

        self._data.update(interface_id=interface_id,
                          interfaces=[intf()],
                          zone_ref=zone_ref)

    @create
    def add_node_interface(self, interface_id, address, network_value,
                           zone_ref=None, nodeid=1, is_mgmt=False, 
                           **kwargs):
        """
        Add a node interface to engine. Node interfaces are used on
        all engine types except single fw engines. For inline and IPS
        engines, this interface type represents a layer 3 routed interface.
        
        :param int interface_id: interface identifier
        :param str address: ip address
        :param str network_value: network cidr
        :param str zone_ref: zone reference
        :param int nodeid: node identifier, used for cluster nodes
        :param boolean is_mgmt: enable management
        :return: None
        :raises: :py:class:`smc.api.exceptions.EngineCommandFailed`
        
        See :py:class:`smc.core.sub_interfaces.NodeInterface` for more information 
        """
        intf = NodeInterface.create(interface_id, address, network_value, 
                                    nodeid=nodeid, **kwargs)
        if is_mgmt:
            intf.outgoing = True
            intf.primary_mgt = True
        
        if self.href:
            try:
                intf_ref = self.get(interface_id) #Does interface already exist?
                self._data.update(intf_ref.data)
                self._data['interfaces'].append(intf())
                self._update = True
                return prepared_request(href=intf_ref.href, json=self._data,
                                        etag=intf_ref.etag).update()
            except EngineCommandFailed:
                pass

        self._data.update(interface_id=interface_id,
                          interfaces=[intf()],
                          zone_ref=zone_ref)

    @create
    def add_capture_interface(self, interface_id, logical_interface_ref, 
                              zone_ref=None, **kwargs):
        """
        Add a capture interface. Supported only on Layer 2 and IPS engines.
        
        :param int interface_id: interface identifier
        :param str logical_interface_ref: logical interface reference
        :param str zone_ref: zone reference
        :return: None
        :raises: :py:class:`smc.api.exceptions.EngineCommandFailed`
        
        See :py:class:`smc.core.sub_interfaces.CaptureInterface` for more information 
        """
        intf = CaptureInterface.create(interface_id, logical_interface_ref, 
                                       **kwargs)
        self._data.update(interface_id=interface_id,
                          interfaces=[intf()],
                          zone_ref=zone_ref)

    @create    
    def add_inline_interface(self, interface_id, logical_interface_ref, 
                             zone_ref_intf1=None,
                             zone_ref_intf2=None):
        """
        Add an inline interface pair
        
        :param str interface_id: interface id; '1-2', '3-4', etc
        :param str logical_interface_ref: logical interface reference
        :param zone_ref_intf1: zone for inline interface 1
        :param zone_ref_intf2: zone for inline interface 2
        :return: None
        :raises: :py:class:`smc.api.exceptions.EngineCommandFailed`
        
        See :py:class:`smc.core.sub_interfaces.InlineInterface` for more information  
        """
        inline_intf = InlineInterface.create(
                                    interface_id, 
                                    logical_interface_ref=logical_interface_ref,
                                    zone_ref=zone_ref_intf2) #second intf zone
        self._data.update(interface_id=interface_id.split('-')[0],
                          interfaces=[inline_intf()],
                          zone_ref=zone_ref_intf1)

    @create
    def add_dhcp_interface(self, interface_id, dynamic_index, 
                           primary_mgmt=False, zone_ref=None, nodeid=1):
        """
        Add a DHCP interface
        
        :param int interface_id: interface id
        :param int dynamic_index: index number for dhcp interface
        :param boolean primary_mgt: whether to make this primary mgt
        :param str zone_ref: zone reference for interface
        :param int nodeid: node identifier
        :return: None
        :raises: :py:class:`smc.api.exceptions.EngineCommandFailed`
        
        See :py:class:`~DHCPInterface` for more information 
        """ 
        intf = SingleNodeInterface.create_dhcp(interface_id,
                                               dynamic_index,
                                               nodeid=nodeid)
        if primary_mgmt:
            intf.primary_mgt = True
            intf.reverse_connection = True
            intf.automatic_default_route = True
            
        self._data.update(interface_id=interface_id,
                          interfaces=[intf()],
                          zone_ref=zone_ref)
  
    @create
    def add_cluster_virtual_interface(self, interface_id, cluster_virtual, 
                                      cluster_mask, macaddress, nodes, 
                                      cvi_mode='packetdispatch', 
                                      zone_ref=None, is_mgmt=False):
        """
        Add cluster virtual interface. A "CVI" interface is used as a VIP
        address for clustered engines.
        
        :param int interface_id: physical interface identifier
        :param int cluster_virtual: CVI address (VIP) for this interface
        :param str cluster_mask: network cidr
        :param str macaddress: required mac address for this CVI
        :param list nodes: list of dictionary items identifying cluster nodes
        :param str cvi_mode: packetdispatch is recommended setting
        :param str zone_ref: if present, is promoted to top level physical interface
        :param boolean is_mgmt: default False, should this be management enabled
        :return: None
        :raises: :py:class:`smc.api.exceptions.EngineCommandFailed`
        
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
        cvi = ClusterVirtualInterface.create(interface_id, cluster_virtual, cluster_mask)
        if is_mgmt:
            cvi.auth_request = True
        
        interfaces=[]
        interfaces.append(cvi())
        
        for node in nodes:
            ndi = NodeInterface.create(interface_id=interface_id, 
                                       address=node.get('address'), 
                                       network_value=node.get('network_value'),
                                       nodeid=node.get('nodeid'))
            if is_mgmt:
                ndi.primary_mgt = True
                ndi.outgoing = True
                ndi.primary_heartbeat = True
            
            interfaces.append(ndi())
        self._data.update(cvi_mode=cvi_mode,
                          macaddress=macaddress,
                          interface_id=interface_id,
                          interfaces=interfaces,
                          zone_ref=zone_ref)
    
    @create
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
        :return: None
        :raises: :py:class:`smc.api.exceptions.EngineCommandFailed`
        """
        interfaces=[]
        for node in nodes:
            ndi = NodeInterface.create(interface_id=interface_id, 
                                       address=node.get('address'), 
                                       network_value=node.get('network_value'),
                                       nodeid=node.get('nodeid'))
            if is_mgmt:
                ndi.primary_mgt = True
                ndi.outgoing = True
                ndi.primary_heartbeat = True
            
            interfaces.append(ndi())
        self._data.update(interface_id=interface_id,
                          interfaces=interfaces,
                          macaddress=macaddress,
                          zone_ref=zone_ref)

    @create          
    def add_vlan_to_single_node_interface(self, interface_id, address, 
                                          network_value, vlan_id, 
                                          zone_ref=None):
        """
        Add a vlan and IP address to a single firewall engine.
        
        :param int interface_id: interface identifier
        :param str address: ip address
        :param str network_value: network cidr
        :param int vlan_id: vlan identifier 
        :param str zone_ref: zone reference
        :return: None
        :raises: :py:class:`smc.api.exceptions.EngineCommandFailed`
        
        See :py:class:`smc.core.sub_interfaces.SingleNodeInterface` for more information 
        """
        vlan = VlanInterface(interface_id, vlan_id, zone_ref=zone_ref)
        sni = SingleNodeInterface.create(vlan.get('interface_id'), address, 
                                         network_value)
        vlan.get('interfaces').append(sni())
        self._data.update(interface_id=interface_id,
                          vlanInterfaces=[vlan])
        
    def add_ipaddress_to_vlan_interface(self, interface_id, address, network_value,
                                        vlan_id, nodeid=1, **kwargs):
        """
        When an existing VLAN exists but has no IP address assigned, use this to
        add an ip address to the VLAN.
        This assumes that the engine context exists as the interface specified 
        This is only supported on layer 3 interfaces.
        
        :param str interface_id: interface to modify
        :param str address: ip address for vlan
        :param str network_value: network for address (i.e. 255.255.255.0)
        :param int vlan_id: id of vlan
        :return: :py:class:`smc.api.web.SMCResult`
        :raises: :py:class:`smc.api.exceptions.EngineCommandFailed` for invalid interface
        """
        if not self.href:
            raise EngineCommandFailed('Adding a vlan to existing interface requires '
                                      'an engine reference.')
        
        if self._engine.type == 'single_fw':
            intf = SingleNodeInterface.create(interface_id, address, network_value, nodeid,
                                              nicid='{}.{}'.format(interface_id, vlan_id))
        else:
            intf = NodeInterface.create(interface_id, address, network_value, nodeid,
                                        nicid='{}.{}'.format(interface_id, vlan_id))
        
        p = self.get(interface_id)
        for vlan in p.sub_interfaces():
            if isinstance(vlan, PhysicalVlanInterface):
                if vlan.interface_id == '{}.{}'.format(interface_id, vlan_id):
                    vlan.data['interfaces'] = [intf()]
           
        return prepared_request(href=p.href, json=p.data,
                                etag=p.etag).update()
        
    @create
    def add_vlan_to_node_interface(self, interface_id, vlan_id, 
                                   virtual_mapping=None, 
                                   virtual_resource_name=None,
                                   zone_ref=None):
        """
        Add vlan to a layer 3 interface. Interface is created if 
        it doesn't already exist. This can be used on any engine
        type.
        
        :param int interface_id: interface identifier
        :param int vlan_id: vlan identifier
        :param int virtual_mapping: virtual engine mapping id
               See :py:class:`smc.core.engine.VirtualResource.vfw_id`
        :param str virtual_resource_name: name of virtual resource
               See :py:class:`smc.core.engine.VirtualResource.name`
        :return: None
        :raises: :py:class:`smc.api.exceptions.EngineCommandFailed`
        """
        vlan = VlanInterface(interface_id, vlan_id, 
                             virtual_mapping,
                             virtual_resource_name,
                             zone_ref)
        self._data.update(interface_id=interface_id,
                          vlanInterfaces=[vlan])
   
    @create    
    def add_vlan_to_inline_interface(self, interface_id, vlan_id,
                                     vlan_id2=None,
                                     logical_interface_ref=None,
                                     zone_ref_intf1=None,
                                     zone_ref_intf2=None):
        """
        Add a VLAN to inline interface. Interface is created if 
        it doesn't already exist.
        
        :param str interface_id: interfaces for inline pair, '1-2', '5-6'
        :param int vlan_id: vlan identifier for interface 1
        :param int vlan_id2: vlan identifier for interface 2 (if none, vlan_id used)
        :param str logical_interface_ref: logical interface reference to use
        :param str zone_ref_intf1: zone for inline interface 1
        :param str zone_ref_intf2: zone for inline interface 2
        :return: None
        :raises: :py:class:`smc.api.exceptions.EngineCommandFailed`
        
        See :py:class:`smc.core.sub_interfaces.InlineInterface` for more information 
        """
        first_intf = interface_id.split('-')[0]
        vlan = VlanInterface(first_intf, vlan_id, zone_ref=zone_ref_intf1)
        
        inline_intf = InlineInterface.create(interface_id, 
                                             logical_interface_ref,
                                             zone_ref=zone_ref_intf2)
        copied_intf = deepcopy(inline_intf())
        vlan.get('interfaces').append(_add_vlan_to_inline(inline_intf(), 
                                                          vlan_id, 
                                                          vlan_id2))
          
        self._data.update(interfaces=[copied_intf],
                          vlanInterfaces=[vlan],
                          interface_id=first_intf)

    def __call__(self):
        return {self.typeof: self._data}

    @property
    def cvi_mode(self):
        """
        HA Cluster mode. Not valid for non-cluster engines.
        
        :param str value: packetdispatch, unicast, multicast, multicastgmp
        :rtype: str
        """
        return self.data.get('cvi_mode')
    
    @cvi_mode.setter
    def cvi_mode(self, value):
        self.data['cvi_mode'] = value
   
    @property
    def macaddress(self):
        """
        MAC Address for cluster virtual interface.
        Only valid for cluster engines.
        
        :param str value: macaddress
        :rtype: str
        """
        return self.data.get('macaddress')
    
    @macaddress.setter
    def macaddress(self, value):
        self.data['macaddress'] = value

    @property
    def multicast_ip(self):
        """
        Enter a multicast address, that is, an IP address from the 
        range 224.0.0.0-239.255.255.255.
        The address is used for automatically calculating a MAC address. 
        Required only if multicastigmp cvi mode is selected as the cvi_mode.
        
        :param str value: address
        :rtype: str 
        """
        return self.data.get('multicast_ip')
    
    @multicast_ip.setter
    def multicast_ip(self, value):
        self.data['multicast_ip'] = value
    
    @property
    def virtual_engine_vlan_ok(self):
        """
        Whether to allow VLAN creation on the Virtual Engine.
        Only valid for master engine.
        
        :param boolean value: enable/disable
        :rtype: boolean
        """
        return self.data.get('virtual_engine_vlan_ok')
    
    @virtual_engine_vlan_ok.setter
    def virtual_engine_vlan_ok(self, value):
        self.data['virtual_engine_vlan_ok'] = value

        
class PhysicalVlanInterface(PhysicalInterface):
    """
    This is a container class used when enumerating vlan interfaces
    from the top level physical interface. In some cases, a physical
    interface may be created with a VLAN which has no IP address
    assigned, as would be the case with Inline Interfaces or layer 3
    engines without an IP yet assigned.
    """
    typeof = 'physical_vlan_interface'
    
    def __init__(self, data, meta=None):
        PhysicalInterface.__init__(self, meta)
        self.meta = Meta(href=None)
        self._cache = Cache(self, None, data)

    @property
    def vlan_id(self):
        """
        VLAN interface on the top level VLAN physical interface.
        
        :param str|int value: new vlan id
        """
        v = self.interface_id.split('.')
        if len(v) > 1:
            return v[1]
        
    @vlan_id.setter
    def vlan_id(self, value):
        intf_id = self.interface_id.split('.')
        intf_id[1] = str(value)
        self.interface_id =  ('.').join(intf_id)
        for subintf in iter(self):
            if subintf:
                subintf.nicid = ('.').join(intf_id)
            
    def __iter__(self):
        if self.data.get('interfaces'):
            for intf in self.data['interfaces']:
                for if_type, values in intf.items():
                    yield _InterfaceFactory(if_type)(values)
        yield []
        
    def __getattr__(self, name):
        for interface in iter(self):
            if interface:
                return getattr(interface, name)

    def __str__(self):
        return '{0}(address={1},vlan_id={2})'.format(self.__class__.__name__, 
                                                     self.address, self.vlan_id)

    def __repr__(self):
        return str(self)

class VirtualPhysicalInterface(PhysicalInterface):
    """ 
    VirtualPhysicalInterface
    This interface type is used by virtual engines and has subtle differences
    to a normal interface. For a VE in layer 3 firewall, it also specifies a 
    Single Node Interface as the physical interface sub-type.
    When creating the VE, one of the interfaces must be designated as the source
    for Auth Requests and Outgoing. 
    """
    typeof = 'virtual_physical_interface'
    
    def __init__(self, meta=None, **kwargs):
        PhysicalInterface.__init__(self, meta, **kwargs)
        pass

import sys, inspect
_intf_map = dict((klazz.typeof, klazz) 
                 for i in [sys.modules[__name__], smc.core.sub_interfaces]
                 for _, klazz in inspect.getmembers(i, inspect.isclass)
                 if hasattr(klazz, 'typeof'))

def _InterfaceFactory(name):
    return _intf_map.get(name)

def _interface_helper(data):
        """
        Return sub interface instance
        """
        for intf in data['interfaces']:
            for if_type, values in intf.items():
                return _InterfaceFactory(if_type)(values)
