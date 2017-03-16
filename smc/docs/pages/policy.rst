Policies
--------

Policies are available for all 3 firewall roles, Firewall, Layer2 and IPS. 
The only initial requirement to create a policy is to reference a policy template. The policy
template is a pre-configured set of best practice rules that provide connectivity and
enables basic features such as stateful inspection, etc.

Obtaining available templates can be achieved through the collections interface::

	>>> from smc.policy.layer3 import FirewallTemplatePolicy
	>>> FirewallTemplatePolicy.objects.all()
	>>> print(list(FirewallTemplatePolicy.objects.all()))
	[FirewallTemplatePolicy(name=Firewall Inspection Template), FirewallTemplatePolicy(name=Firewall Template)]


Example of creating a basic layer 3 policy; reference template by name::

	>>> from smc.policy.layer3 import FirewallPolicy
	>>> FirewallPolicy.create('newpolicy', template='Firewall Template')
	FirewallPolicy(name=newpolicy)
   
Loading an existing policy is similar to obtaining other elements::

	>>> policy = FirewallPolicy('newpolicy')
	>>> policy.template
	FirewallTemplatePolicy(name=Firewall Template)

Once a policy instance has been obtained, rules (policy or NAT) can be added, viewed, or removed.
     
Example of creating a rule for a firewall policy::

	>>> policy.fw_ipv4_access_rules.create(name='newrule', sources='any', destinations='any', services='any', action='permit')
	'http://1.1.1.1:8082/6.1/elements/fw_policy/265/fw_ipv4_access_rule/2099472'
	
	#View all rules
	>>> for rule in policy.fw_ipv4_access_rules.all():
	...   print(rule.name, rule.sources, rule.destinations, rule.services)
	... 
	('newrule', <smc.policy.rule_elements.Source object at 0x1050d3b50>, <smc.policy.rule_elements.Destination object at 0x1050d3dd0>, <smc.policy.rule_elements.Service object at 0x1050d3f50>)
	

NAT can be applied as dynamic source NAT, static source NAT, or static destination NAT.

Example of creating a dynamic source NAT rule::

	>>> from smc.policy.layer3 import FirewallPolicy
	>>> from smc.elements.network import Host
	>>> policy = FirewallPolicy('newpolicy')
	>>> policy.fw_ipv4_nat_rules.create(name='mynat',
	...                                 sources=[Host('kali')],
	...                                 destinations='any',
	...                                 services='any',
	...                                 dynamic_src_nat='1.1.1.1',
	...                                 dynamic_src_nat_ports=(1024,65535))
	'http://1.1.1.1:8082/6.1/elements/fw_policy/265/fw_ipv4_nat_rule/2099475'

Example of creating a destination NAT rule where the destination is to Host('3.3.3.3') and
will be translated to '1.1.1.1'::

	>>> policy.fw_ipv4_nat_rules.create(name='mynat',
	...                                 sources='any',
	...                                 destinations=[Host('3.3.3.3')],
	...                                 services='any',
	...                                 static_dst_nat='1.1.1.1')
	'http://1.1.1.1:8082/6.1/elements/fw_policy/265/fw_ipv4_nat_rule/2099476'

                                                                                                                    
Create an any/any no NAT rule (no value for NAT field)::
   
	>>> policy.fw_ipv4_nat_rules.create(name='nonat',sources='any',destinations='any',services='any')
	'http://1.1.1.1:8082/6.1/elements/fw_policy/265/fw_ipv4_nat_rule/2099477'

                                                                           
For additional NAT related options, see: :py:class:`smc.policy.rule_nat.IPv4NATRule`