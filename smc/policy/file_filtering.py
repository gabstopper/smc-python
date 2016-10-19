from smc.policy.policy import Policy

class FileFilteringRule(object):
    def __init__(self):
        pass
    
    def file_filtering_rules(self):
        pass
    
class FileFilteringPolicy(Policy):
    """ 
    The File Filtering Policy references a specific file based policy for 
    doing additional inspection based on file types. Use the policy parameters 
    to specify how certain files are treated by either threat intelligence feeds,
    sandbox or by local AV scanning. You can also use this policy to disable 
    threat prevention based on specific files.
    """
    typeof = 'file_filtering_policy'
    
    def __init__(self, name, meta):
        Policy.__init__(self, name, meta)
        pass

    @classmethod
    def create(cls):
        pass
    