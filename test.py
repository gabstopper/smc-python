import logging
import time
from pprint import pprint

import smc.api.web as web_api
import smc.actions.search
from smc.elements.policy import Policy

logger = logging.getLogger(__name__)
logging.getLogger()
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s')

web_api.session.login('http://172.18.1.150:8082', 'EiGpKD4QxlLJ25dbBEp20001')

#pprint(web_api.session.get_all_entry_points())

policy = Policy('api-test-policy').load()
policy.open()
policy.create_ipv4_rule('ami', 'any', 'ssh', 'allow')
policy.save()
#policy.export()
#policy.load_ipv4_rules()

pprint(policy.links)
#for rule in policy.ipv4_rules:
#    pprint(smc.search.element_by_href_as_json(rule.get('href')))

#pprint(policy.ipv4_rules)

#policy.load_ipv6_rules()
#policy.load_ipv4_nat_rules()
#policy.load_ipv6_nat_rules()

#pprint(vars(policy))

'''
#Test create hosts, networks, group and routers   
smc.create.host('aidan', '23.23.23.23')   
smc.create.group('lepagegroup', comment='test comments - see this')
smc.create.network('hostbitsnotinnetwork', '1.2.3.0/255.255.252.0')
smc.create.network('goodnetwork', '1.2.0.0/255.255.252.0')
smc.create.network('networkwithcidr', '1.3.0.0/24', 'created by api tool')
smc.create.router('gatewayrouter', '5.5.5.5')

smc.remove.element('aidan')
smc.remove.element('lepagegroup')
    
    
#Test l3route creation
smc.create.l3route('myfw7', '192.18.1.80', 'Any network', 0) #Unknown host
smc.create.l3route('myfw4', '192.18.1.100', 'Any network', 0) #Unknown gw
smc.create.l3route('myfw4', '192.18.1.100', 'Any2 network', 0) #Unknown network
smc.create.l3route('myfw4', '172.18.1.80', 'Any network', 0) #Good
  
    
#Test single_fw, add interfaces and routes
smc.remove.element('myfw')
time.sleep(5)
#Create the objects required for routes
smc.create.router('172.18.1.250', '172.18.1.250')   #name, #ip
smc.create.router('172.20.1.250', '172.20.1.250')   #name, #ip
smc.create.network('192.168.3.0/24', '192.168.3.0/24') #name, #ip  
smc.create.single_fw('myfw', '172.18.1.254', '172.18.1.0/24', dns='5.5.5.5', fw_license=True)
smc.create.l3interface('myfw', '10.10.0.1', '10.10.0.0/16', 3)
smc.create.l3interface('myfw', '172.20.1.254', '172.20.1.0/255.255.255.0', 6)
smc.create.l3route('myfw', '172.18.1.250', 'Any network', 0) #Next hop, dest network, interface
smc.create.l3route('myfw', '172.20.1.250', '192.168.3.0/24', 6)
'''
web_api.session.logout()

