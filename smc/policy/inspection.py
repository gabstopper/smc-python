from smc.policy.policy import Policy

class InspectionRule(object):
   
    def inspection_global_rules(self):
        pass
    
    def inspection_exception_rules(self):
        pass
    
    
class InspectionPolicy(InspectionRule, Policy):
    """
    The Inspection Policy references a specific inspection policy that is a property
    (reference) to either a FirewallPolicy, IPSPolicy or Layer2Policy. This policy
    defines specific characteristics for threat based prevention. 
    In addition, exceptions can be made at this policy level to bypass scanning based
    on the rule properties.
    """
    typeof = 'inspection_template_policy'
    
    def __init__(self, name, meta=None):
        Policy.__init__(self, name)
        pass
    
    def export(self):
        #Not valid for inspection policy
        pass
    
    def upload(self):
        #Not valid for inspection policy
        pass