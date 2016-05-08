import smc.helpers

class Host(object):
    def __init__(self, name, ip, secondary_ip=[], comment=None):
        self.name = name
        self.ip = ip
        self.secondary_ip = secondary_ip
        self.comment = None
        
    def get_json(self):
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
    def __init__(self, name, members=[]):
        self.name = name
        self.members = members
        
    def get_json(self):
        group = smc.helpers.get_json_template('group.json')
        group['name'] = self.name
        if self.members:
            group['element'] = self.members
        return group

class Router(object):
    def __init__(self, name, address, secondary_ip=[]):
        self.name = name
        self.address = address
        self.secondary_ip = secondary_ip 
        
    def get_json(self):
        router = smc.helpers.get_json_template('router.json')
        router['name'] = self.name
        router['address'] = self.address
        if self.secondary_ip:
            for addr in self.secondary_ip:
                router['secondary'].append(addr)
        return router   

class SingleFW(object):
    def __init__(self, name, mgmt_ip, mgmt_network, dns=None, fw_license=False):
        self.name = name
        self.mgmt_ip = mgmt_ip
        self.mgmt_network = mgmt_network
        self.log_server = None
        self.dns = dns
        self.fw_license = fw_license
    
    def get_json(self):
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
           
        
        
        
        
        
        