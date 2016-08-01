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
from collections import OrderedDict
import smc.api.web
import smc.elements.element
from smc.elements.interfaces import PhysicalInterface
from smc.elements.engines import Node, Layer3VirtualEngine

import logging
logging.getLogger()
#logging.basicConfig(level=logging.DEBUG)

master_engine_name = 'master-eng'
csv_filename = '/Users/davidlepage/info.csv'
virtual_intf_offset = 1 #Virtual interface offset based on used MasterEngine interfaces
#Master engine physical interface to zone map
zone_map = {1: 'Web', 
            2: 'App', 
            3: 'Dev'}    

if __name__ == '__main__':

    smc.api.web.session.login('http://172.18.1.150:8082', 'EiGpKD4QxlLJ25dbBEp20001')

    #Get zone references
    for idx, zone in zone_map.iteritems():
        result = smc.search.element_href_use_filter(zone, 'interface_zone')
        if result:
            zone_map[idx] = result
        else:
            zone_map[idx] = \
                smc.elements.element.Zone(zone).create().href
    
    #Load Master Engine
    engine = Node(master_engine_name).load()
    
    engine_info = OrderedDict()
    
    with open(csv_filename, 'rU') as csvfile:
      
        reader = csv.DictReader(csvfile, dialect="excel", 
                                fieldnames=['interface_id', 'vlan_id', 'name',
                                            'ipaddress', 'netmask', 'cidr'])
        previous_engine = 0
        for row in reader:

            current_engine = next(re.finditer(r'\d+$', row.get('name'))).group(0)

            if current_engine != previous_engine:
                previous_engine = current_engine
                virtual_engine_name = 've-'+str(current_engine)
                print "Creating VLANs and Virtual Resources for VE: %s" % virtual_engine_name 
                
                #Create virtual resource on the Master Engine
                print engine.virtual_resource_add(virtual_engine_name, vfw_id=current_engine,
                                            show_master_nic=False)
                
                engine_info[virtual_engine_name] = []
            
            physical_interface_id = int(row.get('interface_id'))    
            virtual_interface_id = physical_interface_id-virtual_intf_offset
            
            #Virtual Engine interface information
            engine_info[virtual_engine_name].append({'interface_id': virtual_interface_id,
                                                     'ipaddress': row.get('ipaddress'),
                                                     'mask': row.get('ipaddress')+'/'+row.get('cidr'),
                                                     'zone': zone_map.get(physical_interface_id)})    
            #print "engine info: %s" % engine_info
            #Create and add VLANs to Master Engine and assign the virtual engine name
            #result = engine.physical_interface_vlan_add(interface_id=physical_interface_id, 
            #                                            vlan_id=row.get('vlan_id'),
            #                                            virtual_mapping=virtual_interface_id,
            #                                            virtual_resource_name=virtual_engine_name)
            physical = PhysicalInterface(physical_interface_id)
            physical.add_vlan(row.get('vlan_id'), 
                              virtual_mapping=virtual_interface_id, 
                              virtual_resource_name=virtual_engine_name)

            result = engine.add_physical_interfaces(physical.data)
            
            if result.href:
                print "Successfully created VLAN %s" % (row.get('vlan_id'))
            else:
                print "Failed creating VLAN %s, reason: %s" % (row.get('vlan_id'), result.msg)
            
                
        for name, interfaces in engine_info.iteritems():
            result = Layer3VirtualEngine.create(name, master_engine_name, name, default_nat=False, 
                                                interfaces=interfaces)
            if result.href:
                print "Success creating virtual engine: %s" % name
            else:
                print "Failed creating virtual engine: %s, message: %s" % (name, result.msg)

        print "Refreshing policy on Master Engine..."
        for msg in engine.refresh():
            print msg
        
    smc.api.web.session.logout()