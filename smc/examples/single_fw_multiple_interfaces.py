"""
Example of creating a single firewall with multiple interface types.
Once interfaces are defined, add routes that are needed. Note that to add a default route,
use the 0.0.0.0/0 address as the gateway address.
Specify a policy to upload once the single FW instance has made the initial contact. This will
be queued and kick off once the contact is complete.
Generate the initial contact information for sg-reconfigure on the virtual or appliance.
"""
from smc import session
from smc.core.engines import Layer3Firewall

if __name__ == '__main__':
    session.login(url='http://172.18.1.25:8082',
                  api_key='4366TuolHMJp3nHaUeF60001')

    # Create base engine specifying management IP info and management
    # interface number
    engine = Layer3Firewall.create('myfirewall',
                                   mgmt_ip='172.18.1.160',
                                   mgmt_network='172.18.1.0/24',
                                   mgmt_interface=0,
                                   domain_server_address=['8.8.8.8'])

    if engine:
        print "Successfully created Layer 3 firewall, adding interfaces.."

    # Create a new physical interface for single firewall
    engine.physical_interface.add_single_node_interface(interface_id=1,
                                                        address='1.1.1.1',
                                                        network_value='1.1.1.0/24')

    # Create a second interface using VLANs and assign IP info
    engine.physical_interface.add_vlan_to_single_node_interface(interface_id=2,
                                                                address='2.2.2.2',
                                                                network_value='2.2.2.0/24',
                                                                vlan_id=2)
    engine.physical_interface.add_vlan_to_single_node_interface(
        2, '3.3.3.3', '3.3.3.0/24', 3)
    engine.physical_interface.add_vlan_to_single_node_interface(
        2, '4.4.4.4', '4.4.4.0/24', 4)
    engine.physical_interface.add_vlan_to_single_node_interface(
        2, '5.5.5.5', '5.5.5.0/24', 5)

    # Add route information, mapping to interface is automatic
    engine.add_route('172.18.1.1', '192.168.1.0/24')
    engine.add_route('2.2.2.1', '192.168.2.0/24')
    engine.add_route('172.18.1.254', '0.0.0.0/0')  # default gateway

    # Fire off a task to queue a policy upload once device is initialized
    engine.upload(policy='Amazon Cloud')

    # Get initial contact information for sg-reconfigure
    for node in engine.nodes:
        print node.initial_contact(enable_ssh=True)

    session.logout()
