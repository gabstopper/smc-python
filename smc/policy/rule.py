"""
Rule module that handles each of the different rule types available 
(IPv4Rule, IPS Rule, Inspection Rule, File Filtering Rule, etc)

This is not called directly, but is linked to a Policy type class which 
will have references to the correct rule types and references to the proper
entry points.

Here is an example of how this is referenced and used::

    policy = FirewallPolicy('smcpython')
    policy.fw_ipv4_access_rules.create(name='myrule', 
                                       sources=mysources,
                                       destinations=mydestinations, 
                                       services=myservices, 
                                       action='permit')
                            
Example of creating a rule for a layer 3 engine that uses a VPN action and
a source network object that already exists::

    policy = FirewallPolicy('Amazon Cloud')
    policy.fw_ipv4_access_rules.create(name='test',
                                       sources=[Network('mynetwork').href],
                                       destinations='any',
                                       services='any',
                                       action='enforce_vpn',
                                       vpn_policy='Amazon')
"""
import smc.actions.search as search
from smc.elements.element import Meta, LogicalInterface
from smc.api.common import SMCRequest
from smc.elements.mixins import UnicodeMixin
from smc.policy.vpn import VPNPolicy
from smc.api.exceptions import ElementNotFound, MissingRequiredInput

class Rule(UnicodeMixin):   
    @property
    def name(self):
        return self.meta.name
        
    @property
    def href(self):
        return self.meta.href
    
    def add_after(self):
        pass
    
    def add_before(self):
        pass
    
    def describe(self):
        return search.element_by_href_as_json(self.href)
    
    def delete(self):
        return SMCRequest(href=self.href).delete()
    
    def all(self):
        """
        Enumerate all rules for this rule type. Return instance
        that has only meta data set (lazy loaded).
        
        :return: class type based on rule type 
        """
        rule_lst = search.element_by_href_as_json(self.href)
        rules=[] 
        for rule in rule_lst:
            #return self class instance by calling type
            rules.append(type(self)(meta=Meta(**rule)))
        return rules
    
    def rule_l2_common(self, logical_interfaces):
        """
        Common values for layer 2 ethernet / IPS rule parameters.
        In particular, logical interfaces are an additional parameter that 
        can be used as a rule match parameter.
        """
        rule_values = {}
        if logical_interfaces is None:
            rule_values.update(logical_interfaces={'any': True})
        else:
            try:
                logicals=[]
                for interface in logical_interfaces:
                    logicals.append(LogicalInterface(interface).href)
                rule_values.update(logical_interfaces=
                                            {'logical_interface': logicals})
            except ElementNotFound:
                raise MissingRequiredInput('Cannot find Logical interface specified '
                                           ': {}'.format(logical_interfaces))
        return rule_values
    
    def rule_common(self, sources, destinations, services):
        """
        Common values for rules. These will apply to all rule types, 
        including NAT.
        """
        rule_values = { 
                'sources': {'src': []},
                'destinations': {'dst': []},
                'services': {'service': []}}

        if sources is not None:
            if isinstance(sources, str) and sources.lower() == 'any':
                rule_values.update(sources={'any': True})
            else:
                rule_values.update(sources={'src': sources})
        else:
            rule_values.update(sources={'none': True})

        if destinations is not None:
            if isinstance(destinations, str) and destinations.lower() == 'any':
                rule_values.update(destinations={'any': True})
            else:
                rule_values.update(destinations={'dst': destinations})
        else:
            rule_values.update(destinations={'none': True})
                
        if services is not None:
            if isinstance(services, str) and services.lower() == 'any':
                rule_values.update(services={'any': True})
            else:
                rule_values.update(services={'service': services})
        else:
            rule_values.update(services={'none': True})
            
        return rule_values
    
    def _compile_rule(self):
        pass
    
    def _src_dst_resolver(self):
        pass
            
    def __unicode__(self):
        return u'{0}(name={1})'.format(self.__class__.__name__, self.name)
  
    def __repr__(self):
        return repr(unicode(self))

