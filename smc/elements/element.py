import smc.helpers

class SMCElement(object):
    def __init__(self):
        self.json = None
        self.etag = None
        self.type = None
        self.name = None
        self.href = None
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
        self.ip = None
        self.secondary_ip = None
        
    def create(self):
        self.json = smc.helpers.get_json_template('host.json')
        self.json['name'] = self.name
        self.json['address'] = self.ip
        if self.comment:
            self.json['comment'] = self.comment
        if self.secondary_ip:
            for addr in self.secondary_ip:
                self.json['secondary'].append(addr)
        
        return self
    
    def __str__(self):
        return "name: %s, type: %s, address: %s" % (self.name, self.type, self.ip)

    
class Group(SMCElement):
    def __init__(self):
        SMCElement.__init__(self)
        self.members = []
     
    def create(self):
        self.json = smc.helpers.get_json_template('group.json')
        self.json['name'] = self.name
        if self.members:
            self.json['element'] = self.members
        if self.comment:
            self.json['comment'] = self.comment
        
        return self
    
    def __str__(self):
        return "name: %s, type: %s, members: %s" % (self.name, self.type, len(self.members))


class IpRange(SMCElement):
    def __init__(self):
        SMCElement.__init__(self)
        self.iprange = None
        
    def create(self):
        self.json = smc.helpers.get_json_template('iprange.json')
        self.json['name'] = self.name
        self.json['ip_range'] = self.iprange
        if self.comment:
            self.json['comment'] = self.comment
        
        return self

    def __str__(self):
        return "name: %s, type: %s, iprange: %s" % (self.name, self.type, self.iprange)
    
        
class Router(SMCElement):
    def __init__(self):
        SMCElement.__init__(self)
        self.address = None
        self.secondary_ip = None 
    
    def create(self):       
        self.json = smc.helpers.get_json_template('router.json')
        self.json['name'] = self.name
        self.json['address'] = self.address
        if self.secondary_ip:
            for addr in self.secondary_ip:
                self.json['secondary'].append(addr)
        if self.comment:
            self.json['comment'] = self.comment
            
        return self   

    def __str__(self):
        return "name: %s, type: %s, address: %s" % (self.name, self.type, self.address)


class Network(SMCElement):
    def __init__(self):
        SMCElement.__init__(self)
        self.ip4_network = None
    
    def create(self):        
        self.json = smc.helpers.get_json_template('network.json')
        self.json['name'] = self.name
        self.json['ipv4_network'] = self.ip4_network
        if self.comment:
            self.json['comment'] = self.comment
        
        return self

    def __str__(self):
        return "name: %s, type: %s, ip4_network: %s" % (self.name, self.type, self.ip4_network)


class Route(SMCElement):
    def __init__(self):
        SMCElement.__init__(self)
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
    
    
class SingleFW(SMCElement):
    """ Create initial single l3 fw 
    By default currently set interface 0 to be the default management port. 
    """
    def __init__(self):
        SMCElement.__init__(self)
        self.mgmt_ip = None
        self.mgmt_network = None
        self.log_server = None
        self.dns = None
        self.fw_license = None
        self.interface_id = None
        
    def create(self):
        
        single_fw = smc.helpers.get_json_template('single_fw.json')
        
        for k in single_fw:
            if k == 'name':
                single_fw[k] = self.name
            elif k == 'nodes':
                single_fw[k][0]['firewall_node']['name'] = self.name + ' node 1'
            elif k == 'physicalInterfaces':               
                single_fw[k][0]['physical_interface']['interfaces'][0]['single_node_interface']['address'] = self.mgmt_ip
                single_fw[k][0]['physical_interface']['interfaces'][0]['single_node_interface']['network_value'] = self.mgmt_network
            elif k == 'log_server_ref':
                single_fw[k] = self.log_server
            elif k == 'domain_server_address':
                if self.dns:
                    single_fw[k].append({"rank": 0, "value": self.dns})
        
        self.json = single_fw
        return self  
                

class L3interface(SMCElement):
    """ Add physical interface to firewall
    
    If interface_id is not set, the next sequential interface id will be used
    
    Implementation detail: mgmt is always installed to interface 0. If the
    operator specifies to add an interface at pos 5 (for example) and adds 
    additional interfaces without specifying position, it will always be +1 of
    the highest interface defined.   
    """
    def __init__(self):
        SMCElement.__init__(self)
        self.ip = None
        self.mask = None
        self.interface_id = None
        
    def create(self):
        
        interface = smc.helpers.get_json_template('routed_interface.json')
        interface_ids = [] #store existing node_id to find next open
        
        from pprint import pprint
        pprint(self.json)
        
        if self.interface_id is None:
            for node_interface in self.json['physicalInterfaces']:
                interface_ids.append(node_interface['physical_interface']['interface_id'])
        
                interface_id = [int(i) for i in interface_ids]  #needed to find max
                self.interface_id = max(interface_id)+1
        
        phys_iface = interface['physical_interface']
        phys_iface['interface_id'] = str(self.interface_id)
        iface = interface['physical_interface']['interfaces'][0]
        iface = iface['single_node_interface']
        iface['address'] = self.ip
        iface['nicid'] = str(self.interface_id)
        iface['network_value'] = self.mask
        
        self.json['physicalInterfaces'].append(interface)
        
        return self        
    
    def __str__(self):
        return "name: %s, type: %s, ip: %s, mask: %s, int_id: %s" % \
            (self.name, self.type, self.ip, self.mask, self.interface_id)   
 
        
class L2FW(SMCElement):
    def __init__(self, SMCElement=None):
        SMCElement.__init__(self)
        self.mgmt_ip = None
        self.mgmt_network = None
        self.log_server = None
        self.dns = None
        self.fw_license = None
        self.log_server = None
        self.interface_id = None
        self.logical_interface = None
        
    def create(self):
        
        layer2_fw = smc.helpers.get_json_template('layer2_fw.json')
        
        for k in layer2_fw:
            if k == 'name':
                layer2_fw[k] = self.name
            elif k == 'nodes':
                layer2_fw[k][0]['fwlayer2_node']['name'] = self.name + ' node 1'
            elif k == 'physicalInterfaces':               
                inline_int = layer2_fw[k][0]
                inline_int['physical_interface']['interfaces'][0]['inline_interface']['logical_interface_ref'] = self.logical_interface
                
                from pprint import pprint
                pprint(inline_int)
                
                mgmt_int = layer2_fw[k][1]
                mgmt_int['physical_interface']['interfaces'][0]['node_interface']['address'] = self.mgmt_ip
                mgmt_int['physical_interface']['interfaces'][0]['node_interface']['network_value'] = self.mgmt_network
            elif k == 'log_server_ref':
                layer2_fw[k] = self.log_server
            elif k == 'domain_server_address':
                if self.dns:
                    layer2_fw[k].append({"rank": 0, "value": self.dns})
                    
        self.json = layer2_fw
        
        return self

        
        
        
        