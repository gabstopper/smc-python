from smc.policy.rule import Rule, RuleCommon
from smc.base.model import Element, SubElement, ElementCreator
from smc.policy.rule_elements import LogOptions
from smc.api.exceptions import ElementNotFound, InvalidRuleValue,\
    CreateRuleFailed
from smc.base.util import element_resolver
from smc.base.structs import NestedDict


class NATRule(Rule):
    @property
    def used_on(self):
        """
        Used on specific whether this NAT rule has a specific engine that
        this rule applies to. Default is ANY (unspecified).

        :param str,Element value: Can be the strings 'ANY' or 'NONE' or an
            Engine element type.
        :return: 'ANY', 'NONE' or the Engine element
        """
        used_on = self.data.get('used_on', {})
        if 'firewall_ref' in used_on:
            return Element.from_href(used_on.get('firewall_ref'))
        return 'ANY' if used_on.get('any') else 'NONE'
    
    @used_on.setter
    def used_on(self, value):
        try:
            used_on = element_resolver(value)
            if used_on == 'ANY':
                self.data.update(used_on={'any': True})
            elif used_on is 'NONE':
                self.data.update(used_on={'none': True})
            else:
                self.data.update(used_on={'firewall_ref': used_on})
        except ElementNotFound:
            pass
    
    def _update_nat_field(self, source_or_dest):
        """
        If the source or destination field of a rule is changed and the rule
        is a NAT rule, this method will check to see if the changed field
        maps to a NAT type and modifies the `original_value` field within
        the NAT dict to reflect the new element reference. It is possible
        that a NAT rule doesn't actually define a NAT type, i.e. meaning do
        not NAT.
        
        :param Source,Destination source_or_dest: source or destination
            element changed. This would be called from update_field on
            the Source or Destination object.
        """
        original_value = source_or_dest.all_as_href()
        if original_value:
            nat_element = None
            if 'src' in source_or_dest.typeof and self.static_src_nat.has_nat:
                nat_element = self.static_src_nat
            elif 'dst' in source_or_dest.typeof and self.static_dst_nat.has_nat:
                nat_element = self.static_dst_nat
            
            if nat_element:
                nat_element.setdefault(nat_element.typeof, {}).update(
                    original_value={'element': original_value[0]})
        
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

        :rtype: DynamicSourceNAT
        """
        return DynamicSourceNAT(self)

    @property
    def static_src_nat(self):
        """
        Static Source NAT configuraiton for this NAT rule.

        :rtype: StaticSourceNAT
        """
        return StaticSourceNAT(self)

    @property
    def static_dst_nat(self):
        """
        Static Destination NAT configuration for this NAT rule

        :rtype: StaticDestNAT
        """
        return StaticDestNAT(self)

    
class NATValue(NestedDict):
    """
    NAT Values are either used as original or translated values
    on all NAT types.
     
    :ivar str element: element href if an element is used
    :ivar str ip_descriptor: IP address assigned. If element href is
        present, the ip_descriptor value is obtained automatically
        from the SMC and represents the elements address in use
    :ivar str min_port: min port for this translation
    :ivar str max_port: max port for this translation  
    """
    def __init__(self, values):
        super(NATValue, self).__init__(data=values)
     
    @property
    def as_element(self):
        if 'element' in self:
            return Element.from_href(self.get('element'))
    
    def _update_field(self, natvalue):
        """
        Update this NATValue if values are different
        
        :rtype: bool
        """
        updated = False
        if natvalue.element and natvalue.element != self.element:
            self.update(element=natvalue.element)
            self.pop('ip_descriptor', None)
            updated = True
        elif natvalue.ip_descriptor and self.ip_descriptor and \
            natvalue.ip_descriptor != self.ip_descriptor:
            self.update(ip_descriptor=natvalue.ip_descriptor)
            self.pop('element', None)
            updated = True

        for port in ('min_port', 'max_port'):
            _port = getattr(natvalue, port, None)
            if _port is not None and getattr(self, port, None) != _port:
                self[port] = _port
                updated = True
    
        return updated
        
    def __getattr__(self, key):
        return self.get(key)


class NATElement(NestedDict):
    """
    Common structure for source and destination NAT
    configurations.
    """
    def __init__(self, rule=None):
        options = LogOptions().data if not rule else \
            rule.data.get('options')
        self.rule = rule
        super(NATElement, self).__init__(data=options)
          
    @property
    def has_nat(self):
        """
        Is NAT already enabled (assuming modification) or newly
        created.
  
        :return: boolean
        """
        return self.typeof in self
      
    def set_none(self):
        """
        Clear the NAT field for this NAT rule. You must call
        `update` or `save` on the rule to commit this change.
          
        :return: None
        """
        self.pop(self.typeof, None)
    
    @property
    def automatic_proxy(self):
        """
        Is proxy arp enabled. Leaving this in the on state is recommended.
  
        :param bool value: enable/disable proxy arp
        :rtype: bool
        """
        return self.get(self.typeof, {}).get(
            'automatic_proxy')
  
    @automatic_proxy.setter
    def automatic_proxy(self, value):
        self.setdefault(self.typeof, {}).update(
            automatic_proxy=value)
    
    def update_field(self, element_or_ip_address=None, 
            start_port=None, end_port=None, **kw):
        """
        Update the source NAT translation on this rule.
        You must call `save` or `update` on the rule to make this
        modification. To update the source target for this NAT rule, update
        the source field directly using rule.sources.update_field(...).
        This will automatically update the NAT value. This method should be
        used when you want to change the translated value or the port
        mappings for dynamic source NAT.
        
        Starting and ending ports are only used for dynamic source NAT and
        define the available ports for doing PAT on the outbound connection.
        
        :param str,Element element_or_ip_address: Element or IP address that
            is the NAT target
        :param int start_port: starting port value, only used for dynamic source NAT
        :param int end_port: ending port value, only used for dynamic source NAT
        :param bool automatic_proxy: whether to enable proxy ARP (default: True)
        :return: boolean indicating whether the rule was modified
        :rtype: bool
        """
        updated = False
        src = _resolve_nat_element(element_or_ip_address) if \
            element_or_ip_address else {}
        
        automatic_proxy = kw.pop('automatic_proxy', None)
        # Original value is only used when creating a rule for static src NAT.
        # This should be the href of the source field to properly create
        # TODO: The SMC API should autofill this based on source field
        _original_value = kw.pop('original_value', None)
        
        src.update(kw)
        
        if not self.translated_value:
            # Adding to a rule
            if 'dynamic_src_nat' in self.typeof:
                src.update(
                    min_port=start_port or 1024,
                    max_port=end_port or 65535)
            
            self.setdefault(self.typeof, {}).update(
                automatic_proxy=automatic_proxy if automatic_proxy else True,
                **self._translated_value(src))
            
            if 'static_src_nat' in self.typeof:
                if self.rule and self.rule.sources.all_as_href():
                    original_value={'element': self.rule.sources.all_as_href()[0]}
                else:
                    original_value={'element': _original_value}
            
                self.setdefault(self.typeof, {}).update(original_value=original_value)
            
            updated = True
        else:
            if 'dynamic_src_nat' in self.typeof:
                src.update(min_port=start_port, max_port=end_port)
            if self.translated_value._update_field(NATValue(src)):
                updated = True
        
        if automatic_proxy is not None and self.automatic_proxy \
            != automatic_proxy:
            self.automatic_proxy = automatic_proxy
            updated = True
            
        return updated
    
    def _translated_value(self, src_dict):
        return {'translated_value': src_dict}
    
    @property
    def translated_value(self):
        """
        The translated value for this NAT type. If this rule
        does not have a NAT value defined, this will return
        None.
        
        :return: NATValue or None
        :rtype: NATValue
        """
        if self.typeof in self:
            return NATValue(self.get(self.typeof, {}).get(
                'translated_value'))


class StaticSourceNAT(NATElement):
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
    

class StaticDestNAT(NATElement):
    typeof = 'static_dst_nat'
    
    def update_field(self, element_or_ip_address=None, 
            original_port=None, translated_port=None, **kw):
        """
        Update the destination NAT translation on this rule. You must call
        `save` or `update` on the rule to make this modification. The
        destination field in the NAT rule determines which destination is
        the target of the NAT. To change the target, call the
        rule.destinations.update_field(...) method. This will automatically
        update the NAT value. This method should be used when you want to
        change the translated value port mappings for the service.
        
        Translated Port values can be used to provide port redirection for
        the service specified in the NAT rule. These should be provided as a
        string format either in single port format, or as a port range.
        
        For example, providing redirection from port 80 to port 8080::
        
            original_port='80'
            translated_port='8080'
        
        You can also use a range format although port range sizes much
        then match in size. The format for range of ports is:
        '80-100', '6000-6020' - port 80 translates to 6000, etc.
        
        For example, doing port range redirection using a range of ports::
         
            original_port='80-90'
            translated_port='200-210'
             
        .. note:: When using a range of ports for static destination translation, you
            must use a port range of equal length or the update will be ignored.
        
        :param str,Element element_or_ip_address: Element or IP address that
            is the NAT target
        :param str,int original_port: The original port is based on the service port
        :param str,int translated_port: The port to translate the original port to
        :param bool automatic_proxy: whether to enable proxy ARP (default: True)
        :return: boolean indicating whether the rule was modified
        :rtype: bool
        """
        updated = False
        src = _resolve_nat_element(element_or_ip_address) if \
            element_or_ip_address else {}
        
        automatic_proxy = kw.pop('automatic_proxy', None)
        # Original value is only used when creating a rule for static src NAT.
        # This should be the href of the source field to properly create
        # TODO: The SMC API should autofill this based on source field
        _original_value = kw.pop('original_value', None)
        
        src.update(kw)
        if translated_port is not None:
            src.update(_extract_ports(translated_port))
        
        if not self.translated_value:
            # Adding to a rule
            self.setdefault(self.typeof, {}).update(
                automatic_proxy=automatic_proxy if automatic_proxy else True,
                **self._translated_value(src))
            
            if self.rule and self.rule.destinations.all_as_href():
                original_value={'element': self.rule.destinations.all_as_href()[0]}
            else:
                # If creating, original_value should be href of resource
                original_value={'element': _original_value}
            
            if original_port is not None:
                original_value.update(_extract_ports(original_port))
            
            self.setdefault(self.typeof, {}).update(
                original_value=original_value)
            
            updated = True
        else:
            if self.translated_value._update_field(NATValue(src)):
                updated = True
            
            if original_port:
                if self.original_value._update_field(NATValue(
                    _extract_ports(original_port))):
                    updated = True
            
        if automatic_proxy is not None and self.automatic_proxy \
            != automatic_proxy:
            self.automatic_proxy = automatic_proxy
            updated = True
            
        return updated
    
    @property
    def original_value(self):
        if self.typeof in self:
            return NATValue(self.get(self.typeof, {}).get(
                'original_value'))
    
       
class DynamicSourceNAT(NATElement):
    """
    Dynamic source NAT is typically used for outbound traffic and
    typically uses a range of ports to perform PAT operations.
    
    """
    typeof = 'dynamic_src_nat'
    
    @property
    def original_value(self):
        pass
    
    @property
    def start_port(self):
        """
        Start port for dynamic source NAT (PAT)
        
        :rtype: int
        """
        if self.has_nat:
            return self.translated_value.min_port
    
    @property
    def end_port(self):
        """
        Ending port specified for outbound dynamic source NAT (PAT)
        
        :rtype: int
        """
        if self.has_nat:
            return self.translated_value.max_port
    
    def _translated_value(self, src_dict):
        return {'translation_values': [src_dict]}
    
    @property
    def translated_value(self):
        """
        The translated value for this NAT type. If this rule
        does not have a NAT value defined, this will return
        None.
        
        :return: NATValue or None
        :rtype: NATValue
        """
        if self.typeof in self:
            return NATValue(self.get(self.typeof, {}).get(
                'translation_values')[0])
    

def _resolve_nat_element(element_or_ip_address):
    """
    NAT elements can be referenced by either IP address or as type
    Element. Resolve that to the right dict structure for the rule
    
    :param str,Element element_or_ip_address: Element or IP string
    :rtype: dict
    """
    try:
        src = {'element': element_or_ip_address.href}
    except AttributeError:
        src = {'ip_descriptor': element_or_ip_address}

    return src


def _extract_ports(port_string):
    """
    Return a dict for translated_value based on a string or int
    value.
    
    Value could be 80, or '80' or '80-90'.
    
    Will be returned as {'min_port': 80, 'max_port': 80} or 
    {'min_port': 80, 'max_port': 90}
    
    :rtype: dict
    """
    _ports = str(port_string)
    if '-' in _ports:
        start, end = _ports.split('-')
        return {'min_port': start, 'max_port': end}
    return {'min_port': _ports, 'max_port': _ports}

    
    
class IPv4NATRule(RuleCommon, NATRule, SubElement):
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
                                        static_dst_nat_ports=(2222,22),
                                        used_on=engine.href)

    Create an any/any no NAT rule from host 'kali'::

        policy.fw_ipv4_nat_rules.create(name='nonat', 
                                        sources=[Host('kali')], 
                                        destinations='any', 
                                        services='any')

    """
    typeof = 'fw_ipv4_nat_rule'

    def create(self, name, sources=None, destinations=None, services=None,
               dynamic_src_nat=None, dynamic_src_nat_ports=(1024, 65535),
               static_src_nat=None, static_dst_nat=None,
               static_dst_nat_ports=None, is_disabled=False, used_on='ANY',
               add_pos=None, after=None, before=None, comment=None, validate=True):
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
        :param str,Engine used_on: Can be None, 'ANY' or and Engine element. Default
            is 'ANY'.
        :type used_on: str,Element
        :param int add_pos: position to insert the rule, starting with position 1. If
            the position value is greater than the number of rules, the rule is inserted at
            the bottom. If add_pos is not provided, rule is inserted in position 1. Mutually
            exclusive with ``after`` and ``before`` params.
        :param str after: Rule tag to add this rule after. Mutually exclusive with ``add_pos``
            and ``before`` params.
        :param str before: Rule tag to add this rule before. Mutually exclusive with ``add_pos``
            and ``after`` params.
        :param str comment: optional comment for the NAT rule
        :param bool validate: validate the inspection policy during rule creation. Default: True
        :raises InvalidRuleValue: if rule requirements are not met
        :raises CreateRuleFailed: rule creation failure
        :return: newly created NAT rule
        :rtype: IPv4NATRule
        """
        rule_values = self.update_targets(sources, destinations, services)
        rule_values.update(name=name, comment=comment, is_disabled=is_disabled)
        
        rule_values.update(used_on={'any': True} if used_on == 'ANY' else \
            element_resolver(used_on))
        
        if dynamic_src_nat:
            nat = DynamicSourceNAT()
            start_port, end_port = dynamic_src_nat_ports
            nat.update_field(dynamic_src_nat, start_port=start_port,
                end_port=end_port)
            rule_values.update(options=nat)
        
        elif static_src_nat:
            sources = rule_values['sources']
            if 'any' in sources or 'none' in sources:
                raise InvalidRuleValue('Source field cannot be none or any for '
                    'static source NAT.')
            
            nat = StaticSourceNAT()
            nat.update_field(static_src_nat,
                original_value=sources.get('src')[0])
            rule_values.update(options=nat)
        
        if static_dst_nat:
            destinations = rule_values['destinations']
            if 'any' in destinations or 'none' in destinations:
                raise InvalidRuleValue('Destination field cannot be none or any for '
                    'destination NAT.')
            
            nat = StaticDestNAT()
            original_port, translated_port = None, None
            if static_dst_nat_ports:
                original_port, translated_port = static_dst_nat_ports
            
            nat.update_field(static_dst_nat,
                original_value=destinations.get('dst')[0],
                original_port=original_port,
                translated_port=translated_port)
            
            rule_values.setdefault('options', {}).update(nat)

        if 'options' not in rule_values:  # No NAT
            rule_values.update(options=LogOptions())
        
        params = {'validate': False} if not validate else {}
        
        href = self.href
        if add_pos is not None:
            href = self.add_at_position(add_pos)
        elif before or after:
            params.update(**self.add_before_after(before, after))
        
        return ElementCreator(
            self.__class__,
            exception=CreateRuleFailed,
            href=href,
            params=params,
            json=rule_values)


class IPv6NATRule(IPv4NATRule):
    """
    Represents an IPv6 NAT rule. Source and/or destination (depending on
    NAT type) should be an IPv6 address. It will be possible to submit
    an IPv4 address however the policy validation engine will fail when
    being deployed to an engine and the rule will be ignored.
    """
    typeof = 'fw_ipv6_nat_rule'
