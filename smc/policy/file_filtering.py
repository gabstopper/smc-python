from smc.policy.policy import Policy
from smc.base.model import Meta, prepared_request
from smc.base.util import find_link_by_name
import smc.actions.search as search

class FileRule(object):
    def __init__(self, meta):
        self.meta = meta
    
    @property
    def name(self):
        return self.meta.name
    
    @property
    def href(self):
        return self.meta.href
    
    def create(self, name):
        pass
    
    def describe(self):
        return search.element_by_href_as_json(self.href)
    
    def delete(self):
        return prepared_request(href=self.href).delete()
    
    def all(self):
        return [FileRule(meta=Meta(**rule))
                for rule in search.element_by_href_as_json(self.href)]
       
    def __unicode__(self):
        return u'{0}(name={1})'.format(self.__class__.__name__, self.name)
  
    def __repr__(self):
        return repr(unicode(self))
    
class FileFilteringRule(object):
    def __init__(self):
        pass
    
    @property
    def file_filtering_rules(self):
        href = find_link_by_name('file_filtering_rules', self.link)
        return FileRule(meta=Meta(href=href))
    
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