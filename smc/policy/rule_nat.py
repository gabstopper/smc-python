from smc.policy.rule import Rule, _rule_common
from smc.base.model import prepared_request, Element, SubElement
from smc.policy.rule_elements import LogOptions, Destination
from smc.api.exceptions import ElementNotFound, InvalidRuleValue,\
    CreateRuleFailed
from smc.base.util import element_resolver


class NATRule(Rule):
    @property
    def used_on(self):
        """
        Used on specific whether this NAT rule has a specific engine that
        this rule applies to. Default is ANY (unspecified).

        :param str,Element value: :py:class:`smc.elements.network` element to
               apply to this NAT rule, or str href
        :return: Element value: name of element this NAT rule is applied on
        """
        if 'used_on' in self.data:
            return Element.from_href(self.data.get('used_on'))

    @used_on.setter
    def used_on(self, value):
        try:
            self.data['used_on'] = element_resolver(value)
        except ElementNotFound:
            pass

    @property
    def action(self):
        pass

    @property
    def authentication_options(self):
        pass

    @property
    def dynamic_src_nat(self):
        """
        Dynamic Source NAT configuration for this NAT rule.

        :return: :py:class:`~DynamicSourceNAT`: dynamic source nat object
        """
        return DynamicSourceNAT(self.data.get('options'))

    @property
    def static_src_nat(self):
        """
        Static Source NAT configuraiton for this NAT rule.

        :return: :py:class:`~StaticSourceNAT`: static source nat object
        """
        return StaticSourceNAT(self.data.get('options'))

    @property
    def static_dst_nat(self):
        """
        Static Destination NAT configuration for this NAT rule

        :return: :py:class:`~StaticDestNAT`: static dest nat object
        """
        return StaticDestNAT(self.data.get('options'))


class NAT(object):
    def __call__(self, data):
        if self.typeof not in self.data:
            self.data[self.typeof] = data
        else:
            for k, v in data.items():
                try:
                    self.data[self.typeof][k].update(v)
                except KeyError:
                    self.data[self.typeof][k] = v

    @property
    def nat_type(self):
        """    
        Return type of NAT for this rule, is any.

        :return: str static_src_nat, dynamic_src_nat, static_dst_nat
        """
        pass

    @property
    def has_nat(self):
        """
        Is NAT already enabled (assuming modification) or newly
        created.

        :return: boolean
        """
        return self.typeof in self.data

    @property
    def automatic_proxy(self):
        """
        Is proxy arp enabled. Leaving this in the on state is recommended.

        :param bool value: enable/disable proxy arp
        :rtype: bool
        """
        if self.has_nat:
            return self.data[self.typeof].get('automatic_proxy')

    @automatic_proxy.setter
    def automatic_proxy(self, value):
        try:
            self.data[self.typeof]['automatic_proxy'] = value
        except KeyError:
            self.data[self.typeof] = {'automatic_proxy': value}

    @property
    def _original_value(self):
        if self.has_nat:
            return self.data[self.typeof].get('original_value')

    @property
    def _translated_value(self):
        if self.has_nat:
            return self.data[self.typeof].get('translated_value')

    @property
    def original_value(self):
        """
        Original value is the elements location. Setting this can
        be done by providing an element from :py:class:`smc.elements.network`
        or the direct href. For source NAT, this will be the NAT source element,
        and for dynamic dst NAT, this will be the destination element.

        :param str value: element or href from source or destination field
        :return: str original_value: element location 
        """
        values = self._original_value
        if values:
            if 'ip_descriptor' in values:
                return values['ip_descriptor']
            elif 'element' in values:
                return values['element']

    @original_value.setter
    def original_value(self, value):
        src = element_resolver(value, do_raise=False)
        if src and src.startswith('http'):
            self({'original_value': {'element': src}})

    @property
    def translated_value(self):
        """
        Translated value is the NAT value based on the type of
        NAT. For source NAT and destination NAT this can be either
        an IP address or an element from :py:class:`smc.elements.network`.

        :param str value: string ip address or Element (or element href)
        :return: str value: translated value, give preference to IP address if
                            ip address and element are both defined.
        """
        values = self._translated_value
        if values:
            if 'ip_descriptor' in values:
                return values['ip_descriptor']
            elif 'element' in values:
                return values['element']

    @translated_value.setter
    def translated_value(self, value):
        if isinstance(value, Element):
            try:
                src = {'element': value.href}
            except ElementNotFound:
                src = None
        else:
            src = {'ip_descriptor': value}

        if src is not None:
            self({'translated_value': src})


