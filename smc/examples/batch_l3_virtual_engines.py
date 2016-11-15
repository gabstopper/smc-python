"""
Example script using smc-python to batch create and configure Layer 3 Virtual Engines.

The prerequisites for running this script is:
- Master Engine instance is created within SMC
- 4 interfaces are created, with the Management interface set to Interface 0.
- Interface 1,2 and 3 are created, but no configuration is provided (no IP addresses, no VLANs).

This script will read in a CSV file and create the Virtual Resources, VLANs on the Master Engine
interfaces, Virtual Firewalls, and Virtual Firewall interfaces will be configured along with zones.

The CSV format is expected to be:

 Interface    VLAN    NAME                        ADDRESS        MASK                CIDR
 1            100     MY_NETWORK_EXTERNAL1        12.12.12.12    255.255.255.252     30
 2            101     MY_NETWORK_DMZ1             1.1.1.1        255.255.255.252     30
 3            102     MY_NETWORK_INTERNAL1        10.10.10.10    255.255.255.252     30

#Interface 1: Zone: 'External'
#Interface 2: Zone: 'DMZ'
#Interface 3: Zone: 'Internal'

In the above example, the last digit in the name field is used in the name the virtual engine ('ve-1') 
and assumes that all names with same digit/s are interface of the same virtual engine.
"""
import re
import csv
from smc import session
from collections import OrderedDict
import smc.actions.search
import smc.elements.network
from smc.core.engines import Layer3VirtualEngine, Engine

import logging
from smc.api.exceptions import SMCException
logging.getLogger()
#logging.basicConfig(level=logging.DEBUG)

master_engine_name = 'master-eng'
csv_filename = '/Users/davidlepage/info.csv'
virtual_intf_offset = 1 #Virtual interface offset based on used MasterEngine interfaces
#Master engine physical interface to zone map
zone_map = {1: 'Web', 
            2: 'App', 
            3: 'Dev'}
#Specify global DNS servers for virtual engines    
dns=['8.8.8.8','8.8.8.9']

if __name__ == '__main__':

    session.login(url='http://172.18.1.150:8082', api_key='EiGpKD4QxlLJ25dbBEp20001')

    #Get zone references
    for idx, zone in zone_map.iteritems():
        result = smc.actions.search.element_href_use_filter(zone, 'interface_zone')
        if result:
            zone_map[idx] = result
        else:
            zone_map[idx] = \
                smc.elements.network.Zone.create(zone).href
    
    #Load Master Engine
    engine = Engine(master_engine_name).load()
    
    engine_info = OrderedDict()
    
    with open(csv_filename, 'rU') as csvfile:
      
        reader = csv.DictReader(csvfile, dialect="excel", 
                                fieldnames=['interface_id', 'vlan_id', 'name',
                                            'address', 'network_value', 'cidr', 'default_gw'])
        previous_engine = 0
        for row in reader:

            current_engine = next(re.finditer(r'\d+$', row.get('name'))).group(0)

            if current_engine != previous_engine:
                previous_engine = current_engine
                virtual_engine_name = 've-'+str(current_engine)
                print "Creating VLANs and Virtual Resources for VE: {}".format(virtual_engine_name) 
                
                #Create virtual resource on the Master Engine
                engine.virtual_resource.create(name=virtual_engine_name, 
                                               vfw_id=current_engine, 
                                               show_master_nic=False)
              
                engine_info[virtual_engine_name] = []
            
            physical_interface_id = int(row.get('interface_id'))    
            virtual_interface_id = physical_interface_id-virtual_intf_offset
            
            #Virtual Engine interface information
            engine_info[virtual_engine_name].append({'interface_id': virtual_interface_id,
                                                     'address': row.get('address'),
                                                     'network_value': row.get('address')+'/'+row.get('cidr'),
                                                     'zone_ref': zone_map.get(physical_interface_id)})    

            result = engine.physical_interface.add_vlan_to_node_interface(
                                                        physical_interface_id,
                                                        row.get('vlan_id'), 
                                                        virtual_mapping=virtual_interface_id, 
                                                        virtual_resource_name=virtual_engine_name)
            
            if result.href:
                print "Successfully created VLAN {}".format(row.get('vlan_id'))
            else:
                print "Failed creating VLAN {}, reason: {}".format(row.get('vlan_id'), result.msg)
                           
        for name, interfaces in engine_info.iteritems():
            try:
                result = Layer3VirtualEngine.create(name, master_engine_name, name, default_nat=False, 
                                                    interfaces=interfaces, dns=dns)        
                print "Success creating virtual engine: %s" % name
    
            except SMCException, reason:
                print "Failed creating virtual engine: {}, reason: {}".format(name, reason)
    
        print "Refreshing policy on Master Engine..."
        for msg in engine.refresh():
            print msg
        
    session.logout()