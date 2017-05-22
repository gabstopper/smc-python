from smc.base.model import Element, ElementCreator
from smc.api.exceptions import ElementNotFound
from smc.base.util import element_resolver


class RuleElement(object):
    @property
    def is_any(self):
        """
        Is the field set to any

        :rtype: bool
        """
        return 'any' in self.data

    def set_any(self):
        """
        Set field to any
        """
        self.data.clear()
        self.data.update({'any': True})

    @property
    def is_none(self):
        """
        Is the field set to none

        :rtype: bool
        """
        return 'none' in self.data

    def set_none(self):
        """
        Set field to none
        """
        self.data.clear()
        self.data.update({'none': True})

    def add(self, data):
        """
        Add a single entry to field.

        Entries can be added to a rule using the href of the element
        or by loading the element directly. Element should be of type
        :py:mod:`smc.elements.network`.
        After modifying rule, call :py:meth:`~.save`.

        Example of adding entry by element::

            policy = FirewallPolicy('policy')
            for rule in policy.fw_ipv4_nat_rules.all():
                if rule.name == 'therule':
                    rule.sources.add(Host('myhost'))
                    rule.save()

        .. note:: If submitting type Element and the element cannot be
                  found, it will be skipped.

        :param data: entry to add
        :type data: Element or str
        """
        if self.is_none or self.is_any:
            self.data.clear()
            self.data[self.typeof] = []

        try:
            self.data[self.typeof].append(element_resolver(data))
        except ElementNotFound:
            pass

    def add_many(self, data):
        """
        Add multiple entries to field. Entries should be list format.
        Entries can be of types relavant to the field type. For example,
        for source and destination fields, elements may be of type 
        :py:mod:`smc.elements.network` or be the elements direct href,
        or a combination of both.

        Add several entries to existing rule::

            policy = FirewallPolicy('policy')
            for rule in policy.fw_ipv4_nat_rules.all():
                if rule.name == 'therule':
                    rule.sources.add_many([Host('myhost'), 
                                          'http://1.1.1.1/hosts/12345'])
                    rule.save()

        :param list data: list of sources

        .. note:: If submitting type Element and the element cannot be
                  found, it will be skipped.
        """
        assert isinstance(data, list), "Incorrect format. Expecting list."
        if self.is_none or self.is_any:
            self.data.clear()
            self.data[self.typeof] = []

        data = element_resolver(data, do_raise=False)
        self.data[self.typeof] = data

    def all_as_href(self):
        """
        Return all elements without resolving to :class:`smc.elements.network`
        or :class:`smc.elements.service`. Just raw representation as href.

        :return: elements in href form
        :rtype: list
        """
        if not self.is_any and not self.is_none:
            return [element for element in self.data[self.typeof]]

    def all(self):
        """
        Return all destinations for this rule. Elements returned
        are of the object type for the given element for further
        introspection.

        Search the fields in rule::

            for sources in rule.sources.all():
                print('My source: %s' % sources)

        :return: elements by resolved object type
        :rtype: list(Element)
        """
        if not self.is_any and not self.is_none:
            return [Element.from_href(href)
                    for href in self.data[self.typeof]]
        return []


class Destination(RuleElement):
    typeof = 'dst'

    def __init__(self, data=None):
        self.data = {'none': True} if data is None else data

    def __call__(self):
        return {'destinations': self.data}


class Source(RuleElement):
    typeof = 'src'

    def __init__(self, data=None):
        self.data = {'none': True} if data is None else data

    def __call__(self):
        return {'sources': self.data}


class Service(RuleElement):
    typeof = 'service'

    def __init__(self, data=None):
        self.data = {'none': True} if data is None else data

    def __call__(self):
        return {'services': self.data}