class DynamicSourceNAT(NAT):
    """
    Dynamic Source NAT. This is commonly used for outbound NAT/PAT to provide return
    routable addresses for non-routable source hosts. 

    It is also possible to provide the source port range/s to use, however if not 
    specified, will default to using 1024-65535.

    Modify a rule to NAT to source '2.2.2.2' and PAT using ports 30000-35000::

        for rule in policy.fw_ipv4_nat_rules.all():
            if rule.name == 'dynsrcnat':
                rule.dynamic_src_nat.translated_value = '2.2.2.2'
                rule.dynamic_src_nat.translated_ports = (30000,35000)

    """
    typeof = 'dynamic_src_nat'

    def __init__(self, data):
        self.data = data

    @property
    def original_value(self):
        pass

    @original_value.setter
    def original_value(self, value):
        pass

    @property
    def _translated_value(self):
        if self.has_nat:
            return self.data[self.typeof].get('translation_values')

    @property
    def translated_value(self):
        """
        The translated value for source NAT is the IP address (or element)
        which will be the translated address for the source. Typically referred
        to as the outbound NAT address.

        When setting a new translated address, input should be a string type
        specifying either the IP address to translate to, or can be a valid
        network element from :py:class:`smc.elements.network`. If translated
        ports are not specified, source NAT will the original ports defined or
        if this is a new object will use a dynamic port range of 1024-65535. 

        :param str value: ipaddress or :py:class:`smc.elements.network` object
        :return: str translated address or name
        """
        values = self._translated_value
        if values:
            for value in values:
                if 'ip_descriptor' in value:
                    return value['ip_descriptor']
                elif 'element' in value:
                    return value['element']

    @translated_value.setter
    def translated_value(self, value):
        if isinstance(value, Element):
            try:
                src = {'element': value.href}
            except ElementNotFound:
                src = None
        else:
            src = {'ip_descriptor': value}

        if src is not None:
            if self._translated_value:
                self.data[self.typeof]['translation_values'][0].update(src)
            else:
                self.data.update({self.typeof: {'translation_values': [src]}})
                if not self.translated_ports:
                    self.translated_ports = (1024, 65535)

    @property
    def translated_ports(self):
        """
        Translated ports allows custom configuration for PAT on the 
        source NAT configuration.

        :param tuple min_port,max_port: starting and ending port for source NAT (PAT)
        :return tuple value: min and max ports defined
        """
        values = self._translated_value
        if values:
            if 'min_port' in values[0]:
                return (values[0].get('min_port'),
                        values[0].get('max_port'))

    @translated_ports.setter
    def translated_ports(self, value):
        assert isinstance(value, tuple), "Input must be tuple"
        min_port, max_port = value
        ports = {'min_port': min_port,
                 'max_port': max_port}
        if self.has_nat:
            self.data[self.typeof]['translation_values'][0].update(ports)
        else:
            self.data.update({self.typeof: {'translation_values': [ports]}})


class StaticSourceNAT(NAT):
    """
    Source NAT defines the available options for configuration. This is
    typically used for outbound traffic where you need to hide the original
    source address.

    Example of changing existing source NAT rule to use a different source
    NAT address::

        for rule in policy.fw_ipv4_nat_rules.all():
            if rule.name == 'sourcenat':
                rule.static_src_nat.translated_value = '10.10.50.50'
                rule.save()

    """
    typeof = 'static_src_nat'

    def __init__(self, data):
        self.data = data


