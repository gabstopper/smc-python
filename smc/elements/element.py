import util

class SMCElement(object):
    """ SMCElement is the base class for all objects added, removed or
    modified through the SMC API.
    Common parameters that are needed are stored in this base class
    :param json: json data to be added or modified
    :param etag: returned during http get and used to identify whether
    an object has been modified in between requests. REQUIRED for updates
    to existing records
    :param type: type of object, used only for str printing from api.common
    :param name: name of object, used for str printing from api.common
    :param href: REQUIRED for create or modify operations to identify
    :param params: If additional parameters are needed for href
    the location of the element
    """
    def __init__(self):
        self.json = None
        self.etag = None
        self.type = None
        self.name = None
        self.href = None
        self.params = None 

    def create(self):
        return self
    
    @staticmethod
    def factory(name=None, href=None, etag=None, 
                _type=None, json=None, params=None):
        element = SMCElement()
        element.name = name
        element.href = href
        element.etag = etag
        element._type = type
        element.json = json
        element.params = params
        return element
    
    def __str__(self):
        return "name: %s, type: %s" % (self.name, self.type)
  
    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)  
        
class Host(SMCElement):
    def __init__(self, name, ip, href, secondary_ip=None, comment=None):
        SMCElement.__init__(self)
        self.type = "host"
        self.name = name
        self.ip = ip
        self.href = href
        self.secondary_ip = []
        self.comment = comment
        if secondary_ip:
            self.secondary_ip.append(secondary_ip)
        
    def create(self):
        self.json = util.get_json_template('host.json')
        self.json['name'] = self.name
        self.json['address'] = self.ip
        self.json['comment'] = self.comment if self.comment is not None else ""
        if self.secondary_ip:
            for addr in self.secondary_ip:
                self.json['secondary'].append(addr)
        
        return self
    
    def __str__(self):
        return "name: %s, type: %s, address: %s, secondary_ip: %s, comment: %s" % \
            (self.name, self.type, self.ip, self.secondary_ip, self.comment)  


class Service(SMCElement):
    def __init__(self, name, min_dst_port, entry_href, proto=None, comment=None):
        SMCElement.__init__(self)
        self.name = name
        self.href = entry_href
        self.type = proto if proto is not None else 'service'
        self.min_dst_port = min_dst_port
        self.proto = proto
        self.comment = comment
        self.services = ['tcp_service', 'icmp_service', 'icmp_ipv6_service', 'ip_service', 'protocol' \
                         'ethernet_service', 'udp_service']
        
    def create(self):
        self.json = util.get_json_template('service.json')
        self.json['name'] = self.name
        self.json['min_dst_port'] = self.min_dst_port
        self.json['comment'] = self.comment if self.comment is not None else ""
        
        return self
    
    def __str__(self):
        return "name: %s, type: %s, port: %s" % (self.name, self.type, self.min_dst_port)
        
        
class Group(SMCElement):
    def __init__(self, name, href, members=None, comment=None):
        SMCElement.__init__(self)       
        self.type = "group"
        self.name = name
        self.href = href
        self.members = []
        self.comment = comment
        if members:
            for member in members:
                self.members.append(member)
     
    def create(self):
        self.json = util.get_json_template('group.json')
        self.json['name'] = self.name
        self.json['element'] = self.members if self.members else []
        self.json['comment'] = self.comment if self.comment is not None else ""
        
        return self
    
    def __str__(self):
        return "name: %s, type: %s, members: %s" % (self.name, self.type, len(self.members))


class IpRange(SMCElement):
    def __init__(self, name, iprange, href, comment=None):
        SMCElement.__init__(self)        
        self.type = "address range"
        self.name = name
        self.iprange = iprange
        self.href = href
        self.comment = comment
        
    def create(self):
        self.json = util.get_json_template('iprange.json')
        self.json['name'] = self.name
        self.json['ip_range'] = self.iprange
        self.json['comment'] = self.comment if self.comment is not None else ""
        
        return self

    def __str__(self):
        return "name: %s, type: %s, iprange: %s, comment: %s" % \
            (self.name, self.type, self.iprange, self.comment)
    
    
class Router(SMCElement):
    def __init__(self, name, address, href, secondary_ip=None, comment=None):
        SMCElement.__init__(self)       
        self.type = "router"
        self.name = name
        self.address = address
        self.href = href
        self.secondary_ip = []
        self.comment = comment
        if secondary_ip:
            self.secondary_ip.append(secondary_ip) 
    
    def create(self):       
        self.json = util.get_json_template('router.json')
        self.json['name'] = self.name
        self.json['address'] = self.address
        self.json['comment'] = self.comment if self.comment is not None else ""
        if self.secondary_ip:
            for addr in self.secondary_ip:
                self.json['secondary'].append(addr)
           
        return self   

    def __str__(self):
        return "name: %s, type: %s, address: %s, secondary_ip: %s, comment: %s" % \
            (self.name, self.type, self.address, self.secondary_ip, self.comment)


