"""
Rule module that handles each of the different rule types available 
(IPv4Rule, IPS Rule, Inspection Rule, File Filtering Rule, etc)

This is not called directly, but is linked to the Policy class which handles using
the correct class instance based on the policy links.

Here is an example of how this is referenced and used::

    policy = FirewallPolicy('smcpython').load()
    policy.fw_ipv4_access_rules.create(name='myrule', 
                                       sources=mysources,
                                       destinations=mydestinations, 
                                       services=myservices, 
                                       action='permit')
                            
For rule creation, refer to each 'create' method based on the rule type to understand the
parameters required. However, each class will have a property to refer to a rule class 
object for creation.
"""
import smc.actions.search as search
from smc.elements.element import Meta
from smc.api.common import SMCRequest

class IPv4Rule(object):
    """ 
    Represents an IPv4 Rule in SMC Policy
    Each rule type may have different requirements, although some fields are
    common across all policies such as source and destination. This class is used
    when the policy to create or delete is an ipv4 rule.
    
    Use refresh() to re-retrieve a current list of rules, especially if
    operations need to be performed after adding or removing rules
    
    Attributes:
    
    :ivar name: name of rule
    """
    typeof = 'fw_ipv4_access_rule'
    
    def __init__(self, meta=None, **kwargs):
        self.meta = meta
        for k, v in kwargs.iteritems():
            setattr(self, k, v)
    
    @property
    def name(self):
        if self.meta:
            return self.meta.name
        
    @property
    def href(self):
        if self.meta:
            return self.meta.href
        
    def create(self, name, sources, destinations, services, action='', 
               is_disabled=False):
        """ Create a new rule
        
        Access the policy required, load the configuration and add a rule::
        
            for policy in describe_fw_policies():
                if policy.name == 'Datacenter Policy':
                    pol = policy.load()
                    pol.fw_ipv4_access_rules.create('smcpython', 'any', 'any', 'any')
                
        Sources and Destinations can be one of any valid network element types defined
        in :py:class:smc.elements.element`.
        
        Source entries by href:: 
        
            source=['http://1.1.1.1:8082/elements/network/myelement',
                    'http://1.1.1.1:8082/elements/host/myhost'], etc
        
        Services have a similar syntax, provide a list of the href's for the services::
        
            services=['http://1.1.1.1/8082/elements/tcp_service/mytcpservice',
                      'http://1.1.1.1/8082/elements/udp_server/myudpservice'], etc
        
        You can obtain the href for the network and service elements by using the 
        :py:mod:`smc.elements.collection` describe functions such as::
        
            describe_hosts(name=['host1', 'host2'], exact_match=False)
            describe_tcp_services(name=['HTTP', 'HTTPS', 'SSH'])
            
        Sources / Destinations and Services can also take the string value 'any' to
        allow all. For example::
        
            sources='any'
            
        :param name: name of rule
        :param list source: source/s for rule, names will be looked up to find href
        :param list destination: destinations, names will be looked up to find href
        :param list service: service/s, names will be looked up to find href
        :param str action: allow|continue|discard|refuse|use vpn
        :return: :py:class:`smc.api.web.SMCResult`
        """
        rule_values = { 
                'name': name,
                'action': {},
                'sources': {'src': []},
                'destinations': {'dst': []},
                'services': {'service': []},
                'is_disabled': is_disabled }
        
        rule_values.update(action={'action': action,
                                   'connection_tracking_options':{}})

        if 'any' in sources:
            rule_values.update(sources={'any': True})
        else:
            rule_values.update(sources={'src': sources})
        
        if 'any' in destinations:
            rule_values.update(destinations={'any': True})
        else:
            rule_values.update(destinations={'dst': destinations})
            
        if 'any' in services:
            rule_values.update(services={'any': True})
        else:
            rule_values.update(services={'service': services})

        return SMCRequest(href=self.href,
                          json=rule_values).create()
    
    def add_after(self):
        pass
    
    def add_before(self):
        pass
    
    def describe(self):
        return search.element_by_href_as_json(self.href)
    
    def delete(self):
        return SMCRequest(href=self.href).delete()
    
    def all(self):
        """
        Get all IPv4Rules for this policy::
        
            for rule in pol.fw_ipv4_access_rules.all():
                print rule.describe()
            
        :return: list `IPv4Rule`
        """
        rule_lst = search.element_by_href_as_json(self.href)
        rules=[] 
        for rule in rule_lst:
            rules.append(IPv4Rule(meta=Meta(**rule)))
        return rules
                      
    def __repr__(self):
        return "%s(%r)" % (self.__class__, 'name={}'
                           .format(self.name))
        
        
class IPv4NATRule(object):
    """
    Manipulate NAT Rules for relevant policy types.
    
    For example, adding a NAT rule for a layer 3 fw policy::
    
        for policy in describe_fw_policies():
            if policy.name == 'Datacenter Policy':
                pol = policy.load()
                pol.fw_ipv4_nat_rules.create(name='mynatrule', 
                                             sources='any', 
                                             destinations='any', 
                                             services='any',
                                             dynamic_src_nat='10.0.0.245')
    """                                         
    def __init__(self, meta=None, **kwargs):
        self.meta = meta
    
    @property
    def href(self):
        if self.meta:
            return self.meta.href
     
    def create(self, name, sources, destinations, services, 
               dynamic_src_nat=None, max_port=65535, min_port=1024, 
               is_disabled=False):
        """
        Create a NAT rule
        
        :param str name: name of NAT rule
        :param list sources: list of source href's
        :param list destinations: list of destination href's
        :param list services: list of service href's
        :param str dynamic_src_nat: ip of dynamic source nat address
        :param int max_port: max port number for PAT
        :param int min_port: min port number for PAT
        :param boolean is_disabled: whether to disable rule or not
        :return: :py:class:`smc.api.web.SMCResult`
        """
        rule_values = { 
                'name': name,
                'sources': {'src': []},
                'destinations': {'dst': []},
                'services': {'service': []},
                'is_disabled': is_disabled }
        
        if 'any' in sources:
            rule_values.update(sources={'any': True})
        else:
            rule_values.update(sources={'src': sources})
        
        if 'any' in destinations:
            rule_values.update(destinations={'any': True})
        else:
            rule_values.update(destinations={'dst': destinations})
            
        if 'any' in services:
            rule_values.update(services={'any': True})
        else:
            rule_values.update(services={'service': services})
            
        if dynamic_src_nat:
            dyn_nat = {'options': {'dynamic_src_nat':
                                   {'automatic_proxy': True,
                                    'translation_values':
                                        [{'ip_descriptor': dynamic_src_nat,
                                          'max_port': max_port,
                                          'min_port': min_port}]}}}
            rule_values.update(dyn_nat)
        return SMCRequest(href=self.href, json=rule_values).create()

    def describe(self):
        return search.element_by_href_as_json(self.href) 

    def add_before(self):
        pass
    
    def add_after(self):
        pass
          
    def all(self):
        """
        Get all IPv4Rules for this policy
        
        for rule in pol.fw_ipv4_access_rules.all():
            print rule.describe()
            
        :return list `IPv4Rule`
        """
        rule_lst = search.element_by_href_as_json(self.href)
        rules=[] 
        for rule in rule_lst:
            rules.append(IPv4NATRule(meta=Meta(**rule)))
        return rules
    
        
class IPv6Rule(object):
    def __init__(self):
        pass
    
class IPv6NATRule(object):
    def __init__(self):
        pass
    