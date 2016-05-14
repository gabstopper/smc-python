import smc.helpers

class SMCElement(object):
    def __init__(self):
        self.json = None
        self.etag = None
        self.type = None
        self.name = None
        self.href = None
        self.comment = None
        self.element = None

    def create(self):
        return self
    
    def modify(self):
        raise "Not Implemented"
    
    def remove(self):
        raise "Not Implemented"
    

class Host(SMCElement):
    def __init__(self):
        SMCElement.__init__(self)
        self.ip = None
        self.secondary_ip = None
        
    def create(self):
        host = smc.helpers.get_json_template('host.json')
        host['name'] = self.name
        host['address'] = self.ip
        if self.comment:
            host['comment'] = self.comment
        if self.secondary_ip:
            for addr in self.secondary_ip:
                host['secondary'].append(addr)
        
        self.json = host
        return self
 
class Group(SMCElement):
    def __init__(self):
        SMCElement.__init__(self)
        self.members = None
     
    def create(self):
        group = smc.helpers.get_json_template('group.json')
        group['name'] = self.name
        if self.members:
            group['element'] = self.members
        if self.comment:
            group['comment'] = self.comment
        
        self.json = group
        return self


class IpRange(SMCElement):
    def __init__(self):
        SMCElement.__init__(self)
        self.iprange = None
        
    def create(self):
        iprange = smc.helpers.get_json_template('iprange.json')
        iprange['name'] = self.name
        iprange['ip_range'] = self.iprange
        if self.comment:
            iprange['comment'] = self.comment
        
        self.json = iprange
        return self

        
class Router(SMCElement):
    def __init__(self):
        SMCElement.__init__(self)
        self.address = None
        self.secondary_ip = None 
    
    def create(self):
        router = smc.helpers.get_json_template('router.json')
        router['name'] = self.name
        router['address'] = self.address
        if self.secondary_ip:
            for addr in self.secondary_ip:
                router['secondary'].append(addr)
        
        self.json = router
        return self   
    

class Network(SMCElement):
    def __init__(self):
        SMCElement.__init__(self)
        self.ip4_network = None
    
    def create(self):
        network = smc.helpers.get_json_template('network.json')
        network['name'] = self.name
        network['ipv4_network'] = self.ip4_network
        if self.comment:
            network['comment'] = self.comment
        
        self.json = network
        return self


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
        self.element = None
        
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
            try:
                self.interface_id = next(item for item in self.element['routing_node'] if item['nic_id'] == str(self.interface_id))
            except StopIteration:
                return None
                
        self.interface_id['routing_node'][0]['routing_node'].append(routing['gateway'])
        
        self.json = self.element
        return self
    
    
class SingleFW(SMCElement):
    def __init__(self):
        SMCElement.__init__(self)
        self.mgmt_ip = None
        self.mgmt_network = None
        self.log_server = None
        self.dns = None
        self.fw_license = None
        self.interface_id = None
    
    def add_interface(self, ip, mask, int_id=None): #TODO: Allow setting the interface
        """ Add physical interface to firewall
            Args: 
                * ip: address of interface
                * mask: in cidr format
                * int_id (optional): id for interface, if not set, uses next available
            Implementation detail: mgmt is always installed to interface 0. If the
            operator specifies to add an interface at pos 5 (for example) and adds 
            additional interfaces without specifying position, it will always be +1 of
            the highest interface defined.
        """
        interface = smc.helpers.get_json_template('routed_interface.json')
        interface_ids = [] #store existing node_id to find next open
        
        if int_id is not None: #specific int id requested
            self.interface_id = int_id
        else:
            for node_interface in self.element.json['physicalInterfaces']:
                interface_ids.append(node_interface['physical_interface']['interface_id'])
        
                interface_id = [int(i) for i in interface_ids]  #needed to find max
                self.interface_id = max(interface_id)+1
           
        phys_iface = interface['physical_interface']
        phys_iface['interface_id'] = str(self.interface_id)
        iface = interface['physical_interface']['interfaces'][0]
        iface = iface['single_node_interface']
        iface['address'] = ip
        iface['nicid'] = str(self.interface_id)
        iface['network_value'] = mask
        
        self.element['physicalInterfaces'].append(interface)
        
        self.json = self.element
        return self
        
    def create(self):
        """ Create initial single l3 fw 
            By default currently set interface 0 to be the default management port. 
        """
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
                

class L2FW(object):
    def __init__(self, SMCElement=None):
        pass
    
    
def get_element(SMCElement):
    pass

        
        
        
        