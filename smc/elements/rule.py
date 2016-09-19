"""
Rule module that handles rule creation and provides a class factory to dispatch
the proper class based on the rule type required (IPv4Rule, IPS Rule, Inspection Rule,
File Filtering Rule, etc)

This is not called directly, but is linked to the Policy class and loading the proper
policy.

Here is an example of how this is referenced and used::

    policy = FirewallPolicy('smcpython').load()
    policy.ipv4_rule.create(name='myrule', 
                            sources=mysources,
                            destinations=mydestinations, 
                            services=myservices, 
                            action='permit')
                            
For rule creation, refer to each 'create' method based on the rule type to understand the
parameters required. However, each class will have a property to refer to a rule class 
object for creation.
"""
import smc.api.common
import smc.actions.search as search
from smc.elements.element import SMCElement

class Rule(object):
    """
    Rule class providing a generic container for any rule type
    along with specific actions such as creating, modifying or
    deleting.
    This base class will hold a limited number of attributes after
    initialization.
    
    Attributes:
    
    :ivar href: href location for the rule
    :ivar name: name of rule
    :ivar type: type of rule
    
    To get the actual rule content, use :py:func:`describe_rule` which
    will retrieve the rule using the rule href and return the correct
    object type.
    
    For example, load a firewall policy and describe all rules::
    
        policy = FirewallPolicy('newpolicy').load()
        for rule in policy.fw_ipv4_access_rules:
            print rule #Is a Rule object
            print rule.describe_rule() #Is an IPv4Rule object
    """
    def __init__(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)
    
    def describe_rule(self):
        if self.type == IPv4Rule.typeof:
            return IPv4Rule(
                    **search.element_by_href_as_json(self.href))
    
    def modify_attribute(self, **kwargs):
        pass
    
    def delete(self):
        return smc.api.common.delete(self.href)
    
    def __repr__(self):
        return "%s(%r)" % (self.__class__, 
                                    'name={}'.format(self.name))
  
class IPv4Rule(object):
    """ 
    Represents an IPv4 Rule in SMC Policy
    Each rule type may have different requirements, although some fields are
    common across all policies such as source and destination. This class is used
    when the policy to create or delete is an ipv4 rule.
    
    Use refresh() to re-retrieve a current list of rules, especially if
    operations need to be performed after adding or removing rules
    
    Attributes:
    
    :ivar name
    :ivar is_disabled: True|False
    :ivar destinations
    :ivar sources
    :ivar services
    :ivar action  
    """
    typeof = 'fw_ipv4_access_rule'
    
    def __init__(self, **kwargs):
        self.name = None
        for k, v in kwargs.iteritems():
            setattr(self, k, v)
    
    def create(self, name, sources, destinations, services, action='', 
               is_disabled=False):
        """ Create a new rule
        
        Sources and Destinations can be one of any valid network element types defined
        in :py:class:smc.elements.element`. 
        
        source=['http://1.1.1.1:8082/elements/network/myelement',
                'http://1.1.1.1:8082/elements/host/myhost'], etc
        
        Services have a similar syntax, provide a list of the href's for the services:
        
        services=['http://1.1.1.1/8082/elements/tcp_service/mytcpservice',
                  'http://1.1.1.1/8082/elements/udp_server/myudpservice'], etc
        
        You can obtain the href for the network and service elements by using the 
        :py:mod:`smc.elements.collection` describe functions such as::
        
            describe_hosts(name=['host1', 'host2'], exact_match=False)
            describe_tcp_services(name=['HTTP', 'HTTPS', 'SSH'])
            
        Sources / Destinations and Services can also take the string value 'any' to
        allow all. For example::
        
            sources=['any']
            
        :param name: name of rule
        :param list source: source/s for rule, names will be looked up to find href
        :param list destination: destinations, names will be looked up to find href
        :param list service: service/s, names will be looked up to find href
        :param str action: allow|continue|discard|refuse|use vpn
        :return: SMCResult
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
                
        return SMCElement(href=self.href,
                          json=rule_values).create()
                          
    def __repr__(self):
        return "%s(%r)" % (self.__class__, 
                                'name={}'.format(self.name))
        
        
class IPv4NATRule(object):
    def __init__(self):
        pass
        
class IPv6Rule(object):
    def __init__(self):
        pass
    
class IPv6NATRule(object):
    def __init__(self):
        pass
    