from smc.policy.policy import Policy
from smc.elements.util import find_link_by_name

class Layer2Rule(object):
    def __init__(self):
        pass
    
    def layer2_ipv4_access_rules(self):
        href = find_link_by_name('layer2_ipv4_access_rules', self.link)
    
    def layer2_ipv6_access_rules(self):
        pass
    
    def layer2_ethernet_rules(self):
        pass
    
class Layer2Policy(Layer2Rule, Policy):
    typeof = 'layer2_policy'
    
    def __init__(self, name, meta=None):
        Policy.__init__(self, name, meta)
        pass
    
    def create(self):
        pass

class Layer2TemplatePolicy(Layer2Rule, Policy):
    typeof = 'layer2_template_policy'
   
    def __init__(self, name, meta=None):
        Policy.__init__(self, name, meta)
        pass
    