class Network(SMCElement):
    def __init__(self, name, ip4_network, href, comment=None):
        SMCElement.__init__(self)        
        self.type  = "network"
        self.name = name
        self.ip4_network = ip4_network
        self.href = href
        self.comment = comment
    
    def create(self):        
        self.json = util.get_json_template('network.json')
        self.json['name'] = self.name
        self.json['ipv4_network'] = self.ip4_network
        self.json['comment'] = self.comment if self.comment is not None else ""
        
        return self

    def __str__(self):
        return "name: %s, type: %s, ip4_network: %s, comment: %s" % \
            (self.name, self.type, self.ip4_network, self.comment)


class Route(SMCElement):
    def __init__(self, gw_name, gw_ip, gw_href, 
                 network_name, network_ip, network_href,
                 interface_id):
        SMCElement.__init__(self)        
        self.type = "route"
        self.gw_name = gw_name
        self.gw_ip = gw_ip
        self.gw_href = gw_href
        self.network_name = network_name
        self.network_ip = network_ip
        self.network_href = network_href
        self.interface_id = interface_id
        
    def create(self):
        routing = util.get_json_template('routing.json')
        #Next Hop Gateway
        #self.json holds original routing table
        routing['gateway']['href'] = self.gw_href
        routing['gateway']['ip'] = self.gw_ip
        routing['gateway']['name'] = self.gw_name
 
        #Network behind Next Hop
        routing['network']['href'] = self.network_href
        routing['network']['ip'] = self.network_ip
        routing['network']['name'] = self.network_name   
        
        #append next hop into gateway router
        routing['gateway']['routing_node'].append(routing['network'])
        
        if self.interface_id is not None:
            try:    #find specified nic_id node and save to interface_json to be modified
                interface_json = next(item for item in self.json['routing_node'] \
                                           if item['nic_id'] == str(self.interface_id))
            except StopIteration:
                return None
                
        interface_json['routing_node'][0]['routing_node'].append(routing['gateway'])
        
        return self
    
    def __str__(self):
        return "name: %s, type: %s, gw: %s, net: %s, int_id: %s" % \
            (self.name, self.type, self.gw_name, self.network_ip, self.interface_id)
   
    
class EngineNode(SMCElement):
    def __init__(self):
        SMCElement.__init__(self)
        self.name = None        
        self.dns = []
        self.log_server = None
        self.interfaces = []
                 
    def create(self):
        self.json = {
            "name": self.name,
            "nodes": [],
            "domain_server_address": [],
            "log_server_ref": self.log_server,
            "physicalInterfaces": self.interfaces
        }
        self.engine = {
            self.type: {
                "activate_test": True,
                "disabled": False,
                "loopback_node_dedicated_interface": [],
                "name": self.name + " node 1",
                "nodeid": 1
                }
        }
        if len(self.dns) > 0:
            rank_i = 0
            for entry in self.dns:
                self.json['domain_server_address'].append({"rank": rank_i, "value": entry})
        self.json['nodes'].append(self.engine)
        return self

    def update(self, original_cfg):
        self.json = original_cfg
        for interface in self.interfaces:
            self.json['physicalInterfaces'].append(interface)
        return self

    def update_route(self, original_cfg):
        self.json = original_cfg
        from pprint import pprint
        pprint(self.json)
        
    
class SingleIPS(EngineNode):
    def __init__(self, name, mgmt_ip, mgmt_network, href, log_server,
                 mgmt_interface='0', inline_interface='1-2', 
                 logical_interface='default_eth', dns=None, 
                 fw_license=False):
        EngineNode.__init__(self)        
        self.type = "ips_node"
        self.name = name
        self.href = href
        self.log_server = log_server
        self.mgmt_ip = mgmt_ip
        self.mgmt_network = mgmt_network
        self.mgmt_interface = mgmt_interface
        self.dns += [dns] if dns is not None else []
        self.inline_interface = inline_interface
        self.logical_interface = logical_interface #should be href of logical interface
        self.fw_license = fw_license
    
    def create(self):
        mgmt_intf = l2_mgmt_interface(self.mgmt_ip, self.mgmt_network, 
                                    interface_id=self.mgmt_interface)
        self.interfaces.append(mgmt_intf.json)
        
        inline_intf = inline_interface(self.logical_interface, interface_id=self.inline_interface)
        self.interfaces.append(inline_intf.json)
        
        return super(SingleIPS, self).create() 

        
class SingleLayer2(SingleIPS):      
    def __init__(self, *args, **kwargs):
        super(SingleLayer2, self).__init__(*args, **kwargs)
        self.type = "fwlayer2_node"   
    
 
class SingleLayer3(EngineNode):
    def __init__(self, name, mgmt_ip, mgmt_network, href, log_server,
                 mgmt_interface='0', dns=None, 
                 fw_license=False):
        EngineNode.__init__(self)
        self.type = "firewall_node"
        self.name = name
        self.mgmt_ip = mgmt_ip
        self.mgmt_network = mgmt_network
        self.href = href
        self.log_server = log_server
        self.mgmt_interface = mgmt_interface
        self.dns += [dns] if dns is not None else []
        self.fw_license = fw_license
    
    def create(self):
        mgmt_intf = l3_mgmt_interface(self.mgmt_ip, self.mgmt_network, 
                                    interface_id=self.mgmt_interface)            
        self.interfaces.append(mgmt_intf.json) 
        return super(SingleLayer3, self).create()      

        
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
        
        