import logging
import time
from pprint import pprint
import smc

logger = logging.getLogger(__name__)

smc.session.login('http://172.18.1.150:8082', 'EiGpKD4QxlLJ25dbBEp20001')

print smc.actions.search.get_element('api-fw')

smc.remove.element('dlepage')

#smc.login('http://172.18.1.150:8082', 'EiGpKD4QxlLJ25dbBEp20001')
#smc.search.get_element('david')

#smc.web_api.login('http://172.18.1.150:8082', 'EiGpKD4QxlLJ25dbBEp20001')

#Example of using a search filter 
#Response is a json record with a reference link to the object
#smc.get_element_by_href(href) gets the record directly


#Create group and add members
smc.create.group('group_with_no_members')
smc.create.host('ami', '1.1.1.1')
smc.create.host('ami2', '2.2.2.2')
smc.create.group('anewgroup', ['ami','ami2'])

    

#Example of creating a group record. If members is included, each member href 
#needs to be validated or warning will be issued that members can't be added
smc.create.group('mygroup')
smc.create.group('mygroup', ['member1','member2','member3'])

#Example of creating a single_fw instance. method signature is:
#smc.create_single_fw(name, IP (mgmt), network (mgmt), dns=None, fw_license=None)
#If DNS and fw_license are provided, DNS is added to fw and an attempt is made to attach an available license if available
smc.create.single_fw('myfw', '172.18.1.5', '172.18.1.0/24', dns='5.5.5.5', fw_license=True)
#time.sleep(5)
smc.remove.element('myfw')    #without filter
smc.remove.element('myfw', 'single_fw')    #with filter


smc.session.logout()

