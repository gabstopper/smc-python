"""
Module that represents server based configurations
"""
from smc.base.model import SubElement, ElementCreator
from smc.elements.helpers import location_helper
from smc.base.model import Element
from smc.base.structs import SerializedIterable
from smc.api.exceptions import CreateElementFailed
from smc.base.util import element_resolver

    
    
class ContactAddress(object):
    """
    A ContactAddress for server elements such as Management Server and
    Log Server.
    """
    def __init__(self, **kwargs):
        self.data = kwargs
    
    @property
    def addresses(self):
        """
        List of addresses set as contact address
        
        :rtype: list
        """
        return self.data['addresses']
    
    @property
    def location_ref(self):
        return self.data['location_ref']

    @property
    def location(self):
        """
        Location name for contact address
        
        :rtype: str
        """
        return Element.from_href(self.location_ref).name
    
    def __repr__(self):
        return '{}(location={},addresses={})'.format(
            self.__class__.__name__, self.location,
            self.addresses)


class MultiContactAddress(SubElement):
    def __len__(self):
        return len(self.data.get('multi_contact_addresses', []))
    
    def __iter__(self):
        for ca in SerializedIterable(
            self.data.get('multi_contact_addresses', []), ContactAddress):
            yield ca
    
    def add(self, contact_address, location):
        location = location_helper(location)
        updated = False
        for loc in self:
            if loc.location_ref == location:
                if contact_address not in loc.addresses:
                    loc.data['addresses'].append(contact_address)
                updated = True
        if not updated:
            self.data.setdefault('multi_contact_addresses', []).append(
                dict(addresses=[contact_address],
                     location_ref=location))
        self.update()

    def remove_by_location(self, location):
        if len(self.data):
            location = location_helper(location)
            data = [loc.data for loc in self
                    if loc.location_ref != location]
            self.data['multi_contact_addresses'] = data
            self.update()

        
class ServerCommon(object):
    def contact_addresses(self):
        """
        View contact addresses for this management server. To add contact
        addresses, call :py:func:`add_contact_address`

        :return: contact addresses
        :rtype: list(ContactAddress)
        """
        return MultiContactAddress(
            href=self.get_relation('contact_addresses'))
        
    def add_contact_address(self, contact_address, location):
        """
        Add a contact address to the Log Server::

            server = LogServer('LogServer 172.18.1.25')
            server.add_contact_address('44.44.44.4', 'ARmoteLocation')

        :param str contact_address: IP address used as contact address
        :param str location: Name of location to use, will be created if
               it doesn't exist
        :raises ModificationFailed: failed adding contact address
        :return: None
        """
        contact = self.contact_addresses()
        contact.add(contact_address, location)

    def remove_contact_address(self, location):
        """
        Remove contact address by name of location. You can obtain all contact
        addresses by calling :func:`contact_addresses`.

        :param str location: str name of location, will be created if it
            doesn't exist
        :raises ModificationFailed: failed removing contact address
        :return: None
        """
        contact = self.contact_addresses()
        contact.remove_by_location(location)

       
class ManagementServer(ServerCommon, Element):
    """
    Management Server configuration. Most configuration settings are better set
    through the SMC UI, such as HA, however this object can be used to do simple
    tasks such as add a contact addresses to the Management Server when a security
    engine needs to communicate over NAT.

    It's easiest to get the management server reference through a collection::

        >>> ManagementServer.objects.first()
        ManagementServer(name=Management Server)

    :ivar name: name of management server
    :ivar address: address of Management Server
    
    """
    typeof = 'mgt_server'


class LogServer(ServerCommon, Element):
    """
    Log Server elements are used to receive log data from the security engines
    Most settings on Log Server generally do not need to be changed, however it
    may be useful to set a contact address location and IP mapping if the Log Server
    needs to be reachable from an engine across NAT

     It's easiest to get the management server reference through a collection::

        >>> LogServer.objects.first()
        LogServer(name=LogServer 172.18.1.150)
    """
    typeof = 'log_server'

    
class HttpProxy(Element):
    """
    An HTTP Proxy based element. Used in various areas of the configuration
    such as engine properties to define proxies for File Reputation, etc.
    
    """
    typeof = 'http_proxy'
    
    @classmethod
    def create(cls, name, address, proxy_port=8080, username=None,
               password=None, secondary=None, comment=None):
        """
        Create a new HTTP Proxy service. Proxy must define at least
        one primary address but can optionally also define a list
        of secondary addresses.
        
        :param str name: Name of the proxy element
        :param str address: Primary address for proxy
        :param int proxy_port: proxy port (default: 8080)
        :param str username: optional username for authentication (default: None)
        :param str password: password for username if defined (default: None)
        :param str comment: optional comment
        :param list secondary: secondary list of proxy server addresses
        :raises CreateElementFailed: Failed to create the proxy element
        :rtype: HttpProxy
        """
        json = {
            'name': name,
            'address': address,
            'comment': comment,
            'http_proxy_port': proxy_port,
            'http_proxy_username': username if username else '',
            'http_proxy_password': password if password else '',
            'secondary': secondary if secondary else []}
        
        return ElementCreator(cls, json)

    
