"""
Policy module represents the classes required to obtaining and manipulating policies within the SMC.

Policy is the abstract base class for all policy subclasses such as FirewallPolicy, InspectionPolicy, 
and FileFilteringPolicy. 
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
from smc.elements.rule import IPv4Rule, IPv4NATRule

cleanr = re.compile('<.*?>')

class Policy(object):
    """ 
    Policy is an abstract base class for all policy types managed by the SMC.
    Policy types are Firewall, Layer2, IPS, Inspection, File Filtering and VPN.
    This base class is not intended to be instantiated directly and thus has two
    abstract methods, load() and create().
    
    Subclasses should implement create(....) individually as each subclass will likely 
    have different input requirements.
    
    All generic functions that are policy level, such as 'open', 'save', 'force_unlock',
    'export', and 'upload' are encapsulated into this base class.
    """
    __metaclass__ = ABCMeta
    
    def __init__(self, name):
        self.name = name
        self.policy_type = None
        self.policy_template = None
        self.file_filtering_policy = None
        self.inspection_policy = None
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
                self.file_filtering_policy = policy_cfg.get('file_filtering_policy')
                self.inspection_policy = policy_cfg.get('inspection_policy')
                self.policy_template = policy_cfg.get('template')
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
               wait_for_finish=True, sleep_interval=3):
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
        :param sleep_interval: length of time to sleep between progress checks (secs)
        :return: follower href is wait_for_finish=False
        """
        import time
        element = self._element('upload')
        element.params = {'filter': device}
        upload = self._commit_create(element)
        if upload.json:
            if wait_for_finish:
                last_msg = ''
                while True:
                    status = search.element_by_href_as_json(upload.json.get('follower'))
                    msg = status.get('last_message')
                    if msg != last_msg:
                        yield re.sub(cleanr,'', msg)
                        last_msg = msg
                    if status.get('success') == True:
                        break
                    time.sleep(sleep_interval)
            else:
                yield upload.json.get('follower')

    def open(self):
        """ 
        Open policy locks the current policy, Use when making multiple
        edits that may require more time. Simple create or deleting elements
        generally can be done without locking via open.
        
        :method: GET
        """
        self._commit_create(self._element('open'))
    
    def save(self):
        """ Save policy that was modified 
        
        :method: POST
        """
        self._commit_create(self._element('save'))
        
    def force_unlock(self):
        """ Forcibly unlock a locked policy 
        
        :method: POST
        """
        self._commit_create(self._element('force_unlock'))

    def export(self):
        self._commit_create(self._element('export'))
                
    def search_rule(self, parameter):
        pass
    
    def _commit_create(self, element):
        """ Submit command to SMC, i.e. open, save, export, etc """
        return smc.api.common.create(element)
    
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
    
    def _element(self, link):
        """ 
        Simple iterator factory to return SMCElement for policy 
        based events such as 'save', 'open', 'export' and 'force_unlock'
        
        :param link: entry point based on the link name. i.e. save, open
        :return: SMCElement
        """
        link_href = self._load_href(link)
        #[entry.get('href') for entry in self.links \
        #               if entry.get('rel') == link]       
        return SMCElement.factory(name=link, 
                                  href=link_href)
       
    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)

class FirewallPolicy(Policy):
    """ 
    This subclass represents a FirewallPolicy installed on layer 3 
    devices. Layer 3 FW's support either ipv4 or ipv6 rules. 
    
    They also have NAT rules and reference to an Inspection and
    File Filtering Policy.
    
    :param name: name of firewall policy
    """
    def __init__(self, name):
        Policy.__init__(self, name)
        self.ipv4_rule = IPv4Rule()
        self.ipv4_nat_rules = IPv4NATRule()
        self.ipv6_rules = []
        self.ipv6_nat_rules = []
    
    def load(self):
        """ 
        Load the policy specified::
        
            FirewallPolicy('mypolicy').load()
        
        :return: self
        """    
        super(FirewallPolicy, self).load()
        self.ipv4_rule.href = self.ipv4_rules_href() #ipv4 rule href
        self.ipv4_nat_rules = self.ipv4_nat_rules_href() #ipv4 nat rule href
        self.ipv4_rule.refresh()
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
        :return: href for new policy
        
        To use after successful creation, call::
        
            FirewallPolicy('newpolicy').load()
        """
        template_href = smc.search.fw_template_policies(policy=template_policy)
        policy = {'name': name,
                  'template': template_href}
        policy_href = smc.search.element_entry_point('fw_policy')
        
        element = SMCElement.factory(name=name, href=policy_href,
                                  json=policy)
        return smc.api.common.create(element)
        
    def ipv4_rules_href(self):
        """ Get href to fw_ipv4_access_rules
         
        :return: href
        """
        return self._load_href('fw_ipv4_access_rules')
                
    def ipv6_rules_href(self):
        """ Get href to fw_ipv6_access_rules
        
        :return: href
        """
        return self._load_href('fw_ipv6_access_rules')
                      
    def ipv4_nat_rules_href(self):
        """ Get href to fw_ipv4_nat_rules
        
        :return: href
        """
        return self._load_href('fw_ipv4_nat_rules')
        
    def ipv6_nat_rules_href(self):
        """ Get href to fw_ipv4_nat_rules
        
        :return: href
        """
        return self._load_href('fw_ipv6_nat_rules')
    
    def __str__(self):
        return "Name: %s, policy_type: %s; %s" % (self.name, self.policy_type, self.__dict__)
          
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
