"""
A ContactAddress is used by elements to provide an alternate
address for communication between engine and management/log server.
This is typically used when the SMC sits behind a NAT address and 
the SMC needs to contact the engine directly (this is a default behavior).
In this case, you would add the public IP in front of the engine as a 
contact address to the engine interface.

Example usage::

    >>> from smc import session
    >>> session.login()
    >>> from smc.core.engine import Engine
    >>> from smc.core.contact_address import ContactAddress
    >>> engine = Engine('testfw')
    >>> list(engine.contact_addresses)
    [ContactInterface(name=Interface 12,address=19.19.19.19), ContactInterface(name=Tunnel Interface 2000,address=12.12.12.12), 
     ContactInterface(name=Tunnel Interface 2000,address=13.13.13.13), ContactInterface(name=Interface 11,address=17.17.17.17), 
     ContactInterface(name=Interface 10,address=14.14.14.14), ContactInterface(name=Interface 10,address=10.10.10.10) .... 
    ...
    >>> interface1 = engine.contact_addresses(1)    #get by interface
    >>> interface1
    [ContactInterface(name=Interface 1,address=1.1.1.1), ContactInterface(name=Interface 1,address=2.2.2.2)]
    >>> interface1[0].contact_addresses
    []
    >>> interface1[1].contact_addresses
    []
    >>> for ipv4 in interface1:
    ...   if ipv4.address == '2.2.2.2':
    ...     contact = ContactAddress.create('23.23.23.23', location='Default')
    ...     ipv4.add_contact_address(contact)
    ... 
    >>> interface1[1].contact_addresses
    [ContactAddress(address=23.23.23.23)]

Remove a contact address::
    
    for interface in engine.contact_addresses(1):
        if interface.address == '2.2.2.2':
            for contact in interface.contact_addresses:
                if contact.address == '23.23.23.23':
                    interface.remove_contact_address(contact)
                    
.. note:: Contact Addresses for servers (Management/Log Server) do not use
          this same object definition
    
See :py:class:`smc.elements.other.ServerContactAddress` for more information.
"""
from smc.base.model import prepared_request, Element
from smc.api.exceptions import FetchElementFailed, EngineCommandFailed


class ContactAddress(object):
    """
    Contact address definition used on engine interfaces
    """

    def __init__(self, data):
        self.data = data

    @classmethod
    def create(cls, address, location='Default', dynamic=False):
        """
        Create a new contact address.

        :param str address: IP Address of contact address
        :param str location: Location element to associate with address
        :param bool dynamic: Is this a dynamic address
        :return: `~ContactAddress`
        """
        from smc.elements.helpers import location_helper
        location_ref = location_helper(location)
        data = {'address': address,
                'dynamic': dynamic,
                'location_ref': location_ref}
        return ContactAddress(data)

    @property
    def address(self):
        """
        Address of the contact address

        :rtype: str
        """
        return self.data.get('address')

    @property
    def dynamic(self):
        """
        Is this a dynamic IP based contact address

        :rtype: boolean
        """
        return self.data.get('dynamic') == 'true'

    @property
    def location_ref(self):
        """
        Reference url for the location element

        :rtype: str url href of location
        """
        return self.data.get('location_ref')

    @property
    def location(self):
        """    
        Each contact address has a location associated which is attached
        to the management/log server to identify when to use the 
        contact address. This is that location element.

        :rtype: Element location object
        """
        return Element.from_href(self.location_ref)

    def __repr__(self):
        return '{0}(address={1})'.format(self.__class__.__name__, self.address)


class ContactResource(object):
    def __init__(self, data):
        self.data = data

    def __iter__(self):
        for interface in self.data:
            yield ContactInterface(**interface)

    def __call__(self, interface_id):
        match = 'Interface {}'.format(interface_id)
        return [interface
                for interface in iter(self)
                if match in interface.name]

    def all(self):
        return iter(self)


class ContactInterface(object):
    """
    A ContactInterface represents a contact address configuration
    bound to a specific interface. A contact address can be bound
    to an interface that can have a layer 3 IP Address and in some
    cases may have multiple IP addresses assigned. Each assigned 
    IP can have a unique contact address (or multiple).
    """

    def __init__(self, **kw):
        self.href = kw.pop('href', None)
        fullname = kw.pop('name', None)
        self.name, self.address = fullname.split('_', 1)

    def add_contact_address(self, contact_address):
        """
        Add a contact address to this specified interface. A 
        contact address is an alternative address which is 
        typically applied when NAT is used between the NGFW
        and another component (such as management server).

        :param contact_address: the contact address element
        :type: :py:class:`~ContactAddress`
        :raises EngineCommandFailed: invalid contact address
        :return: None
        """
        result = prepared_request(
            FetchElementFailed,
            href=self.href
        ).read()

        if result.json:  # Existing contact addresses
            data = [address
                    for address in result.json['contact_addresses']
                    if address.get('location_ref') != contact_address.location_ref]
            data.append(contact_address.data)
        else:
            data = [contact_address.data]

        data = {'contact_addresses': data}

        prepared_request(
            EngineCommandFailed,
            href=self.href,
            json=data,
            etag=result.etag
        ).update()

    def remove_contact_address(self, contact_address):
        """
        Remove a contact address from an interface.

        :param contact_address: the contact address element
        :type contact_address: ContactAddress 
        :raises EngineCommandFailed: problem removing address
        :return: None
        """
        result = prepared_request(
            FetchElementFailed,
            href=self.href
        ).read()
        if result.json:
            data = [address
                    for address in result.json['contact_addresses']
                    if address.get('address') != contact_address.address]

            data = {'contact_addresses': data}

            prepared_request(
                EngineCommandFailed,
                href=self.href,
                json=data,
                etag=result.etag
            ).update()

    @property
    def contact_addresses(self):
        """
        Show any assigned contact addresses.

        :return: list :class:`~ContactAddress`
        """
        result = prepared_request(
            FetchElementFailed,
            href=self.href).read().json
        if result:
            return [ContactAddress(address)
                    for address in result.get('contact_addresses')]
        return []

    def __repr__(self):
        return '{0}(name={1},address={2})'.format(
            self.__class__.__name__, self.name, self.address)
