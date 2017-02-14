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
          needed, calling open() will lock the policy from test_external modifications
          until save() is called.
"""
from smc.base.util import find_link_by_name
from smc.api.exceptions import TaskRunFailed
from smc.base.model import prepared_request
from smc.administration.tasks import task_handler, Task
from smc.base.model import Element

class Policy(Element):
    """ 
    Policy is the base class for all policy types managed by the SMC.
    This base class is not intended to be instantiated directly.
    
    Subclasses should implement create(....) individually as each subclass will likely 
    have different input requirements.
    
    All generic methods that are policy level, such as 'open', 'save', 'force_unlock',
    'export', and 'upload' are encapsulated into this base class.
    """
    def __init__(self, name, meta=None):
        self._name = name #: Name of policy
        self.meta = meta
                                   
    def upload(self, engine, wait_for_finish=True):
        """ 
        Upload policy to specific device. This is an asynchronous call
        that will return a 'follower' link that can be queried to determine 
        the status of the task. 
        
        If wait_for_finish is False, the progress
        href is returned when calling this method. If wait_for_finish is
        True, this generator function will return the new messages as they
        arrive.

        :param engine: name of device to upload policy to
        :param wait_for_finish: whether to wait in a loop until the upload completes
        :return: generator with updates, or follower href if wait_for_finish=False
        """
        element = prepared_request(
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

        :return: :py:class:`smc.api.web.SMCResult` or None if SMC API >= 6.1
        """
        href = find_link_by_name('open', self.link)
        if href:
            return prepared_request(href=href).create()

    def save(self):
        """ Save policy that was modified
        This is only used in SMC API v6.0 and below.

        :return: :py:class:`smc.api.web.SMCResult` or None if SMC API >= 6.1
        """
        href = find_link_by_name('save', self.link)
        if href:
            return prepared_request(href=href).create()

    def force_unlock(self):
        """ Forcibly unlock a locked policy 

        :return: :py:class:`smc.api.web.SMCResult`
        """
        return prepared_request(
                href=find_link_by_name('force_unlock', self.link)).create()
    
    def search_rule(self, search):
        """
        Search a rule for a rule tag or name value
        Result will be the meta data for rule (name, href, type)
        
        Searching for a rule in specific policy::
        
            f = FirewallPolicy(policy)
            search = f.search_rule(searchable)
        
        :param str search: search string
        :return: list rule elements matching criteria
        """
        result = prepared_request(
                        href=find_link_by_name('search_rule', self.link),
                        params={'filter': search}).read()
        if result.json:
            results = _RuleTypeFactory(result.json)
            return results
        else: return []
   
    def search_category_tags_from_element(self):
        pass

def _RuleTypeFactory(meta):
    """
    Temporary
    Need to sort a sensible map for rules that share the same class template
    Maybe nest in child classes
    """
    import inspect
    import smc.policy.rule, smc.policy.rule_nat
    from smc.base.model import Meta
    intf_map = dict((klazz.typeof, klazz) 
                    for i in [smc.policy.rule, smc.policy.rule_nat]
                    for _, klazz in inspect.getmembers(i, inspect.isclass)
                    if hasattr(klazz, 'typeof'))
    
    results = []
    for data in meta:
        if data.get('type').endswith('_ethernet_rule'):
            results.append(intf_map.get('ethernet_rule')(meta=Meta(**data)))
        elif data.get('type').startswith('ips_ipv4_access_rule'):
            results.append(intf_map.get('layer2_ipv4_access_rule')(meta=Meta(**data)))
        else:
            if intf_map.get(data.get('type')): #Some rule types not implemented
                results.append(intf_map.get(data.get('type'))(meta=Meta(**data)))
    return results
    