class StaticDestNAT(NAT):
    """
    Destination NAT provides the ability to translate the destination address
    to a specified location. The NAT rules destination field will be the
    match and the static destination nat address defines how the request is
    rewritten.

    Example of changing an existing NAT rule to use a different NAT destination
    and map port 80 to 8080::

        for rule in policy.fw_ipv4_nat_rules.all():
            if rule.name == 'destnat':
                rule.static_dst_nat.translated_value = '30.30.30.30'
                rule.static_dst_nat.translated_ports = (80, 8080)
                rule.save()

    """
    typeof = 'static_dst_nat'

    def __init__(self, data):
        self.data = data

    @property
    def translated_ports(self):
        """
        Translated ports for destination NAT can be either single source
        to single destination port, or ranges of ports to translate.
        The format for single ports is: (source_port, destination_port),
        or (80, 443) - translate source port 80 to 443.
        You can also use a range format although port range sizes much
        then match in size. The format for range of ports is:
        ('80-100', '6000-6020') - port 80 translates to 6000, etc.

        :param tuple value: (source_port/s, destination_port/s)
        :return tuple value: ports used for destination PAT
        """
        o_values = self._original_value
        t_values = self._translated_value

        if o_values is None or t_values is None:
            return None

        o_min_port = o_values['min_port']
        o_max_port = o_values['max_port']

        if o_min_port == o_max_port:
            o_values = o_min_port
        else:
            o_values = '{}-{}'.format(o_min_port, o_max_port)

        t_min_port = t_values['min_port']
        t_max_port = t_values['max_port']

        if t_min_port == t_max_port:
            t_values = t_min_port
        else:
            t_values = '{}-{}'.format(t_min_port, t_max_port)

        return (o_values, t_values)

    @translated_ports.setter
    def translated_ports(self, value):
        assert isinstance(value, tuple), "Input must be tuple"
        orig_port, trans_port = value

        if isinstance(orig_port, int):
            o_ports = {'min_port': orig_port,
                       'max_port': orig_port}
            t_ports = {'min_port': trans_port,
                       'max_port': trans_port}
        elif isinstance(orig_port, str):
            psplit = orig_port.split('-')
            o_ports = {'min_port': psplit[0],
                       'max_port': psplit[1]}
            psplit = trans_port.split('-')
            t_ports = {'min_port': psplit[0],
                       'max_port': psplit[1]}

        # TODO: Return if wrong type given
        # Raise instead?

        self({'original_value': o_ports})
        self({'translated_value': t_ports})