class Action(object):
    """
    This represents the action associated with the rule.
    """
    def __init__(self, data=None):
        if data is None:
            conn = ConnectionTracking()
            self.data = {'action': 'allow'}
            self.data.update(conn())
            self.data.update(scan_detection='undefined')
        else:
            self.data = data

    def __call__(self):
        return {'action': self.data}

    @property
    def action(self):
        """
        Action set for this rule

        :param str value: allow\|discard\|continue\|refuse\|jump\|apply_vpn
                          \|enforce_vpn\|forward_vpn\|blacklist\|terminate
        :rtype: str
        """
        return self.data.get('action')

    @action.setter
    def action(self, value):
        self.data['action'] = value

    @property
    def connection_tracking_options(self):
        """
        Enables connection tracking.
        The firewall allows or discards packets according to the selected Connection
        Tracking mode. Reply packets are allowed as part of the allowed connection
        without an explicit Access rule. Protocols that use a dynamic port assignment
        must be allowed using a Service with the appropriate Protocol Agent for that
        protocol (in Access rules and NAT rules).

        :return: :py:class:`smc.policy.rule_elements.ConnectionTracking`
        """
        return ConnectionTracking(self.data.get('connection_tracking_options'))

    @property
    def deep_inspection(self):
        """
        Selects traffic that matches this rule for checking against the Inspection
        Policy referenced by this policy. Traffic is inspected as the Protocol that
        is attached to the Service element in this rule.

        :param bool value: True, False
        :rtype: bool
        """
        return self.data.get('deep_inspection')

    @deep_inspection.setter
    def deep_inspection(self, value):
        self.data['deep_inspection'] = value

    @property
    def file_filtering(self):
        """
        (IPv4 Only) Inspects matching traffic against the File Filtering policy.
        Selecting this option should also activates the Deep Inspection option.
        You can further adjust virus scanning in the Inspection Policy. 

        :param bool value: True, False
        :rtype: bool
        """
        return self.data.get('file_filtering')

    @file_filtering.setter
    def file_filtering(self, value):
        self.data['file_filtering'] = value

    @property
    def dos_protection(self):
        """
        Enable or disable DOS protection mode

        :param bool value: True, False
        :rtype: bool
        """
        return self.data.get('dos_protection')

    @dos_protection.setter
    def dos_protection(self, value):
        self.data['dos_protection'] = value

    @property
    def scan_detection(self):
        """
        Enable or disable Scan Detection for traffic that matches the
        rule. This overrides the option set in the Engine properties.

        Enable scan detection on this rule::

            for rule in policy.fw_ipv4_access_rules.all():
                rule.action.scan_detection = 'on'

        :param str value: on\|off\|undefined
        :return: scan detection setting (on,off,undefined)
        :rtype: str
        """
        return self.data.get('scan_detection')

    @scan_detection.setter
    def scan_detection(self, value):
        if value in ['on', 'off', 'undefined']:
            self.data['scan_detection'] = value

    @property
    def sub_policy(self):
        """
        Sub policy is used when ``action=jump``.
        
        :rtype: FirewallSubPolicy
        """
        if 'sub_policy' in self.data:
            return Element.from_href(self.data['sub_policy'])

    @sub_policy.setter
    def sub_policy(self, value):
        self.data['sub_policy'] = element_resolver(value)
    
    @property
    def user_response(self):
        """
        Read-only user response setting
        """
        return self.data.get('user_response')

    @property
    def vpn(self):
        """
        Return vpn reference. Only used if 'enforce_vpn', 'apply_vpn',
        or 'forward_vpn' is the action type.

        :rtype: VPNPolicy
        """
        if 'vpn' in self.data:
            return self.data.get('vpn')

    @vpn.setter
    def vpn(self, value):
        self.data['vpn'] = value

    @property
    def mobile_vpn(self):
        """
        Mobile VPN only applies to engines that support VPN and that
        have the action of 'enforce_vpn', 'apply_vpn' or 'forward_vpn'
        set. This will enable mobile VPN traffic on this VPN rule.

        :return: mobile vpn enabled
        :rtype: boolean
        """
        return self.data.get('mobile_vpn')

    @mobile_vpn.setter
    def mobile_vpn(self, value):
        self.data['mobile_vpn'] = value


class ConnectionTracking(object):
    """
    Connection tracking settings can be configured on a per rule basis to
    control settings such as enforced MSS and how to handle connection states.

    Configuring a rule to enable MSS and set connection state tracking to
    normal::

        for rule in policy.fw_ipv4_access_rules.all():
            rule.action.connection_tracking_options.mss_enforced = True
            rule.action.connection_tracking_options.state = 'normal'
            rule.action.connection_tracking_options.mss_enforced_min_max = (1400, 1450)
            rule.save()
    """
    def __init__(self, data=None):
        self.data = {'mss_enforced': False,
                     'mss_enforced_max': 0,
                     'mss_enforced_min': 0,
                     'timeout': -1} if data is None else data

    def __call__(self):
        return {'connection_tracking_options': self.data}

    @property
    def mss_enforced(self):
        """
        Is MSS enforced

        :param bool value: True, False
        :return: bool
        """
        return self.data.get('mss_enforced')

    @mss_enforced.setter
    def mss_enforced(self, value):
        self.data['mss_enforced'] = value

    @property
    def mss_enforced_min_max(self):
        """
        Allows entering the Minimum and Maximum value for the MSS in bytes.
        Headers are not included in the MSS value; MSS concerns only the
        payload portion of the packet.

        :param tuple int value: tuple containing (min, max) in bytes
        :return: (min, max) values
        :rtype: tuple
        """
        return (self.data.get('mss_enforced_min'),
                self.data.get('mss_enforced_max'))

    @mss_enforced_min_max.setter
    def mss_enforced_min_max(self, value):
        if isinstance(value, tuple):
            minimum, maximum = value
            self.data['mss_enforced_min'] = minimum
            self.data['mss_enforced_max'] = maximum

    @property
    def state(self):
        """
        Connection tracking mode. See Stonesoft documentation for
        more info.

        :param str value: no,loose,normal,strict
        :return: str
        """
        return self.data.get('state')

    @state.setter
    def state(self, value):
        self.data['state'] = value

    @property
    def timeout(self):
        """
        The timeout (in seconds) after which inactive connections are closed.
        This timeout only concerns idle connections. Connections are not cut
        because of timeouts while the hosts are still communicating.

        :param int value: time in seconds
        :return: int
        """
        return self.data.get('timeout')

    @timeout.setter
    def timeout(self, value):
        self.data['timeout'] = value


