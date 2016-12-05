"""
Other element types that treated more like generics, or that can be applied in 
different areas within the SMC. They will not independently be created as standalone
objects and will be more generic container classes that define the required json when
used by API functions or methods.
For example, Blacklist can be applied to an engine directly or system wide. This class
will define the format when calling blacklist functions.
"""
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
        Element.__init__(self, name, meta)
        pass
    
    @classmethod
    def create(cls, name, comment=None):
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
        Element.__init__(self, name, meta)
        pass
    
    @classmethod
    def create(cls, name, comment=None):
        """    
        Create the logical interface
        
        :param str name: name of logical interface
        :param str comment: optional comment
        :return: :py:class:`smc.api.web.SMCResult`
        """
        comment = comment if comment else ''
        cls.json = {'name': name,
                    'comment': comment}
        return ElementCreator(cls)

class MacAddress(Element):
    """
    Mac Address network element that can be used in L2 and IPS
    policy.
    
    Creating a MacAddress::
    
        MacAddress.create(name='mymac', mac_address='22:22:22:22:22:22')
    """
    typeof = 'mac_address'
    
    def __init__(self, name, meta=None):
        Element.__init__(self, name, meta)
        pass
    
    @classmethod
    def create(cls, name, mac_address, comment=None):
        """    
        Create the Mac Address
        
        :param str name: name of mac address
        :param str mac_address: mac address notation
        :param str comment: optional comment
        :return: :py:class:`smc.api.web.SMCResult`
        """
        comment = comment if comment else ''
        cls.json = {'name': name,
                    'address': mac_address,
                    'comment': comment}
        return ElementCreator(cls)
       
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

def prepare_contact_address(address, location, dynamic=False):
    """
    Contact Addresses are used to by Locations to identify the IP address/es 
    assigned to the location. This identifies how an engine, SMC, Log Server, 
    or any element can be contacted when behind a NAT connection.
    
    .. note:: Contact Addresses for servers (Management/Log Server) do not use
              this same object definition
    
    :param list addresses: list of IP addresses for contact address
    :param str location: location href to map this contact address to
    :param boolean dynamic: should this be considered a dynamic contact address. This
           can be used to define an FQDN as address value.
    """
    from smc.elements.helpers import location_helper
    location_ref = location_helper(location)
    contact_addresses = [{'address': address,
                          'dynamic': dynamic,
                          'location_ref': location_ref}]
    return {'contact_addresses': contact_addresses}
