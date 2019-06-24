'''
Example of creating a Master Engine and 8 virtual engines. Each virtual engine is mapped to 2
Master Engine interfaces and a unique VLAN.

This example is based on SMC 6.5.x
'''


from smc.core.engines import MasterEngine, Layer3VirtualEngine
from smc.elements.network import Router, Network
from smc import session, set_stream_logger
set_stream_logger()

session.login(url='http://172.18.1.26:8082', api_key='kKphtsbQKjjfHR7amodA0001')
    
    
master_engine = MasterEngine.create(name='master', master_type='firewall', mgmt_ip='172.18.1.1', mgmt_network='172.18.1.0/24', mgmt_interface=0)

# Create top level interface on master engine with a zone name
master_engine.physical_interface.add(interface_id=1, zone_ref='Northbound')
master_engine.physical_interface.add(interface_id=2, zone_ref='Southbound')

# First create the Virtual Resources (Customer 1 - 8)
for vr in range(1, 9):
    master_engine.virtual_resource.create(name='Customer {}'.format(vr), vfw_id=vr)

# Add the VLANs to the interfaces and attach the Virtual Resources
for vr in range(1, 9):
    master_engine.physical_interface.add_layer3_vlan_interface(interface_id=1, vlan_id=vr, virtual_mapping=1, virtual_resource_name='Customer {}'.format(vr))
    master_engine.physical_interface.add_layer3_vlan_interface(interface_id=2, vlan_id=vr, virtual_mapping=2, virtual_resource_name='Customer {}'.format(vr))

# Router object used for default route
router = Router.update_or_create(name='southbound', address='10.1.2.254', comment='virtual engine gateway')

# Now create the Virtual Firewalls for each customer and set interface information
# VirtualEngine interface numbering starts at interface 1!
for vr in range(1, 9):
    virtual_engine = Layer3VirtualEngine.create(name='Customer {}'.format(vr), master_engine='master', 
            virtual_resource='Customer {}'.format(vr), outgoing_intf=1,
            interfaces=[{'interface_id': 1,
                         'address': '10.1.1.1', 
                         'network_value': '10.1.1.0/24',  
                         'zone_ref': ''},
                        {'interface_id': 2,
                         'address': '10.1.2.1',
                         'network_value': '10.1.2.0/24',
                         'zone_ref': ''}])
    # Add default route
    interface_1 = virtual_engine.routing.get(2)
    interface_1.add_static_route(gateway=Router('southbound'), destination=[Network('Any network')])
    