"""
IPS Engine policy

Module that represents resources related to creating and managing IPS engine 
policies.

To get an existing policy::

    IPSPolicy('existing_policy_by_name')
    
Or through describe_xxx methods::

    for policy in describe_ips_policy():
        policy.describe()
    
To create a new policy, use::
    
    policy = IPSPolicy.create(name='my_ips_policy', 
                              template='High Security Inspection Template')
    policy.ips_ipv4_access_rules.create(name='ipsrule1', 
                                        sources='any', 
                                        action='continue')
                                        
    for rule in policy.ips_ipv4_access_rules.all():
        print rule

Example rule deletion::

    policy = IPSPolicy('Amazon Cloud')
    for rule in policy.ips_ipv4_access_rules.all():
        if rule.name == 'ipsrule1':
            rule.delete()
"""
from smc.policy.policy import Policy
from smc.policy.rule import IPv4Layer2Rule, EthernetRule
from smc.actions.search import element_name_by_href
from smc.elements.element import Meta
from smc.elements.util import find_link_by_name
from smc.api.exceptions import ElementNotFound, LoadPolicyFailed,\
    CreatePolicyFailed

class IPSRule(object):
    """
    Encapsulates all references to IPS rule related entry
    points. This is referenced by multiple classes such as 
    IPSPolicy and IPSPolicyTemplate.
    """
    def __init__(self):
        pass
    
    @property
    def ips_ipv4_access_rules(self):
        """ 
        IPS ipv4 access rules
        
        :return: :py:class:`smc.policy.rule.IPv4Layer2Rule`
        """
        href = find_link_by_name('ips_ipv4_access_rules', self.link)
        return IPv4Layer2Rule(meta=Meta(href=href))
    
    @property    
    def ips_ipv6_access_rules(self):
        """
        """
        #href = find_link_by_name('ips_ipv6_access_rules', self.link)
        pass
    
    @property
    def ips_ethernet_rules(self):
        """
        IPS Ethernet access rule
        
        :param :py:class:`smc.policy.rule.EthernetRule`
        """
        href = find_link_by_name('ips_ethernet_rules', self.link)
        return EthernetRule(meta=Meta(href=href))

class IPSPolicy(IPSRule, Policy):
    """
    IPS Policy represents a set of rules installed on an IPS / IDS
    engine. IPS mode supports both inline and SPAN interface types and 
    ethernet based rules. Layer 2 and IPS engines do not current features that
    require routed interfaces.
    
    :ivar template: which policy template is used

    Instance Resources:
    
    :ivar ips_ipv4_access_rules: :py:class:`~IPSRule.ips_ipv4_access_rules`
    :ivar ips_ipv6_access_rules: :py:class:`~IPSRule.ips_ipv6_access_rules`
    :ivar ips_ethernet_rules: :py:class:`~IPSRule.ips_ethernet_rules`
    """
    typeof = 'ips_policy'
    
    def __init__(self, name, meta=None):
        Policy.__init__(self, name, meta)
        pass

    @classmethod
    def create(cls, name, template):
        try:
            fw_template = IPSTemplatePolicy(template).href
        except ElementNotFound:
            raise LoadPolicyFailed('Cannot find specified firewall template: {}'
                                   .format(template))
        cls.json = {'name': name,
                    'template': fw_template}
        result = cls._create()
        if result.href:
            return IPSPolicy(name, Meta(href=result.href))
        else:
            raise CreatePolicyFailed('Failed to create firewall policy: {}'
                                     .format(result.msg))
    
    @property
    def template(self):
        """
        IPS template used by the IPS policy.
        
        :return: :py:class:`smc.policy.ips.IPSTemplatePolicy`
        """
        href = self.describe().get('template') #href for template
        name = element_name_by_href(href)
        return IPSTemplatePolicy(name=name, meta=Meta(href=href))
        
class IPSTemplatePolicy(IPSRule, Policy):
    """
    All IPS Policies will reference an IPS policy template.

    Most templates will be pre-configured best practice configurations
    and rarely need to be modified. However, you may want to view the
    details of rules configured in a template or possibly insert additional
    rules.
    
    For example, view rules in an ips policy template after loading the
    ips policy::
    
        policy = IPSPolicy('InlineIPS')
        for rule in policy.template.ips_ipv4_access_rules.all():
            print rule
    """
    typeof = 'ips_template_policy'
    
    def __init__(self, name, meta=None):
        Policy.__init__(self, name)
        pass 