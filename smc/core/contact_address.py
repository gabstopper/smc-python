"""
A ContactAddress is used by elements to provide an alternate
address for communication between engine and management/log server.
This is typically used when the SMC sits behind a NAT address and 
the SMC needs to contact the engine directly (this is a default behavior).
In this case, you would add the public IP in front of the engine as a 
contact address to the engine interface.

Obtain all eligible interfaces for contact addressess::
        
    >>> engine = Engine('dingo')
    >>> for ca in engine.contact_addresses:
    ...   ca
    ... 
    ContactAddressInterface(interface_id=11, interface_ip=10.10.10.20)
    ContactAddressInterface(interface_id=120, interface_ip=120.120.120.100)
    ContactAddressInterface(interface_id=0, interface_ip=1.1.1.1)
    ContactAddressInterface(interface_id=12, interface_ip=3.3.3.3)
    ContactAddressInterface(interface_id=12, interface_ip=17.17.17.17)
        
Retrieve a specific contact address interface for modification::

    >>> ca = engine.contact_addresses.get(interface_id=12, bound_to='3.3.3.3')
    >>> ca
    ContactAddressInterface(interface_id=12, interface_ip=3.3.3.3)
    >>> list(ca)
    [ContactAddress(address=4.4.4.4, location=Default), ContactAddress(address=3.4.5.6, location=Foo)]

Add a new contact address to the fetched interface::
    
    >>> ca.add_contact_address('23.23.23.23', location='mynewlocation')
    >>> list(ca)
    [ContactAddress(address=4.4.4.4, location=Default), ContactAddress(address=3.4.5.6, location=Foo),
     ContactAddress(address=23.23.23.23, location=mynewlocation)]

Remove a contact address::

    >>> ca.remove_contact_address('23.23.23.23')
    >>> list(ca)
    [ContactAddress(address=4.4.4.4, location=Default), ContactAddress(address=3.4.5.6, location=Foo)]
    
.. note:: Contact Addresses for servers (Management/Log Server) do not use
          this same object definition
"""
from smc.base.model import Element, SubElement, SubDict
from smc.elements.helpers import location_helper


class ContactAddress(SubDict):
    """
    Contact address definition used on engine interfaces. This is a
    dict and can be updated directly.
    
    :ivar str address: Address for this contact address
    :ivar str location_ref: raw ref for this contact address. Use the
        location property to obtain the resolved value
    :ivar bool dynamic: is this a dynamic contact address
    """
    def __init__(self, data):
        super(ContactAddress, self).__init__(data=data)

    @property
    def dynamic(self):
        return self.get('dynamic', 'false') == 'true'
    
    @property
    def location(self):
        """    
        Each contact address has a location associated which is attached
        to the management/log server to identify when to use the 
        contact address. This is that location element.

        :rtype: Element location object
        """
        return Element.from_href(self.get('location_ref')).name
    
    def __repr__(self):
        return 'ContactAddress(address={}, location={})'.format(
            self.get('address'), self.location)
    

class ContactAddressInterface(SubElement):
    def __init__(self, **meta):
        meta.update(type='contact_addresses')
        super(ContactAddressInterface, self).__init__(**meta)
        self._name, self._address = self.name.split('_')
    
    def add_contact_address(self, contact_address, location='Default'):
        """
        Add a contact address to this specified interface. A 
        contact address is an alternative address which is 
        typically applied when NAT is used between the NGFW
        and another component (such as management server). Adding a
        contact address operation is committed immediately.

        :param str contact_address: IP address for this contact address.
        :raises EngineCommandFailed: invalid contact address
        :return: None
        """
        location = location_helper(location)
        if self.data:
            duplicate = False
            for address in self.data['contact_addresses']:
                if address['location_ref'] == location:
                    address['address'] = contact_address
                    duplicate = True
                    break
            if not duplicate:
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

        :param str contact_address: ip for contact address
        :raises EngineCommandFailed: problem removing address
        :return: None
        """
        if self.data:
            data = [address
                    for address in self.data['contact_addresses']
                    if address['address'] != contact_address]
            self.data['contact_addresses'] = data
            self.update()
            
    @property
    def interface_id(self):
        """
        The interface ID for this contact address interface
        
        :rtype: str
        """
        return self._name.split(' ')[-1]
    
    @property
    def interface_ip(self):
        """
        The IP address for this contact address interface
        
        :rtype: str
        """
        return self._address
    
    def __iter__(self):
        for addr in self.data.get('contact_addresses', []):
            yield ContactAddress(addr)

    def __str__(self):
        return 'ContactAddressInterface(interface_id={}, interface_ip={})'.format(
            self.interface_id, self.interface_ip)

            
class ContactAddressCollection(object):
    """
    A contact address collection provides all available interfaces that
    can be used to configure a contact address. An eligible interface is
    one that is a layer 3 interface with an address assigned (including
    VLANs)::
    
        for ca in engine.contact_addresses:
            ...
    """
    def __init__(self, engine):
        self._engine = engine
    
    def __iter__(self):
        for addr in self._engine.make_request(resource='contact_addresses'):
            yield ContactAddressInterface(**addr)
    
    def all(self):
        return iter(self)
    
    def get(self, interface_id, bound_to=None):
        """
        Get will return a list of interface references based on the
        specified interface id. Multiple references can be returned if
        a single interface has multiple IP addresses assigned.
        
        :return: If bound_to is provided, the ContactAddressInterface is returned.
            If not provided, a list is returned with all ContactAddressInterface's
            available.
        """ 
        interfaces = []
        for interface in iter(self):
            if interface.interface_id == str(interface_id):
                if bound_to:
                    if interface.interface_ip == bound_to:
                        return interface
                else:
                    interfaces.append(interface)
        return interfaces
        
