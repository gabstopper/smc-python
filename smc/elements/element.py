import smc.helpers

class SMCElement(object):
    def __init__(self, json):
        self.json = json

        
class Host(object):
    def __init__(self):
        self.name = None
        self.ip = None
        self.secondary_ip = None
        self.comment = None
    
    def create(self):
        host = smc.helpers.get_json_template('host.json')
        host['name'] = self.name
        host['address'] = self.ip
        if self.comment:
            host['comment'] = self.comment
        if self.secondary_ip:
            for addr in self.secondary_ip:
                host['secondary'].append(addr)
        return host 
    
    
class Group(object):
    def __init__(self):
        self.name = None
        self.members = None
        self.comment = None
    
    def create(self):
        group = smc.helpers.get_json_template('group.json')
        group['name'] = self.name
        if self.members:
            group['element'] = self.members
        if self.comment:
            group['comment'] = self.comment
        return group


class Router(object):
    def __init__(self):
        self.name = None
        self.address = None
        self.secondary_ip = None 
    
    def create(self):
        router = smc.helpers.get_json_template('router.json')
        router['name'] = self.name
        router['address'] = self.address
        if self.secondary_ip:
            for addr in self.secondary_ip:
                router['secondary'].append(addr)
        return router   
    

class Network(object):
    def __init__(self):
        self.name = None
        self.ip4_network = None
        self.comment = None
    
    def create(self):
        network = smc.helpers.get_json_template('network.json')
        network['name'] = self.name
        network['ipv4_network'] = self.ip4_network
        if self.comment:
            network['comment'] = self.comment
        return network

        
class SingleFW(object):
    def __init__(self, SMCElement=None):
        self.name = None
        self.mgmt_ip = None
        self.mgmt_network = None
        self.log_server = None
        self.dns = None
        self.fw_license = None
        self.element = SMCElement    #existing json for modification/add
    
    def add_interface(self, ip, mask, int_id=None):
        """ Add physical interface to firewall
            Args: 
                * ip: address of interface
                * mask: in cidr format
                * int_id (optional): id for interface
        """
        interface = smc.helpers.get_json_template('routed_interface.json')
        interface_ids = [] #store existing node_id to find next open
        
        for node_interface in self.element.json['physicalInterfaces']:
            interface_ids.append(node_interface['physical_interface']['interface_id'])
        interface_id = [int(i) for i in interface_ids]  #needed to find max
        interface_id = max(interface_id)+1
        #print "Next available interface is: %s" % interface_id

        phys_iface = interface['physical_interface']
        phys_iface['interface_id'] = str(interface_id)
        iface = interface['physical_interface']['interfaces'][0]
        iface = iface['single_node_interface']
        iface['address'] = ip
        iface['nicid'] = str(interface_id)
        iface['network_value'] = mask
        
        self.element.json['physicalInterfaces'].append(interface)
        
        return self.element.json
        
    def create(self):
        single_fw = smc.helpers.get_json_template('single_fw.json')
        
        for k,v in single_fw.iteritems():    
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
        return single_fw
       

class L2FW(object):
    def __init__(self, SMCElement=None):
        pass
    
    
def get_element(SMCElement):
    pass

        
        
        
        