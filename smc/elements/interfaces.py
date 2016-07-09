import util
from smc.elements.element import SMCElement

class Interface(object):
    def __init__(self):
        self.interface_id = '0'
        self.nicid = '0' #should match interface_id
        self.nodeid = '1'
        self.json = None
        self.config = util.get_json_template('interface.json')
        
    def create(self):
        #assemble full interface
        self.json = self.config['physical_interface']
        self.json['physical_interface']['interface_id'] = self.interface_id
        self.json['physical_interface']['interfaces'].append(self.int_json)
       
        
class SingleNodeInterface(Interface):
    def __init__(self):
        Interface.__init__(self)        
        self.type = "single node interface"
        self.address = None
        self.network_value = None
        self.auth_request = False
        self.primary_mgt = False
        self.outgoing = False
        
    def create(self):
        self.int_json = self.config['single_node_interface']
        self.int_json['single_node_interface']['address'] = self.address
        self.int_json['single_node_interface']['network_value'] = self.network_value
        self.int_json['single_node_interface']['nodeid'] = self.nodeid
        self.int_json['single_node_interface']['nicid'] = self.nicid
        self.int_json['single_node_interface']['auth_request'] = self.auth_request
        self.int_json['single_node_interface']['primary_mgt'] = self.primary_mgt
        self.int_json['single_node_interface']['outgoing'] = self.outgoing
        super(SingleNodeInterface, self).create()


class NodeInterface(Interface):
    def __init__(self):
        Interface.__init__(self)       
        self.type = "node interface"
        self.address = None
        self.network_value = None
        self.primary_mgt = False
        self.outgoing = False
        
    def create(self):
        self.int_json = self.config['node_interface']
        self.int_json['node_interface']['address'] = self.address
        self.int_json['node_interface']['network_value'] = self.network_value
        self.int_json['node_interface']['nodeid'] = self.nodeid
        self.int_json['node_interface']['nicid'] = self.nicid
        self.int_json['node_interface']['primary_mgt'] = self.primary_mgt
        self.int_json['node_interface']['outgoing'] = self.outgoing
        super(NodeInterface, self).create()
        
        
class InlineInterface(Interface):
    def __init__(self):
        Interface.__init__(self)       
        self.type = "inline interface"
        self.logical_interface_ref = None
        
    def create(self):
        self.int_json = self.config['inline_interface']
        self.int_json['inline_interface']['logical_interface_ref'] = self.logical_interface_ref
        self.int_json['inline_interface']['nicid'] = self.nicid
        super(InlineInterface, self).create()

               
class CaptureInterface(Interface):
    def __init__(self):
        Interface.__init__(self)       
        self.type = "capture interface"
        self.logical_interface_ref = None
        
    def create(self):
        self.int_json = self.config['capture_interface']
        self.int_json['capture_interface']['logical_interface_ref'] = self.logical_interface_ref
        self.int_json['capture_interface']['nicid'] = self.nicid
        super(CaptureInterface, self).create()


class LogicalInterface(SMCElement):
    def __init__(self, name, href, comment=None):
        SMCElement.__init__(self)        
        self.type = "logical interface"
        self.name = name
        self.href = href
        self.comment = comment if comment is not None else ""
    
    def create(self):
        self.json = {
                    "comment": self.comment,
                    "name": self.name
        }
    
        return self


#helpers
def l3_mgmt_interface(mgmt_ip, mgmt_network, interface_id=0):
    l3_intf = SingleNodeInterface()
    l3_intf.address = mgmt_ip
    l3_intf.network_value = mgmt_network
    l3_intf.auth_request = True
    l3_intf.primary_mgt = True
    l3_intf.outgoing = True
    l3_intf.nicid = l3_intf.interface_id = interface_id
    
    l3_intf.create()
    return l3_intf        


def l2_mgmt_interface(mgmt_ip, mgmt_network, interface_id=0):
    l3_intf = NodeInterface()
    l3_intf.address = mgmt_ip
    l3_intf.network_value = mgmt_network
    l3_intf.primary_mgt = True
    l3_intf.outgoing = True
    l3_intf.nicid = l3_intf.interface_id = interface_id
    
    l3_intf.create()
    return l3_intf


def l3_interface(ipaddress, network, interface_id):
    l3_intf = SingleNodeInterface()
    l3_intf.address = ipaddress
    l3_intf.network_value = network
    l3_intf.nicid = l3_intf.interface_id = interface_id
    
    l3_intf.create() 
    return l3_intf    

def inline_intf(logical_interface_ref, interface_id='1-2'):
    """ create inline interface
    The logical interface href is required, can't be referenced by name
    """
    inline_intf = InlineInterface()
    inline_intf.logical_interface_ref = logical_interface_ref
    inline_intf.interface_id = interface_id.split('-')[0]
    inline_intf.nicid = interface_id
    
    inline_intf.create()
    return inline_intf
          
def inline_interface(logical_interface_ref, interface_id='1-2'):
    """ create inline interface
    The logical interface href is required, can't be referenced by name
    """
    inline_intf = InlineInterface()
    inline_intf.logical_interface_ref = logical_interface_ref
    inline_intf.interface_id = interface_id.split('-')[0]
    inline_intf.nicid = interface_id
    
    inline_intf.create()
    return inline_intf
        
def capture_interface(logical_interface_ref, interface_id=1):
    """ create capture interface
    The logical interface href is required, can't be referenced by name
    """
    capture = CaptureInterface()
    capture.logical_interface_ref = logical_interface_ref
    capture.interface_id = interface_id
    capture.nicid = interface_id
    
    capture.create()
    return capture
        