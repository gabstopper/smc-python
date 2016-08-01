
import smc.api.web
from smc.elements.engines import Layer3Firewall
from smc.elements.interfaces import PhysicalInterface

if __name__ == '__main__':
    smc.api.web.session.login('http://172.18.1.150:8082', 'EiGpKD4QxlLJ25dbBEp20001')
    
    #Create base engine specifying management IP info and management interface number
    engine = Layer3Firewall.create('myfirewall',
                                   mgmt_ip='172.18.1.160',
                                   mgmt_network='172.18.1.0/24',
                                   mgmt_interface=0,
                                   dns=['8.8.8.8'])
    
    if engine:
        print "Successfully created Layer 3 firewall, adding interfaces.."
        
    #Create a new physical interface for single firewall
    physical = PhysicalInterface(1)
    physical.add_single_node_interface('1.1.1.1', '1.1.1.0/24')
    engine.add_physical_interfaces(physical.data)
    
    #Create a second interface using VLANs and assign IP info
    physical = PhysicalInterface(2)
    physical.add_single_node_interface_to_vlan('2.2.2.2', '2.2.2.0/24', 2)
    physical.add_single_node_interface_to_vlan('3.3.3.3', '3.3.3.0/24', 3)
    physical.add_single_node_interface_to_vlan('4.4.4.4', '4.4.4.0/24', 4)
    physical.add_single_node_interface_to_vlan('5.5.5.5', '5.5.5.0/24', 5)
    engine.add_physical_interfaces(physical.data)
    
    #Add route information, mapping to interface is automatic
    engine.add_route('172.18.1.1', '192.168.1.0/24')
    engine.add_route('2.2.2.1', '192.168.2.0/24')
    engine.add_route('172.18.1.254', '0.0.0.0/0') #default gateway
    
    #Fire off a task to queue a policy upload once device is initialized
    engine.upload(policy='Layer 3 Router Policy')
    
    #Get initial contact information for sg-reconfigure
    print engine.initial_contact('myfirewall', enable_ssh=True)
    
    smc.api.web.session.logout()