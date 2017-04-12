"""
Layer 2 Firewall Policy

Module that represents resources related to creating and managing layer 2 firewall
engine policies.

To get an existing policy::

    >>> from smc.policy.layer2 import Layer2Policy
    >>> policy = Layer2Policy('MyLayer2Policy')
    >>> print(policy.template)
    Layer2TemplatePolicy(name=Layer 2 Firewall Inspection Template)
    
Or through collections::

    >>> from smc.policy.layer2 import Layer2Policy
    >>> list(Search('layer2_policy').objects.all())
    [Layer2Policy(name=MyLayer2Policy)]
    
To create a new policy, use::

    policy = Layer2Policy.create(name='newpolicy', template='layer2_fw_template')
    
Example rule creation::

    policy = Layer2Policy('smcpython-l2')
    
    policy.layer2_ipv4_access_rules.create(
                                name='nonerule', 
                                sources='any', 
                                destinations='any', 
                                services='any',
                                logical_interfaces=[location_href_to_logical_interface])
    
Create Ethernet rule for layer 2 firewall::

    policy.layer2_ethernet_rules.create(name='nonerule', 
                                        sources='any', 
                                        destinations='any', 
                                        services='any')

.. note:: Leaving parameter logical_interfaces out of create will default to 'ANY'.

Example rule deletion::

    policy = Layer2Policy('Amazon Cloud')
    for rule in policy.layer2_ipv4_access_rules.all():
        if rule.name == 'myrule':
            print rule.delete()
"""
from smc.base.model import ElementCreator
from smc.api.exceptions import ElementNotFound, LoadPolicyFailed,\
    CreatePolicyFailed, CreateElementFailed
from smc.policy.policy import Policy
from smc.policy.rule import IPv4Layer2Rule, EthernetRule

class Layer2Rule(object):
    """
    Encapsulates all references to layer 2 firewall rule related 
    entry points. This is referenced by multiple classes such as 
    Layer2Policy and Layer2TemplatePolicy.
    """
    @property
    def layer2_ipv4_access_rules(self):
        """ 
        Layer2 Firewall access rule
        
        :return: :py:class:`smc.policy.rule.IPv4Layer2Rule`
        """
        return IPv4Layer2Rule(href=self.resource.layer2_ipv4_access_rules)
    
    @property    
    def layer2_ipv6_access_rules(self):
        """
        Layer 2 IPv6 access rule
        
        """
        #href = self._link('layer2_ipv6_access_rules')
        pass
    
    @property
    def layer2_ethernet_rules(self):
        """
        Layer 2 Ethernet access rule
        
        :param :py:class:`smc.policy.rule.EthernetRule`
        """
        return EthernetRule(href=self.resource.layer2_ethernet_rules)
    
class Layer2Policy(Layer2Rule, Policy):
    """
    Layer 2 Policy represents a set of rules installed on a layer 2 firewall
    engine. Layer 2 mode supports both inline and SPAN interface types and 
    ethernet based rules. Layer 2 and IPS engines do not current features that
    require routed interfaces.
    
    :ivar template: which policy template is used

    Instance Resources:
    
    :ivar layer2_ipv4_access_rules: :py:class:`~Layer2Rule.layer2_ipv4_access_rules`
    :ivar layer2_ipv6_access_rules: :py:class:`~Layer2Rule.layer2_ipv6_access_rules`
    :ivar layer2_ethernet_rules: :py:class:`~Layer2Rule.layer2_ethernet_rules`
    """
    typeof = 'layer2_policy'
    
    def __init__(self, name, **meta):
        super(Layer2Policy, self).__init__(name, **meta)
        pass
    
    @classmethod
    def create(cls, name, template):
        """ 
        Create Layer 2 Firewall Policy. Template policy is required for 
        the policy. The template parameter should be the name of the
        template.
        
        The template should exist as a layer 2 template policy and should be 
        referenced by name.
        
        This policy will then inherit the Inspection and File Filtering
        policy from the specified template.
        
        :mathod: POST
        :param str name: name of policy
        :param str template: name of the FW template to base policy on
        :raises LoadPolicyFailed: cannot find policy by name
        :raises CreatePolicyFailed: cannot create policy with reason
        :return: `~FirewallPolicy`
        
        To use after successful creation, reference the policy to obtain
        context::
        
            Layer2Policy('newpolicy')
        """
        try:
            fw_template = Layer2TemplatePolicy(template).href
        except ElementNotFound:
            raise LoadPolicyFailed('Cannot find specified layer2 firewall '
                                   'template: {}'.format(template))
        json = {'name': name,
                'template': fw_template}
        try:
            result = ElementCreator(cls, json)
            return Layer2Policy(name, href=result)
        except CreateElementFailed as err:
            raise CreatePolicyFailed('Failed to create firewall policy: {}'
                                     .format(err))


class Layer2TemplatePolicy(Layer2Rule, Policy):
    """
    All Layer 2 Firewall Policies will reference a firewall policy template.

    Most templates will be pre-configured best practice configurations
    and rarely need to be modified. However, you may want to view the
    details of rules configured in a template or possibly insert additional
    rules.
    
    For example, view rules in the layer 2 policy template after loading the
    firewall policy::
    
        policy = Layer2Policy('Amazon Cloud')
        for rule in policy.template.layer2_ipv4_access_rules.all():
            print rule
    """
    typeof = 'layer2_template_policy'
   
    def __init__(self, name, **meta):
        super(Layer2TemplatePolicy, self).__init__(name, **meta)
        pass
    
    def export(self):
        #Not supported on the template
        pass
    
    def upload(self):
        #Not supported on the template
        pass