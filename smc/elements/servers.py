"""
Module that represents server based configurations
"""
from smc.base.model import SubElement, ElementCreator
from smc.elements.helpers import location_helper
from smc.base.model import Element


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
        Address for contact address
        
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
        return Element.from_href(self.data['location_ref']).name
    
    def __repr__(self):
        return '{}(location={},addresses={})'.format(
            self.__class__.__name__, self.location,
            self.addresses)


class ServerContactAddress(SubElement):
    def __init__(self, **meta):
        super(ServerContactAddress, self).__init__(**meta)

    def __iter__(self):
        if self.data:
            for contact in self.data['multi_contact_addresses']:
                yield ContactAddress(**contact)
        
    def add(self, contact_address, location):
        location = location_helper(location)
        if self.data:
            seen = False
            for address in self.data['multi_contact_addresses']:
                if address['location_ref'] == location:
                    if contact_address not in address['addresses']:
                        address['addresses'].append(contact_address)
                    seen = True
                    break
            if not seen:
                self.data['multi_contact_addresses'].append(
                    {'addresses': [contact_address],
                     'location_ref': location})       
        else:
            self.data['multi_contact_addresses'] = \
                [{'addresses': [contact_address],
                  'location_ref': location}]
        self.update()

    def remove_by_location(self, location):
        if len(self.data):
            location = location_helper(location)
            contact = self.data['multi_contact_addresses']
            addresses = [locations for locations in contact
                         if locations['location_ref'] != location]
            contact = addresses
            self.data['multi_contact_addresses'] = addresses
            self.update()

        
class ServerCommon(object):
    def contact_addresses(self):
        """
        View contact addresses for this management server. To add contact
        addresses, call :py:func:`add_contact_address`

        :return: contact addresses
        :rtype: list(ContactAddress)
        """
        contact = ServerContactAddress(
            href=self.data.get_link('contact_addresses'))
        return [c for c in contact]

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
        contact = ServerContactAddress(
            href=self.data.get_link('contact_addresses'))
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
        contact = ServerContactAddress(
            href=self.data.get_link('contact_addresses'))
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

    :param name: name of management server
    """
    typeof = 'mgt_server'

    def __init__(self, name, **meta):
        super(ManagementServer, self).__init__(name, **meta)
        pass


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

    def __init__(self, name, **meta):
        super(LogServer, self).__init__(name, **meta)
        pass

    
class HttpProxy(Element):
    """
    An HTTP Proxy based element. Used in various areas of the configuration
    such as engine properties to define proxies for File Reputation, etc.
    
    """
    typeof = 'http_proxy'
    
    def __init__(self, name, **meta):
        super(HttpProxy, self).__init__(name, **meta)
        pass
    
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

    def __init__(self, name, **meta): 
        super(DNSServer, self).__init__(name, **meta) 
    
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
