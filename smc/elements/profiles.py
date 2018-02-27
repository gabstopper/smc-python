"""
Profiles are templates used in other parts of the system to provide default 
functionality for specific feature sets. For example, to enable DNS Relay on
an engine you must specify a DNSRelayProfile to use which defines the common
settings (or sub-settings) for that feature.

A DNS Relay Profile allows multiple DNS related mappings that can be configured.
Example usage::

    >>> from smc.elements.profiles import DNSRelayProfile
    >>> profile = DNSRelayProfile('mynewprofile')

.. note:: If the DNSRelayProfile does not exist, it will automatically be
    created when a DNS relay rule is added to the DNSRelayProfile instance.
    
Add a fixed domain answer rule::

    >>> profile.fixed_domain_answer.add([('microsoft3.com', 'foo.com'), ('microsoft4.com',)])
    >>> profile.fixed_domain_answer.all()
    [{u'domain_name': u'microsoft3.com', u'translated_domain_name': u'foo.com'}, {u'domain_name': u'microsoft4.com'}]
    
Translate hostnames (not fqdn) to a specific IP address::

    >>> profile.hostname_mapping.add([('hostname1,hostname2', '1.1.1.12')])
    >>> profile.hostname_mapping.all()
    [{u'hostnames': u'hostname1,hostname2', u'ipaddress': u'1.1.1.12'}]

Translate an IP address to another::

    >>> profile.dns_answer_translation.add([('12.12.12.12', '172.18.1.20')])
    >>> profile.dns_answer_translation.all()
    [{u'translated_ipaddress': u'172.18.1.20', u'original_ipaddress': u'12.12.12.12'}]

Specify a DNS server to handle specific domains::

    >>> profile.domain_specific_dns_server.add([('myfoo.com', '172.18.1.20')])
    >>> profile.domain_specific_dns_server.all()
    [{u'dns_server_addresses': u'172.18.1.20', u'domain_name': u'myfoo.com'}]

"""
from smc.base.model import Element, ElementCreator
from smc.api.exceptions import ElementNotFound


class DNSRule(object):
    """
    DNSRule is the parent class for all DNS relay rules.
    """
    __slots__ = ('profile')
    def __init__(self, profile):
        self.profile = profile
    
    def add(self, instance, answers):
        key, left, right = instance._attr
        json = [dict(zip([left, right], d)) 
                for d in answers]
        try:
            self.profile.data[key].extend(json)
            self.profile.update()
        except ElementNotFound:
            j = {'name': self.profile.name,
                  key: json}
            return ElementCreator(self.profile.__class__, j)
    
    def all(self):
        """
        Return all entries
        
        :rtype: list(dict)
        """
        attribute = self._attr[0]
        return self.profile.data.get(attribute, [])

    
class FixedDomainAnswer(DNSRule):
    """
    Direct requests for specific domains to IPv4 addresses, IPv6
    addresses, fully qualified domain names (FQDNs), or empty DNS replies
    """
    _attr = ('fixed_domain_answer', 'domain_name', 'translated_domain_name')
    
    def add(self, answers):
        """
        Add a fixed domain answer. This should be a list of
        two-tuples, the first entry is the domain name, and
        the second is the translated domain value::
        
            profile = DNSRelayProfile('dnsrules')
            profile.fixed_domain_answer.add([
                ('microsoft.com', 'foo.com'), ('microsoft2.com',)])
        
        :param answers: (domain_name, translated_domain_name)
        :type answers: tuple[str, str]
        :raises UpdateElementFailed: failure to add to SMC
        :return: None
        
        .. note:: translated_domain_name can be none, which will cause
            the NGFW to return NXDomain for the specified domain.
        """
        super(FixedDomainAnswer, self).add(self, answers)

    
