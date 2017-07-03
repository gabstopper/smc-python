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
from smc.base.util import element_resolver


class Category(Element):
    """
    A Category is used by an element to group and categorize elements by
    some criteria. Once a category is created, it can be assigned to the
    element and used as a search filter when managing large
    numbers of elements. A category can be added to a category tag (or tags)
    to provide a higher level container/group for searching.
    ::

        >>> from smc.elements.other import Category
        >>> Category.create(name='footag', comment='test tag')
        Category(name=footag)
    """
    typeof = 'category_tag'

    def __init__(self, name, **meta):
        super(Category, self).__init__(name, **meta)

    @classmethod
    def create(cls, name, comment=None):
        """
        Add a category element

        :param name: name of location
        :return: instance with meta
        :rtype: Category
        """
        json = {'name': name,
                'comment': comment}

        return ElementCreator(cls, json)

    def search_elements(self):
        """
        Find all elements assigned to this category tag. You can also find
        category tags assigned directly to an element also::
        
            >>> host = Host('kali')
            >>> host.categories
            [Category(name=myelements), Category(name=foocategory)]

        :return: :py:class:`smc.base.model.Element`
        :rtype: list
        """
        return [Element.from_meta(**tag)
                for tag in
                self.data.get_json('search_elements_from_category_tag')]

    def add_element(self, element):
        """
        Element can be href or type :py:class:`smc.base.model.Element`
        ::

            >>> from smc.elements.other import Category
            >>> category = Category('foo')
            >>> category.add_element(Host('kali'))

        :param str,Element element: element to add to tag
        :raises: ModificationFailed: failed adding element
        :return: None
        """
        element = element_resolver(element)

        prepared_request(
            ModificationFailed,
            href=self.data.get_link('category_add_element'),
            json={'value': element}
        ).create()

    def remove_element(self, element):
        """
        Remove an element from this category tag. Find elements assigned
        by :func:`~search_elements`. Element can be str href or type
        :py:class:`smc.base.model.Element`.
        ::

            >>> from smc.elements.other import Category
            >>> from smc.elements.network import Host
            >>> category.remove_element(Host('kali'))

        :param str, Element element: element to remove
        :raises ModificationFailed: cannot remove element
        :return: None
        """
        element = element_resolver(element)

        prepared_request(
            ModificationFailed,
            href=self.data.get_link('category_remove_element'),
            json={'value': element}
        ).create()

    def add_category_tag(self, tags, append_lists=True):
        """
        Add this category to a category tag (group). This provides drop down
        filters in the SMC UI by category tag.
        
        :param list tags: category tag by name
        :param bool append_lists: append to existing tags or overwrite
            default: append)
        :type tags: list(str)
        :return: None
        """
        tags = element_resolver(tags)
        self.update(
            category_parent_ref=tags,
            append_lists=append_lists)

    def add_category(self, tags):
        pass
    
    @property
    def categories(self):
        """
        Categories can be children of category tags (groups). Show category
        tags that have this category as a member.
        
        :return: category tag/s for this category
        :rtype: list
        """
        return [Element.from_href(tag)
                for tag in self.data.get('category_parent_ref')]


class CategoryTag(Element):
    """
    A Category Tag is a grouping of categories within SMC. Category Tags
    are used as filters (typically in the SMC UI) to change the view based
    on the tag.
    """
    typeof = 'category_group_tag'
    
    def __init__(self, name, **meta):
        super(CategoryTag, self).__init__(name, **meta)
    
    @classmethod
    def create(cls, name, comment=None):
        """
        Create a CategoryTag. A category tag represents a group of categories
        or a group of category tags (nested groups). These are used to provide
        filtering views within the SMC and organize elements by user defined
        criteria.
        
        :param str name: name of category tag
        :param str comment: optional comment
        :raises CreateElementFailed: problem creating tag
        :return: instance with meta
        :rtype: CategoryTag
        """
        json = {'name': name,
                'comment': comment}
        return ElementCreator(cls, json)

    def remove_category(self, categories):
        """
        Remove a category from this Category Tag (group).
        
        :param list categories: categories to remove
        :type categories: list(str,Element)
        :return: None
        """
        categories = element_resolver(categories)
        diff = [category for category in self.data['category_child_ref']
                if category not in categories]
        self.update(category_child_ref=diff)

    @property
    def child_categories(self):
        """
        Return categories or category tag's that are children of this category
        tag.
        
        :return: child categories and/or category tag elements
        :rtype: list
        """
        return [Element.from_href(category)
                for category in self.data.get('category_child_ref')]
    
    @property
    def parent_categories(self):
        """
        If this category tag is a nested elment, return parent category tags
        that are linked.
        
        :return: linked parent category tags (groups)
        :rtype: list
        """
        return [Element.from_href(category)
                for category in self.data.get('category_parent_ref')]