class IPv4NATRule(NATRule, SubElement):
    """
    Create NAT Rules for relevant policy types. Rule requirements are 
    similar to a normal rule with exception of the NAT field and no action
    field. 

    Like policy rules, specifying source/destination and services can be
    done either using the element href or element defined in element classes
    defined under package ``smc.elements``.
    For example, using networks from  :py:class:`smc.elements.network` or 
    services from :py:class:`smc.elements.service`.

    Example of creating a dynamic source NAT for host 'kali'::

        policy = FirewallPolicy('smcpython')
        policy.fw_ipv4_nat_rules.create(name='mynat', 
                                        sources=[Host('kali')], 
                                        destinations='any', 
                                        services='any', 
                                        dynamic_src_nat='1.1.1.1', 
                                        dynamic_src_nat_ports=(1024,65535))


    Example of creating a static source NAT for host 'kali'::

        policy.fw_ipv4_nat_rules.create(name='mynat', 
                                        sources=[Host('kali')], 
                                        destinations='any', 
                                        services='any', 
                                        static_src_nat='1.1.1.1')

    Example of creating a destination NAT rule for destination host '3.3.3.3'
    with destination translation address of '1.1.1.1'::

        policy.fw_ipv4_nat_rules.create(name='mynat', 
                                        sources='any', 
                                        destinations=[Host('3.3.3.3')], 
                                        services='any', 
                                        static_dst_nat='1.1.1.1')

    Destination NAT with destination port translation::

        policy.fw_ipv4_nat_rules.create(name='aws_client', 
                                        sources='any', 
                                        destinations=[Alias('$$ Interface ID 0.ip')], 
                                        services='any', 
                                        static_dst_nat='1.1.1.1', 
                                        static_dst_nat_ports=(2222, 22),
                                        used_on=engine.href)

    Create an any/any no NAT rule from host 'kali'::

        policy.fw_ipv4_nat_rules.create(name='nonat', 
                                        sources=[Host('kali')], 
                                        destinations='any', 
                                        services='any')

    """
    typeof = 'fw_ipv4_nat_rule'

    def __init__(self, **meta):
        super(IPv4NATRule, self).__init__(**meta)
        pass

    def create(self, name, sources=None, destinations=None, services=None,
               dynamic_src_nat=None, dynamic_src_nat_ports=(1024, 65535),
               static_src_nat=None, static_dst_nat=None,
               static_dst_nat_ports=None, is_disabled=False, used_on=None):
        """
        Create a NAT rule.

        When providing sources/destinations or services, you can provide the
        element href, network element or services from ``smc.elements``.
        You can also mix href strings with Element types in these fields. 

        :param str name: name of NAT rule
        :param list sources: list of sources by href or Element
        :type sources: list(str,Element)
        :param list destinations: list of destinations by href or Element
        :type destinations: list(str,Element)
        :param list services: list of services by href or Element
        :type services: list(str,Element)
        :param dynamic_src_nat: str ip or Element for dest NAT
        :type dynamic_src_nat: str,Element
        :param tuple dynamic_src_nat_ports: starting and ending ports for PAT.
            Default: (1024, 65535)
        :param str static_src_nat: ip or element href of used for source NAT
        :param str static_dst_nat: destination NAT IP address or element href
        :param tuple static_dst_nat_ports: ports or port range used for original
            and destination ports (only needed if a different destination port
            is used and does not match the rules service port)
        :param bool is_disabled: whether to disable rule or not
        :param str used_on: href or Element (of security engine) where this
            NAT rule applies, Default: Any
        :type used_on: str,Element
        :raises InvalidRuleValue: if rule requirements are not met
        :raises CreateRuleFailed: rule creation failure
        :return: None
        """
        rule_values = _rule_common(sources, destinations, services)
        rule_values.update(name=name)
        rule_values.update(is_disabled=is_disabled)

        options = LogOptions()

        if dynamic_src_nat:
            nat = DynamicSourceNAT(options.data)
            nat.translated_value = dynamic_src_nat
            nat.translated_ports = (dynamic_src_nat_ports)
            rule_values.update(options=nat.data)

        elif static_src_nat:
            nat = StaticSourceNAT(options.data)
            nat.translated_value = static_src_nat
            nat.original_value = sources[0].href
            rule_values.update(options=nat.data)

        if static_dst_nat:
            destination = Destination(rule_values['destinations'])
            if destination.is_any or destination.is_none:
                raise InvalidRuleValue('Destination field cannot be none or any for '
                                       'destination NAT.')
            nat = StaticDestNAT(options.data)
            nat.translated_value = static_dst_nat
            nat.original_value = destination.all_as_href()[0]
            if static_dst_nat_ports:
                nat.translated_ports = static_dst_nat_ports
            rule_values.update(options=nat.data)

        if 'options' not in rule_values:  # No NAT
            rule_values.update(options=options.data)

        rule_values.update(used_on=used_on)
        return prepared_request(CreateRuleFailed,
                                href=self.href,
                                json=rule_values).create().href


class IPv6NATRule(IPv4NATRule):
    """
    Represents an IPv6 NAT rule. Source and/or destination (depending on
    NAT type) should be an IPv6 address. It will be possible to submit
    an IPv4 address however the policy validation engine will fail when
    being deployed to an engine and the rule will be ignored.
    """
    typeof = 'fw_ipv6_nat_rule'

    def __init__(self, **meta):
        super(IPv6NATRule, self).__init__(**meta)
        pass
