'''
Firewall Policy example

Create a new Firewall policy, open (lock) the policy, create a rule and save, then delete
a rule by name. 
'''
from smc import session
from smc.policy.layer3 import FirewallPolicy
from smc.elements.element import Host
from smc.elements.collection import describe_tcp_service

import logging
logging.getLogger()
logging.basicConfig(level=logging.INFO)

if __name__ == '__main__':
    
    session.login(url='http://172.18.1.25:8082', api_key='4366TuolHMJp3nHaUeF60001')
    
    """ 
    Create a new Firewall Policy using the Firewall Inspection Template
    """
    FirewallPolicy.create(name='smcpython',
                          template='Firewall Inspection Template') 
    
    """
    Get an existing policy
    """                            
    policy = FirewallPolicy('smcpython')
    
    """
    Open the policy for editing, create a rule, and save the policy
    """
    myservices = describe_tcp_service(name=['HTTP', 'HTTPS'])
    myservices = [service.href for service in myservices]
    
    host = Host.create(name='amazon-linux-host', address='192.168.1.5')
    mysources = [host.href]
    
    mydestinations = ['any']
    
    policy.fw_ipv4_access_rules.create(name='mynewrule', 
                                       sources=mysources, 
                                       destinations=mydestinations, 
                                       services=myservices,
                                       action='permit')
    
    """
    View a metadata version of each configured rule
    """
    for rule in policy.fw_ipv4_access_rules.all():
        print rule.name
            
    """
    View details of the rule/s (this can be resource intensive depending on
    how many rules are configured
    """
    for rule in policy.fw_ipv4_access_rules.all():
        print rule.describe()
    
    """
    Delete a rule by name (comment this out to verify rule creation)
    """
    #for rule in policy.fw_ipv4_access_rules.all():
    #    if rule.name == 'myrule':
    #        rule.delete()
            
    session.logout()
