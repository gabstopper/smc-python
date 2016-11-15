"""
Layer 2 Firewall Policy

Module that represents resources related to creating and managing layer 2 firewall
engine policies.

To get an existing policy::

    Layer2Policy('existing_policy_by_name')
    
Or through describe_xxx methods::

    for policy in describe_layer2_policy():
        policy.describe()

Find the available FW templates::
        
    for template in describe_layer2_template_policy():
        print template.name
        ....
    
To create a new policy, use::

    policy = Layer2Policy.create(name='newpolicy', template='layer2_fw_template')
    policy.describe()
    
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
from smc.base.model import Meta, ElementCreator
from smc.base.util import find_link_by_name
from smc.actions.search import element_name_by_href
from smc.api.exceptions import ElementNotFound, LoadPolicyFailed,\
    CreatePolicyFailed
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
        href = find_link_by_name('layer2_ipv4_access_rules', self.link)
        return IPv4Layer2Rule(meta=Meta(href=href))
    
    @property    
    def layer2_ipv6_access_rules(self):
        """
        Layer 2 IPv6 access rule
        
        """
        #href = find_link_by_name('layer2_ipv6_access_rules', self.link)
        pass
    
    @property
    def layer2_ethernet_rules(self):
        """
        Layer 2 Ethernet access rule
        
        :param :py:class:`smc.policy.rule.EthernetRule`
        """
        href = find_link_by_name('layer2_ethernet_rules', self.link)
        return EthernetRule(meta=Meta(href=href))
    
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
    
    def __init__(self, name, meta=None):
        Policy.__init__(self, name, meta)
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
        :return: :py:class:`smc.elements.policy.FirewallPolicy`
        :raises: :py:class:`smc.api.exceptions.LoadPolicyFailed`,
                 :py:class:`smc.api.exceptions.CreatePolicyFailed`
        
        To use after successful creation, reference the policy to obtain
        context::
        
            Layer2Policy('newpolicy')
        """
        try:
            fw_template = Layer2TemplatePolicy(template).href
        except ElementNotFound:
            raise LoadPolicyFailed('Cannot find specified layer2 firewall '
                                   'template: {}'.format(template))
        cls.json = {'name': name,
                    'template': fw_template}
        result = ElementCreator(cls)
        if result.href:
            return Layer2Policy(name, Meta(href=result.href))
        else:
            raise CreatePolicyFailed('Failed to create firewall policy: {}'
                                     .format(result.msg))

    @property
    def template(self):
        """
        Layer 2 Firewall policy template used by the Layer 2 Policy.
        
        :return: :py:class:`smc.policy.layer2.Layer2TemplatePolicy`
        """
        href = self.describe().get('template') #href for template
        name = element_name_by_href(href)
        return Layer2TemplatePolicy(name=name, meta=Meta(href=href))

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
   
    def __init__(self, name, meta=None):
        Policy.__init__(self, name, meta)
        pass
    
    def export(self):
        #Not supported on the template
        pass
    
    def upload(self):
        #Not supported on the template
        pass