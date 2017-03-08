"""
Rule module is a base class for all access control and NAT rules.

::

    Policy (base)
          |
    Layer3FirewallPolicy -----> fw_ipv4_access_rules
                                        |
                                        |
                              IPv4Rule / IPv4NATRule (smc.policy.rule.Rule)
                                  |            |
                                   ------------
                                        |
                                       name
                                       comment
                                       sources (smc.policy.rule_elements.Source)
                                       destinations (smc.policy.rule_elements.Destination)
                                       services (smc.policy.rule_elements.Service)
                                       action (smc.policy.rule_elements.Action)
                                       authentication_options (smc.policy.rule_elements.AuthenticationOptions)
                                       is_disabled
                                       disable
                                       enable
                                       options (smc.policy.rule_elements.LogOptions)
                                       parent_policy
                                             
For example, access policy information for a known Layer 3 policy:

.. code-block:: python

   policy = FirewallPolicy('mypolicy')
   for rule in policy.fw_ipv4_access_rules.all():
        if rule.name == 'foo':
            print(rule.destinations.all())  # Show all resolved destinations
            if rule.sources.is_any:
                print("Source set to any!")
            rule.destinations.add(Host('kali')) #Add a host
            rule.save()

"""
import smc.actions.search as search
from smc.base.model import Meta, SubElement, prepared_request
from smc.elements.other import LogicalInterface
from smc.vpn.policy import VPNPolicy
from smc.api.exceptions import ElementNotFound, MissingRequiredInput,\
    CreateRuleFailed, PolicyCommandFailed
from smc.policy.rule_elements import Action, LogOptions, Destination, Source,\
    Service, AuthenticationOptions

class Rule(object):
    """ 
    Top level rule construct with methods required to modify common 
    behavior of any rule types. To retrieve a rule, access by reference::
    
        policy = FirewallPolicy('mypolicy')
        for rule in policy.fw_ipv4_nat_rules.all():
            print(rule.name, rule.comment, rule.is_disabled)
            
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
    
    @property
    def action(self):
        """
        Action for this rule. 
        
        :return: :py:class:`smc.policy.rule_elements.Action`
        """
        return Action(self.data.get('action'), self.actions)
    
    @property
    def authentication_options(self):
        """
        Read only authentication options field
        
        :return: :py:class:`smc.policy.rule_elements.AuthenticationOptions`
        """
        return AuthenticationOptions(self.data.get('authentication_options'))
    
    @property
    def comment(self):
        """
        Optional comment for this rule.
        
        :param str value: string comment
        :return: str
        """
        return self.data.get('comment')
    
    @comment.setter
    def comment(self, value):
        self.data['comment'] = value
    
    @property
    def is_disabled(self):
        """
        Whether the rule is enabled or disabled
        
        :param boolean value: True, False
        :return: boolean
        """
        return self.data.get('is_disabled')
    
    def disable(self):
        """
        Disable this rule
        """
        self.data['is_disabled'] = True
    
    def enable(self):
        """
        Enable this rule
        """
        self.data['is_disabled'] = False

    @property
    def destinations(self):
        """
        Destinations for this rule
        
        :return: :py:class:`smc.policy.rule_elements.Destination`
        """
        return Destination(self.data.get('destinations'))
    
    @property
    def options(self):
        """
        Rule based options for logging. Enabling and
        disabled specific log settings.
        
        :return: :py:class:`smc.policy.rule_elements.LogOptions`
        """
        return LogOptions(self.data.get('options'))
    
    @property
    def parent_policy(self):
        """
        Read-only name of the parent policy
        
        :return: str
        """
        return search.element_name_by_href(self.data.get('parent_policy'))

    def save(self):
        """
        After making changes to a rule element, you must call save
        to apply the changes.
        
        :raises: :py:class:`smc.api.exceptions.PolicyCommandFailed`
        :return: None
        """
        prepared_request(PolicyCommandFailed,
                         href=self.href, json=self.data,
                         etag=self.etag).update()
    
    @property
    def services(self):
        """
        Services assigned to this rule
        
        :return: :py:class:`smc.policy.rule_elements.Service`
        """
        return Service(self.data.get('services'))
    
    @property
    def sources(self):
        """
        Sources assigned to this rule
        
        :return: :py:class:`smc.policy.rule_elements.Source`
        """
        return Source(self.data.get('sources'))
    
    #@property
    #def time_range(self):
    #    """
    #    Time range/s assigned to this rule. May be None if 
    #    no time range configured.
    #    
    #    :return: :py:class:`smc.policy.rule_elements.TimeRange`
    #    """
    #    trange = self.data.get('time_range')
    #    if trange:
    #        return TimeRange(self.data.get('time_range'))
    
    def all(self):
        """
        Enumerate all rules for this rule type. Return instance
        that has only meta data set (lazy loaded).
        
        :return: class type based on rule type 
        """
        return [type(self)(meta=Meta(**rule))
                for rule in search.element_by_href_as_json(self.href)]
    
