"""
Other element types that treated more like generics, or that can be applied in 
different areas within the SMC. They will not independently be created as standalone
objects and will be more generic container classes that define the required json when
used by API functions or methods.
For example, Blacklist can be applied to an engine directly or system wide. This class
will define the format when calling blacklist functions.
"""
from smc.base.model import Element, ElementCreator, prepared_request
from smc.api.exceptions import ModificationFailed

class CategoryTag(Element):
    """
    CategoryTag is used to group and categorize elements by
    type. Once a tag is created, it can be assigned by an 
    element and used as a search filter when managing large
    numbers of elements.
    ::
    
        >>> from smc.elements.other import CategoryTag
        >>> CategoryTag.create(name='foo', comment='test tag')
        'http://172.18.1.150:8082/6.1/elements/category_tag/3531'
    """
    typeof = 'category_tag'
    
    def __init__(self, name, **meta):
        super(CategoryTag, self).__init__(name, **meta)
        pass

    @classmethod
    def create(cls, name, comment=None):
        """
        Add a category element

        :param name: name of location
        :return: str href: href of location element
        """
        comment = comment if comment else ''
        json = {'name': name,
                'comment': comment}
        
        return ElementCreator(cls, json)
    
    def search_elements(self):
        """
        Find all elements assigned to this category tag
        
        :return list :py:class:`smc.base.model.Element`
        """
        return [Element.from_meta(**tag)
                for tag in 
                prepared_request(
                    href=self.resource.search_elements_from_category_tag
                    ).read().json] 
    
    def add_element(self, element):
        """
        Element can be href or type :py:class:`smc.base.model.Element`
        ::
        
            >>> from smc.elements.other import CategoryTag
            >>> category = CategoryTag('foo')
            >>> category.add_element(Host('kali'))

        :param str,Element element: element to add to tag
        :raises: ModificationFailed: failed adding element
        :return: None
        """
        if isinstance(element, Element):
            element = element.href
        
        prepared_request(
            ModificationFailed,
            href=self.resource.category_add_element,
            json={'value': element}
            ).create()

    def remove_element(self, element):
        """
        Remove an element from this category tag. Find elements assigned
        by :func:`~search_elements`. Element can be str href or type
        :py:class:`smc.base.model.Element`.
        ::
        
            >>> from smc.elements.other import CategoryTag
            >>> from smc.elements.network import Host
            >>> category.remove_element(Host('kali'))
    
        :param str, Element element: element to remove
        :raises ModificationFailed: cannot remove element
        :return: None
        """
        if isinstance(element, Element):
            element = element.href
            
        prepared_request(
            ModificationFailed,
            href=self.resource.category_remove_element,
            json={'value': element}
            ).create()
                         
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

    def __init__(self, name, **meta):
        super(Location, self).__init__(name, **meta)
        pass
    
    @classmethod
    def create(cls, name, comment=None):
        """
        Create a location element
        
        :param name: name of location
        :return: href of location element
        """
        comment = comment if comment else ''
        json = {'name': name,
                'comment': comment}
        
        return ElementCreator(cls, json)
    
    @property
    def used_on(self):
        """
        Return all NAT'd elements using this location. 
        
        .. note::
            Available only in SMC version 6.2
        
        :return: list elements used by this location
        """
        return [Element.from_meta(**element)
                for element in
                prepared_request(
                    href=self.resource.search_nated_elements_from_location
                    ).read().json]
    
class LogicalInterface(Element):
    """
    Logical interface is used on either inline or capture interfaces. If an
    engine has both inline and capture interfaces (L2 Firewall or IPS role),
    then you must use a unique Logical Interface on the interface type.

    Create a logical interface::
    
        LogicalInterface.create('mylogical_interface')  
    """
    typeof = 'logical_interface'
    
    def __init__(self, name, **meta):
        super(LogicalInterface, self).__init__(name, **meta)
        pass
    
    @classmethod
    def create(cls, name, comment=None):
        """    
        Create the logical interface
        
        :param str name: name of logical interface
        :param str comment: optional comment
        :return: href of logical interface element
        """
        comment = comment if comment else ''
        json = {'name': name,
                'comment': comment}
    
        return ElementCreator(cls, json)

class MacAddress(Element):
    """
    Mac Address network element that can be used in L2 and IPS
    policy source and destination fields.
    
    Creating a MacAddress::
    
        MacAddress.create(name='mymac', mac_address='22:22:22:22:22:22')
    """
    typeof = 'mac_address'
    
    def __init__(self, name, **meta):
        super(MacAddress, self).__init__(name, **meta)
        pass
    
    @classmethod
    def create(cls, name, mac_address, comment=None):
        """    
        Create the Mac Address
        
        :param str name: name of mac address
        :param str mac_address: mac address notation
        :param str comment: optional comment
        :return: href of macaddress element
        """
        comment = comment if comment else ''
        json = {'name': name,
                'address': mac_address,
                'comment': comment}
    
        return ElementCreator(cls, json)

class ServerContactAddress(object):
    def __init__(self, data):
        self.data = data
        
    @classmethod
    def create(cls, address, location):
        """
        :param str address: ip address of contact address
        :param str location: name of location
        :return: ServerContactAddress
        """
        from smc.elements.helpers import location_helper
        location_ref = location_helper(location)
        data = {'addresses': [address],
                'location_ref': location_ref}
        return ServerContactAddress(data)
    
    @property
    def addresses(self):
        """                
        Return list of addresses associated with this contact
        address
        :return: list contact addresses
        """
        return self.data.get('addresses')
    
    @property
    def location_ref(self):
        return self.data.get('location_ref')
    
    @property
    def location(self):
        return Element.from_href(self.location_ref)
    
    def __repr__(self):
        return '{0}(addresses={1})'.format(self.__class__.__name__,
                                          ','.join(self.addresses))
           
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