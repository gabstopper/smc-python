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
    policy.ipv4_rule.create('api1', 'host-test', 'smi', 'any', 'allow')
    policy.ipv4_rule.create('api2', 'ami', 'home-network', 'any', 'discard')
    policy.ipv4_rule.create('api3', 'ami', 'any', 'any', 'refuse')
    policy.save()

.. note:: It is not required to call open() if simple operations are being performed. 
          If longer running operations are needed, calling open() will lock the policy from external modifications
          until save() is called.

Example rule deletion::

    policy = FirewallPolicy('newpolicy').load()
    policy.ipv4_rule.delete('api3')
"""

import re
from abc import ABCMeta, abstractmethod
import smc.actions.search as search
import smc.api.common
from smc.api.web import SMCException
from smc.elements.element import SMCElement
from smc.elements.rule import IPv4Rule, IPv4NATRule, IPv6Rule, IPv6NATRule

cleanr = re.compile('<.*?>')

class Policy(object):
    """ 
    Policy is an abstract base class for all policy types managed by the SMC.
    This base class is not intended to be instantiated directly and thus has two
    abstract methods, load() and create().
    
    Subclasses should implement create(....) individually as each subclass will likely 
    have different input requirements.
    
    All generic functions that are policy level, such as 'open', 'save', 'force_unlock',
    'export', and 'upload' are encapsulated into this base class.
    """
    __metaclass__ = ABCMeta
    
    def __init__(self, name):
        self.name = name #: Name of policy
        self.policy_type = None #: FirewallPolicy, Layer2Firewall, IPS
        self.policy_template = None #: Which policy template is used by this policy
        self.file_filtering_policy = None #: Which file filtering policy is used
        self.inspection_policy = None #: Which inspection policy is used
        self.links = []
    
    @abstractmethod    
    def load(self):
        """ Load top level policy settings for selected policy
        Called via super from inheriting subclass
        
        :return: self
        """
        base_policy = search.element_info_as_json(self.name)
        if base_policy:
            policy_cfg = search.element_by_href_as_json(base_policy.get('href'))
            if policy_cfg:
                self.policy_type = base_policy.get('type')
                self.file_filtering_policy = \
                    search.element_by_href_as_json(policy_cfg.get('file_filtering_policy'))
                self.inspection_policy = \
                    search.element_by_href_as_json(policy_cfg.get('inspection_policy'))
                self.policy_template = \
                    search.element_by_href_as_json(policy_cfg.get('template'))
                self.links.extend(policy_cfg.get('link'))
        else:
            raise SMCException("Policy does not exist: %s" % self.name)
        return self            

    @abstractmethod
    def create(self):
        """ 
        Implementation should be provided by the subclass
       
        For example::
        
            FirewallPolicy.create('mypolicy', ....)
            FirewallPolicy('mypolicy').load()
        
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
        href is returned when calling this function. If wait_for_finish is
        True, this generator function will return the new messages as they
        arrive.
        
        :method: POST
        :param device: name of device to upload policy to
        :param wait_for_finish: whether to wait in a loop until the upload completes
        :return: generator with updates, or follower href if wait_for_finish=False
        """
        element = SMCElement(href=self._load_href('upload'),
                             params={'filter': device}).create()
        if not element.msg:
            return smc.api.common.async_handler(element.json.get('follower'), 
                                                wait_for_finish=wait_for_finish)
        else: 
            return [element]

    def open(self):
        """ 
        Open policy locks the current policy, Use when making multiple
        edits that may require more time. Simple create or deleting elements
        generally can be done without locking via open.
        
        :method: GET
        :return: SMCResult, href set to location if success, msg attr set if fail
        """
        return SMCElement(href=self._load_href('open')).create()
    
    def save(self):
        """ Save policy that was modified 
        
        :method: POST
        :return: SMCResult, href set to location if success, msg attr set if fail
        """
        return SMCElement(href=self._load_href('save')).create()
        
    def force_unlock(self):
        """ Forcibly unlock a locked policy 
        
        :method: POST
        :return: SMCResult, success unless msg attr set
        """
        return SMCElement(href=self._load_href('force_unlock')).create()

    def export(self, wait_for_finish=True, filename='policy_export.zip'):
        """ Export the policy
        
        :method: POST
        :param wait_for_finish: wait for the async process to finish or not
        :param filename: specifying the filename indicates export should be downloaded
        :return: None if success and file downloaded indicated. SMCResult with msg attr
                 set upon failure
        """
        element = SMCElement(href=self._load_href('export')).create()
        if not element.msg: #no error
            href = next(smc.api.common.async_handler(element.json.get('follower'), 
                                                         display_msg=False))
                    
            return smc.api.common.fetch_content_as_file(href, filename)
        else: 
            return [element]
                
    def search_rule(self, parameter):
        pass
    
    def _load_href(self, rule_type):
        """ 
        Used by subclasses to retrieve the entry point for 
        the rule href's. All links for top level policy are stored
        in self.links. An example rule_type would be: 
        fw_ipv4_access_rules, fw_ipv6_access_rules, etc
        
        :param rule_type: href for given rule type
        :return: type of rule href
        """
        rule = [entry.get('href') for entry in self.links \
                if entry.get('rel') == rule_type]      
        if rule:
            return rule.pop()

    def __str__(self):
        return 'Policy Name: {}\nPolicy Type: {}\nPolicy Template: {}\n' \
               'Inspection Policy: {}\nFile Filtering Policy: {}' \
               .format(self.name,
                       self.policy_type,
                       self.policy_template.get('name'),
                       self.inspection_policy.get('name'),
                       self.file_filtering_policy.get('name'))

    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)

class FirewallPolicy(Policy):
    """ 
    This subclass represents a FirewallPolicy installed on layer 3 
    devices. Layer 3 FW's support either ipv4 or ipv6 rules. 
    
    They also have NAT rules and reference to an Inspection and
    File Filtering Policy.
    
    :param name: name of firewall policy
    :return: self
    """
    def __init__(self, name):
        Policy.__init__(self, name)
        self.ipv4_rule = IPv4Rule() #: Reference to IPv4Rule class
        self.ipv4_nat_rule = IPv4NATRule() #: Reference to IPv4NATRule class
        self.ipv6_rule = IPv6Rule() #: Reference to IPv6Rule class
        self.ipv6_nat_rule = IPv6NATRule() #: Reference to IPv6NATRule class
    
    def load(self):
        """ 
        Load the policy specified::
        
            FirewallPolicy('mypolicy').load()
        
        :return: self
        """    
        super(FirewallPolicy, self).load()
        self.ipv4_rule.href = self._load_href('fw_ipv4_access_rules')
        self.ipv4_nat_rule.href = self._load_href('fw_ipv4_nat_rules')
        self.ipv6_rule.href = self._load_href('fw_ipv6_access_rules')
        self.ipv6_nat_rule.href = self._load_href('fw_ipv6_nat_rules')
        return self
    
    @classmethod
    def create(cls, name, template_policy):
        """ 
        Create Firewall Policy. Template policy is required for the
        policy. The template policy parameter should be the href of the
        template entry as obtained from the SMC API.
        
        This policy will then inherit the Inspection and File Filtering
        policy from that template.
        Existing policies and templates are retrievable from search methods, 
        such as::
        
            smc.search.fw_template_policies(policy=None)
        
        :mathod: POST
        :param name: name of policy
        :param template_policy: href of FW template to base policy on
        :return: SMCResult with href attribute set with location of new policy
        
        To use after successful creation, call::
        
            FirewallPolicy('newpolicy').load()
        """
        template_href = smc.search.fw_template_policies(policy=template_policy)
        policy = {'name': name,
                  'template': template_href}
        policy_href = smc.search.element_entry_point('fw_policy')
        
        return SMCElement(href=policy_href, json=policy).create()
    
class InspectionPolicy(Policy):
    """
    The Inspection Policy references a specific inspection policy that is a property
    (reference) to either a FirewallPolicy, IPSPolicy or Layer2Policy. This policy
    defines specific characteristics for threat based prevention. 
    In addition, exceptions can be made at this policy level to bypass scanning based
    on the rule properties.
    """
    def __init__(self, name):
        Policy.__init__(self, name)
        print "Inspection Policy"
        
class FileFilteringPolicy(Policy):
    """ The File Filtering Policy references a specific file based policy for doing 
    additional inspection based on file types. Use the policy parameters to specify how
    certain files are treated by either threat intelligence feeds, sandbox or by local AV
    scanning. You can also use this policy to disable threat prevention based on specific
    files.
    """
    def __init__(self, name):
        Policy.__init__(self, name)
        print "File Filtering Policy"
