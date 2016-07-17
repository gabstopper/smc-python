import util

class PhysicalInterface(object):
    """ Physical Interface definition
    Represents the top level physical interface definition. This is the basis for 
    interface types: Inline, Capture, SingleNode and Node.
    This builds the top level json for the required interface.
    """
    def __init__(self, interfaceid, nodeid=1):
        self.interfaceid = interfaceid
        self.nicid = self.interfaceid
        self.nodeid = nodeid
        self.cfg = util.get_json_template('interface.json')

    def build(self):
        self.json = self.cfg.get('physical_interface')
        self.json['physical_interface']['interface_id'] = self.interfaceid
        self.json['physical_interface']['interfaces'].append(self.interface)

class SingleNodeInterface(PhysicalInterface):
    """ SingleNodeInterface interface definition
    Represents a layer3 interface, either standard interface or mgmt interface 
    """
    def __init__(self, address, network, interfaceid, 
                 nodeid=1, 
                 is_mgmt=False):
        PhysicalInterface.__init__(self, interfaceid, nodeid)
        self.address = address
        self.network = network
        self.is_mgmt = is_mgmt
    
    def build(self):
        self.interface = self.cfg.get('single_node_interface')
        self.interface['single_node_interface']['address'] = self.address
        self.interface['single_node_interface']['network_value'] = self.network
        self.interface['single_node_interface']['nodeid'] = self.nodeid
        self.interface['single_node_interface']['nicid'] = self.nicid
        self.interface['single_node_interface']['auth_request'] = True if self.is_mgmt else False
        self.interface['single_node_interface']['primary_mgt'] = True if self.is_mgmt else False
        self.interface['single_node_interface']['outgoing'] = True if self.is_mgmt else False
        super(SingleNodeInterface, self).build()
        return self

class NodeInterface(PhysicalInterface):
    """ NodeInterface definition
    Represents a physical interface for a layer 2 or IPS device. Typically
    used as the management interface
    """
    def __init__(self, address, network, interfaceid, 
                 nodeid=1, 
                 is_mgmt=False):
        PhysicalInterface.__init__(self, interfaceid, nodeid)      
        self.address = address
        self.network = network
        self.is_mgmt = is_mgmt
        
    def build(self):
        self.interface = self.cfg['node_interface']
        self.interface['node_interface']['address'] = self.address
        self.interface['node_interface']['network_value'] = self.network
        self.interface['node_interface']['nodeid'] = self.nodeid
        self.interface['node_interface']['nicid'] = self.nicid
        self.interface['node_interface']['primary_mgt'] = True if self.is_mgmt else False
        self.interface['node_interface']['outgoing'] = True if self.is_mgmt else False
        super(NodeInterface, self).build()
        return self

class CaptureInterface(PhysicalInterface):
    """ CaptureInterface defintion
    Represents a capture/span interface for a layer2 or IPS
    """
    def __init__(self, interfaceid, logical_ref, nodeid=1):
        PhysicalInterface.__init__(self, interfaceid, nodeid)       
        self.logical_interface_ref = logical_ref
        
    def build(self):
        self.interface = self.cfg.get('capture_interface')
        self.interface['capture_interface']['logical_interface_ref'] = self.logical_interface_ref
        self.interface['capture_interface']['nicid'] = self.nicid
        super(CaptureInterface, self).build()
        return self

class InlineInterface(PhysicalInterface):
    """ InlineInterface defintion
    Represents an inline interface for a layer2 or IPS 
    """
    def __init__(self, interfaceid, logical_ref, nodeid=1):
        PhysicalInterface.__init__(self, interfaceid, nodeid)      
        self.logical_interface_ref = logical_ref
        
    def build(self):
        self.interface = self.cfg.get('inline_interface')
        self.interface['inline_interface']['logical_interface_ref'] = self.logical_interface_ref
        self.interface['inline_interface']['nicid'] = self.nicid
        super(InlineInterface, self).build()
        self.json['physical_interface']['interface_id'] = self.interfaceid.split('-')[0]
        return self
        