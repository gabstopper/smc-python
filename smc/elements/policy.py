import smc.actions.search as search
import smc.api.common
from smc.api.web import SMCException
from smc.elements.element import SMCElement

class Policy(object):
    def __init__(self, name):
        self.name = name
        self.policy_cfg = None
        self.policy_type = None
        self.policy_template = None
        self.file_filtering_policy = None
        self.inspection_policy = None
        self.actions = []
        self.ipv4_rules = []
        self.ipv6_rules = []
        self.ipv4_nat_rules = []
        self.ipv6_nat_rules = []
        self.links = []
        
    def load(self):
        base_policy = search.element_info_as_json(self.name)
        if base_policy:
            self.policy_cfg = search.element_by_href_as_json(base_policy.get('href'))
            if self.policy_cfg:
                self.file_filtering_policy = self.policy_cfg.get('file_filtering_policy')
                self.inspection_policy = self.policy_cfg.get('inspection_policy')
                self.policy_template = self.policy_cfg.get('template')
                self.links.extend(self.policy_cfg.get('link'))
                self.actions = [entry.get('rel') for entry in self.policy_cfg.get('link') \
                                if entry.get('rel') != 'self']
        
        if not base_policy and not self.policy_cfg:
            raise SMCException("Policy does not exist: %s" % self.name)
        return self            
    
    def create(self):
        pass
           
    def ipv4_rules_href(self):
        return self._load_rule_href('fw_ipv4_access_rules')
                
    def ipv6_rules_href(self):
        return self._load_rule_href('fw_ipv6_access_rules')
                      
    def ipv4_nat_rules_href(self):
        return self._load_rule_href('fw_ipv4_nat_rules')
        
    def ipv6_nat_rules_href(self):
        return self._load_rule_href('fw_ipv6_nat_rules')
    
    def load_ipv4_rules(self):
        rules = search.element_by_href_as_json(self.ipv4_rules_href())
        for rule in rules:
            self.ipv4_rules.append(rule)
                       
    def upload(self):
        pass
    
    def open(self):
        self.commit(self._element('open'))
    
    def save(self):
        self.commit(self._element('save'))
        
    def force_unlock(self):
        self.commit(self._element('force_unlock'))

    def export(self):
        self.commit(self._element('export'))
                
    def search_rule(self, parameter):
        pass
    
    def create_ipv4_rule(self, source, dest, service, action):
        rule = Rule(source, dest, service, action)
        
        element = SMCElement()
        element.name = 'rule'
        element.href = self.ipv4_rules_href()
        element.json = rule.create()
        self.commit(element)
    
    def commit(self, element):
        smc.api.common._create(element)
    
    def _load_rule_href(self, rule_type):
        try:
            rule = [entry.get('href') for entry in self.links \
                    if entry.get('rel') == rule_type]
        except StopIteration:
            pass
        
        if rule:
            return rule.pop()
    
    def _element(self, link):
        link_href = [entry.get('href') for entry in self.links \
                       if entry.get('rel') == link]
        element = SMCElement()
        element.href = link_href.pop()
        return element
        
    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)


class Rule(object):
    def __init__(self, source, dest, service, action, rank=None):
        self.rule = {}
        self.source = source
        self.destination = dest
        self.service = service
        self.action = action
        self.is_disabled = False
        self.rank = rank
        self.any = {'any': True}
        
    def load(self):
        pass
    
    def destinations(self):
        if self.destination.lower() == 'any':
            return self.any
        else:
            dst = {'dst': []}
            element = search.element_href(self.destination)
            if element:
                dst.get('dst').append(element)
            else:
                print "element not found: %s" % self.destination #TODO: create
            return dst    
           
    def sources(self):
        if self.source.lower() == 'any':
            return self.any
        else:
            src = {'src': []}
            element = search.element_href(self.source)
            if element:
                src.get('src').append(element)
            else:
                print "src element not found: %s" % self.source #TODO: create
            return src
            
    def is_disabled(self):
        pass    
    
    def actions(self):
        if self.action in ['allow', 'continue', 'discard', 'refuse']:
            return self.action
        else:
            return ''   #continue action
            
    def authentication_options(self):
        pass
    
    def options(self):
        pass
    
    def rank(self):
        pass
    
    def services(self):
        if self.service.lower() == 'any':
            return self.any
        else:
            service = {'service': []}
            element = search.element_href(self.service)
            if element:
                service.get('service').append(element)
            else:
                print "service element not found: %s" % self.service #TODO: create
            return service
        

    def create(self):
        rule = {
           "action":
           {
            "action": self.actions(),
            "connection_tracking_options":
            {
            }
           },
            "destinations":
                self.destinations()
           ,
            "services":
                self.services()
           ,
            "sources":
                self.sources()
        }
        return rule
    
    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)    
        
        
                