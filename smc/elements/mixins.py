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
from smc.elements.util import unicode_to_bytes, find_link_by_name
from smc.actions.tasks import task_handler, Task

class ModifiableMixin(object):
    """
    A class that implements ModifiableMixin can have attribute/values
    modified.
    Mixin takes a key=value pair to modify. The value modified
    can only be of type str, list or dict. In the case of a list,
    the list is replaced, a dict will be updated and a str replaced.
    """
    def modify_attribute(self, **kwargs):
        """
        Modify the attribute / value pair
        
        :param dict kwargs: key=value pair to change      
        :return: :py:class:`smc.api.web.SMCResult`
        """
        if self.href:
            element = search.element_by_href_as_smcresult(self.href)
        if element.json:
            for k, v in kwargs.iteritems():
                target_value = element.json.get(k)
                if isinstance(target_value, dict):
                    element.json[k].update(v)
                elif isinstance(target_value, list):
                    element.json[k] = v
                else: #single key/value
                    element.json.update({k: v})
            return SMCRequest(href=self.meta.href, 
                              json=element.json,
                              etag=element.etag).update()

class ExportableMixin(object):
    """
    Elements that implement this mixin can be exported individually 
    from the SMC. Only non-system related elements can be exported 
    independently. System elements are created by dynamic update packages
    and can only be exported by exporting all elements by type.
    """
    def export(self, filename='element.zip', wait_for_finish=False):
        """
        Export this element
        
        :method: POST
        :param str filename: filename to store exported element
        :param boolean wait_for_finish: wait for update msgs (default: False)
        :return: generator yielding updates on progress, or [] if element cannot
                 be exported due to system element
        """
        href = find_link_by_name('export', self.link)
        if href is not None:
            element = SMCRequest(
                        href=find_link_by_name('export', self.link),
                        filename=filename).create()
            task = task_handler(Task(**element.json), 
                                wait_for_finish=wait_for_finish, 
                                filename=filename)
            return task
        else:
            return []
        
class UnicodeMixin(object):
    """
    Mixin used to stage for supporting python 3. After py2 support is dropped
    then this can be removed. Py2 requires that __str__ returns bytes whereas
    py3 should return unicode. Each py2 supported class will have a __unicode__
    method.
    
    Consider migrating to future module and use their class decorator
    from future.utils import python_2_unicode_compatible
    \@python_2_unicode_compatible
    From: http://python-future.org/what_else.html
    """
    import sys
    if sys.version_info > (3, 0):
        __str__ = lambda x: x.__unicode__()
    else:
        __str__ = lambda x: unicode_to_bytes(unicode(x))