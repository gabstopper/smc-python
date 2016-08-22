'''
Firewall Policy example

Create a new Firewall policy, open (lock) the policy, create a rule and save, then delete
a rule by name. 
'''

from smc.elements.policy import FirewallPolicy
from smc.api.session import session
import smc.actions.search as search

if __name__ == '__main__':
    
    session.login(url='http://172.18.1.150:8082', api_key='EiGpKD4QxlLJ25dbBEp20001')
    
    """ 
    Create a new Firewall Policy using the Firewall Inspection Template
    """
    policy = FirewallPolicy.create(name='smcpython',
                                   template='Firewall Inspection Template') 
    
    """
    Load an existing policy
    """                            
    policy = FirewallPolicy('smcpython').load() 
    
    """
    View non-detailed version of each configured rule
    """
    for rule in policy.fw_ipv4_access_rules:
            print rule
            
    """
    View details of the rule/s (this can be resource intensive depending on
    how many rules are configured
    """
    for rule in policy.fw_ipv4_access_rules:
            print rule.describe_rule()
    
    """
    Open the policy for editing, create a rule, and save the policy
    """   
    myservices = [v
                  for item in search.element_href_by_batch(['HTTP', 'HTTPS'], 'tcp_service')
                  for k, v in item.iteritems()
                  if v]
    
    mysources = [v
                 for item in search.element_href_by_batch(['foonetwork', 'amazon-linux'])
                 for k, v in item.iteritems()
                 if v]
    
    mydestinations = ['any']
    
    policy.open()
    policy.ipv4_rule.create(name='myrule', 
                            sources=mysources,
                            destinations=mydestinations, 
                            services=myservices, 
                            action='permit')
    policy.save()
    
    """
    Delete a rule by name
    """
    for rule in policy.fw_ipv4_access_rules:
        if rule.name == 'myrule':
            rule.delete()
            
    session.logout()
