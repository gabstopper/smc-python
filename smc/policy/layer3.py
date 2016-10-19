"""
Layer 3 Firewall Policy

Module that represents resources related to creating and managing layer 3 firewall
engine policies.

To get an existing policy::

    FirewallPolicy('existing_policy_by_name')
    
Or through describe_xxx methods::

    for policy in describe_fw_policy():
        policy.describe()
    
To create a new policy, use::

    policy = FirewallPolicy.create(name='newpolicy', template='layer3_fw_template')
    policy.describe()
    
Example rule creation::

    policy = FirewallPolicy('Amazon Cloud')
    policy.open() #Only required for SMC API <= 6.0
    policy.fw_ipv4_access_rules.create(name='mynewrule', sources='any', 
                                       destinations='any', services='any',
                                       action='permit')
    policy.save() #Only required for SMC API <= 6.0
    
Example rule deletion::

    policy = FirewallPolicy('Amazon Cloud')
    for rule in policy.fw_ipv4_access_rules.all():
        if rule.name == 'mynewrule':
            print rule.delete()
"""
import smc.actions.search as search
from smc.elements.util import find_link_by_name
from smc.elements.element import Meta
from smc.api.exceptions import CreatePolicyFailed, ElementNotFound, LoadPolicyFailed
from smc.policy.policy import Policy
from smc.policy.rule import IPv4Rule, IPv4NATRule, IPv6Rule, IPv6NATRule

class FirewallRule(object):
    """
    Encapsulates all references to firewall rule related entry
    points. This is referenced by multiple classes such as 
    FirewallPolicy and FirewallPolicyTemplate.
    
    Instance Resources:
    
    :ivar fw_ipv4_access_rules: :py:class:`IPv4Rule` reference
    :ivar fw_ipv4_nat_rules: :py:class:`IPv4NATRule` reference
    :ivar fw_ipv6_access_rules: :py:class:`IPv6Rule` reference
    :ivar fw_ipv6_nat_rules: :py:class:`IPv6NATRule` reference
    """
    def __init__(self):
        pass
    
    @property
    def fw_ipv4_access_rules(self):
        """
        IPv4 rule entry point
        
        :return: :py:class:`smc.elements.rule.IPv4Rule`
        """
        href = find_link_by_name('fw_ipv4_access_rules', self.link)
        return IPv4Rule(meta=Meta(href=href))

    @property
    def fw_ipv4_nat_rules(self):
        """
        IPv4NAT Rule entry point
        
        :return: :py:class:`smc.elements.rule.IPv4NATRule`
        """
        href = find_link_by_name('fw_ipv4_nat_rules', self.link)
        return IPv4NATRule(meta=Meta(href=href))
        
    @property
    def fw_ipv6_access_rules(self):
        """
        IPv6 Rule entry point
        
        :return: :py:class:`smc.elements.rule.IPv6Rule`
        """
        href = find_link_by_name('fw_ipv6_access_rules', self.link)
        return IPv6Rule(meta=Meta(href=href))
    
    @property
    def fw_ipv6_nat_rules(self):
        """
        IPv6NAT Rule entry point
        
        :return: :py:class:`smc.elements.rule.IPv6NATRule`
        """
        href = find_link_by_name('fw_ipv6_nat_rules', self.link)
        return IPv6NATRule(meta=Meta(href=href)) 
    
class FirewallPolicy(FirewallRule, Policy):
    """ 
    This subclass represents a FirewallPolicy installed on layer 3 
    devices. Layer 3 FW's support either ipv4 or ipv6 rules. 
    
    They also have NAT rules and reference to an Inspection and
    File Filtering Policy.

    :ivar template: which policy template is used
    :ivar file_filtering_policy: mapped file filtering policy
    :ivar inspection_policy: mapping inspection policy
    
    Instance Resources:
    
    :ivar fw_ipv4_access_rules: :py:class:`~FirewallRule.fw_ipv4_access_rules`
    :ivar fw_ipv4_nat_rules: :py:class:`~FirewallRule.ipv4_nat_rules`
    :ivar fw_ipv6_access_rules: :py:class:`~FirewallRule.ipv6_access_rules`
    :ivar fw_ipv6_nat_rules: :py:class:`~FirewallRule.ipv6_nat_rules`
    
    :param str name: name of firewall policy
    :return: self
    """
    typeof = 'fw_policy'
    
    def __init__(self, name, meta=None):
        Policy.__init__(self, name, meta)
        pass
    
    @classmethod
    def create(cls, name, template):
        """ 
        Create Firewall Policy. Template policy is required for the
        policy. The template parameter should be the name of the
        firewall template.
        
        This policy will then inherit the Inspection and File Filtering
        policy from the specified template.
        Existing policies and templates are searchable from describe methods, 
        such as::
        
            import smc.elements.collection
            for policy in describe_fw_policy():
                for rule in policy.fw_ipv4_access_rules.all():
                    print rule
                
        Find the available FW templates::
        
            for template in describe_fw_template_policy():
                print template.name
                ....
        
        :mathod: POST
        :param str name: name of policy
        :param str template: name of the FW template to base policy on
        :return: :py:class:`smc.elements.policy.FirewallPolicy`
        :raises: :py:class:`smc.api.exceptions.LoadPolicyFailed`,
                 :py:class:`smc.api.exceptions.CreatePolicyFailed`
        
        To use after successful creation, reference the policy to obtain
        context::
        
            FirewallPolicy('newpolicy')
        """
        try:
            fw_template = FirewallTemplatePolicy(template).href
        except ElementNotFound:
            raise LoadPolicyFailed('Cannot find specified firewall template: {}'
                                   .format(template))
        cls.json = {'name': name,
                    'template': fw_template}
        result = cls._create()
        if result.href:
            return FirewallPolicy(name, Meta(href=result.href))
        else:
            raise CreatePolicyFailed('Failed to create firewall policy: {}'
                                     .format(result.msg))
 
    @property
    def template(self):
        href = self.describe().get('template') #href for template
        name = search.element_name_by_href(href)
        return FirewallTemplatePolicy(name=name, meta=Meta(href=href))

class FirewallTemplatePolicy(FirewallRule, Policy):
    """
    All Firewall Policies will reference a firewall policy template (even an
    empty custom one - although not recommended).
    Most templates will be pre-configured best practice configurations
    and rarely need to be modified. However, you may want to view the
    details of rules configured in a template or possibly insert additional
    rules.
    
    For example, view rules in firewall policy template after loading the
    firewall policy::
    
        policy = FirewallPolicy('Amazon Cloud')
        for rule in policy.template.fw_ipv4_access_rules.all():
            print rule
    """
    typeof = 'fw_template_policy'
    
    def __init__(self, name, meta=None):
        Policy.__init__(self, name)
        pass    
    
    def export(self):
        #Not supported on the template
        pass
    
    def upload(self):
        #Not supported on the template
        pass