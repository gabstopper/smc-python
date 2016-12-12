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
from smc.base.model import Meta, Element, prepared_request
from smc.elements.other import LogicalInterface
from smc.vpn.policy import VPNPolicy
from smc.api.exceptions import ElementNotFound, MissingRequiredInput

class Rule(Element):
    """ 
    Top level rule construct with methods required to modify common 
    behavior of any rule types
    """
    @property
    def name(self):
        """
        Name attribute of rule element
        """
        return self.meta.name

    def add_after(self):
        pass
    
    def add_before(self):
        pass
    
    def all(self):
        """
        Enumerate all rules for this rule type. Return instance
        that has only meta data set (lazy loaded).
        
        :return: class type based on rule type 
        """
        #return self class instance by calling type
        return [type(self)(meta=Meta(**rule))
                for rule in search.element_by_href_as_json(self.href)]
    
    def _rule_l2_common(self, logical_interfaces):
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
    
    def _rule_common(self, sources, destinations, services):
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
    in :py:class:`smc.elements.network`.
        
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

        rule_values = self._rule_common(sources, destinations, services)
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

        return prepared_request(href=self.href,
                            json=rule_values).create()
        
class IPv4NATRule(Rule):
    """
    Manipulate NAT Rules for relevant policy types. Rule requirements are 
    similar to a normal rule with exception of the NAT field. 
    When specifying the destination or source NAT, you can use the string value
    IP address or the element href.
    
    It is possible to do source and destination NAT in the same rule, although it 
    is not possible to do static source NAT and dynamic source NAT together.
    
    Adding a Dynamic Source NAT rule for a layer 3 FW policy::
    
        network = Network.create('internal', '172.18.1.0/24').href
        policy = FirewallPolicy('Amazon Cloud')
        policy.fw_ipv4_nat_rules.create(name='sourcenat', 
                                        sources=[network], 
                                        destinations='any', 
                                        services='any',
                                        dynamic_src_nat={'ip_descriptor': '2.2.2.2'})
                                        
    Destination NAT, translated to '3.3.3.3'::
        
        policy.fw_ipv4_nat_rules.create(name='dstnat', 
                                        sources='any', 
                                        destinations=[host],
                                        services='any',
                                        static_dst_nat={'translated_value': {
                                                            'ip_descriptor': '3.3.3.3'}}) 
    
    Create an any/any no NAT rule::
    
        policy.fw_ipv4_nat_rules.create(name='nonat', 
                                        sources='any', 
                                        destinations='any', 
                                        services='any')
                                            
    """                                         
    def __init__(self, meta=None):
        self.meta = meta
  
    def create(self, name, sources=None, destinations=None, services=None,
               dynamic_src_nat=None, static_src_nat=None, static_dst_nat=None,
               is_disabled=False):
        """
        Create a NAT rule
       
        Source dynamic NAT data structure::
        
            dynamic_src_nat={'element': 'http://1.1.1.1',
                             'ip_descriptor': '',
                             'max_port': 65535,
                             'min_port': 1024}
        
        For dynamic source NAT provide either 'element' or 'ip_descriptor'.
        If both are provided, element will take precedence. Min and Max
        ports are optional and are used to define the ports used for PAT.
        
        Static dest NAT data structure::
        
            static_dst_nat = {'original_value': {'max_port': '',
                                                 'min_port': ''},
                              'translated_value': {'element': element,
                                                   'ip_descriptor': ip_descriptor,
                                                   'max_port': '',
                                                   'min_port': ''}}
        
        For static destination NAT provide either 'element' or 'ip_descriptor'
        for the 'translated_value' dict key. If both are provided, element will 
        take precedence. All other fields are optional, including 'original_value'
        key.
        Min and Max ports are optional and used for redirection to/from a specific
        port. If the service port for a rule uses HTTP on port 80, dest PAT will
        default to port 80 unless min/max ports are used. If port ranges are needed,
        use min/max ports to specify the source (original) and destiantion (translated)
        values. If a single port needs to be redirected, set min/max to the same values.
        
        :param str name: name of NAT rule
        :param list sources: list of source href's
        :param list destinations: list of destination href's
        :param list services: list of service href's
        :param dict dynamic_src_nat: ip or element href of dynamic source nat address
        :param dict static_dst_nat: ip or element href of host to redirect to
        :param boolean is_disabled: whether to disable rule or not
        :return: :py:class:`smc.api.web.SMCResult`
        """
        rule_values = self._rule_common(sources, destinations, services)
        rule_values.update(name=name)
        rule_values.update(is_disabled=is_disabled)
        
        options = {'log_accounting_info_mode': False,
                   'log_closing_mode': True,
                   'log_level': 'undefined',
                   'log_payload_additionnal': False,
                   'log_payload_excerpt': False,
                   'log_payload_record': False,
                   'log_severity': -1}

        if dynamic_src_nat:
            
            dyn_nat = {'dynamic_src_nat': {}}
            
            values = []
            values.append(dynamic_src_nat)
            translation_values = {'automatic_proxy': True,
                                  'translation_values': values}
            dyn_nat.update(dynamic_src_nat=translation_values)
            options.update(dyn_nat)
    
        elif static_src_nat:
            
            if isinstance(sources, list) and sources:
                source = sources[0]
                
                stat_nat = {'static_src_nat': {}}
                original_value={'automatic_proxy': True,
                                'original_value': {'element': source},
                                'translated_value': static_src_nat}
                
                stat_nat.update(static_src_nat=original_value)
                options.update(stat_nat)

        if static_dst_nat:
            
            if isinstance(destinations, list) and destinations:
                dest = destinations[0] #Destination should be 1-to-1
                
                original_value = {'element': dest}

                translated_value = {'element': None,
                                    'ip_descriptor': None}
                if 'original_value' in static_dst_nat:
                    original_value.update(static_dst_nat.get('original_value'))
                
                if 'translated_value' in static_dst_nat:
                    translated_value.update(static_dst_nat.get('translated_value'))
                    
                dst_nat = {'static_dst_nat': {'automatic_proxy': True,
                                              'original_value': original_value,
                                              'translated_value': translated_value}}
                
                options.update(dst_nat)
           
        rule_values.update(options=options)
        return prepared_request(href=self.href, json=rule_values).create()
    
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
        rule_values = self._rule_common(sources, destinations, services)
        rule_values.update(name=name)
        rule_values.update(is_disabled=is_disabled)
        
        actions = ['allow', 'continue', 'discard', 'refuse', 'blacklist']
        
        if action not in actions:
            action = 'allow'
        
        rule_values.update(action={'action': action,
                                   'connection_tracking_options':{}})
    
        rule_values.update(self._rule_l2_common(logical_interfaces))

        return prepared_request(href=self.href, json=rule_values).create()

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
        rule_values = self._rule_common(sources, destinations, services)
        rule_values.update(name=name)
        rule_values.update(is_disabled=is_disabled)
        
        actions = ['allow', 'continue', 'discard', 'refuse', 'blacklist']
        
        if action not in actions:
            action = 'allow'
        
        rule_values.update(action={'action': action,
                                   'connection_tracking_options':{}})
    
        rule_values.update(self._rule_l2_common(logical_interfaces))

        return prepared_request(href=self.href, json=rule_values).create()
    
class IPv6Rule(object):
    def __init__(self):
        pass
    
class IPv6NATRule(object):
    def __init__(self):
        pass
