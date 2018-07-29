"""
Module that represents server based configurations
"""
from smc.base.model import SubElement, ElementCreator, Element, ElementRef
from smc.elements.helpers import location_helper
from smc.elements.other import ContactAddress
from smc.api.exceptions import CreateElementFailed
from smc.base.util import element_resolver
            

class MultiContactAddress(SubElement):
    """ 
    A MultiContactAddress is a location and contact address pair which
    can have multiple addresses. Server elements such as Management
    and Log Server can have configured locations with mutliple addresses
    per location.
    
    Use this server reference to create, add or remove contact addresses
    from servers::
    
        mgt_server = ManagementServer.objects.first()
        mgt_server.contact_addresses.update_or_create(
            location='mylocation', addresses=['1.1.1.1', '1.1.1.2'])
    
    Or remove by location::
    
        mgt_server.contact_addresses.delete('mylocation')
    
    """
    @property
    def _cas(self):
        return self.data.get('multi_contact_addresses', [])
    
    def __iter__(self):
        for address in self._cas:
            yield ContactAddress(**address)
    
    def __contains__(self, location_href):
        for location in self._cas:
            if location.get('location_ref') == location_href:
                return True
        return False
    
    def get(self, location_name):
        """
        Get a contact address by location name
        
        :param str location_name: name of location
        :return: return contact address element or None
        :rtype: ContactAddress
        """
        location_ref = location_helper(location_name, search_only=True)
        if location_ref:
            for location in self:
                if location.location_ref == location_ref:
                    return location
    
    def delete(self, location_name):
        """
        Remove a given location by location name. This operation is
        performed only if the given location is valid, and if so,
        `update` is called automatically.
        
        :param str location: location name or location ref
        :raises UpdateElementFailed: failed to update element with reason
        :rtype: bool
        """
        updated = False
        location_ref = location_helper(location_name, search_only=True)
        if location_ref in self:
            self._cas[:] = [loc for loc in self
                if loc.location_ref != location_ref]
            self.update()
            updated = True
        return updated

    def update_or_create(self, location, contact_addresses, with_status=False,
            overwrite_existing=False, **kw):
        """
        Update or create a contact address and location pair. If the
        location does not exist it will be automatically created. If the
        server already has a location assigned with the same name, the
        contact address specified will be added if it doesn't already
        exist (Management and Log Server can have multiple address for a
        single location).
        
        :param list(str) contact_addresses: list of contact addresses for
            the specified location
        :param str location: location to place the contact address in
        :param bool overwrite_existing: if you want to replace existing
            location to address mappings set this to True. Otherwise if
            the location exists, only new addresses are appended
        :param bool with_status: if set to True, a 3-tuple is returned with 
            (Element, modified, created), where the second and third tuple
            items are booleans indicating the status
        :raises UpdateElementFailed: failed to update element with reason
        :rtype: MultiContactAddress
        """
        updated, created = False, False
        location_ref = location_helper(location)
        if location_ref in self:
            for loc in self:
                if loc.location_ref == location_ref:
                    if overwrite_existing:
                        loc['addresses'][:] = contact_addresses
                        updated = True
                    else:
                        for ca in contact_addresses:
                            if ca not in loc.addresses:
                                loc['addresses'].append(ca)
                                updated = True
        else:
            self.data.setdefault('multi_contact_addresses', []).append(
                dict(addresses=contact_addresses, location_ref=location_ref))
            created = True
        
        if updated or created:
            self.update()
        if with_status:
            return self, updated, created
        return self
        

class ContactAddressMixin(object):
    """
    Mixin class to provide an interface to contact addresses on the
    management and log server.
    Contact addresses on servers can contain multiple IP's for a single
    location.
    """
    @property
    def contact_addresses(self):
        """
        Provides a reference to contact addresses used by this server.
        
        Obtain a reference to manipulate or iterate existing contact
        addresses::
        
            >>> from smc.elements.servers import ManagementServer
            >>> mgt_server = ManagementServer.objects.first()
            >>> for contact_address in mgt_server.contact_addresses:
            ...   contact_address
            ... 
            ContactAddress(location=Default,addresses=[u'1.1.1.1'])
            ContactAddress(location=foolocation,addresses=[u'12.12.12.12'])
        
        :rtype: MultiContactAddress
        """
        return MultiContactAddress(
            href=self.get_relation('contact_addresses'),
            type=self.typeof,
            name=self.name)
        
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
        return self.contact_addresses.update_or_create(location, [contact_address])

    def remove_contact_address(self, location):
        """
        Remove contact address by name of location. You can obtain all contact
        addresses by calling :func:`contact_addresses`.

        :param str location: str name of location, will be created if it
            doesn't exist
        :raises ModificationFailed: failed removing contact address
        :return: None
        """
        return self.contact_addresses.delete(location)

   
class ManagementServer(ContactAddressMixin, Element):
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


class LogServer(ContactAddressMixin, Element):
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

   
class ProxyServer(ContactAddressMixin, Element):
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
    
    :param str http_proxy: type of proxy configuration, either generic or forcepoint_ap-web_cloud
    """     
    typeof = 'proxy_server'
    location = ElementRef('location_ref')
    
    @classmethod
    def create(cls, name, address, inspected_service, secondary=None,
               balancing_mode='ha', proxy_service='generic', location=None,
               comment=None, add_x_forwarded_for=False, trust_host_header=False,
               **kw):
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
    
    @property
    def proxy_service(self):
        """
        The proxy service for this proxy server configuration
        
        :rtype: str
        """
        return self.data.get('http_proxy')

    @classmethod
    def update_or_create(cls, with_status=False, **kwargs):
        element, updated, created = super(ProxyServer, cls).update_or_create(
            defer_update=True, **kwargs)
        
        if not created:
            if 'proxy_service' in element.data and element.http_proxy != element.data['proxy_service']:
                element.data['http_proxy'] = element.data.pop('proxy_service')
                updated = True
            if 'address' in kwargs:
                if ',' in element.data.get('address'):
                    addresses = element.data.pop('address').split(',')
                    element.data['address'] = addresses.pop(0)
                    # Remainder is ip_address attribute
                    if set(addresses) ^ set(element.data.get('ip_address', [])):
                        element.data['ip_address'] = addresses
                    updated = True
                    
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
    
    @property
    def inspected_services(self):
        """
        The specified services for inspection. An inspected service is a
        reference to a protocol that can be forwarded for inspection, such
        as HTTP, HTTPS, FTP and SMTP.
        
        :rtype: list(InspectedService)
        """
        return [InspectedService(**service) for service in self.make_request(
            resource='inspected_services')]

    
class InspectedService(SubElement):
    """
    This represents the service defined for inspection for a
    ProxyServer element.
    
    :ivar str service_type: the service type for inspection
    :ivar int port: the port for this service 
    """
    pass

#     @classmethod
#     def create(cls, service_type, port, comment=None):
#         """
#         Create a service type defintion for a proxy server protocol.
#         
#         :param str service_type: service type to use, HTTP, HTTPS, FTP or
#             SMTP
#         :param str,int port: port for this service
#         :param str comment: optional comment
#         """
#         json = {'service_type': service_type.upper(),
#             'port': port, 'comment': comment}
#         data = ElementCache(data=json)
#         return type(cls.__name__, (cls,), {'data': data})()
