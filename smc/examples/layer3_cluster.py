"""
Example of how to create a 3 node cluster in SMC

Before any operations can be done on the SMC, you must first call login, and remember to call logout
after complete::
    
    smc.api.web.session.login('http://172.18.1.150:8082', 'EiGpKD4QxlLJ25dbBEp20001')
    smc.api.web.session.logout()
    
This is a Layer 3 Firewall cluster with the following configuration::
    
    :param name: Name of cluster engine
    :param cluster_virtual: IP address of CVI
    :param cluster_mask: Netmask of CVI
    :param cluster_nic: Which physical nic id to use
    :param macaddress: Packet Dispatch clustering requires a MAC address
    :param nodes: Node addresses to add to cluster. Each address/netmask combination is added as a singular node
    :param dns: Optional DNS settings for engine
    :param zone_ref: Optional zone to assign to physical interface

See :class:`smc.elements.engines.FirewallCluster` for more details.
    
Once the Cluster has been created, initial contact is done to retrieve the initial configuration required
to fully bootstrap each engine. A filename is specified to which to save the engine.cfg, but it can also be
printed out by retrieving result.content (SMCResult).

SMC-python is configured to leverage the python logging module. To obtain logger messages, uncomment the following
line below and set the logging level (recommend ERROR unless troubleshooting)::

    logging.basicConfig(level=logging.ERROR)
"""

from smc.api.session import session
from smc.elements.engines import FirewallCluster
from smc.elements.element import zone_helper

import logging
from smc.elements.interfaces import PhysicalInterface
logging.getLogger()
#logging.basicConfig(level=logging.ERROR)

if __name__ == '__main__':
    
    session.login(url='http://172.18.1.150:8082', api_key='EiGpKD4QxlLJ25dbBEp20001')
    
    #Create the Firewall Cluster
    engine = FirewallCluster.create(name='mycluster', 
                                    cluster_virtual='1.1.1.1', 
                                    cluster_mask='1.1.1.0/24',
                                    cluster_nic=0,
                                    macaddress='02:02:02:02:02:02',
                                    nodes=[{'address': '1.1.1.2', 'network_value': '1.1.1.0/24', 'nodeid':1},
                                           {'address': '1.1.1.3', 'network_value': '1.1.1.0/24', 'nodeid':2},
                                           {'address': '1.1.1.4', 'network_value': '1.1.1.0/24', 'nodeid':3}],
                                    domain_server_address=['1.1.1.1'], 
                                    zone_ref=zone_helper('Internal'))
    
    physical = PhysicalInterface(1)
    physical.add_cluster_virtual_interface(cluster_virtual='5.5.5.1', 
                                           cluster_mask='5.5.5.0/24', 
                                           macaddress='02:03:03:03:03:03', 
                                           nodes=[{'address':'5.5.5.2', 'network_value':'5.5.5.0/24', 'nodeid':1},
                                                  {'address':'5.5.5.3', 'network_value':'5.5.5.0/24', 'nodeid':2},
                                                  {'address':'5.5.5.4', 'network_value':'5.5.5.0/24', 'nodeid':3}],
                                           zone_ref=zone_helper('Heartbeat'))
    
    engine.add_physical_interfaces(physical.data)
    
    physical = PhysicalInterface(2)
    physical.add_cluster_virtual_interface(cluster_virtual='10.10.10.1', 
                                           cluster_mask='10.10.10.0/24', 
                                           macaddress='02:04:04:04:04:04', 
                                           nodes=[{'address':'10.10.10.2', 'network_value':'10.10.10.0/24', 'nodeid':1},
                                                  {'address':'10.10.10.3', 'network_value':'10.10.10.0/24', 'nodeid':2},
                                                  {'address':'10.10.10.4', 'network_value':'10.10.10.0/24', 'nodeid':3}],
                                           zone_ref=zone_helper('External'))
    
    engine.add_physical_interfaces(physical.data)
    
    engine.add_route('10.10.10.254', '0.0.0.0/0')
    engine.add_route('5.5.5.100', '192.168.3.0/24')
    
    
    #Create initial configuration for each node
    for node in engine.node_names():
        result = engine.initial_contact(node, enable_ssh=True, filename=node+'.cfg')
        if result:
            print "Successfully wrote initial configuration for node: {}, to file: {}".format( \
                        node, node+'.cfg')
        
        
    session.logout()