class Location(Element):
    """
    Locations are used by elements to identify when they are behind a NAT
    connection. For example, if you have an engine that connects to the SMC
    across the internet using a public address, a location will be the tag
    applied to the Management Server (with contact address) and on the engine
    to identify how to connect. In this case, the location will map to a contact
    address using a public IP.

    .. note:: Locations require SMC API version >= 6.1
    """
    typeof = 'location'

    def __init__(self, name, **meta):
        super(Location, self).__init__(name, **meta)

    @classmethod
    def create(cls, name, comment=None):
        """
        Create a location element

        :param name: name of location
        :raises CreateElementFailed: failed creating element with reason
        :return: instance with meta
        :rtype: Location
        """
        json = {'name': name,
                'comment': comment}

        return ElementCreator(cls, json)

    @property
    def used_on(self):
        """
        Return all NAT'd elements using this location. 

        .. note::
            Available only in SMC version 6.2

        :return: elements used by this location
        :rtype: list
        """
        return [Element.from_meta(**element)
                for element in
                self.data.get_json('search_nated_elements_from_location')]


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

    @classmethod
    def create(cls, name, comment=None):
        """    
        Create the logical interface

        :param str name: name of logical interface
        :param str comment: optional comment
        :raises CreateElementFailed: failed creating element with reason
        :return: instance with meta
        :rtype: LogicalInterface
        """
        json = {'name': name,
                'comment': comment}

        return ElementCreator(cls, json)


class AdminDomain(Element):
    """
    Administrative domain element. Domains are used to provide object
    based segmentation within SMC. If domains are in use, you can
    log in directly to a domain to modify contents within that domain.
        
    Find all available domains::
    
        >>> list(AdminDomain.objects.all())
        [AdminDomain(name=Shared Domain)]
  
    .. note:: Admin Domains require and SMC license.
    """
    typeof = 'admin_domain'
    
    def __init__(self, name, **meta):
        super(AdminDomain, self).__init__(name, **meta)
        
    @classmethod
    def create(cls, name, comment=None):
        """
        Create a new Admin Domain element for SMC objects.
        
        Example::
    
            >>> AdminDomain.create(name='mydomain', comment='mycomment')
            >>> AdminDomain(name=mydomain) 
        
        :param str name: name of domain
        :param str comment: optional comment
        :raises CreateElementFailed: failed creating element with reason
        :return: instance with meta
        :rtype: AdminDomain
        """
        json = {'name': name,
                'comment': comment}
        
        return ElementCreator(cls, json)


class MacAddress(Element):
    """
    Mac Address network element that can be used in L2 and IPS
    policy source and destination fields.

    Creating a MacAddress::

        >>> MacAddress.create(name='mymac', mac_address='22:22:22:22:22:22')
        MacAddress(name=mymac)
    """
    typeof = 'mac_address'

    def __init__(self, name, **meta):
        super(MacAddress, self).__init__(name, **meta)

    @classmethod
    def create(cls, name, mac_address, comment=None):
        """    
        Create the Mac Address

        :param str name: name of mac address
        :param str mac_address: mac address notation
        :param str comment: optional comment
        :raises CreateElementFailed: failed creating element with reason
        :return: instance with meta
        :rtype: MacAddress
        """
        json = {'name': name,
                'address': mac_address,
                'comment': comment}

        return ElementCreator(cls, json)


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
