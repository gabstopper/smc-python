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
                                       tag
                                       ...
                                             
Examples of rule operations::

    >>> from smc.policy.layer3 import FirewallPolicy
    >>> from smc.policy.rule_elements import LogOptions
    >>> from smc.policy.rule_elements import Action
    >>> from smc.elements.other import Alias
    ...
    >>> options = LogOptions()
    >>> options.log_accounting_info_mode=True
    >>> options.log_level='stored'
    ...
    >>> policy = FirewallPolicy('AWS_Default')
    >>> options = LogOptions()
    >>> options.log_accounting_info_mode=True
    >>> options.log_level='stored'
    >>> policy.fw_ipv4_access_rules.create(name='mylogrule',services='any',sources='any',destinations='any',actions='continue',log_options=options)
    'http://172.18.1.150:8082/6.2/elements/fw_policy/272/fw_ipv4_access_rule/2099703'
    ...
    >>> actions = Action()
    >>> actions.deep_inspection = True
    >>> actions.file_filtering=False
    ...
    >>> policy.fw_ipv4_access_rules.create(name='outbound',sources=[Alias('$$ Interface ID 1.net')],destinations='any',services='any',action=actions,log_options=options)
    'http://172.18.1.150:8082/6.2/elements/fw_policy/272/fw_ipv4_access_rule/2099704'
    >>> for rule in policy.fw_ipv4_access_rules.all():
    ...   print(rule)
    ... 
    IPv4Rule(name=outbound)
    IPv4Rule(name=mylogrule)
    ...
    >>> policy.search_rule('outbound')
    [IPv4Rule(name=outbound)]
    ...
    >>> policy.fw_ipv4_access_rules.create(name='discard at bottom', sources='any',destinations='any',services='any',action='discard',add_pos=50)
    'http://172.18.1.150:8082/6.2/elements/fw_policy/272/fw_ipv4_access_rule/2099705'
    >>> for rule in policy.fw_ipv4_access_rules.all():
    ...   print(rule, rule.name, rule.action.action)
    ... 
    IPv4Rule(name=outbound) outbound allow
    IPv4Rule(name=mylogrule) mylogrule allow
    IPv4Rule(name=discard at bottom) discard at bottom discard

