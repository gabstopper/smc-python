"""
Profiles are templates used in other parts of the system to provide default 
functionality for specific feature sets. For example, to enable DNS Relay on
an engine you must specify a DNSRelayProfile to use which defines the common
settings (or sub-settings) for that feature.

Profile's do not have a direct ``create`` method like other resources of type
:class:`smc.core.model.Element`. They are created dynamically if they do not 
exist. However they require at least one of the instance methods be called
in order to properly initialize the profile.

For example, to create a DNSRelayProfile, specify the resource by name and call
a method to initialize::

    >>> from smc.elements.profiles import DNSRelayProfile
    >>> p = DNSRelayProfile('mynewprofile')
    >>> p.add_hostname_mapping(hostnames='myhost,myhost2',ipaddress='1.1.1.1')
    >>> p.hostname_mapping
    [{u'hostnames': u'myhost,myhost2', u'ipaddress': u'1.1.1.1'}]
    >>> p.add_fixed_domain_answer('malwaresite.com', 'sinkhole.local')
    >>> p.fixed_domain_answer
    [{u'domain_name': u'malwaresite.com', u'translated_domain_name': u'sinkhole.local'}]
    >>> 
    >>> myprofile = DNSRelayProfile('mynewprofile')
    >>> myprofile.href
    u'http://172.18.1.150:8082/6.2/elements/dns_relay_profile/5'

.. seealso:: :class:`smc.core.properties.EngineFeature.enable_dns_relay` for
             enabling dns relay on an engine using a DNSRelayProfile.

"""
from smc.base.model import Element, ElementCreator
from smc.api.exceptions import ElementNotFound


class DNSRelayProfile(Element):
    """
    DNS Relay Settings specify a profile to handle how the engine will
    interpret DNS queries. Stonesoft can act as a DNS relay, rewrite 
    DNS queries or redirect domains to the specified DNS servers.

    All DNSRelayProfile methods support an ``as_list`` keyword argument 
    that will take a list of 2-tuple's that should contain the values for
    each ``add_`` method. The constructor of each method indicates the order
    which the tuple will be mapped.

    For example, loading a list of hostname_mappings::

        profile.add_hostname_mapping(
            as_list=[('hostname1', 'ipaddress1'),
                     ('hostname2', 'ipaddress2'),
                     ('hostname3', 'ipaddress3')]

    If keyword argument ``as_list`` is not provided, a single entry can be
    added using the other available method arguments. 
    """
    typeof = 'dns_relay_profile'

    def __init__(self, name, **meta):
        super(DNSRelayProfile, self).__init__(name, **meta)
        pass

    def _create_or_update(self, key, json):
        try:
            self.data[key].extend(json)
            self.update()
        except ElementNotFound:
            j = {'name': self.name,
                 key: json}
            return ElementCreator(self.__class__, j)

    def add_dns_answer_translation(self, original_ipaddress=None,
                                   translated_ipaddress=None, as_list=None):
        """
        Takes an IPv4 address and translates to a specified IPv4 value

        :param str original_ipaddress: original IP address
        :param str translated_ipaddress: translate original IP to this IP address
        :param list as_list: provide a list of tuple values in same order as
            constructor: [(original_ipaddress,translated_ipaddress)]
        :raises UpdateElementFailed: failure to add to SMC
        :return: None
        """
        if as_list:
            json = [dict(zip(['original_ipaddress', 'translated_ipaddress'], d))
                    for d in as_list]
        else:
            json = [{'original_ipaddress': original_ipaddress,
                     'translated_ipaddress': translated_ipaddress}]

        self._create_or_update('dns_answer_translation', json)

    @property
    def dns_answer_translation(self):
        """
        This profiles original ip to translated ip values

        :return: list of dict (original ip, translated ip)
        """
        return self.data.get('dns_answer_translation', [])

    def add_fixed_domain_answer(self, domain_name=None,
                                translated_domain_name=None,
                                as_list=None):
        """
        Takes a source domain and translates it to a specified domain
        or returns a NXDomain (no such domain) if no translated domain
        is provided.

        :param str domain_name: source domain to match
        :param str translated_domain_name: translate source domain to this domain
        :param list as_list: provide a list of tuple values in same order as
            constructor: [(domain_name,translated_domain_name)]
        :raises UpdateElementFailed: failure to add to SMC
        :return: None

        .. note:: If translated_domain_name is None, NXDomain is returned for
                  the source domain.
        """
        if as_list:
            json = [dict(zip(['domain_name', 'translated_domain_name'], d))
                    for d in as_list]
        else:
            json = [{'domain_name': domain_name,
                     'translated_domain_name': translated_domain_name}]

        self._create_or_update('fixed_domain_answer', json)

    @property
    def fixed_domain_answer(self):
        """
        This profiles fixed domain translation values

        :return: list of dict (domain name, translated domain)
        """
        return self.data.get('fixed_domain_answer', [])

    def add_hostname_mapping(self, hostnames=None, ipaddress=None,
                             as_list=None):
        """
        Map specific hostname to specified IP address

        :param str hostnames: fqdn or hostname/s of host to translate (comma separate multiple)
        :param str ipaddress: ip address for reply
        :param list as_list: provide a list of tuple values in same order as
            constructor: [(hostnames,ipaddress)]
        :raises UpdateElementFailed: failure to add to SMC
        :return: None
        """
        if as_list:
            json = [dict(zip(['hostnames', 'ipaddress'], d))
                    for d in as_list]
        else:
            json = [{'hostnames': hostnames,
                     'ipaddress': ipaddress}]

        self._create_or_update('hostname_mapping', json)

    @property
    def hostname_mapping(self):
        """
        This profiles hostname to ip address mappings

        :return: list of dict (hostname, ip address mapping)
        """
        return self.data.get('hostname_mapping', [])

    def add_domain_specific_dns_server(self, domain_name=None,
                                       dns_server_addresses=None,
                                       as_list=None):
        """
        Relay specific domains to a specified DNS server

        :param str domain_name: domain name for match
        :param str dns_server_addresses: DNS servers to use (comma separate multiple)
        :param list as_list: provide a list of tuple values in same order as
            constructor: [(domain_name,dns_server_addresses)]
        :raises UpdateElementFailed: failure to add to SMC
        :return: None
        """
        if as_list:
            json = [dict(zip(['domain_name', 'dns_server_addresses'], d))
                    for d in as_list]
        else:
            json = [{'domain_name': domain_name,
                     'dns_server_addresses': dns_server_addresses}]

        self._create_or_update('domain_specific_dns_server', json)

    @property
    def domain_specific_dns_server(self):
        """
        This profiles domain to dns server mappings

        :return: list of dict (domain, dns server/s)
        """
        return self.data.get('domain_specific_dns_server', [])
