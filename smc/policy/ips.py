"""
IPS Engine policy

Module that represents resources related to creating and managing IPS engine 
policies.

To get an existing policy::

    >>> policy = IPSPolicy('Default IPS Policy')
    >>> print(policy.template)
    IPSTemplatePolicy(name=High-Security IPS Template)
    
Or through collections::

    >>> from smc.policy.ips import IPSPolicy
    >>> list(IPSPolicy.objects.all())
    [IPSPolicy(name=Default IPS Policy), IPSPolicy(name=High-Security Inspection IPS Policy)]
    
To create a new policy, use::
    
    policy = IPSPolicy.create(name='my_ips_policy', 
                              template='High Security Inspection Template')
    policy.ips_ipv4_access_rules.create(name='ipsrule1', 
                                        sources='any', 
                                        action='continue')
                                        
    for rule in policy.ips_ipv4_access_rules.all():
        print(rule)

Example rule deletion::

    policy = IPSPolicy('Amazon Cloud')
    for rule in policy.ips_ipv4_access_rules.all():
        if rule.name == 'ipsrule1':
            rule.delete()
"""
from smc.policy.policy import Policy
from smc.policy.rule import IPv4Layer2Rule, EthernetRule
from smc.base.model import ElementCreator
from smc.api.exceptions import ElementNotFound, LoadPolicyFailed,\
    CreatePolicyFailed, CreateElementFailed
from smc.base.collection import rule_collection


class IPSRule(object):
    """
    Encapsulates all references to IPS rule related entry
    points. This is referenced by multiple classes such as 
    IPSPolicy and IPSPolicyTemplate.
    """
    @property
    def ips_ipv4_access_rules(self):
        """ 
        IPS ipv4 access rules

        :rtype: rule_collection(IPv4Layer2Rule)
        """
        return rule_collection(
            self.get_relation('ips_ipv4_access_rules'),
            IPv4Layer2Rule)

    @property
    def ips_ipv6_access_rules(self):
        """
        """
        pass

    @property
    def ips_ethernet_rules(self):
        """
        IPS Ethernet access rule

        :rtype: rule_collection(EthernetRule)
        """
        return rule_collection(
            self.get_relation('ips_ethernet_rules'),
            EthernetRule)


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

    @classmethod
    def create(cls, name, template='High-Security IPS Template'):
        """
        Create an IPS Policy

        :param str name: Name of policy
        :param str template: name of template
        :raises CreatePolicyFailed: policy failed to create
        :return: IPSPolicy
        """
        try:
            if cls.typeof == 'ips_template_policy' and template is None:
                fw_template = None
            else:
                fw_template = IPSTemplatePolicy(template).href
        except ElementNotFound:
            raise LoadPolicyFailed(
                'Cannot find specified firewall template: {}'.format(template))
        json = {
            'name': name,
            'template': fw_template}
        try:
            return ElementCreator(cls, json)
        except CreateElementFailed as err:
            raise CreatePolicyFailed(err)


class IPSTemplatePolicy(IPSPolicy):
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
            print(rule)
    """
    typeof = 'ips_template_policy'

    def upload(self): pass