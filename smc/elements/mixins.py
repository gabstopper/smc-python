"""
Modify an internal attribute for classes that inherit this mixin. This 
implies that the particular element supports being modified and has
a meta attribute.
        
Example of modifying a top level engine attribute. In this case, disable
a setting, enable antivirus and mcafee gti::
            
    engine.modify_attribute(passive_discard_mode=False)
    engine.modify_attribute(antivirus={'antivirus_enabled':True, 
                                       'virus_log_level':'stored'})
    engine.modify_attribute(gti_settings={'file_reputation_context': 
                                          'gti_cloud_only'})
                                          
Example of enabling an existing interfaces to accept VPN traffic::
        
        for gateway in engine.internal_gateway.internal_endpoint.all():
            if gateway.name.startswith('50.50.50.50'):
                gateway.modify_attribute(nat_t=True,enabled=True)
                
To find attributes of a particular element, obtain the context of that
element and call it's describe() method. The easiest way to obtain the
context is by using a :py:class:`smc.elements.collection` describe function.
For example::

    for host in describe_hosts():
        print host.describe()  
"""
from smc.actions import search
from smc.api.common import SMCRequest

class ModifiableMixin(object):
    """ 
    Mixin takes a key=value pair to modify. The value modified
    can only be of type str, list or dict. In the case of a list,
    the list is replaced, a dict will be updated and a str replaced.
    A class that implements ModifiableMixin must have an attribute
    or property 'href' which will have the location of the element.
            
    :return: :py:class:`smc.api.web.SMCResult`
    """
    def modify_attribute(self, **kwargs):
        # First we need to retrieve the updated full json for
        # the requested element. Each modifiable element will
        # have meta data that will have the element href. Once
        # retrieved, modify only top level key/value pairs no
        # recursion) and update dict, list or str values.
        element = self.load_attributes()
        if element.json:
            for k, v in kwargs.iteritems():
                target_value = element.json.get(k)
                if isinstance(target_value, dict):
                    element.json[k].update(v)
                elif isinstance(target_value, list):
                    #element.json[k].extend(v)
                    element.json[k] = v
                else: #single key/value
                    element.json.update({k: v})
            return SMCRequest(href=self.meta.href, 
                              json=element.json,
                              etag=element.etag).update()

    def load_attributes(self):
        if self.href:
            return search.element_by_href_as_smcresult(self.href)
        #return search.element_by_href_as_smcresult(self.meta.href)
