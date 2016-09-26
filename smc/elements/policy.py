"""
Policy module represents the classes required to obtaining and manipulating policies within the SMC.

Policy is the abstract base class for all policy subclasses such as :class:`FirewallPolicy`, :class:`InspectionPolicy`, 
and :class:`FileFilteringPolicy`. 
Each policy type should first be loaded before changes can be made. 

To load an existing policy type::

    FirewallPolicy('existing_policy_by_name').load()
    
To create a new policy, use::

    FirewallPolicy.create('newpolicy', 'layer3_fw_template')
    FirewallPolicy('newpolicy').load()
    
Example rule creation::

    policy = FirewallPolicy('newpolicy').load()
    policy.open()
    policy.ipv4_rule.create(name='myrule', 
                            sources=mysources,
                            destinations=mydestinations, 
                            services=myservices, 
                            action='permit')
    policy.save()

.. note:: It is not required to call open() if simple operations are being performed. 
          If longer running operations are needed, calling open() will lock the policy from external modifications
          until save() is called.

Example rule deletion::

    policy = FirewallPolicy('newpolicy').load()
    for rule in policy.fw_ipv4_access_rules:
        if rule.name == 'myrule':
            rule.delete()
"""

from abc import ABCMeta, abstractmethod
import smc.actions.search as search
from smc.elements.util import find_link_by_name
from smc.api.exceptions import SMCException, CreatePolicyFailed, TaskRunFailed
from smc.elements.element import SMCElement, Meta
from smc.elements.rule import IPv4Rule, IPv4NATRule, IPv6Rule, IPv6NATRule
from smc.actions.tasks import task_handler, Task