class IPv4Rule(Rule, SubElement):
    """ 
    Represents an IPv4 Rule for a layer 3 engine.
    
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
    
    Source entries using network elements::
    
        sources=[Host('myhost'), Network('thenetwork'), AddressRange('range')]
    
    Services have a similar syntax and can take any type of :py:class:`smc.elements.service`
    or  the element href or both::
        
            services=['http://1.1.1.1/8082/elements/tcp_service/mytcpservice',
                      'http://1.1.1.1/8082/elements/udp_server/myudpservice',
                      TCPService('myservice')], etc
        
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

    """
    typeof = 'fw_ipv4_access_rule'
    
    def __init__(self, meta=None):
        super(IPv4Rule, self).__init__(meta)
        self.actions = ['allow', 'discard', 'continue', 
                        'refuse', 'jump', 'apply_vpn', 
                        'enforce_vpn', 'forward_vpn', 
                        'blacklist']

    def create(self, name, sources=None, destinations=None, 
               services=None, action='allow', is_disabled=False, 
               vpn_policy=None, **kwargs):
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
        :raises: :py:class:`smc.api.exceptions.MissingRequiredInput` when options are
                 specified the need additional setting, i.e. use_vpn action requires a
                 vpn policy be specified.
        :raises: :py:class:`smc.api.exceptions.CreateRuleFailed`: rule creation failure
        :return: str href: href of new rule
        """
        rule_values = _rule_common(sources, destinations, services)
        rule_values.update(name=name)
       
        rule_action = Action(actions=self.actions)
        rule_action.action = action
        
        if rule_action.action in ['apply_vpn', 'enforce_vpn', 'forward_vpn']:
            if vpn_policy is None:
                raise MissingRequiredInput('A VPN policy must be specified when '
                                           'rule action has a VPN action')
            try:
                vpn = VPNPolicy(vpn_policy).href
                rule_action.vpn = vpn
            except ElementNotFound:
                raise MissingRequiredInput('Cannot find VPN policy specified: {}, '
                                           .format(vpn_policy))
        
        rule_values.update(rule_action())
        
        log_options = LogOptions()    
        auth_options = AuthenticationOptions()
        
        rule_values.update(log_options())
        rule_values.update(auth_options())
        rule_values.update(is_disabled=is_disabled)
        
        return prepared_request(CreateRuleFailed,
                                href=self.href,
                                json=rule_values).create().href
        
class IPv4Layer2Rule(Rule, SubElement):
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
        super(IPv4Layer2Rule, self).__init__(meta)
        self.actions = ['allow', 'continue', 'discard', 
                        'refuse', 'jump', 'blacklist']
        
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
        :param str action: \|allow\|continue\|discard\|refuse\|blacklist
        :param boolean is_disabled: whether to disable rule or not
        :raises: :py:class:`smc.api.exceptions.MissingReuqiredInput` when options are
                 specified the need additional setting, i.e. use_vpn action requires a
                 vpn policy be specified.
        :raises: :py:class:`smc.api.exceptions.CreateRuleFailed`: rule creation failure
        :return: str href: href of new rule
        """
        rule_values = _rule_common(sources, destinations, services)
        rule_values.update(name=name)
        rule_values.update(is_disabled=is_disabled)
        
        rule_action = Action(actions=self.actions)
        rule_action.action = action
        rule_values.update(rule_action())
    
        rule_values.update(_rule_l2_common(logical_interfaces))
        
        return prepared_request(CreateRuleFailed,
                                href=self.href, 
                                json=rule_values).create().href
    
class EthernetRule(Rule, SubElement):
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
        super(EthernetRule, self).__init__(meta)
        self.actions = ['allow', 'discard']
    
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
        :param str action: \|allow\|continue\|discard\|refuse\|blacklist
        :param boolean is_disabled: whether to disable rule or not
        :raises: :py:class:`smc.api.exceptions.MissingReuqiredInput` when options are
                 specified the need additional setting, i.e. use_vpn action requires a
                 vpn policy be specified.
        :raises: :py:class:`smc.api.exceptions.CreateRuleFailed`: rule creation failure
        :return: str href: href of new rule
        """
        rule_values = _rule_common(sources, destinations, services)
        rule_values.update(name=name)
        rule_values.update(is_disabled=is_disabled)
        
        rule_action = Action(actions=self.actions)
        rule_action.action = action
        rule_values.update(rule_action())

        rule_values.update(_rule_l2_common(logical_interfaces))

        return prepared_request(CreateRuleFailed,
                                href=self.href, 
                                json=rule_values).create().href
        
class IPv6Rule(IPv4Rule):
    """
    IPv6 access rule defines sources and destinations that must be
    in IPv6 format. 
    
    .. note:: It is possible to submit a source or destination in
              IPv4 format, however this will fail validation when
              attempting to push policy.
    """
    typeof = 'fw_ipv6_access_rule'
    
    def __init__(self, meta=None):
        super(IPv6Rule, self).__init__(meta)
        pass        
       
def _rule_l2_common(logical_interfaces):
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

def _rule_common(sources, destinations, services):
    """
    Common rule elements
    """
    source = Source()
    destination = Destination()
    service = Service()
    
    if sources is not None:
        if isinstance(sources, str) and sources.lower() == 'any':
            source.set_any()
        else:
            source.add_many(sources)
    else:
        source.set_none()
    
    if destinations is not None:
        if isinstance(destinations, str) and destinations.lower() == 'any':
            destination.set_any()
        else:
            destination.add_many(destinations)
    else:
        destination.set_none()
                
    if services is not None:
        if isinstance(services, str) and services.lower() == 'any':
            service.set_any()
        else:
            service.add_many(services)
    else:
        service.set_none()
    
    e = {}
    e.update(source())
    e.update(destination())
    e.update(service())
    return e
