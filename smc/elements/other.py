"""
Other element types that treated more like generics, or that can be applied in 
different areas within the SMC. They will not independently be created as standalone
objects and will be more generic container classes that define the required json when
used by API functions or methods.
For example, Blacklist can be applied to an engine directly or system wide. This class
will define the format when calling blacklist functions.
"""
from helpers import location_helper

class Blacklist(object):
    """ Add a blacklist entry by source / destination
    A blacklist can be added directly from the engine node, or from
    the system context. If submitting from the system context, it becomes
    a global blacklist.
    
    :param src: source address, with cidr, i.e. 10.10.10.10/32
    :param dst: destination address with cidr
    :param int duration: length of time to blacklist
    """
    def __init__(self, src, dst, duration=3600, name=None):
        self.name = name
        self.duration = duration
        self.end_point1 = {'name': '', 'address_mode': 'address',
                           'ip_network': src}
        self.end_point2 = {'name': '', 'address_mode': 'address',
                           'ip_network': dst}


class ContactAddress(object):
    """
    Contact Addresses are used to by Locations to identify the IP address/es 
    assigned to the location. This identifies how an engine, SMC, Log Server, 
    or any element can be contacted when behind a NAT connection.
    
    .. note:: Contact Addresses for servers (Management/Log Server) do not use
              this same object definition
    
    :param list addresses: list of IP addresses for contact address
    :param str location: location href to map this contact address to
    :param boolean dynamic: should this be considered a dynamic contact address
    """
    def __init__(self, address, location, dynamic=False):
        location_ref = location_helper(location)
        self.contact_addresses = [{'address': address,
                                   'dynamic': dynamic,
                                   'location_ref': location_ref}]