class LogOptions(object):
    """
    Log Options represent the settings related to per rule logging.

    Example of obtaining a rule reference and turning logging on 
    for a particular rule::

        policy = FirewallPolicy('smcpython')
        for rule in policy.fw_ipv4_access_rules.all():
            if rule.name == 'foo':
                rule.options.log_accounting_info_mode = True
                rule.options.log_level = 'stored'
                rule.options.application_logging = 'enforced'
                rule.options.user_logging = 'enforced'
                rule.save()
    """
    def __init__(self, data=None):
        self.data = {'log_accounting_info_mode': False,
                     'log_closing_mode': True,
                     'log_level': 'undefined',
                     'log_payload_additionnal': False,
                     'log_payload_excerpt': False,
                     'log_payload_record': False,
                     'log_severity': -1} if data is None else data

    def __call__(self):
        return {'options': self.data}

    @property
    def application_logging(self):
        """
        Stores information about Application use. You can log spplication
        use even if you do not use Applications for access control.

        :param str value: off\|default\|enforced
        :return: str
        """
        return self.data.get('application_logging')

    @application_logging.setter
    def application_logging(self, value):
        if value in ['off', 'default', 'enforced']:
            self.data['application_logging'] = value

    @property
    def log_accounting_info_mode(self):
        """
        Both connection opening and closing are logged and information
        on the volume of traffic is collected. This option is not 
        available for rules that issue alerts.
        If you want to create reports that are based on traffic volume, 
        you must select this option for all rules that allow traffic that
        you want to include in the reports.

        :param bool value: log accounting information (bits/bytes transferred)
        :return: bool 
        """
        return self.data.get('log_accounting_info_mode')

    @log_accounting_info_mode.setter
    def log_accounting_info_mode(self, value):
        self.data['log_accounting_info_mode'] = value

    @property
    def log_closing_mode(self):
        """
        Specifying False means no log entries are created when 
        connections are closed. True will mean both connection 
        opening and closing are logged, but no information is 
        collected on the volume of traffic.

        :param bool value: enable/disable accounting data
        :return: bool
        """
        return self.data.get('log_closing_mode')

    @log_closing_mode.setter
    def log_closing_mode(self, value):
        self.data['log_closing_mode'] = value

    @property
    def log_level(self):
        """
        Configure per rule logging. It is recommended to configure an
        Any/Any/Any/Continue rule in position 1 if global logging is 
        required. This can be used to override any global logging setting.

        :param str value: none\|stored\|transient\|essential\|alert
        :return: str
        """
        return self.data.get('log_level')

    @log_level.setter
    def log_level(self, value):
        if value in ['none', 'stored', 'transient', 'essential', 'alert']:
            self.data['log_level'] = value
        if not self.log_accounting_info_mode:
            self.log_accounting_info_mode = True

    @property
    def log_payload_additional(self):
        """
        Stores packet payload extracted from the traffic. The collected 
        payload provides information for some of the additional log fields
        depending on the type of traffic.

        :param bool value: True, False
        :return: bool
        """
        return self.data.get('log_payload_additionnal')

    @log_payload_additional.setter
    def log_payload_additional(self, value):
        self.data['log_payload_additionnal'] = value

    @property
    def log_payload_excerpt(self):
        """
        Stores an excerpt of the packet that matched. The maximum recorded
        excerpt size is 4 KB. This allows quick viewing of the payload in
        the logs view.

        :param bool value: collect excerpt or not
        :return: bool
        """
        return self.data.get('log_payload_excerpt')

    @log_payload_excerpt.setter
    def log_payload_excerpt(self, value):
        self.data['log_payload_excerpt'] = value

    @property
    def log_payload_record(self):
        """
        Records the traffic up to the limit that is set in the Record 
        Length field.

        :param bool value: True, False
        :return: bool
        """
        return self.data.get('log_payload_record')

    @log_payload_record.setter
    def log_payload_record(self, value):
        self.data['log_payload_record'] = value

    @property
    def log_severity(self):
        """
        Read only log severity level

        :return: str
        """
        return self.data.get('log_severity')

    @property
    def user_logging(self):
        """
        Stores information about Users when they are used as the Source
        or Destination of an Access rule.
        You must select this option if you want Users to be referenced by
        name in log entries, statistics, reports, and user monitoring.
        Otherwise, only the IP address associated with the User at the time
        the log was created is stored.

        :param str value: false\|true\|enforced
        :return: str
        """
        return self.data.get('user_logging')

    @user_logging.setter
    def user_logging(self, value):
        if value in ['true', 'false', 'enforced']:
            self.data['user_logging'] = value


