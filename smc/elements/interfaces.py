from UserDict import UserDict
from copy import deepcopy

class NodeInterface(object):
    """ Node Dedicated Interface
    Node dedicated interface is used on specific engine types and represents an interface
    used for management (ips and layer 2 engines), or non-traffic type interfaces
    
    :param address: ip address of the interface
    :param network_value: network/netmask, i.e. x.x.x.x/24
    :param interfaceid: interface id
    :type interfaceid: int 
    :param nodeid: for clusters, used to identify the node number
    :type nodeid: int
    """
    def __init__(self, address, network_value, interfaceid,
                 nodeid=1):
        self.address = address
        self.network_value = network_value
        self.nicid = interfaceid
        self.auth_request = False
        self.backup_heartbeat = False
        self.nodeid = nodeid
        self.outgoing = False
        self.primary_mgt = False
    
    def as_dict(self):
        return {'node_interface': self.__dict__}

class InlineInterface(object):
    """ InlineInterface
    This interface is used by layer 2 or ips engines for a layer 2 configuration and 
    consists of 2 interfaces.
    
    :param nicid: should be the two interfaces, seperated by -; i.e. 1-2
    :type nicid: string
    :oaram logical_ref: logical interface reference
    
    The logical interface reference needs to be unique on the same engine that uses both
    inline and capture interfaces
    """
    def __init__(self, nicid, logical_interface_ref, zone_ref=None):
        self.failure_mode = 'normal'
        self.inspect_unspecified_vlans = True
        self.nicid = nicid
        self.logical_interface_ref = logical_interface_ref
        self.zone_ref = zone_ref
    
    def add_vlan(self, vlan_id):
        try:
            first, last = self.nicid.split('-')
            self.nicid = first + '.' + str(vlan_id) + '-' + last + '.' + str(vlan_id)
        except ValueError:
            pass
        
    def as_dict(self):
        return {'inline_interface': self.__dict__}

          
class SingleNodeInterface(object):
    """ SingleNodeInterface
    This interface is used by specific engine types like Layer 3 Engines. This type of interface
    can be a management interface as well as a non-management routed interface
    
    :param address: address of this interface
    :param network_value: network of this interface in cidr x.x.x.x/24
    :param nicid: nic id, will match the interface id, numbering starts at 0
    :type nicid: int
    :param nodeid: if a cluster, identifies which node this is for
    :type nodeid: int
    """
    def __init__(self, address, network_value, nicid,
                 nodeid=1):
        self.address = address
        self.auth_request = False
        self.auth_request_source = False
        self.primary_heartbeat = False
        self.backup_heartbeat = False
        self.backup_mgt = False
        self.dynamic = False
        self.network_value = network_value
        self.nicid = nicid
        self.nodeid = nodeid
        self.outgoing = False
        self.primary_mgt = False

    def as_dict(self):
        return {'single_node_interface': self.__dict__}

class ClusterVirtualInterface(object):
    """ Represents a cluster virtual interface (CVI)
    
    :param address: address of CVI
    :param network_value: network for CVI
    :param nicid: nic id to use for physical interface
    """
    def __init__(self, address, network_value, nicid):
        self.address = address
        self.network_value = network_value
        self.nicid = nicid
        self.auth_request = False
    
    def as_dict(self):
        return {'cluster_virtual_interface': self.__dict__}

class CaptureInterface(object):
    """ Capture Inteface (span)
    This interface type can be used on layer 2 or ips engine types
    
    :param interfaceid: the interface id
    :type interfaceid: int
    :oaram logical_ref: logical interface reference, must be unique from inline intfs
    """
    def __init__(self, interfaceid, logical_ref):
        self.inspect_unspecified_vlans = True
        self.logical_interface_ref = logical_ref
        self.nicid = interfaceid

    def as_dict(self):
        return {'capture_interface': self.__dict__}

class VlanInterface(object):
    """ VLAN Interface assigned to a SingleNode or Node Interface
    
    :param interface_id: id of interface to assign VLAN to
    :param vlan_id: ID of vlan
    :type vlan_id: int
    :param virtual_mapping: The interface ID for the virtual engine. Virtual engine
               interface mapping starts numbering at 0 by default, which means you must
               account for interfaces used by master engine
    :param virtual_resource_name: Name of virtual resource for this VLAN if a VE
    """
    def __init__(self, interface_id, vlan_id,
                 virtual_mapping=None,
                 virtual_resource_name=None,
                 zone_ref=None):
        self.interface_id = str(interface_id) + '.' + str(vlan_id)
        self.virtual_mapping = virtual_mapping
        self.virtual_resource_name = virtual_resource_name
        self.interfaces = []
        self.zone_ref = zone_ref

    def as_dict(self):
        return self.__dict__
    
