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
    ContactAddressNode(interface_id=11, interface_ip=10.10.10.20)
    ContactAddressNode(interface_id=120, interface_ip=120.120.120.100)
    ContactAddressNode(interface_id=0, interface_ip=1.1.1.1)
    ContactAddressNode(interface_id=12, interface_ip=3.3.3.3)
    ContactAddressNode(interface_id=12, interface_ip=17.17.17.17)
        
Retrieve a specific contact address interface for modification::

    >>> ca = engine.contact_addresses.get(interface_id=12, interface_ip='3.3.3.3')
    >>> ca
    ContactAddressNode(interface_id=12, interface_ip=3.3.3.3)
    >>> list(ca)
    [InterfaceContactAddress(location=Default,address=4.4.4.4), InterfaceContactAddress(location=Foo,address=3.4.5.6)]

Add a new contact address to the fetched interface::
    
    >>> ca.add_contact_address('23.23.23.23', location='mynewlocation')
    >>> list(ca)
    [InterfaceContactAddress(location=Default,address=4.4.4.4), InterfaceContactAddress(location=Foo,address=3.4.5.6),
     InterfaceContactAddress(location=mynewlocation,address=23.23.23.23)]

Remove a contact address::

    >>> ca.remove_contact_address('23.23.23.23')
    >>> list(ca)
    [InterfaceContactAddress(location=Default,address=4.4.4.4), InterfaceContactAddress(location=Foo,address=3.4.5.6)]
    
.. note:: Contact Addresses for servers (Management/Log Server) do not use
          this same object definition
"""
from smc.base.model import SubElement
from smc.elements.helpers import location_helper
from smc.elements.other import ContactAddress
from smc.base.collection import SubElementCollection


class InterfaceContactAddress(ContactAddress):
    """
    An interface contact address is used on engine interfaces
    to provide an alternative location to address mapping. This
    is frequently used when the engine sits behind a NAT and
    you need a public NAT mapping, as might be the case with 
    site to site VPN.
    """
    @property
    def addresses(self):
        return self.get('address')
    
    @property
    def dynamic(self):
        return self.get('dynamic', 'false') == 'true'


class ContactAddressNode(SubElement):
    """
    A mapping of contact address to interface. This is specific to
    assigning the contact address on the engine.
    """
    def __init__(self, **meta):
        meta.update(type='contact_addresses')
        super(ContactAddressNode, self).__init__(**meta)
        self._name, self._address = self.name.split('_')
    
    @property
    def _cas(self):
        return self.data.get('contact_addresses', [])
    
    def __iter__(self):
        for addr in self._cas:
            yield InterfaceContactAddress(addr)
    
    def __contains__(self, location_href):
        for location in self._cas:
            if location.get('location_ref') == location_href:
                return True
        return False
    
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
    
    def update_or_create(self, location, contact_address, with_status=False, **kw):
        """
        Update an existing contact address or create if the location does
        not exist.
        
        :param str location: name of the location, the location will be added
            if it doesn't exist
        :param str contact_address: contact address IP. Can be the string 'dynamic'
            if this should be a dynamic contact address (i.e. on DHCP interface)
        :param bool with_status: if set to True, a 3-tuple is returned with 
            (Element, modified, created), where the second and third tuple
            items are booleans indicating the status
        :raises UpdateElementFailed: failed to update element with reason
        :rtype: ContactAddressNode
        """
        updated, created = False, False
        location_ref = location_helper(location)
        if location_ref in self:
            for ca in self:
                if ca.location_ref == location_ref:
                    ca.update(
                        address=contact_address if 'dynamic' not in contact_address\
                            else 'First DHCP Interface ip',
                        dynamic='true' if 'dynamic' in contact_address else 'false')
                    updated = True
        else:
            self.data.setdefault('contact_addresses', []).append(
                dict(address=contact_address if 'dynamic' not in contact_address\
                        else 'First DHCP Interface ip',
                     dynamic='true' if 'dynamic' in contact_address else 'false',
                     location_ref=location_ref))
            created = True
        
        if updated or created:
            self.update()
        if with_status:
            return self, updated, created
        return self
    
    def add_contact_address(self, contact_address, location='Default'):
        """
        Add a contact address to this specified interface. A 
        contact address is an alternative address which is 
        typically applied when NAT is used between the NGFW
        and another component (such as management server). Adding a
        contact address operation is committed immediately.

        :param str contact_address: IP address for this contact address.
        :raises EngineCommandFailed: invalid contact address
        :return: ContactAddressNode
        """
        return self.update_or_create(location, contact_address)
    
    def remove_contact_address(self, location):
        """
        Remove a contact address from an interface by the location
        name. There is a one to one relationship between a
        contact address and 

        :param str contact_address: ip for contact address
        :raises EngineCommandFailed: problem removing address
        :return: status of delete as boolean
        :rtype: bool
        """
        return self.delete(location)
            
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

    def __str__(self):
        return '{}(interface_id={}, interface_ip={})'.format(
            self.__class__.__name__, self.interface_id, self.interface_ip)


class ContactAddressCollection(SubElementCollection):
    """
    A contact address collection provides all available interfaces that
    can be used to configure a contact address. An eligible interface is
    one that is a layer 3 interface with an address assigned (including
    VLANs)::
    
        for ca in engine.contact_addresses:
            ...
    
    .. note:: All eligible interfaces are returned, regardless of whether
        a contact address is assigned or not.
    """
    def __init__(self, resource):
        super(ContactAddressCollection, self).__init__(
            resource, ContactAddressNode)
        
    def get(self, interface_id, interface_ip=None):
        """
        Get will return a list of interface references based on the
        specified interface id. Multiple references can be returned if
        a single interface has multiple IP addresses assigned.
        
        :return: If interface_ip is provided, a single ContactAddressNode
            element is returned if found. Otherwise a list will be
            returned with all contact address nodes for the given
            interface_id.
        """ 
        interfaces = []
        for interface in iter(self):
            if interface.interface_id == str(interface_id):
                if interface_ip:
                    if interface.interface_ip == interface_ip:
                        return interface
                else:
                    interfaces.append(interface)
        return interfaces
