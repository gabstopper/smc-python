#!/usr/bin/python
import smc
import logging
from pprint import pprint

logger = logging.getLogger(__name__)

smc.login('http://172.18.1.150:8082', 'EiGpKD4QxlLJ25dbBEp20001')

#smc.web_api.login('http://172.18.1.150:8082', 'EiGpKD4QxlLJ25dbBEp20001')

#Example of using a search filter 
#Response is a json record with a reference link to the object
#smc.get_element_by_href(href) gets the record directly

#Search for group named (Skype Servers)
mygroup = smc.search.get_element('Skype Servers', 'group')
if mygroup:
    pprint(smc.get_element_by_href(mygroup['href']))
 
#Search for single_fw instance named vmware-fw   
myfw = smc.search.get_element('myfwname', 'single_fw')
if myfw:
    pprint(smc.get_element_by_href(myfw['href']))

#Search for host named ami
myhost = smc.search.get_element('ami', 'host')
if myhost:
    pprint(smc.get_element_by_href(myhost['href']))    

#Search by top level element if element type is not known
myobject = smc.search.get_element('myelement')


#Creating/removing a host record. Validation is done based on IP address.
smc.create.host('ami', '1.1.1.2')
smc.remove.element('ami')   #remove element with name 'ami', no element type filter

smc.create.host('a', 'a.b.c.d') #Should fail, not valid IP
smc.remove.element('ami2') #should fail if host doesn't exist
smc.remove.element('somenetwork', 'network')


'''
#Create group and add members
smc.create.group('group_with_no_members')
smc.create.host('ami', '1.1.1.1')
smc.create.host('ami2', '2.2.2.2')
smc.create.group('anewgroup', ['ami','ami2'])
'''
    
'''
#Example of creating a group record. If members is included, each member href 
#needs to be validated or warning will be issued that members can't be added
smc.create.group('mygroup')
smc.create.group('mygroup', ['member1','member2','member3'])
'''

'''
#Example of creating a single_fw instance. method signature is:
#smc.create_single_fw(name, IP (mgmt), network (mgmt), dns=None, fw_license=None)
#If DNS and fw_license are provided, DNS is added to fw and an attempt is made to attach an available license if available
smc.create.single_fw('lepage', '172.18.1.5', '172.18.1.0/24', dns='5.5.5.5', fw_license=True)
time.sleep(5)
smc.remove.element('myfw')    #without filter
smc.remove.element('myfw', 'single_fw')    #with filter
'''


'''
#Get available dynamic licenses
print "License: %s" % smc.get_dynamic_license()
'''

smc.logout()

