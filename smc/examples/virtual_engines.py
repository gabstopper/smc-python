'''
Example of automating the creation of a L3 Master Engine or Master Engine Cluster,
configuring interfaces and creating the virtual engines.
'''
from smc import session
from smc.core.engine import Engine
from smc.core.engines import Layer3VirtualEngine, MasterEngineCluster, MasterEngine

def create_single_master_engine():
    """
    Create a single master engine instance example
    :raises: `smc.api.exceptions.CreateEngineFailed`
    """
    MasterEngine.create('api-master',
                        mgmt_ip='1.1.1.1',
                        mgmt_netmask='1.1.1.0/24',
                        master_type='firewall', 
                        domain_server_address=['8.8.4.4', '7.7.7.7'])
    #Returns smc.core.engine.Engine instance
    
def create_cluster_master_engine():
    """
    Create the master engine cluster with 2 nodes example
    
    Nodes data structure is:
        [{'address': '',            #ip address of node
          'network_value': '',      #network/cidr
          'nodeid': 1}]             #node identifier, 1, 2, 3, etc
  
    :raises: `smc.api.exceptions.CreateEngineFailed`
    """
    MasterEngineCluster.create(
                            name='engine-cluster',
                            master_type='firewall', 
                            macaddress='22:22:22:22:22:22', 
                            nodes=[{'address':'5.5.5.2', 
                                    'network_value':'5.5.5.0/24', 
                                    'nodeid':1},
                                   {'address':'5.5.5.3', 
                                    'network_value':'5.5.5.0/24', 
                                    'nodeid':2}])
    #Returns smc.core.engine.Engine instance

def delete(ve, master_engine):
    #Delete easily. Just load the engine resource and call delete. Delete VE's first.
    #All elements descend from smc.base.model.Element
    #Note: Most operations will return an instance of smc.api.web.SMCResult so you 
    #can view the return attributes if necessary.
    ve = Engine('layer3-ve').load()
    ve.delete()
    
    master = Engine('engine-cluster').load()
    master.delete()
    
if __name__ == '__main__':
    session.login(url='https://172.18.1.25:8082', api_key='avUj6vFZTUSZ7sr8mNsP0001', timeout=120,
                  verify=False)
    
    create_cluster_master_engine()
    
    #Load the existing master engine named 'master-eng'
    engine = Engine('engine-cluster').load()
    
    #Create a virtual resource named 've-1' with virtual firewall id 1
    #vfw_id should increment by 1 for each new virtual firewall under the
    #same Master Engine
    print engine.virtual_resource.create(name='ve-1', vfw_id=1)
    
    #Example of allocating the entire physical interface to a virtual engine
    #Create the interface mapping to virtual resource 've-1'
    print engine.physical_interface.add(interface_id=1,
                                        virtual_mapping=0,
                                        virtual_resource_name='ve-1')
    
    #Example of allocating a VLAN to a virtual engine on a specific physical
    #interface.
    #engine.physical_interface.add_vlan_to_node_interface(
    #                                                    interface_id=1,
    #                                                    vlan_id=100, 
    #                                                    virtual_mapping=0, 
    #                                                    virtual_resource_name='ve-1')
    
    #Virtual Engine interface mappings start at 0 (interface_id) regardless of the 
    #real interface index on the master engine. The interface_id for the virtual engine
    #will start it's numbering at index 0 and increment by 1 for each interface allocated.
    #The interface_id field correlates to the "Virtual Engine Interface ID" property of
    #the master engine's physical interface.
    #:raises: `smc.api.exceptions.CreateEngineFailed` 
    Layer3VirtualEngine.create('layer3-ve', 
                                master_engine='engine-cluster', 
                                virtual_resource='ve-1',
                                interfaces=[{'interface_id': 0,
                                             'address': '1.1.1.1',
                                             'network_value': '1.1.1.0/24'}])
    #Returns smc.core.engine.Layer3VirtualEngine instance
    
    #delete()
    session.logout()