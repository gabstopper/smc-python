"""
Access Rights provides an interface to Access Control Lists defined
on the SMC and optionally applied to elements such as engines. 
"""

from smc.base.model import Element, ElementFactory

class AccessControlList(Element):
    """
    A permission represents an access control list applied to the
    engine. The access control list will have 'granted elements' 
    that represent the elements that apply to this permission. This
    provides a way to provide specific administrator access to a
    specific engine.
    """
    typeof = 'access_control_list'
    
    def __init__(self, name, meta=None):
        super(AccessControlList, self).__init__(name, meta)
        pass
   
    @property
    def _granted_element(self):
        return self.data.get('granted_element')
    
    def granted_element(self):
        """
        Elements associated to this permission. This will be the specific
        object as produced by ElementFactory. If a specific class exists
        it is returned, otherwise type will be :py:class:`smc.base.model.Element`
        
        :return: Element class deriving from :py:class:`smc.base.model.Element`
        """
        return [ElementFactory(e) for e in self._granted_element]
    
    @property
    def comment(self):
        return self.data.get('comment')
    
    def add(self, value):
        pass