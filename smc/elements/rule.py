"""
Module that represents rules within the SMC.
These classes are linked by composition references from the subclasses of Policy 
:class:`FirewallPolicy`, :class:`InspectionPolicy`, :class:`FileFilteringPolicy`, etc)

This is called indirectly from Policy subclass for manipulation of rules for 
specific engine types. 

For example, modifying rules for a FirewallPolicy::

    policy = FirewallPolicy('mypolicy').load()
    policy.ipv4_rule.create('newrule', ['mysource1', 'mysource2'], ['mydest1', 'mydest2'], ['myservice'], action)
    
"""
import smc.api.common
import smc.actions.search as search
from smc.elements.element import SMCElement

class Rule(object):
    """
    Represents the base class for all rules, ipv4, ipv6, ethernet, inspection, 
    and file filtering.
    Functions provided should be called from inheriting class to perform the create, 
    modify or delete operations.
    
    All attributes are used to calculate the rule with exception of rules_href which 
    will hold the href to where the rule type exists. For operations like create/delete, 
    this is required to be an SMCElement.href attribute
    """ 
    def __init__(self):
        self.rank = 0 
        self.is_disabled = False #: Is rule disabled (boolean)
        self.href = None #: Base href for rule list location, can be called to retrieve all rules
        self.rules = [] #: Placeholder container for rule list, call self.href to fill list
        self.any = {'any': True} 
        self.none = {'none': True}
               
    @classmethod    
    def load(cls, rule):
        return "reserved for loading rule to modify"
        
    def authentication_options(self):
        pass
    
    def options(self):
        pass
    
    def rank(self):
        pass
    
    def create(self, element):
        """ Create element convenience method """
        return smc.api.common.create(element)
    
    def modify(self):
        pass
       
    def delete(self, name):
        """ Delete rule by name. This requires that the rule name matches.
        
        :param name: Name of rule to delete
        """
        for rule in search.element_by_href_as_json(self.href):
            if rule.get('name') == name:
                smc.api.common.delete(name)
                  
    def fetch_element(self, name):
        """ Fetch element by name """
        src_href = smc.search.element_href(name)
        if src_href:
            return src_href
            
    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)


class IPv4Rule(Rule):
    """ 
    Represents an IPv4 Rule in SMC Policy
    Each rule type may have different requirements, although some fields are
    common across all policies such as source and destination. This class is used
    when the policy to create or delete is an ipv4 rule.
    
    Use refresh() to re-retrieve a current list of rules, especially if
    operations need to be performed after adding or removing rules  
    """
    def __init__(self):
        Rule.__init__(self)
        self.actions = ['allow', 'continue', 'discard', 'refuse', 'use_vpn'] #: Allowed rule actions
      
    def create(self, name, sources, destinations, services, action, 
               is_disabled=False):
        """ Create a new rule
        
        :param name: name of rule
        :param source: source/s for rule, names will be looked up to find href
        :type source: list
        :param destination: destinations, names will be looked up to find href
        :type destination: list
        :param service: service/s, names will be looked up to find href
        :type service: list
        :param action: actions, see self.actions
        :return: SMCResult, if success, href attr will include new href to rule
        """
        rule_values = { 
                'name': name,
                'action': { "action": '', "connection_tracking_options":{}},
                'sources': {'src': []},
                'destinations': {'dst': []},
                'services': {'service': []},
                'is_disabled': is_disabled }
        
        rule_values['action']['action'] = action if action in self.actions else '' #continue action
        
        for source in sources:
            if source.lower() == 'any':
                rule_values['sources'] = self.any
            else:
                href = self.fetch_element(source)
                if href:
                    rule_values['sources']['src'].append(href)
        
        for destination in destinations:
            if destination.lower() == 'any':
                rule_values['destinations'] = self.any
            else:
                href = self.fetch_element(destination)
                if href:
                    rule_values['destinations']['dst'].append(href)
        
        for service in services:
            if service.lower() == 'any':
                rule_values['services'] = self.any
            else:
                href = self.fetch_element(service)
                if href:
                    rule_values['services']['service'].append(href)
                    
        element = SMCElement(json=rule_values, 
                             href=self.href)
       
        return super(IPv4Rule, self).create(element)
    
    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)
        
        
class IPv4NATRule(Rule):
    def __init__(self):
        Rule.__init__(self)
        
class IPv6Rule(Rule):
    def __init__(self):
        Rule.__init__(self)
        
class IPv6NATRule(Rule):
    def __init__(self):
        Rule.__init__(self)
        