class IPv4Rule(Rule):
    """ 
    Represents an IPv4 Rule for a layer 3 engine.
    
    Access the policy required, and add a rule::
        
            for policy in describe_fw_policy():
                print policy
                
    Create a rule::

        policy = FirewallPolicy('mypolicy')
        policy.fw_ipv4_access_rules.create(name='smcpython', 
                                           sources='any', 
                                           destinations='any', 
                                           services='any')
                
        Sources and Destinations can be one of any valid network element types defined
        in :py:class:smc.elements.element`.
        
        Source entries by href:: 
        
            sources=['http://1.1.1.1:8082/elements/network/myelement',
                     'http://1.1.1.1:8082/elements/host/myhost'], etc
        
        Services have a similar syntax, provide a list of the href's for the services::
        
            services=['http://1.1.1.1/8082/elements/tcp_service/mytcpservice',
                      'http://1.1.1.1/8082/elements/udp_server/myudpservice'], etc
        
        You can obtain the href for the network and service elements by using the 
        :py:mod:`smc.elements.collection` describe functions such as::
        
            services=[x.href for x in describe_tcp_service(name=['80','443', 'FTP'])]
            sources=[x.href for x in describe_network(name=['172.18.1.0'])]
            
        Services by application (get all facebook applications)::
        
            services = [x.href for x in describe_application_situation(
                        name=['Facebook'], exact_match=False)]

        Sources / Destinations and Services can also take the string value 'any' to
        allow all. For example::
        
            sources='any'
    
    :ivar name: name of rule
    """
    typeof = 'fw_ipv4_access_rule'
    
    def __init__(self, meta=None):
        self.meta = meta

    def create(self, name, sources=None, destinations=None, 
               services=None, action='allow', is_disabled=False, 
               vpn_policy=None):
        """ 
        Create a layer 3 firewall rule
            
        :param str name: name of rule
        :param list source: source/s for rule, in href format
        :param list destination: destinations, in href format
        :param list service: service/s, in href format
        :param str action: allow|continue|discard|refuse|enforce_vpn|apply_vpn|blacklist 
               (default: allow)
        :param str: vpn_policy: vpn policy name; required for enforce_vpn and apply_vpn 
               actions 
        :return: :py:class:`smc.api.web.SMCResult`
        :raises: :py:class:`smc.api.exceptions.MissingReuqiredInput` when options are
                 specified the need additional setting, i.e. use_vpn action requires a
                 vpn policy be specified.
        """
        actions = ['allow', 'continue', 'discard', 'refuse', 
                   'enforce_vpn', 'apply_vpn', 'blacklist']

        rule_values = self.rule_common(sources, destinations, services)
        rule_values.update(name=name)

        if action not in actions:
            rule_values.update(action={'action': 'allow',
                                       'connection_tracking_options':{}})
        elif action == 'enforce_vpn' or action == 'apply_vpn':
            if vpn_policy is None:
                raise MissingRequiredInput('A VPN policy must be specified when '
                                           'rule action has a VPN action')
            try:
                vpn = VPNPolicy(vpn_policy).href
                rule_values.update(action={'action': action,
                                           'connection_tracking_options':{},
                                           'vpn': vpn})
            except ElementNotFound:
                raise MissingRequiredInput('Cannot find VPN policy specified: {}, '
                                           .format(vpn_policy))
        else:
            rule_values.update(action={'action': action,
                                       'connection_tracking_options':{}})

        rule_values.update(is_disabled=is_disabled)

        return SMCRequest(href=self.href,
                          json=rule_values).create()
        
class IPv4NATRule(Rule):
    """
    Manipulate NAT Rules for relevant policy types. For the most
    part the rule structure is the same as any other rule type with
    the exception of defining the NAT field.
    
    For example, adding a NAT rule for a layer 3 FW policy::
    
        network = Network.create('internal', '172.18.1.0/24').href
        policy = FirewallPolicy('Amazon Cloud')
        policy.fw_ipv4_nat_rules.create(name='mynatrule', 
                                        sources=[network], 
                                        destinations='any', 
                                        services='any',
                                        dynamic_src_nat='10.0.0.245')
    """                                         
    def __init__(self, meta=None):
        self.meta = meta
  
    def create(self, name, sources=None, destinations=None, services=None,
               dynamic_src_nat=None, max_port=65535, min_port=1024, 
               is_disabled=False):
        """
        Create a NAT rule
        
        :param str name: name of NAT rule
        :param list sources: list of source href's
        :param list destinations: list of destination href's
        :param list services: list of service href's
        :param str dynamic_src_nat: ip of dynamic source nat address
        :param int max_port: max port number for PAT
        :param int min_port: min port number for PAT
        :param boolean is_disabled: whether to disable rule or not
        :return: :py:class:`smc.api.web.SMCResult`
        """
        rule_values = self.rule_common(sources, destinations, services)
        rule_values.update(name=name)
        rule_values.update(is_disabled=is_disabled)
        
        if dynamic_src_nat:
            dyn_nat = {'options': {'dynamic_src_nat':
                                    {'automatic_proxy': True,
                                     'translation_values':
                                        [{'ip_descriptor': dynamic_src_nat,
                                          'max_port': max_port,
                                          'min_port': min_port}]}}}
            rule_values.update(dyn_nat)

        return SMCRequest(href=self.href, json=rule_values).create()
    