class DNSServer(Element):
    """
    There are some cases in which you must define an External DNS Server
    element.

    * For dynamic DNS (DDNS) updates with a Multi-Link configuration.
    * If you want to use a DNS server for resolving malware signature mirrors.
    * If you want to use a DNS server for resolving domain names and URL filtering
      categorization services on Firewalls, IPS engines, and Layer 2 Firewalls.
        
    You can also optionally use External DNS Server elements to specify the DNS servers
    to which the firewall forwards DNS requests when you configure DNS relay.
    
    :ivar int time_to_live: how long a DNS entry can be cached
    :ivar int update_interval: how often DNS entries can be updated
    """
    typeof = 'dns_server'

    @classmethod
    def create(cls, name, address, time_to_live=20, update_interval=10,
               secondary=None, comment=None):
        """
        Create a DNS Server element.
        
        :param str name: Name of DNS Server
        :param str address: IP address for DNS Server element
        :param int time_to_live: Defines how long a DNS entry can be cached
            before querying the DNS server again (default: 20)
        :param int update_interval: Defines how often the DNS entries can be
            updated to the DNS server if the link status changes constantly
            (default: 10)
        :param list secondary: a secondary set of IP address for this element
        :raises CreateElementFailed: Failed to create with reason
        :rtype: DNSServer
        """
        json = {
            'name': name,
            'address': address,
            'comment': comment,
            'time_to_live': time_to_live,
            'update_interval': update_interval,
            'secondary': secondary if secondary else []}
        
        return ElementCreator(cls, json)

   
class ProxyServer(Element):
    """
    A ProxyServer element is used in the firewall policy to provide the ability to
    send HTTP, HTTPS, FTP or SMTP traffic to a next hop proxy.
    There are two types of next hop proxies, 'Generic' and 'Forcepoint AP Web".
    
    Example of creating a configuration for a Forcepoint AP-Web proxy redirect::
    
        server = ProxyServer.update_or_create(name='myproxy',
            address='1.1.1.1', proxy_service='forcepoint_ap-web_cloud',
            fp_proxy_key='mypassword', fp_proxy_key_id=3, fp_proxy_user_id=1234,
            inspected_service=[{'service_type': 'HTTP', 'port': '80'}])
    
    Create a Generic Proxy forward service::
    
        server = ProxyServer.update_or_create(name='generic', address='1.1.1.1,1.1.1.2',
            inspected_service=[{'service_type': 'HTTP', 'port': 80}, {'service_type': 'HTTPS', 'port': 8080}])
    
    Inspected services take a list of keys `service_type` and `port`. Service type key values
    are 'HTTP', 'HTTPS', 'FTP' and 'SMTP'. Port value is the port for the respective protocol.
    """     
    typeof = 'proxy_server'
    
    @classmethod
    def create(cls, name, address, secondary=None, balancing_mode='ha',
               proxy_service='generic', location=None, comment=None,
               add_x_forwarded_for=False, trust_host_header=False,
               inspected_service=None, **kw):
        """
        Create a Proxy Server element
        
        :param str name: name of proxy server element
        :param str address: address of element. Can be a single FQDN or comma separated
            list of IP addresses
        :param list secondary: list of secondary IP addresses
        :param str balancing_mode: how to balance traffic, valid options are
            ha (first available server), src, dst, srcdst (default: ha)
        :param str proxy_service: which proxy service to use for next hop, options
            are generic or forcepoint_ap-web_cloud
        :param str,Element location: location for this proxy server
        :param bool add_x_forwarded_for: add X-Forwarded-For header when using the
            Generic Proxy forwarding method (default: False)
        :param bool trust_host_header: trust the host header when using the Generic
            Proxy forwarding method (default: False)
        :param dict inspected_service: inspection services dict. Valid keys are
            service_type and port. Service type valid values are HTTP, HTTPS, FTP or SMTP
            and are case sensitive
        :param str comment: optional comment
        :param kw: keyword arguments are used to collect settings when the proxy_service
            value is forcepoint_ap-web_cloud. Valid keys are `fp_proxy_key`, 
            `fp_proxy_key_id`, `fp_proxy_user_id`. The fp_proxy_key is the password value.
            All other values are of type int
        """     
        json = {'name': name,
                'comment': comment,
                'secondary': secondary or [],
                'http_proxy': proxy_service,
                'balancing_mode': balancing_mode,
                'inspected_service': inspected_service,
                'trust_host_header': trust_host_header,
                'add_x_forwarded_for': add_x_forwarded_for,
                'location_ref': element_resolver(location)
            }
        addresses = address.split(',')
        json.update(address=addresses.pop(0))
        json.update(ip_address=addresses if 'ip_address' not in kw else kw['ip_address'])
        
        if proxy_service == 'forcepoint_ap-web_cloud':
            for key in ('fp_proxy_key', 'fp_proxy_key_id', 'fp_proxy_user_id'):
                if key not in kw:
                    raise CreateElementFailed('Missing required fp key when adding a '
                        'proxy server to forward to forcepoint. Missing key: %s' % key)
                json[key] = kw.get(key)
        
        return ElementCreator(cls, json)

    @classmethod
    def update_or_create(cls, with_status=False, **kwargs):
        if 'proxy_service' in kwargs:
            kwargs.update(http_proxy=kwargs.pop('proxy_service'))
        if 'address' in kwargs and ',' in kwargs.get('address'):
            addresses = kwargs.pop('address').split(',')
            kwargs.update(address=addresses.pop(0))
            kwargs.update(ip_address=addresses)          
        element, updated, created = super(ProxyServer, cls).update_or_create(
            defer_update=True, **kwargs)
        if not created:
            inspected_service = kwargs.pop('inspected_service', None)
            if inspected_service is not None:
                service_keys = set([k.get('service_type') for k in inspected_service])
                element_keys = set([k.get('service_type') for k in element.data.get(
                    'inspected_service', [])])
                if service_keys ^ element_keys:
                    element.data['inspected_service'] = inspected_service
                    updated = True
            if updated:
                element.update()
                
        if with_status:
            return element, updated, created
        return element
