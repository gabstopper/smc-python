"""
Layer 3 Firewall Policy

Module that represents resources related to creating and managing layer 3 firewall
engine policies.

To get an existing policy::

    >>> from smc.policy.layer3 import FirewallPolicy
    >>> policy = FirewallPolicy('Standard Firewall Policy with Inspection')
    >>> print(policy.template)
    FirewallTemplatePolicy(name=Firewall Inspection Template)

Or through collections::

    >>> list(Search('fw_policy').objects.all())
    [FirewallPolicy(name=Standard Firewall Policy with Inspection), FirewallPolicy(name=Layer 3 Virtual FW Policy)]

To create a new policy, use::

    policy = FirewallPolicy.create(name='newpolicy', template='layer3_fw_template')

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
            rule.delete()
"""
from smc.base.model import ElementCreator
from smc.api.exceptions import CreatePolicyFailed, ElementNotFound, LoadPolicyFailed,\
    CreateElementFailed
from smc.policy.policy import Policy
from smc.policy.rule import IPv4Rule, IPv6Rule
from smc.policy.rule_nat import IPv4NATRule, IPv6NATRule
from smc.base.collection import create_collection


class FirewallRule(object):
    """
    Encapsulates all references to firewall rule related entry
    points. This is referenced by multiple classes such as
    FirewallPolicy and FirewallPolicyTemplate.
    """
    @property
    def fw_ipv4_access_rules(self):
        """
        IPv4 rule entry point

        :return: collection of :class:`smc.policy.rule.IPv4Rule`
        :rtype: SubElementCollection
        """
        return create_collection(
            self.data.get_link('fw_ipv4_access_rules'),
            IPv4Rule)

    @property
    def fw_ipv4_nat_rules(self):
        """
        IPv4NAT Rule entry point

        :return: collection of :class:`smc.policy.rule_nat.IPv4NATRule`
        :rtype: SubElementCollection
        """
        return create_collection(
            self.data.get_link('fw_ipv4_nat_rules'),
            IPv4NATRule)

    @property
    def fw_ipv6_access_rules(self):
        """
        IPv6 Rule entry point

        :return: collection of :class:`smc.policy.rule.IPv6Rule`
        :rtype: SubElementCollection
        """
        return create_collection(
            self.data.get_link('fw_ipv6_access_rules'),
            IPv6Rule)

    @property
    def fw_ipv6_nat_rules(self):
        """
        IPv6NAT Rule entry point

        :return: collection of :class:`smc.policy.rule.IPv6NATRule`
        :rtype: SubElementCollection
        """
        return create_collection(
            self.data.get_link('fw_ipv6_nat_rules'),
            IPv6NATRule)


class FirewallPolicy(FirewallRule, Policy):
    """
    FirewallPolicy represents a set of rules installed on layer 3
    devices. Layer 3 FW's support either ipv4 or ipv6 rules.

    They also have NAT rules and reference to an Inspection and
    File Filtering Policy.

    :ivar template: which policy template is used

    Instance Resources:

    :ivar fw_ipv4_access_rules: :py:class:`~FirewallRule.fw_ipv4_access_rules`
    :ivar fw_ipv4_nat_rules: :py:class:`~FirewallRule.ipv4_nat_rules`
    :ivar fw_ipv6_access_rules: :py:class:`~FirewallRule.ipv6_access_rules`
    :ivar fw_ipv6_nat_rules: :py:class:`~FirewallRule.ipv6_nat_rules`

    """
    typeof = 'fw_policy'

    def __init__(self, name, **meta):
        super(FirewallPolicy, self).__init__(name, **meta)
        pass

    @classmethod
    def create(cls, name, template='Firewall Inspection Template'):
        """
        Create Firewall Policy. Template policy is required for the
        policy. The template parameter should be the name of the
        firewall template.

        This policy will then inherit the Inspection and File Filtering
        policy from the specified template.

        :param str name: name of policy
        :param str template: name of the FW template to base policy on
        :raises LoadPolicyFailed: Cannot load the policy after creation
        :raises CreatePolicyFailed: policy creation failed with message
        :return: FirewallPolicy

        To use after successful creation, reference the policy to obtain
        context::

            FirewallPolicy('newpolicy')
        """
        try:
            fw_template = FirewallTemplatePolicy(template).href
        except ElementNotFound:
            raise LoadPolicyFailed(
                'Cannot find specified firewall template: {}'
                .format(template))
        json = {
            'name': name,
            'template': fw_template}
        try:
            return ElementCreator(cls, json)
        except CreateElementFailed as err:
            raise CreatePolicyFailed(
                'Failed to create firewall policy: {}'.format(err))


class FirewallSubPolicy(Policy):
    """
    A Firewall Sub Policy is a rule section within a firewall policy
    that provides a container to create rules that are referenced from
    a 'jump' rule. Typically rules in a sub policy are similar in some
    fashion such as applying to a specific service. Sub Policies can also
    be delegated from an administrative perspective.

    Firewall Sub Policies only provide access to creating IPv4 rules. NAT
    is done on the parent firewall policy::

        p = FirewallSubPolicy('MySubPolicy')
        p.fw_ipv4_access_rules.create(
            name='newule',
            sources='any',
            destinations='any',
            services=[TCPService('SSH')],
            action='discard')
    """
    typeof = 'sub_ipv4_fw_policy'

    def __init__(self, name, **meta):
        super(FirewallSubPolicy, self).__init__(name, **meta)
        pass

    @classmethod
    def create(cls, name):
        """
        Create a sub policy. Only name is required. Other settings are
        inherited from the parent firewall policy (template, inspection
        policy, etc).

        :param str name: name of sub policy
        :raises CreateElementFailed: failed to create policy
        :rtype: FirewallSubPolicy
        """
        return ElementCreator(cls, json={'name': name})

    @property
    def fw_ipv4_access_rules(self):
        """
        IPv4 rule entry point

        :return: collection of :class:`smc.policy.rule.IPv4Rule`
        :rtype: SubElementCollection
        """
        return create_collection(
            self.data.get_link('fw_ipv4_access_rules'),
            IPv4Rule)


class FirewallTemplatePolicy(FirewallRule, Policy):
    """
    All Firewall Policies will reference a firewall policy template.

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

    def __init__(self, name, **meta):
        super(FirewallTemplatePolicy, self).__init__(name, **meta)
        pass

    def export(self): pass  # Not supported on the template

    def upload(self): pass  # Not supported on the template
