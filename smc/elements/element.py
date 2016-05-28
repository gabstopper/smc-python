import smc.helpers

class SMCElement(object):
    def __init__(self):
        self.json = None    #required for post/put
        self.etag = None    #required for put
        self.type = None    #required
        self.name = None    #required
        self.href = None    #required
        self.comment = None

    def create(self):
        return self
    
    def modify(self):
        raise "Not Implemented"
    
    def remove(self):
        raise "Not Implemented"
    
    def __str__(self):
        return "name: %s, type: %s" % (self.name, self.type)
  
        
class Host(SMCElement):
    def __init__(self):
        SMCElement.__init__(self)
        self.type = "host"
        self.ip = None
        self.secondary_ip = None
        
    def create(self):
        self.json = smc.helpers.get_json_template('host.json')
        self.json['name'] = self.name
        self.json['address'] = self.ip
        self.comment = self.json['comment'] if self.comment is not None else ""
        if self.secondary_ip:
            for addr in self.secondary_ip:
                self.json['secondary'].append(addr)
        
        return self
    
    def __str__(self):
        return "name: %s, type: %s, address: %s" % (self.name, self.type, self.ip)

    
class Group(SMCElement):
    def __init__(self):
        SMCElement.__init__(self)
        self.type = "group"
        self.members = []
     
    def create(self):
        self.json = smc.helpers.get_json_template('group.json')
        self.json['name'] = self.name
        self.members = self.json['element'] if self.members is not None else []
        self.comment = self.json['comment'] if self.comment is not None else ""
        
        return self
    
    def __str__(self):
        return "name: %s, type: %s, members: %s" % (self.name, self.type, len(self.members))


class IpRange(SMCElement):
    def __init__(self):
        SMCElement.__init__(self)
        self.type = "address range"
        self.iprange = None
        
    def create(self):
        self.json = smc.helpers.get_json_template('iprange.json')
        self.json['name'] = self.name
        self.json['ip_range'] = self.iprange
        self.comment = self.json['comment'] if self.comment is not None else ""
        
        return self

    def __str__(self):
        return "name: %s, type: %s, iprange: %s" % (self.name, self.type, self.iprange)
    
        
class Router(SMCElement):
    def __init__(self):
        SMCElement.__init__(self)
        self.type = "router"
        self.address = None
        self.secondary_ip = None 
    
    def create(self):       
        self.json = smc.helpers.get_json_template('router.json')
        self.json['name'] = self.name
        self.json['address'] = self.address
        self.comment = self.json['comment'] if self.comment is not None else ""
        if self.secondary_ip:
            for addr in self.secondary_ip:
                self.json['secondary'].append(addr)
           
        return self   

    def __str__(self):
        return "name: %s, type: %s, address: %s" % (self.name, self.type, self.address)


class Network(SMCElement):
    def __init__(self):
        SMCElement.__init__(self)
        self.type  = "network"
        self.ip4_network = None
    
    def create(self):        
        self.json = smc.helpers.get_json_template('network.json')
        self.json['name'] = self.name
        self.json['ipv4_network'] = self.ip4_network
        self.comment = self.json['comment'] if self.comment is not None else ""
        
        return self

    def __str__(self):
        return "name: %s, type: %s, ip4_network: %s" % (self.name, self.type, self.ip4_network)


class Route(SMCElement):
    def __init__(self):
        SMCElement.__init__(self)
        self.type = "route"
        self.gw_ip = None
        self.gw_name = None
        self.gw_href = None
        self.network_ip = None
        self.network_name = None
        self.network_href = None
        self.interface_id = None
        self.interface_json = None
        
    def create(self):
        routing = smc.helpers.get_json_template('routing.json')
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
            try:    #find specified nic_id
                self.interface_json = next(item for item in self.json['routing_node'] if item['nic_id'] == str(self.interface_id))
            except StopIteration:
                return None
                
        self.interface_json['routing_node'][0]['routing_node'].append(routing['gateway'])
        
        return self
    
    def __str__(self):
        return "name: %s, type: %s, gw: %s, net: %s, int_id: %s" % (self.name, self.type, self.gw_name, self.network_ip, self.interface_id)


class EngineNodeFactory(object):
        
    def makeNode(self, name, mgmt_ip, mgmt_network, log_server, kwargs):
        
        element = None
        node_type = kwargs['node_type']
        if node_type == "ips" or node_type == "l2fw":
            l3_intf = NodeInterface()
            l3_intf.address = mgmt_ip
            l3_intf.network_value = mgmt_network
            l3_intf.primary_mgt = True
            l3_intf.outgoing = True
            l3_intf.nicid = l3_intf.interface_id = 0
            l3_intf.create()
            
            inline_intf = InlineInterface()
            inline_intf.logical_interface_ref = kwargs['logical_interface']
            inline_intf.interface_id = kwargs['interface_id'].split('-')[0]
            inline_intf.nicid = kwargs['interface_id']
            inline_intf.create() 
            
            if node_type == "l2fw":
                element = FWLayer2()
            elif node_type == "ips":
                element = IPS()
                
            element.name = name
            element.dns += [kwargs['dns']] if kwargs['dns'] is not None else []
            element.log_server = log_server
            element.interfaces.append(l3_intf.json)
            element.interfaces.append(inline_intf.json)
                
            return element
                                       
        elif node_type == "l3fw":
            l3_intf = SingleNodeInterface()
            l3_intf.address = mgmt_ip
            l3_intf.network_value = mgmt_network
            l3_intf.auth_request = True
            l3_intf.primary_mgt = True
            l3_intf.outgoing = True
            l3_intf.nicid = l3_intf.interface_id = kwargs['interface_id']
            l3_intf.create()
            
            l3fw = L3FW()
            l3fw.dns += [kwargs['dns']] if kwargs['dns'] is not None else []
            l3fw.interfaces.append(l3_intf.json)
            l3fw.log_server = log_server
            
            return l3fw
        
    
class EngineNode(SMCElement):
    def __init__(self):
        SMCElement.__init__(self)
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
 
                   
class IPS(EngineNode):
    def __init__(self):
        EngineNode.__init__(self)
        self.type = "ips_node"
 
        
class FWLayer2(EngineNode):
    def __init__(self):
        EngineNode.__init__(self)
        self.type = "fwlayer2_node"
 
                           
class L3FW(EngineNode):
    def __init__(self):
        EngineNode.__init__(self)
        self.type = "firewall_node"

        
class Interface(object):
    def __init__(self):
        self.interface_id = '0'
        self.nicid = '0' #should match interface_id
        self.nodeid = '1'
        self.json = None
        self.config = smc.helpers.get_json_template('interface.json')
        
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
    def __init__(self, SMCElement=None):
        SMCElement.__init__(self)
        self.type = "logical interface"
    
    def create(self):
        self.json = {
                    "comment": self.comment,
                    "name": self.name
        }
    
        return self

        
        
        
        