class AuthenticationOptions(object):
    """
    Authentication options are set on a per rule basis and dictate
    whether a user requires identification to match.
    """

    def __init__(self, data=None):
        self.data = {'methods': [],
                     'require_auth': False,
                     'timeout': 3600,
                     'users': []} if data is None else data

    def __call__(self):
        return {'authentication_options': self.data}

    @property
    def methods(self):
        """
        Read only authentication methods enabled

        :return: list value: auth methods enabled
        """
        return self.data.get('methods')

    @property
    def require_auth(self):
        """
        Ready only authentication required

        :return: boolean
        """
        return self.data.get('require_auth')

    @property
    def timeout(self):
        """
        Timeout between authentications

        :return: int
        """
        return self.data.get('timeout')

    @property
    def users(self):
        """
        List of users required to authenticate

        :return: list
        """
        return self.data.get('users')


class TimeRange(object):
    """
    Represents a time range setting for a given rule.
    Time ranges can currently be set up to support rules based
    on starting month and ending month. At that time the rule
    will be disabled automatically.
    """

    def __init__(self, data):
        self.data = data

    @property
    def day_ranges(self):
        """
        Not Yet Implemented
        """
        pass

    @property
    def month_range_start(self):
        """
        Starting month for rule validity. Use this with month_range_end.

        :param str jan,feb,mar,apr,may,jun,jul,aug,sep,oct,nov,dec
        """
        return self.data.get('month_range_start')

    @month_range_start.setter
    def month_range_start(self, value):
        self.data['month_range_start'] = value

    @property
    def month_range_end(self):
        """
        Set month end range. Use this with month_range_start.

        :param str jan,feb,mar,apr,may,jun,jul,aug,sep,oct,nov,dec
        """
        return self.data.get('month_range_end')

    @month_range_end.setter
    def month_range_end(self, value):
        self.data['month_range_end'] = value


class MatchExpression(Element):
    """
    A match expression is used in the source / destination / service fields to group
    together elements into an 'AND'ed configuration. For example, a normal rule might
    have a source field that could include network=172.18.1.0/24 and zone=Internal 
    objects. A match expression enables you to AND these elements together to enforce
    the match requires both. Logically it would be represented as
    (network 172.18.1.0/24 AND zone Internal).

        >>> from smc.elements.network import Host, Zone
        >>> from smc.policy.rule_elements import MatchExpression
        >>> from smc.policy.layer3 import FirewallPolicy
        >>> match = MatchExpression.create(name='mymatch', network_element=Host('kali'), zone=Zone('Mail'))
        >>> policy = FirewallPolicy('smcpython')
        >>> policy.fw_ipv4_access_rules.create(name='myrule', sources=[match], destinations='any', services='any')
        'http://172.18.1.150:8082/6.2/elements/fw_policy/261/fw_ipv4_access_rule/2099740'
        >>> rule = policy.search_rule('myrule')
        ...
        >>> for source in rule[0].sources.all():
        ...   print(source, source.values())
        ... 
        MatchExpression(name=MatchExpression _1491760686976_2) [Zone(name=Mail), Host(name=kali)]

    .. note:: 
        MatchExpression is currently only supported on source and destination fields.

    """
    typeof = 'match_expression'

    def __init__(self, name, **meta):
        super(MatchExpression, self).__init__(name, **meta)
        pass

    @classmethod
    def create(cls, name, user=None, network_element=None, domain_name=None,
               zone=None, executable=None):
        """
        Create a match expression

        :param str name: name of match expression
        :param str user: name of user or user group
        :param Element network_element: valid network element type, i.e. host, network, etc
        :param DomainName domain_name: domain name network element
        :param Zone zone: zone to use
        :param str executable: name of executable or group
        :raises ElementNotFound: specified object does not exist
        :return: instance with meta
        :rtype: MatchExpression
        """
        ref_list = []
        if user:
            pass
        if network_element:
            ref_list.append(network_element.href)
        if domain_name:
            ref_list.append(domain_name.href)
        if zone:
            ref_list.append(zone.href)
        if executable:
            pass

        json = {'name': name,
                'ref': ref_list}

        return ElementCreator(cls, json)

    def values(self):
        return [Element.from_href(ref) for ref in self.data.get('ref')]
