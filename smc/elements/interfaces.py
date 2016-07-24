import util

class NodeInterface(object):
    """ Node Dedicated Interface
    Node dedicated interface is used on specific engine types and represents an interface
    used for management (ips and layer 2 engines), or non-traffic type interfaces
    
    :param address: ip address of the interface
    :param network_value: network/netmask, i.e. x.x.x.x/24
    :param interfaceid: interface id 
    :param nodeid: for clusters, used to identify the node number
    :type interfaceid: int
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
        
    def __repr__(self):
        p = PhysicalInterface(self.nicid, {'node_interface': self.__dict__})
        return p.__dict__

class InlineInterface(object):
    """ InlineInterface (layer 2)
    This interface is used by layer 2 or ips engines for a layer 2 configuration and 
    consists of 2 interfaces.
    
    :param interfaceid: should be the two interfaces, seperated by -; i.e. 1-2
    :oaram logical_ref: logical interface reference
    
    The logical interface reference needs to be unique on the same engine that uses both
    inline and capture interfaces
    """
    def __init__(self, interfaceid, logical_ref):
        self.failure_mode = 'normal'
        self.inspect_unspecified_vlans = True
        self.nicid = interfaceid
        self.logical_interface_ref = logical_ref
        
    def __repr__(self):
        p = PhysicalInterface(self.nicid.split('-')[0], {'inline_interface': self.__dict__})
        return p.__dict__
          
class SingleNodeInterface(object):
    """ SingleNodeInterface
    This interface is used by specific engine types like Layer 3 Engines. This type of interface
    can be a management interface as well as a non-management routed interface
    
    :param address: address of this interface
    :param network_value: network of this interface in cidr x.x.x.x/24
    :param nicid: nic id, will match the interface id, numbering starts at 0
    :param nodeid: if a cluster, identifies which node this is for
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

    def __repr__(self):
        """ Use if adding interfaces after engine exists. This json doesn't need the
        top level physical_interface definition, just the node level info """
        p = PhysicalInterface(self.nicid, {'single_node_interface': self.__dict__})
        return p.__dict__

class CaptureInterface(object):
    """ Capture Inteface (span)
    This interface type can be used on layer 2 or ips engine types
    
    :param interfaceid: the interface id
    :type interfaceid: int
    :oaram logical_ref: logical interface reference
    
    The logical interface reference needs to be unique on the same engine that uses both
    inline and capture interfaces
    """
    def __init__(self, interfaceid, logical_ref):
        self.inspect_unspecified_vlans = True
        self.logical_interface_ref = logical_ref
        self.nicid = interfaceid
    
    def __repr__(self):
        p = PhysicalInterface(self.nicid, {'capture_interface': self.__dict__})
        return p.__dict__
    
class PhysicalInterface(object):
    """ Physical Interface definition
    Represents the top level physical interface definition. This is the basis for 
    interface types: Inline, Capture, SingleNode and Node.
    This builds the top level json for the required interface when calling child
    classes such as SingleNodeInterface, CaptureInterface, etc. 
    
    :param interfaceid: id of this physical interface
    :param interfaces: interfaces to be added
    :type interface: list
    :param zone: define zone if any
    """   
    def __init__(self, interfaceid, interfaces,
                 zone=None):
        self.interface_id = interfaceid
        self.interfaces = []
        self.vlanInterfaces = []
        self.zone_ref = zone
        self.interfaces.append(interfaces)

    def __repr__(self):
        return {'physical_interface': self.__dict__}
