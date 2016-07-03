'''
Created on Jul 2, 2016

@author: davidlepage
'''
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
        self.is_disabled = False
        self.href = None #base href for policies rule location
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
        return smc.api.common._create(element)
    
    def modify(self):
        pass
       
    def delete(self, element):
        smc.api.common._remove(element)
    
    def refresh(self):
        rules = search.element_by_href_as_json(self.href)
        for rule in rules:
            yield rule    
    
    def rule_element(self, element):
        src_href = smc.search.element_href(element)
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
    :attributes
        :ip4_rules list of existing rules, this holds a list of references for each
        rule, content looks like:
        [{u'href': u'http://172.18.1.150:8082/6.0/elements/fw_policy/226/fw_ipv4_access_rule/2098650', 
        u'type': u'fw_ipv4_access_rule', 
        u'name': u'api rule'}] 
        Use refresh() to re-retrieve a current list of rules, especially if
        operations need to be performed after adding or removing rules
        :actions action options for ipv4 rules    
    """
    def __init__(self):
        Rule.__init__(self)
        self.ipv4_rules = []
        self.actions = ['allow', 'continue', 'discard', 'refuse', 'use_vpn'] 
      
    def create(self, name, source, destination, service, action, 
               is_disabled=False):
        rule_values = { 
                'name': name,
                'action': { "action": '', "connection_tracking_options":{}},
                'sources': {'src': []},
                'destinations': {'dst': []},
                'services': {'service': []},
                'is_disabled': is_disabled }
        rule_values['action']['action'] = action if action in self.actions else '' #continue action
       
        if destination == 'any':
            rule_values['destinations'] = self.any
        else:
            dst = self.rule_element(destination)
            if dst:
                rule_values['destinations']['dst'].append(dst)
            else:
                rule_values['destinations'] = self.none
            
        if source == 'any':
            rule_values['sources'] = self.any
        else:
            src = self.rule_element(source)
            if src:
                rule_values['sources']['src'].append(src)
            else:
                rule_values['sources'] = self.none
                
        if service == 'any':
            rule_values['services'] = self.any
        else:
            svc = self.rule_element(service)
            if svc:
                rule_values['services']['service'].append(svc)
            else:
                rule_values['services'] = self.none
          
        rule_dict = {}
        for header in rule_values.keys():
            rule_dict[header] = rule_values.get(header)
        
        element = SMCElement.factory(json=rule_dict, 
                                     href=self.href)
       
        return super(IPv4Rule, self).create(element)
     
    def modify(self, existing_rule):
        """ Modify existing rule
        :param existing_rule: full json of existing rule 
        """
        pass
        
    def delete(self, name):
        """ Delete ipv4 rule based on the name of the rule
        Note: if a policy has been 'open' for edit, a previous snapshot in time was made so
        queries will result in showing the policy before it was opened. You should save 
        policy before deleting or just delete without opening (which locks policy), modifying,
        then deleting. 
        :param name: name of rule
        """
        self.refresh()
        for rule in self.ipv4_rules:
            if rule.get('name') == name:
                element = SMCElement.factory(href=rule.get('href'))
                self.ipv4_rules.remove(rule)
                return super(IPv4Rule, self).delete(element)

    def refresh(self):
        self.ipv4_rules[:] = []
        for rule in super(IPv4Rule, self).refresh():
            self.ipv4_rules.append(rule)
            
class IPv4NATRule(Rule):
    def __init__(self):
        Rule.__init__(self)
        self.ipv4_nat_rules = []
