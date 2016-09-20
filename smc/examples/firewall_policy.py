'''
Firewall Policy example

Create a new Firewall policy, open (lock) the policy, create a rule and save, then delete
a rule by name. 
'''

from smc import session
from smc.elements.policy import FirewallPolicy
from smc.elements.collection import describe_tcp_services, describe_hosts

import logging
logging.getLogger()
logging.basicConfig(level=logging.INFO)

if __name__ == '__main__':
    
    session.login(url='http://172.18.1.150:8082', api_key='EiGpKD4QxlLJ25dbBEp20001')
    
    """ 
    Create a new Firewall Policy using the Firewall Inspection Template
    """
    #policy = FirewallPolicy.create(name='smcpython',
    #                               template='Firewall Inspection Template') 
    
    """
    Load an existing policy
    """                            
    policy = FirewallPolicy('smcpython').load() 
    print "Loaded firewall policy successfully..."
    
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
    Open the policy for editing, create a rule, and save the policy
    """
    myservices = describe_tcp_services(name=['HTTP', 'HTTPS'])
    myservices = [service.href for service in myservices]
    
    mysources = describe_hosts(name=['amazon-linux'])
    mysources = [host.href for host in mysources]
    
    mydestinations = ['any']
    
    policy.open()
    policy.ipv4_rule.create(name='myrule', 
                            sources=mysources,
                            destinations=mydestinations, 
                            services=myservices, 
                            action='permit')
    policy.save()
    
    """
    Delete a rule by name (comment this out to verify rule creation)
    """
    for rule in policy.fw_ipv4_access_rules.all():
        if rule.name == 'myrule':
            rule.delete()
            
    session.logout()