class IPv4Layer2Rule(Rule):
    """
    Create IPv4 rules for Layer 2 Firewalls
    
    Example of creating an allow all rule::
    
        policy = Layer2Policy('mylayer2')
        policy.layer2_ipv4_access_rules.create(name='myrule', 
                                               sources='any', 
                                               destinations='any', 
                                               services='any')
    """
    typeof = 'layer2_ipv4_access_rule'
   
    def __init__(self, meta=None):
        self.meta = meta
    
    def create(self, name, sources=None, destinations=None, 
               services=None, action='allow', is_disabled=False, 
               logical_interfaces=None):
        """
        Create an IPv4 Layer 2 FW rule
        
        :param str name: name of rule
        :param list sources: list of source href's
        :param list destinations: list of destination href's
        :param list services: list of service href's
        :param list logical_interfaces: logical interfaces by name
        :param str action: |allow|continue|discard|refuse|blacklist
        :param boolean is_disabled: whether to disable rule or not
        :return: :py:class:`smc.api.web.SMCResult`
        :raises: :py:class:`smc.api.exceptions.MissingReuqiredInput` when options are
                 specified the need additional setting, i.e. use_vpn action requires a
                 vpn policy be specified.
        """
        rule_values = self.rule_common(sources, destinations, services)
        rule_values.update(name=name)
        rule_values.update(is_disabled=is_disabled)
        
        actions = ['allow', 'continue', 'discard', 'refuse', 'blacklist']
        
        if action not in actions:
            action = 'allow'
        
        rule_values.update(action={'action': action,
                                   'connection_tracking_options':{}})
    
        rule_values.update(self.rule_l2_common(logical_interfaces))

        return SMCRequest(href=self.href, json=rule_values).create()

class EthernetRule(Rule):
    """
    Ethernet Rule represents a policy on a layer 2 or IPS engine.
    
    If logical_interfaces parameter is left blank, 'any' logical
    interface is used.

    Create an ethernet rule for a layer 2 policy::
    
        policy = Layer2Policy('layer2policy')
        policy.layer2_ethernet_rules.create(name='l2rule',
                                            logical_interfaces=['dmz'], 
                                            sources='any',
                                            action='discard')
    """                          
    typeof = 'ethernet_rule'
    
    def __init__(self, meta=None):
        self.meta = meta

    def create(self, name, sources=None, destinations=None, 
               services=None, action='allow', is_disabled=False, 
               logical_interfaces=None):
        """
        Create an Ethernet rule
        
        :param str name: name of rule
        :param list sources: list of source href's
        :param list destinations: list of destination href's
        :param list services: list of service href's
        :param list logical_interfaces: logical interfaces by name
        :param str action: |allow|continue|discard|refuse|blacklist
        :param boolean is_disabled: whether to disable rule or not
        :return: :py:class:`smc.api.web.SMCResult`
        :raises: :py:class:`smc.api.exceptions.MissingReuqiredInput` when options are
                 specified the need additional setting, i.e. use_vpn action requires a
                 vpn policy be specified.
        """
        rule_values = self.rule_common(sources, destinations, services)
        rule_values.update(name=name)
        rule_values.update(is_disabled=is_disabled)
        
        actions = ['allow', 'continue', 'discard', 'refuse', 'blacklist']
        
        if action not in actions:
            action = 'allow'
        
        rule_values.update(action={'action': action,
                                   'connection_tracking_options':{}})
    
        rule_values.update(self.rule_l2_common(logical_interfaces))

        return SMCRequest(href=self.href, json=rule_values).create()
    
class IPv6Rule(object):
    typeof = 'ipv6_rule'
    
    def __init__(self):
        pass
    
class IPv6NATRule(object):
    typeof = 'ipv6_nat_rule'
    
    def __init__(self):
        pass
