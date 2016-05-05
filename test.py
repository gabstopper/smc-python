#!/usr/bin/python
import smc
from pprint import pprint
import time
import logging

logger = logging.getLogger(__name__)

smc.login('http://172.18.1.150:8082', 'EiGpKD4QxlLJ25dbBEp20001')


#Example of using a search filter 
#Response is a json record with a reference link to the object
#smc.get_element_by_href(href) gets the record directly

#Search for group named (Skype Servers)
mygroup = smc.filter_by_type('group', 'Skype Servers')
if mygroup:
    pprint(smc.get_element_by_href(mygroup['href']))
 
#Search for single_fw instance named vmware-fw   
myfw = smc.filter_by_type('single_fw', 'vmware-fw')
if myfw:
    pprint(smc.get_element_by_href(myfw['href']))

#Search for host named ami
myhost = smc.filter_by_type('host', 'ami')
if myhost:
    pprint(smc.get_element_by_href(myhost['href']))    

#Search by top level element if element type is not known
myobject = smc.filter_by_element('myelement')


'''
#Creating/removing a host record. Validation is done based on IP address.
smc.create_host('ami', '1.1.1.2')
smc.remove_host('ami')

smc.create_host('a', 'a.b.c.d') #Should fail, not valid IP
smc.remove_host('ami2') #should fail if host doesn't exist
'''

'''
#Create group and add members
smc.create_group('group_with_no_members')
smc.create_host('ami', '1.1.1.1')
smc.create_host('ami2', '2.2.2.2')
smc.create_group('anewgroup', ['ami','ami2'])
'''
    
'''
#Example of creating a group record. If members is included, each member href 
#needs to be validated or warning will be issued that members can't be added
smc.create_group('mygroup')
smc.create_group('mygroup', ['member1','member2','member3'])
'''

'''
#Example of creating a single_fw instance. method signature is:
#smc.create_single_fw(name, IP (mgmt), network (mgmt), dns=None, fw_license=None)
#If DNS and fw_license are provided, DNS is added to fw and an attempt is made to attach an available license if available
smc.create_single_fw('lepage', '172.18.1.5', '172.18.1.0/24', dns='5.5.5.5', fw_license=True)
time.sleep(5)
smc.remove_single_fw('lepage')
'''


'''
#Get available dynamic licenses
print "License: %s" % smc.get_dynamic_license()
'''

smc.logout()

