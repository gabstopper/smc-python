from smc.policy.policy import Policy
from smc.base.model import Meta, Element
from smc.base.util import find_link_by_name
import smc.actions.search as search

class FileFilteringRule(Element):
    def __init__(self, meta):
        self.meta = meta
    
    @property
    def name(self):
        return self.meta.name if self.meta else None
    
    def create(self):
        pass
    
    def add_after(self):
        pass
    
    def add_before(self):
        pass
    
    def all(self):
        """
        Return all file filtering rules::
        
            for rule in FileFiltering('mypolicy).
        """ 
        return [type(self)(meta=Meta(**rule))
                for rule in search.element_by_href_as_json(self.href)]
        
class FileFilteringPolicy(FileFilteringRule, Policy):
    """ 
    The File Filtering Policy references a specific file based policy for 
    doing additional inspection based on file types. Use the policy 
    parameters to specify how certain files are treated by either threat 
    intelligence feeds,sandbox or by local AV scanning. You can also use 
    this policy to disable threat prevention based on specific files.
    """
    typeof = 'file_filtering_policy'
    
    def __init__(self, name, meta=None):
        Policy.__init__(self, name, meta)
        pass

    @classmethod
    def create(cls):
        pass
    
    def export(self):
        #Not valid on file filtering policy
        pass
    
    @property
    def file_filtering_rules(self):
        href = find_link_by_name('file_filtering_rules', self.link)
        return FileFilteringRule(meta=Meta(href=href))