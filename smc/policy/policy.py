"""
Policy module represents the classes required to obtaining and manipulating 
policies within the SMC.

Policy is the top level base class for all policy subclasses such as 
:py:class:`smc.policy.layer3.FirewallPolicy`,
:py:class:`smc.policy.layer2.Layer2Policy`,
:py:class:`smc.policy.ips.IPSPolicy`,
:py:class:`smc.policy.inspection.InspectionPolicy`,
:py:class:`smc.policy.file_filtering.FileFilteringPolicy` 

Policy represents actions that are common to all policy types, however for
options that are not possible in a policy type, the method is overridden to
return None. For example, 'upload' is not called on a template policy, but 
instead on the policy referencing that template. Therefore 'upload' is 
overidden.

.. note:: It is not required to call open() and save() on SMC API >= 6.1. It is 
          also optional on earlier versions but if longer running operations are 
          needed, calling open() will lock the policy from external modifications
          until save() is called.
"""

import smc.actions.search as search
from smc.elements.util import find_link_by_name, bytes_to_unicode
from smc.api.exceptions import TaskRunFailed
from smc.elements.element import ElementLocator
from smc.actions.tasks import task_handler, Task
from smc.api.common import SMCRequest
from smc.elements.mixins import ExportableMixin, UnicodeMixin

class Policy(UnicodeMixin, ExportableMixin):
    """ 
    Policy is the base class for all policy types managed by the SMC.
    This base class is not intended to be instantiated directly.
    
    Subclasses should implement create(....) individually as each subclass will likely 
    have different input requirements.
    
    All generic methods that are policy level, such as 'open', 'save', 'force_unlock',
    'export', and 'upload' are encapsulated into this base class.
    """
    href = ElementLocator()

    def __init__(self, name, meta=None):
        self._name = name #: Name of policy
        self.meta = meta

    @property
    def name(self):
        return bytes_to_unicode(self._name)

    @property
    def link(self):
        result = search.element_by_href_as_json(self.href)
        return result.get('link')

    @classmethod
    def _create(cls):
        return SMCRequest(
                    href=search.element_entry_point(cls.typeof),
                    json=cls.json).create()

    def delete(self):
        return SMCRequest(self.href).delete()

    def describe(self):
        return search.element_by_href_as_json(self.href)
                                     
    def upload(self, engine, wait_for_finish=True):
        """ 
        Upload policy to specific device. This is an asynchronous call
        that will return a 'follower' link that can be queried to determine 
        the status of the task. 
        
        If wait_for_finish is False, the progress
        href is returned when calling this method. If wait_for_finish is
        True, this generator function will return the new messages as they
        arrive.
        
        :method: POST
        :param engine: name of device to upload policy to
        :param wait_for_finish: whether to wait in a loop until the upload completes
        :return: generator with updates, or follower href if wait_for_finish=False
        """
        element = SMCRequest(
                    href=find_link_by_name('upload', self.link),
                    params={'filter': engine}).create()
        if not element.json:
            raise TaskRunFailed("Upload task failed with message: {}"
                                .format(element.msg))
        return task_handler(Task(**element.json), 
                            wait_for_finish=wait_for_finish)

    def open(self):
        """ 
        Open policy locks the current policy, Use when making multiple
        edits that may require more time. Simple create or deleting elements
        generally can be done without locking via open.
        This is only used in SMC API 6.0 and below
        
        :method: GET
        :return: :py:class:`smc.api.web.SMCResult` or None if SMC API >= 6.1
        """
        href = find_link_by_name('open', self.link)
        if href:
            return SMCRequest(href=href).create()
    
    def save(self):
        """ Save policy that was modified
        This is only used in SMC API v6.0 and below.
        
        :method: POST
        :return: :py:class:`smc.api.web.SMCResult` or None if SMC API >= 6.1
        """
        href = find_link_by_name('save', self.link)
        if href:
            return SMCRequest(href=href).create()
    
    def force_unlock(self):
        """ Forcibly unlock a locked policy 
        
        :method: POST
        :return: :py:class:`smc.api.web.SMCResult`
        """
        print "Force unlock link: %s" % find_link_by_name('force_unlock', self.link)
        return SMCRequest(
                href=find_link_by_name('force_unlock', self.link)).create()
    
    def search_rule(self, parameter):
        pass
   
    def search_category_tags_from_element(self):
        pass
    
    def __unicode__(self):
        return u'{0}(name={1})'.format(self.__class__.__name__, self.name)

    def __repr__(self):
        return repr(unicode(self))