class PhysicalInterface(UserDict):
    """
    Represents all interfaces considered to be a physical interface type such as 
    Single Node Interface (single layer 3 firewall), Node Dedicated
    Interface (IPS, Layer 2 and Clusters), Inline Interface and Capture Interface. 
    Use this class to build the interface configuration and then add to the engine by 
    calling :py:func:`smc.elements.engines.Engine.add_physical_interfaces`
    
    Zones can be applied at different levels depending on the configuration. 
    
    If using an inline interface, you can set the zone on the physical interface level
    which will apply both zones to the inline pair. Alternatively you can apply
    individual zones to each inline interface.
    This would be accomplished by::
        
        physical = PhysicalInterface('10-11')
        physical.add_inline_interface(self, logical_interface_ref, 
                                            zone_ref_intf1='zone_for_first',
                                            zone_ref_intf2='zone_for_second')
        
    If using VLANs, zones can be applied at the VLAN level or the top level physical interface
    encapsulating the VLANs. 
    
    :param interface_id: interface id for this physical interface
    :type interface_id: string
    :param zone_ref: zone to set on top level interface, superseding others 
    """
    def __init__(self, interface_id, p_dict=None, zone_ref=None):
        self.data = {} #: data attribute representing interface
        if p_dict is not None: 
            self.update(p_dict)
        else:
            self.interface_id = interface_id
            default = {'interface_id': self.interface_id,
                       'interfaces': [],
                       'vlanInterfaces': [],
                       'zone_ref': zone_ref}
            self.update(default)
    
    def add_single_node_interface(self, address, network_value, 
                                  zone_ref=None, is_mgmt=False):
        """ Add single node interface, used for layer 3 firewalls
        Zone applied here will apply to top level physical interface
        
        :param address: ip address
        :param network_value: network, in form: x.x.x.x/y
        :param zone_ref: default None, zone for this interface
        :param is_mgmt: default False, should this be a management enabled interface
        """
        intf = SingleNodeInterface(address, network_value, self.interface_id)
        if is_mgmt:
            intf.auth_request = True
            intf.outgoing = True
            intf.primary_mgt = True
        self.get('interfaces').append(intf.as_dict())
        if zone_ref is not None: self.update({'zone_ref': zone_ref})
    
    def add_single_node_interface_to_vlan(self, address, network_value, vlan_id, 
                                          zone_ref=None):
        """ Add a single node interface to a VLAN, used on single layer 3 firewalls
        This will create the physical interface if it doesn't already exist. If it does
        exist, this will simply add the VLAN identifier and if a zone_ref is defined,
        it will add the zone for that particular vlan and specified network
        
        :param address: ip address
        :param network_value: network, in form: x.x.x.x/y
        :param vlan_id: ID for the vlan
        :param zone_ref: zone name for VLAN. Set on physical intf to use zone for all vlans
        """
        vlan = VlanInterface(self.interface_id, vlan_id, zone_ref=zone_ref)
        node = SingleNodeInterface(address, network_value, vlan.interface_id)
        vlan.interfaces.append(node.as_dict())
        self.get('vlanInterfaces').append(vlan.as_dict())

    def add_node_interface(self, address, network_value, zone_ref=None, 
                           nodeid=1, is_mgmt=False):
        """ Add an NDI. Used on IPS, Layer2, and Layer3 clusters

        :param address: ip address
        :param network_value: network, in the form: x.x.x.x/y
        :param zone_ref: default None, zone for this interface
        :param nodeid: nodeid identifying this node. Used in clusters.
        :type nodeid: int
        :param is_mgmt: default False, should this be a management enabled interface
        """
        intf = NodeInterface(address, network_value, self.interface_id, nodeid=nodeid)
        if is_mgmt:
            intf.primary_mgt = True
            intf.outgoing = True
        self.get('interfaces').append(intf.as_dict())
        if zone_ref is not None: self.update({'zone_ref': zone_ref})
    
    def add_vlan_to_node_interface(self, vlan_id, 
                                   virtual_mapping=None,
                                   virtual_resource_name=None,
                                   zone_ref=None):
        """ Add a vlan to node physical interface. Works on any interface with
        exception of inline interfaces.

        Zone applied here will apply to the VLAN specifically (versus top level phys intf)
        
        :param vlan_id: vlan identifier
        :param virtual_mapping: virtual resource associated with this vlan
        :param virtual_resource: virtual mapping id
        """
        vlan = VlanInterface(self.interface_id, vlan_id,
                             virtual_mapping=virtual_mapping,
                             virtual_resource_name=virtual_resource_name,
                             zone_ref=zone_ref)
        self.get('vlanInterfaces').append(vlan.as_dict())
    
    def add_inline_interface(self, logical_interface_ref, 
                             zone_ref_intf1=None,
                             zone_ref_intf2=None):
        """ Inline interface pair for layer 2 or IPS engines
        Zones specified here can be specific to the inline interface
        
        :param logical_interface_ref: logical interface reference
        :param zone_ref_intf1: set zone on first inline interface pair
        :param zone_ref_intf2: set zone on seceond inline interface pair
        """
        if self.get('zone_ref') is not None: #set at physical level
            zone_ref_intf1 = zone_ref_intf2 = self.get('zone_ref')
            
        inline_intf = InlineInterface(self.interface_id, 
                                      logical_interface_ref=logical_interface_ref,
                                      zone_ref=zone_ref_intf2) #zone for second intf
        self.update({'interface_id': self.interface_id.split('-')[0]})
        self.get('interfaces').append(inline_intf.as_dict())
        self.update({'zone_ref': zone_ref_intf1}) #1st intf zone
        
    def add_vlan_to_inline_interface(self, vlan_id, 
                                     logical_interface_ref=None,
                                     zone_ref_intf1=None,
                                     zone_ref_intf2=None):
        """ Add VLAN to inline interface. Used on layer 2 firewall or IPS
        When the inline interface does not exist, this will create it and the
        specified VLANs. If it does exist, existing VLANs will be preserved and
        new ones added.
        Zones set here will apply to each inline interface
        
        :param vlan_id: vlan identifier
        :param logical_interface_ref: logical interface reference
        :param zone_ref_intf1: first interface in inline pair
        :param zone_ref_intf2: second interface in inline pair
        """
        first_intf = self.interface_id.split('-')[0]
        
        vlan = VlanInterface(first_intf, vlan_id, zone_ref=zone_ref_intf1)
        
        inline_intf = InlineInterface(self.interface_id, 
                                      logical_interface_ref,
                                      zone_ref=zone_ref_intf2)

        self.get('interfaces').append(deepcopy(inline_intf.as_dict()))
        
        inline_intf.add_vlan(vlan_id)
        vlan.interfaces.append(inline_intf.as_dict())
        self.get('vlanInterfaces').append(vlan.as_dict())
        self.update({'interface_id': first_intf})
    
    def add_capture_interface(self, logical_interface_ref, zone_ref=None):
        """ Add capture interface. Used in layer 2 or IPS engines
        Zone applied here will apply to the top level physical interface.
        
        :param logical_interface_ref: logical interface reference
        :param zone_ref: default None, zone for this capture interface
        """
        intf = CaptureInterface(self.interface_id, logical_interface_ref)
        self.get('interfaces').append(intf.as_dict())
        if zone_ref is not None: self.update({'zone_ref': zone_ref})

    def add_cluster_virtual_interface(self, cluster_virtual, cluster_mask, 
                                      macaddress, nodes, zone_ref=None, is_mgmt=False):
        """ Cluster virtual interface, used in cluster configurations
        
        :param cluster_virtual: CVI address (VIP) for this interface
        :param cluster_mask: network for this interface, in form: x.x.x.x/y
        :param macaddress: required mac address for this CVI
        :param nodes: list of dictionary items identifying cluster nodes, in 
            the form of: [{'address': '1.1.1.2', 'netmask': '1.1.1.0/24', 'nodeid':1}]
        :param zone_ref: if present, is promoted to top level physical interface
        :param is_mgmt: default False, should this be management enabled
        """    
        self.setdefault('cvi_mode', 'packetdispatch')
        self.setdefault('macaddress', macaddress)
        
        cvi = ClusterVirtualInterface(cluster_virtual, cluster_mask, self.interface_id)
        if is_mgmt:
            cvi.auth_request = True
        self.get('interfaces').append(cvi.as_dict())
        
        for node in nodes:
            intf = NodeInterface(node.get('address'), node.get('network_value'),
                                 self.interface_id, node.get('nodeid'))
            if is_mgmt:
                intf.primary_mgt = True
                intf.outgoing = True
                intf.__setattr__('primary_heartbeat', True)
            self.get('interfaces').append(intf.as_dict())
        if zone_ref is not None: self.update({'zone_ref': zone_ref})
    
    def modify_single_node_interface(self, **kwds):    
        intf = self.get('interfaces')[0].get('single_node_interface')
        for k, v in kwds.iteritems():
            if k in intf:
                intf[k] = v
    
    def modify_physical_interface(self, **kwds):
        """ If key=value exists in interface dict then replace 
        For example, to change the zone: zone_ref=new_zone
        """
        self.update({k:v for k,v in kwds.iteritems() if k in self.data})
    
    def as_dict(self):
        return {'physical_interface': self.data}
    
    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)
    
class VirtualPhysicalInterface(PhysicalInterface):
    """ Represents a Layer 3 VirtualEngine physical interface 
    One of the physical interfaces for a Layer 3 VE must be set as the source
    for Auth Requests and Outgoing. Unless specified during creation of the
    node interface, this will default to interface 0 on the VE.
    
    :param interface_id: interface id for this virtual interface
    :param intfdict: dictionary representing interface information
    :param zone_ref: zone for top level physical interface
    """
    def __init__(self, interface_id, intfdict=None, zone_ref=None):
        PhysicalInterface.__init__(self, interface_id, intfdict, zone_ref)
    
    def add_single_node_interface(self, address, network_value, 
                                  zone_ref=None, outgoing_intf=0):
        
        intf = SingleNodeInterface(address, network_value, self.interface_id)
        if self.interface_id == outgoing_intf:
            intf.auth_request = True
            intf.outgoing = True
        self.get('interfaces').append(intf.as_dict())
        if zone_ref is not None: self.update({'zone_ref': zone_ref})
    
    def as_dict(self):
        return {'virtual_physical_interface': self.data}   