class Policy(object):
    """ 
    Policy is an abstract base class for all policy types managed by the SMC.
    This base class is not intended to be instantiated directly and thus has two
    abstract methods, load() and create().
    
    Subclasses should implement create(....) individually as each subclass will likely 
    have different input requirements.
    
    All generic methods that are policy level, such as 'open', 'save', 'force_unlock',
    'export', and 'upload' are encapsulated into this base class.
    """
    __metaclass__ = ABCMeta
    
    def __init__(self, name):
        self.name = name #: Name of policy
    
    @abstractmethod    
    def load(self):
        """ Load top level policy settings for selected policy
        Called via super from inheriting subclass
        
        :return: self
        """
        base_policy = search.element_info_as_json(self.name)
        if base_policy:
            self.json = search.element_by_href_as_json(base_policy.get('href'))
            return self
        else:
            raise SMCException("Policy does not exist: %s" % self.name)
        return self            

    @abstractmethod
    def create(self):
        """ 
        Implementation should be provided by the subclass
       
        For example::
        
            FirewallPolicy.create('mypolicy', ....)

        Each policy type have slightly different requirements for referencing adjacent
        policies or required policy references.
         
        To find existing policies or templates, use::
        
            smc.search.inspection.policies(), 
            smc.search.file_filtering_policies(), etc.
        """
        pass
                             
    def upload(self, device, 
               wait_for_finish=True):
        """ 
        Upload policy to specific device. This is an asynchronous call
        that will return a 'follower' link that can be queried to determine 
        the status of the task. 
        
        If wait_for_finish is False, the progress
        href is returned when calling this method. If wait_for_finish is
        True, this generator function will return the new messages as they
        arrive.
        
        :method: POST
        :param device: name of device to upload policy to
        :param wait_for_finish: whether to wait in a loop until the upload completes
        :return: generator with updates, or follower href if wait_for_finish=False
        """
        element = SMCElement(
                    href=find_link_by_name('upload', self.link),
                    params={'filter': device}).create()
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
        
        :method: GET
        :return: SMCResult, href set to location if success, msg attr set if fail
        """
        return SMCElement(
                href=find_link_by_name('open', self.link)).create()
    
    def save(self):
        """ Save policy that was modified 
        
        :method: POST
        :return: SMCResult, href set to location if success, msg attr set if fail
        """
        return SMCElement(
                href=find_link_by_name('save', self.link)).create()
        
    def force_unlock(self):
        """ Forcibly unlock a locked policy 
        
        :method: POST
        :return: SMCResult, success unless msg attr set
        """
        return SMCElement(
                href=find_link_by_name('force_unlock', self.link)).create()

    def export(self, filename='policy_export.zip',wait_for_finish=True):
        """ Export the policy
        
        :method: POST
        :param wait_for_finish: wait for the async process to finish or not
        :param filename: specifying the filename indicates export should be downloaded
        :return: None if success and file downloaded indicated. SMCResult with msg attr
                 set upon failure
        :raises: :py:class:`smc.api.exceptions.TaskRunFailed`
        """
        element = SMCElement(
                    href=find_link_by_name('export', self.link)).create()
        
        task = task_handler(Task(**element.json), 
                            wait_for_finish=wait_for_finish, 
                            filename=filename)
        return task
    
    def search_rule(self, parameter):
        pass

class FirewallPolicy(Policy):
    """ 
    This subclass represents a FirewallPolicy installed on layer 3 
    devices. Layer 3 FW's support either ipv4 or ipv6 rules. 
    
    They also have NAT rules and reference to an Inspection and
    File Filtering Policy.
    
    Attributes:
    
    :ivar template: which policy template is used
    :ivar file_filtering_policy: mapped file filtering policy
    :ivar inspection_policy: mapping inspection policy
    
    Instance Resources:
    
    :ivar fw_ipv4_access_rules: :py:class:`IPv4Rule` reference
    :ivar fw_ipv4_nat_rules: :py:class:`IPv4NATRule` reference
    :ivar fw_ipv6_access_rules: :py:class:`IPv6Rule` reference
    :ivar fw_ipv6_nat_rules: :py:class:`IPv6NATRule` reference
    
    :param name: name of firewall policy
    :return: self
    """
    typeof = 'fw_policy'
    
    def __init__(self, name, meta=None):
        Policy.__init__(self, name)
        self.name = name
    
    def load(self):
        """ 
        Load the policy specified::
        
            FirewallPolicy('mypolicy').load()
        
        :return: FirewallPolicy
        """    
        super(FirewallPolicy, self).load()
        return self
    
    @classmethod
    def create(cls, name, template):
        """ 
        Create Firewall Policy. Template policy is required for the
        policy. The template policy parameter should be the href of the
        template entry as obtained from the SMC API.
        
        This policy will then inherit the Inspection and File Filtering
        policy from that template.
        Existing policies and templates are retrievable from describe methods, 
        such as::
        
            import smc.elements.collection
            for policy in describe_fw_policies():
                mypolicy = policy.load()
                
        Find the FW template href for a rule by using smc.elements.collection::
        
            for template in describe_fw_template_policies():
                print template
                ....
        
        :mathod: POST
        :param str name: name of policy
        :param str template: href of the FW template to base policy on
        :return: SMCResult with href attribute set with location of new policy
        
        To use after successful creation, call::
        
            FirewallPolicy('newpolicy').load()
        """
        policy = {'name': name,
                  'template': template}
        policy_href = search.element_entry_point(cls.typeof)
        
        result = SMCElement(href=policy_href, json=policy).create()
        if result.href:
            return FirewallPolicy(name).load()
        else:
            raise CreatePolicyFailed('Failed to load firewall policy: {}'.format(
                                        result.msg))
    
    @property
    def fw_ipv4_access_rules(self):
        """
        IPv4 rule entry point
        
        :return: :py:class:`IPv4Rule`
        """
        href=find_link_by_name('fw_ipv4_access_rules', self.link)
        return IPv4Rule(meta=Meta(
                            name=None, href=href, type=self.typeof))

    @property
    def fw_ipv4_nat_rules(self):
        """
        IPv4NAT Rule entry point
        
        :return: :py:class: `IPv4NATRule`
        """
        href=find_link_by_name('fw_ipv4_nat_rules', self.link)
        return IPv4NATRule(meta=Meta(
                            name=None, href=href, type=self.typeof))
        
    @property
    def fw_ipv6_access_rules(self):
        """
        IPv6 Rule entry point
        
        :return: :py:class: `IPv6Rule`
        """
        href=find_link_by_name('fw_ipv6_access_rules', self.link)
        return IPv6Rule(meta=Meta(
                            name=None, href=href, type=self.typeof))
    
    @property
    def fw_ipv6_nat_rules(self):
        """
        IPv6NAT Rule entry point
        
        :return: :py:class:`IPv6NATRule`
        """
        href=find_link_by_name('fw_ipv6_nat_rules', self.link)
        return IPv6NATRule(meta=Meta(
                            name=None, href=href, type=self.typeof)) 
    
    @property
    def href(self):
        return find_link_by_name('self', self.link)
    
    @property
    def link(self):
        if hasattr(self, 'json'):
            return self.json.get('link')
    
    @property
    def file_filtering_policy(self):
        return search.element_by_href_as_json(
                    self.json.get('file_filtering_policy')).get('name')
    
    @property
    def inspection_policy(self):
        return search.element_by_href_as_json(
                    self.json.get('inspection_policy')).get('name')
    
    @property
    def template(self):
        return search.element_by_href_as_json(
                    self.json.get('template')).get('name')
    
    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, "name={}"\
                           .format(self.name))
        
class InspectionPolicy(Policy):
    """
    The Inspection Policy references a specific inspection policy that is a property
    (reference) to either a FirewallPolicy, IPSPolicy or Layer2Policy. This policy
    defines specific characteristics for threat based prevention. 
    In addition, exceptions can be made at this policy level to bypass scanning based
    on the rule properties.
    """
    def __init__(self, name, meta=None):
        Policy.__init__(self, name)
        print "Inspection Policy"
    
    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, "name={}"\
                           .format(self.name))
        
class FileFilteringPolicy(Policy):
    """ 
    The File Filtering Policy references a specific file based policy for 
    doing additional inspection based on file types. Use the policy parameters 
    to specify how certain files are treated by either threat intelligence feeds,
    sandbox or by local AV scanning. You can also use this policy to disable 
    threat prevention based on specific files.
    """
    def __init__(self, name):
        Policy.__init__(self, name)
        