class HostnameMapping(DNSRule):
    """
    Statically map host names, aliases for host names, and unqualified
    names (a host name without the domain suffix) to IPv4 or IPv6
    addresses
    """
    _attr = ('hostname_mapping', 'hostnames', 'ipaddress')
    
    def add(self, answers):
        """
        Map specific hostname to specified IP address. Provide a list
        of two-tuples. The first entry is the hostname/s to translate
        (you can provide multiple comma separated values). The second
        entry should be the IP address to map the hostnames to::
        
            profile = DNSRelayProfile('dnsrules')
            profile.hostname_mapping.add([('hostname1,hostname2', '1.1.1.1')])

        :param answers: (hostnames, ipaddress), hostnames can be a
            comma separated list.
        :type answers: tuple[str, str]
        :raises UpdateElementFailed: failure to add to SMC
        :return: None
        """
        super(HostnameMapping, self).add(self, answers)


class DomainSpecificDNSServer(DNSRule):
    """
    Forward DNS requests to different DNS servers based on
    the requested domain.
    """
    _attr = ('domain_specific_dns_server', 'domain_name', 'dns_server_addresses')
    
    def add(self, answers):
        """
        Relay specific domains to a specified DNS server. Provide
        a list of two-tuple with first entry the domain name to relay
        for. The second entry is the DNS server that should handle the
        query::
            
            profile = DNSRelayProfile('dnsrules')
            profile.domain_specific_dns_server.add([('myfoo.com', '172.18.1.20')])

        :param answers: (domain_name, dns_server_addresses), dns server
            addresses can be a comma separated string
        :type answers: tuple[str, str]
        :raises UpdateElementFailed: failure to add to SMC
        :return: None
        """
        super(DomainSpecificDNSServer, self).add(self, answers)
        

class DNSAnswerTranslation(DNSRule):
    """
    Map IPv4 addresses resolved by external DNS servers to IPv4
    addresses in the internal network.  
    """
    _attr = ('dns_answer_translation', 'original_ipaddress', 'translated_ipaddress')
    
    def add(self, answers):
        """
        Takes an IPv4 address and translates to a specified IPv4 value.
        Provide a list of two-tuple with the first entry providing the
        original address and second entry specifying the translated address::
        
            profile = DNSRelayProfile('dnsrules')
            profile.dns_answer_translation.add([('12.12.12.12', '172.18.1.20')])
        
        :param answers: (original_ipaddress, translated_ipaddress)
        :type answers: tuple[str, str]
        :raises UpdateElementFailed: failure to add to SMC
        :return: None
        """
        super(DNSAnswerTranslation, self).add(self, answers)

   
class DNSRelayProfile(Element):
    """
    DNS Relay Settings specify a profile to handle how the engine will
    interpret DNS queries. Stonesoft can act as a DNS relay, rewrite 
    DNS queries or redirect domains to the specified DNS servers.
    """
    typeof = 'dns_relay_profile'

    @property
    def fixed_domain_answer(self):
        """
        Add a fixed domain answer entry.
        
        :rtype: FixedDomainAnswer
        """
        return FixedDomainAnswer(self)
    
    @property
    def hostname_mapping(self):
        """
        Add a hostname to IP mapping
        
        :rtype: HostnameMapping
        """
        return HostnameMapping(self)
    
    @property
    def domain_specific_dns_server(self):
        """
        Add domain to DNS server mapping
        
        :rtype: DomainSpecificDNSServer
        """
        return DomainSpecificDNSServer(self)
    
    @property
    def dns_answer_translation(self):
        """
        Add a DNS answer translation
        
        :rtype: DNSAnswerTranslation
        """
        return DNSAnswerTranslation(self)
        

class SNMPAgent(Element):
    """
    Minimal implementation of SNMPAgent
    """
    typeof = 'snmp_agent'
    
    @classmethod
    def create(cls, name, snmp_monitoring_contact=None,
               snmp_monitoring_listening_port=161, snmp_version='v3',
               comment=None):
        
        json = {'boot': False,
                'go_offline': False,
                'go_online': False,
                'hardware_alerts': False,
                'name': name,
                'policy_applied': False,
                'shutdown': False,
                'snmp_monitoring_contact': snmp_monitoring_contact,
                'snmp_monitoring_listening_port': snmp_monitoring_listening_port,
                'snmp_monitoring_user_name': [],
                'snmp_trap_destination': [],
                'snmp_user_name': [],
                'snmp_version': snmp_version,
                'user_login': False}
    
        return ElementCreator(cls, json)
    

class SandboxService(Element):
    typeof = 'sandbox_service'

