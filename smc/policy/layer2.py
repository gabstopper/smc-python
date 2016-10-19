from smc.policy.policy import Policy

class Layer2Rule(object):
    def __init__(self):
        pass
    
    def layer2_ipv4_access_rules(self):
        pass
    
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
    