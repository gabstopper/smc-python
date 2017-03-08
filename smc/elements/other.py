"""
Other element types that treated more like generics, or that can be applied in 
different areas within the SMC. They will not independently be created as standalone
objects and will be more generic container classes that define the required json when
used by API functions or methods.
For example, Blacklist can be applied to an engine directly or system wide. This class
will define the format when calling blacklist functions.
"""
import smc.actions.search as search
from smc.base.model import Element, ElementCreator

class Location(Element):
    """
    Locations are used by elements to identify when they are behind a NAT
    connection. For example, if you have an engine that connects to the SMC
    across the internet using a public address, a location will be the tag
    applied to the Management Server (with contact address) and on the engine
    to identify how to connect. In this case, the location will map to a contact
    address using a public IP.
    
    :param str name: name of location
    
    .. note:: Locations require SMC API version >= 6.1
    """
    typeof = 'location'

    def __init__(self, name, meta=None):
        super(Location, self).__init__(name, meta)
        pass
    
    @classmethod
    def create(cls, name, comment=None):
        """
        Create a location element
        
        :param name: name of location
        :return: str href: href of location element
        """
        comment = comment if comment else ''
        cls.json = {'name': name,
                    'comment': comment}
        return ElementCreator(cls)

class LogicalInterface(Element):
    """
    Logical interface is used on either inline or capture interfaces. If an
    engine has both inline and capture interfaces (L2 Firewall or IPS role),
    then you must use a unique Logical Interface on the interface type.

    Create a logical interface::
    
        LogicalInterface.create('mylogical_interface')  
    """
    typeof = 'logical_interface'
    
    def __init__(self, name, meta=None):
        super(LogicalInterface, self).__init__(name, meta)
        pass
    
    @classmethod
    def create(cls, name, comment=None):
        """    
        Create the logical interface
        
        :param str name: name of logical interface
        :param str comment: optional comment
        :return: str href: href of logical interface element
        """
        comment = comment if comment else ''
        cls.json = {'name': name,
                    'comment': comment}
        return ElementCreator(cls)

class MacAddress(Element):
    """
    Mac Address network element that can be used in L2 and IPS
    policy source and destination fields.
    
    Creating a MacAddress::
    
        MacAddress.create(name='mymac', mac_address='22:22:22:22:22:22')
    """
    typeof = 'mac_address'
    
    def __init__(self, name, meta=None):
        super(MacAddress, self).__init__(name, meta)
        pass
    
    @classmethod
    def create(cls, name, mac_address, comment=None):
        """    
        Create the Mac Address
        
        :param str name: name of mac address
        :param str mac_address: mac address notation
        :param str comment: optional comment
        :return: str href: href of macaddress element
        """
        comment = comment if comment else ''
        cls.json = {'name': name,
                    'address': mac_address,
                    'comment': comment}
        return ElementCreator(cls)

class ContactAddress(object):
    """
    A ContactAddress is used by elements to provide an alternate
    address for communication between engine and management/log server.
    This is typically used when the SMC sits behind a NAT address and 
    the SMC needs to contact the engine directly (this is a default behavior).
    In this case, you would add the public IP in front of the engine as a 
    contact address to the engine interface.
    
    .. note:: Contact Addresses for servers (Management/Log Server) do not use
              this same object definition
    """
    def __init__(self, data):
        self.data = data
    
    @classmethod
    def create(cls, address, location='Default', dynamic=False):
        """
        Create a new contact address.
        
        :param str address: IP Address of contact address
        :param str location: Location element to associate with address
        :param boolean dynamic: Is this a dynamic address
        :return: dict contact address
        """
        from smc.elements.helpers import location_helper
        location_ref = location_helper(location)
        address = [{'address': address,
                    'dynamic': dynamic,
                    'location_ref': location_ref}]
        return {'contact_addresses': address}
    
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
        return bool(self.data.get('dynamic') == 'true')
    
    @property
    def location(self):
        """    
        Each contact address has a location associated which is attached
        to the management/log server to identify when to use the 
        contact address. This is that location element.
        
        :rtype: str
        """
        return search.element_name_by_href(self.data.get('location_ref'))
           
def prepare_blacklist(src, dst, duration=3600):
    """ 
    Add a blacklist entry by source / destination
    A blacklist can be added directly from the engine node, or from
    the system context. If submitting from the system context, it becomes
    a global blacklist. This will return the properly formatted json
    to submit.
    
    :param src: source address, with cidr, i.e. 10.10.10.10/32
    :param dst: destination address with cidr
    :param int duration: length of time to blacklist
    """
    
    json = {}
    end_point1 = {'name': '', 'address_mode': 'address',
                           'ip_network': src}
    end_point2 = {'name': '', 'address_mode': 'address',
                           'ip_network': dst}
    json.update(duration=duration)
    json.update(end_point1=end_point1)
    json.update(end_point2=end_point2)
    return json