"""
from smc.base.model import Element, SubElement, prepared_request
from smc.elements.other import LogicalInterface
from smc.vpn.policy import VPNPolicy
from smc.api.exceptions import ElementNotFound, MissingRequiredInput,\
    CreateRuleFailed, PolicyCommandFailed, FetchElementFailed
from smc.policy.rule_elements import Action, LogOptions, Destination, Source,\
    Service, AuthenticationOptions, TimeRange
from smc.base.util import element_resolver


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
        return self._meta.name

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
        return Action(self.data.get('action'))

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
        :rtype: str
        """
        return self.data.get('comment')

    @comment.setter
    def comment(self, value):
        self.data['comment'] = value

    @property
    def is_disabled(self):
        """
        Whether the rule is enabled or disabled

        :param bool value: True, False
        :rtype: boolean
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

        :return: :py:class:`smc.base.model.Element` of type policy
        """
        return Element.from_href(self.data.get('parent_policy'))

    def save(self):
        """
        After making changes to a rule element, you must call save
        to apply the changes. Rule changes are made to cache before
        sending to SMC.

        :raises PolicyCommandFailed: failed to save with reason
        :return: None
        """
        self.update(PolicyCommandFailed)

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

    @property
    def tag(self):
        """
        Value of rule tag. Read only.

        :return: rule tag
        :rtype: str
        """
        return self.data.get('tag')

    #@property
    # def time_range(self):
    #    """
    #    Time range/s assigned to this rule. May be None if
    #    no time range configured.

    #    :return: :py:class:`smc.policy.rule_elements.TimeRange`
    #    """
    #    time_range = self.data.get('time_range')
    #    if time_range:
    #        return TimeRange(self.data.get('time_range'))


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

            services=[TCPService('myservice'),
                      'http://1.1.1.1/8082/elements/tcp_service/mytcpservice',
                      'http://1.1.1.1/8082/elements/udp_server/myudpservice'], etc

    You can obtain services and href for the elements by using the 
    :py:class:`smc.base.collection` collections::

        >>> services = list(TCPService.objects.filter('80'))
        >>> for service in services:
        ...   print(service, service.href)
        ... 
        (TCPService(name=tcp80443), u'http://172.18.1.150:8082/6.1/elements/tcp_service/3535')
        (TCPService(name=HTTP to Web SaaS), u'http://172.18.1.150:8082/6.1/elements/tcp_service/589')
        (TCPService(name=HTTP), u'http://172.18.1.150:8082/6.1/elements/tcp_service/440')

    Services by application (get all facebook applications)::

        >>> applications = Search('application_situation').objects.filter('facebook')
        >>> print(list(applications))
        [ApplicationSituation(name=Facebook-Plugins-Share-Button), ApplicationSituation(name=Facebook-Plugins]
        ...

    Sources / Destinations and Services can also take the string value 'any' to
    allow all. For example::

        sources='any'
    """
    typeof = 'fw_ipv4_access_rule'

    def __init__(self, **meta):
        super(IPv4Rule, self).__init__(**meta)
        self._actions = ['allow', 'discard', 'continue',
                         'refuse', 'jump', 'apply_vpn',
                         'enforce_vpn', 'forward_vpn',
                         'blacklist']

    def create(self, name, sources=None, destinations=None,
               services=None, action='allow', log_options=None,
               is_disabled=False, vpn_policy=None, add_pos=None,
               after=None, before=None, sub_policy=None, **kwargs):
        """ 
        Create a layer 3 firewall rule

        :param str name: name of rule
        :param list[str, Element] sources: source/s for rule
        :type sources: list[str, Element]
        :param destinations: destination/s for rule
        :type destinations: list[str, Element]
        :param services: service/s for rule
        :type services: list[str, Element]
        :param action: allow,continue,discard,refuse,enforce_vpn,
            apply_vpn,blacklist (default: allow)
        :type action: Action or str
        :param LogOptions log_options: LogOptions object
        :param str: vpn_policy: vpn policy name; required for enforce_vpn and apply_vpn 
               actions
        :param str,Element sub_policy: sub policy required when rule has an action of 'jump'.
            Can be the FirewallSubPolicy element or href.
        :param int add_pos: position to insert the rule, starting with position 1. If
            the position value is greater than the number of rules, the rule is inserted at
            the bottom. If add_pos is not provided, rule is inserted in position 1. Mutually
            exclusive with ``after`` and ``before`` params.
        :param str after: Rule tag to add this rule after. Mutually exclusive with ``add_pos``
            and ``before`` params.
        :param str before: Rule tag to add this rule before. Mutually exclusive with ``add_pos``
            and ``after`` params.
        :raises MissingRequiredInput: when options are specified the need additional 
            setting, i.e. use_vpn action requires a vpn policy be specified.
        :raises CreateRuleFailed: rule creation failure
        :return: href of new element
        :rtype: str
        """
        rule_values = _rule_common(sources, destinations, services)
        rule_values.update(name=name)

        if isinstance(action, Action):
            rule_action = action
        else:
            rule_action = Action()
            rule_action.action = action

        if not rule_action.action in self._actions:
            raise CreateRuleFailed('Action specified is not valid for this '
                                   'rule type; action: {}'
                                   .format(rule_action.action))

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
        elif rule_action.action in ['jump']:
            try:
                rule_action.sub_policy = element_resolver(sub_policy)
            except ElementNotFound:
                raise MissingRequiredInput('Cannot find sub policy specified: {} '
                                           .format(sub_policy))
        
        rule_values.update(rule_action())

        if log_options is None:
            log_options = LogOptions()

        auth_options = AuthenticationOptions()

        rule_values.update(log_options())
        rule_values.update(auth_options())
        rule_values.update(is_disabled=is_disabled)

        if add_pos is not None:
            href = _add_position(add_pos, self.href)
        else:
            href = self.href

        params = None
        if not add_pos:
            if after is not None:
                params = {'after': after}
            elif before is not None:
                params = {'before': before}

        return prepared_request(
            CreateRuleFailed,
            href=href,
            params=params,
            json=rule_values
        ).create().href


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

    def __init__(self, **meta):
        super(IPv4Layer2Rule, self).__init__(**meta)
        self._actions = ['allow', 'continue', 'discard',
                         'refuse', 'jump', 'blacklist']

    def create(self, name, sources=None, destinations=None,
               services=None, action='allow', is_disabled=False,
               logical_interfaces=None, add_pos=None):
        """
        Create an IPv4 Layer 2 FW rule

        :param str name: name of rule
        :param sources: source/s for rule
        :type sources: list[str, Element]
        :param destinations: destination/s for rule
        :type destinations: list[str, Element]
        :param services: service/s for rule
        :type services: list[str, Element]
        :param list logical_interfaces: logical interfaces by name
        :param str, Action action: \|allow\|continue\|discard\|refuse\|blacklist
        :param bool is_disabled: whether to disable rule or not
        :raises MissingRequiredInput: when options are specified the need additional
            setting, i.e. use_vpn action requires a vpn policy be specified.
        :raises CreateRuleFailed: rule creation failure
        :return: href of new element
        :rtype: str
        """
        rule_values = _rule_common(sources, destinations, services)
        rule_values.update(name=name)
        rule_values.update(is_disabled=is_disabled)

        if isinstance(action, Action):
            rule_action = action
        else:
            rule_action = Action()
            rule_action.action = action

        if not rule_action.action in self._actions:
            raise CreateRuleFailed('Action specified is not valid for this '
                                   'rule type; action: {}'
                                   .format(rule_action.action))

        rule_values.update(rule_action())

        rule_values.update(_rule_l2_common(logical_interfaces))

        if add_pos is not None:
            href = _add_position(add_pos, self.href)
        else:
            href = self.href

        return prepared_request(
            CreateRuleFailed,
            href=href,
            json=rule_values
        ).create().href


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

    def __init__(self, **meta):
        super(EthernetRule, self).__init__(**meta)
        self._actions = ['allow', 'discard']

    def create(self, name, sources=None, destinations=None,
               services=None, action='allow', is_disabled=False,
               logical_interfaces=None, add_pos=None):
        """
        Create an Ethernet rule

        :param str name: name of rule
        :param sources: source/s for rule
        :type sources: list[str, Element]
        :param destinations: destination/s for rule
        :type destinations: list[str, Element]
        :param services: service/s for rule
        :type services: list[str, Element]
        :param list logical_interfaces: logical interfaces by name
        :param str action: \|allow\|continue\|discard\|refuse\|blacklist
        :param bool is_disabled: whether to disable rule or not
        :raises MissingReuqiredInput: when options are specified the need additional
            setting, i.e. use_vpn action requires a vpn policy be specified.
        :raises CreateRuleFailed: rule creation failure
        :return: href of new element
        :rtype: str
        """
        rule_values = _rule_common(sources, destinations, services)
        rule_values.update(name=name)
        rule_values.update(is_disabled=is_disabled)

        if isinstance(action, Action):
            rule_action = action
        else:
            rule_action = Action()
            rule_action.action = action

        if not rule_action.action in self._actions:
            raise CreateRuleFailed('Action specified is not valid for this '
                                   'rule type; action: {}'
                                   .format(rule_action.action))

        rule_values.update(rule_action())

        rule_values.update(_rule_l2_common(logical_interfaces))

        if add_pos is not None:
            href = _add_position(add_pos, self.href)
        else:
            href = self.href

        return prepared_request(
            CreateRuleFailed,
            href=href,
            json=rule_values
        ).create().href


class IPv6Rule(IPv4Rule):
    """
    IPv6 access rule defines sources and destinations that must be
    in IPv6 format. 

    .. note:: It is possible to submit a source or destination in
              IPv4 format, however this will fail validation when
              attempting to push policy.
    """
    typeof = 'fw_ipv6_access_rule'

    def __init__(self, **meta):
        super(IPv6Rule, self).__init__(**meta)
        pass


def _add_position(pos, rules_href):
    """
    Add the position for the rule. If the position is a larger number
    than number of rules, it will be placed at the end. Otherwise
    inserted into the position specified.
    """
    if pos <= 0:
        pos = 1
    rules = prepared_request(
        FetchElementFailed, href=rules_href).read().json
    if rules:
        if len(rules) >= pos:  # Position somewhere in the list
            for position, entry in enumerate(rules):
                if position + 1 == pos:
                    return SubElement(**entry).data.get_link('add_before')
        else:  # Put at the end
            last_rule = rules.pop()
            return SubElement(**last_rule).data.get_link('add_after')
    return rules_href


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
            logicals = []
            for interface in logical_interfaces:
                logicals.append(LogicalInterface(interface).href)
            rule_values.update(logical_interfaces={
                               'logical_interface': logicals})
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
