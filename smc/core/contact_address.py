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
    >>> engine = Engine('ve-3')
    >>> list(engine.contact_addresses)
    [InterfaceContactAddress(name=Interface 0,address=10.29.248.29), InterfaceContactAddress(name=Interface 1,address=10.29.248.33)]
    >>> interface1 = engine.contact_addresses(1)
    >>> interface1
    [InterfaceContactAddress(name=Interface 1,address=10.29.248.33)]
    >>> interface1[0].contact_addresses
    []
    >>> for interfaces in interface1:
    ...   if interfaces.address == '10.29.248.33':
    ...     interfaces.add_contact_address(contact_address='12.12.12.12', location='foo')
    ... 
    >>> interface1[0].contact_addresses
    [ContactAddress(location=foolocation,address=12.12.12.12)]
    >>> 

Remove a contact address::
    
    >>> interface1 = engine.contact_addresses(1)
    >>> interface1
    [InterfaceContactAddress(name=Interface 1,address=10.29.248.33)]
    >>> interface1[0].contact_addresses
    [ContactAddress(location=foolocation,address=12.12.12.12)]
    >>> interface1[0].remove_contact_address('12.12.12.12')
    >>> interface1[0].contact_addresses
    []

.. note:: Contact Addresses for servers (Management/Log Server) do not use
          this same object definition
"""
from smc.base.model import Element, SubElement
from smc.elements.helpers import location_helper


class ContactAddress(object):
    """
    Contact address definition used on engine interfaces
    """
    def __init__(self, **kwargs):
        self.data = kwargs

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
        return Element.from_href(self.location_ref).name

    def __repr__(self):
        return '{}(location={},address={})'.format(
            self.__class__.__name__, self.location,
            self.address)


class ContactResource(object):
    def __init__(self, data):
        self.data = data

    def __iter__(self):
        for interface in self.data:
            #yield ContactInterface(**interface)
            yield InterfaceContactAddress(**interface)

    def __call__(self, interface_id):
        match = 'Interface {}'.format(interface_id)
        return [interface
                for interface in iter(self)
                if match in interface.name]

    def all(self):
        return iter(self)


class InterfaceContactAddress(SubElement):
    """
    InterfaceContactAddress is used to specify a unique NAT
    address on an interface used to contact the engine.
    """
    def __init__(self, **meta):
        fullname = meta.pop('name', None)
        name, self._address = fullname.split('_', 1)
        meta.update(name=name)
        super(InterfaceContactAddress, self).__init__(**meta)
        
    @property
    def address(self):
        return self._address
        
    @property
    def contact_addresses(self):
        """
        Contact addresses for this interface
        """
        if len(self.data):
            return [ContactAddress(**contact)
                    for contact in self.data['contact_addresses']]
        return []
    
    def add_contact_address(self, contact_address, location='Default'):
        """
        Add a contact address to this specified interface. A 
        contact address is an alternative address which is 
        typically applied when NAT is used between the NGFW
        and another component (such as management server).

        :param str contact_address: IP address for this contact
            address.
        :type: :py:class:`~ContactAddress`
        :raises EngineCommandFailed: invalid contact address
        :return: None
        """
        location = location_helper(location)
        if self.data:
            seen = False
            for address in self.data['contact_addresses']:
                if address['location_ref'] == location:
                    address['address'] = contact_address
                    seen = True
                    break
            if not seen:
                self.data['contact_addresses'].append(
                    {'address': contact_address,
                     'location_ref': location,
                     'dynamic': False})
        else:
            self.data['contact_addresses'] = \
                [{'address': contact_address,
                  'location_ref': location,
                  'dynamic': False}]
        self.update()
    
    def remove_contact_address(self, contact_address):
        """
        Remove a contact address from an interface.

        :param contact_address: the contact address element
        :type contact_address: ContactAddress 
        :raises EngineCommandFailed: problem removing address
        :return: None
        """
        if self.data:
            data = [address
                    for address in self.data['contact_addresses']
                    if address['address'] != contact_address]
            self.data['contact_addresses'] = data
            self.update()
    
    def __unicode__(self):
        return u'{0}(name={1},address={2})'.format(
            self.__class__.__name__, self.name, self.address)

    def __repr__(self):
        return str(self)
    
    