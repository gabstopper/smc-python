from abc import ABCMeta, abstractmethod
import re
import smc.actions.search as search
import smc.api.common
from smc.api.web import SMCException
from smc.elements.element import SMCElement
from smc.elements.rule import IPv4Rule, IPv4NATRule

cleanr = re.compile('<.*?>')

class Policy(object):
    """ 
    Policy is the base class for all policy types managed by the SMC.
    Policy types are Firewall, Layer2, IPS, Inspection, File Filtering and VPN.
    This base class is not intended to be instantiated directly and thus has two
    abstract methods, load() and create().
    If the policy already exists within the SMC, you can simply load it directly and
    make any modifications as needed:
    Policy('mypolicy').load().
    Once policy is loaded all top level policy settings and references to subclasses
    policies (FirewallPolicy, IPSPolicy, etc) are available. 
    
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
        """ Load top level policy settings for selected policy """
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
        Intent is to use this as a classmethod to create a new policy. To use the 
        newly created policy, first create the policy by calling the subclass, then 
        load().
        For example: 
        FirewallPolicy.create('mypolicy', ....)
        FirewallPolicy('mypolicy').load()
        Each policy type has slightly different requirements for referencing adjacent
        policies or required policy references. 
        To find existing policies or templates, use 
        smc.search.inspection.policies(), 
        smc.search.file_filtering_policies(), etc.
        """
        pass
                             
    def upload(self, device, 
               wait_for_finish=True, sleep_interval=3):
        """ 
        Upload policy to specific device. This is an asynchronous call
        that will return a 'follower' link that can be queried to determine 
        the status of the task. If wait_for_finish is False, the progress
        href is returned when calling this function. If wait_for_finish is
        True, this generator function will return the new messages as they
        arrive.
        :param device: name of device to upload policy to
        :param wait_for_finish: whether to wait in a loop until the upload completes,
        otherwise return the progress href to query outside of this function
        :param sleep_interval: length of time to sleep between progress checks (secs)
        """
        import time
        element = self._element('upload')
        element.params = {'filter': device}
        upload = self._commit(element)
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
        """
        self._commit(self._element('open'))
    
    def save(self):
        """ Save policy that was modified """
        self._commit(self._element('save'))
        
    def force_unlock(self):
        self._commit(self._element('force_unlock'))

    def export(self):
        self._commit(self._element('export'))
                
    def search_rule(self, parameter):
        pass
    
    def _commit(self, element):
        """ Submit command to SMC, i.e. open, save, export, etc """
        return smc.api.common._create(element)
    
    def _load_rule_href(self, rule_type):
        """ 
        Used by subclasses to retrieve the entry point for 
        the rule href's. All links for top level policy are stored
        in self.links. An example rule_type would be: 
        fw_ipv4_access_rules, fw_ipv6_access_rules, etc
        :param rule_type: href for given rule type
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
        :return SMCElement
        """
        link_href = [entry.get('href') for entry in self.links \
                       if entry.get('rel') == link]       
        return SMCElement.factory(name=link, 
                                  href=link_href.pop())
       
    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)

class FirewallPolicy(Policy):
    """ 
    This subclass represents a FirewallPolicy installed on layer 3 
    devices. Layer 3 FW's support either ipv4 or ipv6 rules. Initialize
    this to manipulate or create a new policy.
    To load an existing FirewallPolicy, run:
    FirewallPolicy('mypolicy').load()
    To create a new FirewallPolicy, use the classmethod 'create':
    FirewallPolicy.create('mypolicy', 'firewall_policy_template')
    where 'firewall_policy_template' is an existing FW policy template in
    the SMC. This policy will then inherit the Inspection and File Filtering
    policy from that template.
    :param name: name of firewall policy
    """
    def __init__(self, name):
        Policy.__init__(self, name)
        self.ipv4_rule = IPv4Rule()
        self.ipv4_nat_rules = IPv4NATRule()
        self.ipv6_rules = []
        self.ipv6_nat_rules = []
    
    def load(self):
        super(FirewallPolicy, self).load()
        self.ipv4_rule.href = self.ipv4_rules_href() #ipv4 rule href
        self.ipv4_nat_rules = self.ipv4_nat_rules_href() #ipv4 nat rule href
        self.ipv4_rule.refresh()
        return self
    
    @classmethod
    def create(self, name, template_policy):
        """ 
        Create Firewall Policy. Required field inputs are all href's to the adjacent policies
        :param name: name of policy
        :param template_policy: FW template to base policy on
        :return href for new policy
        Call Policy('newpolicy').load() to use policy after creation
        """
        policy = {'name': name,
                  'template': template_policy}
        policy_href = smc.search.element_entry_point('fw_policy')
        
        element = SMCElement.factory(name=name, href=policy_href,
                                  json=policy)
        return smc.api.common._create(element)
        
    def ipv4_rules_href(self):
        return self._load_rule_href('fw_ipv4_access_rules')
                
    def ipv6_rules_href(self):
        return self._load_rule_href('fw_ipv6_access_rules')
                      
    def ipv4_nat_rules_href(self):
        return self._load_rule_href('fw_ipv4_nat_rules')
        
    def ipv6_nat_rules_href(self):
        return self._load_rule_href('fw_ipv6_nat_rules')
    
    def __str__(self):
        return "Name: %s, policy_type: %s; %s" % (self.name, self.policy_type, self.__dict__)
          
class InspectionPolicy(Policy):
    def __init__(self, name):
        Policy.__init__(self, name)
        print "Inspection Policy"
        
class FileFilteringPolicy(Policy):
    def __init__(self, name):
        Policy.__init__(self, name)
        print "File Filtering Policy"
