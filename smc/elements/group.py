"""
Groups that are used for element types, such as TCPServiceGroup,
Group (generic), etc. All group types inherit from GroupMixin which
allow for modifications of existing groups and their members.
"""
from smc.base.model import Element, ElementCreator
from smc.base.util import element_resolver


class GroupMixin(object):
    """
    Methods associated with handling modification of Group 
    objects for existing elements
    """

    def update_members(self, members, append_lists=False):
        """
        Update group members with member list. Set append=True
        to append to existing members, or append=False to overwrite.

        :param list members: new members for group by href or Element
        :type members: list[str, Element]
        :param bool append: whether to append
        :return: None
        """
        self.update(
            element=element_resolver(members),
            append_lists=append_lists)

    def obtain_members(self):
        """
        Obtain all group members from this group

        :return: group members as elements
        :rtype: list(Element)
        """
        return [Element.from_href(member)
                for member in self.data.get('element')]

    def empty_members(self):
        """
        Empty members from group

        :return: None
        """
        self.update(element=[])


class Group(GroupMixin, Element):
    """ 
    Class representing a Group object used in access rules
    Groups can hold other network element types as well as
    other groups.

    Create a group element::

        Group.create('mygroup') #no members

    Group with members::

        Group.create('mygroup', [Host('kali'), Network('mynetwork')])
        
    Available attributes:
    
    :ivar list element: list of elements by href. Call `~obtain_members` to
        retrieved the resolved list of elements.
    """
    typeof = 'group'

    def __init__(self, name, **meta):
        super(Group, self).__init__(name, **meta)
        pass

    @classmethod
    def create(cls, name, members=None, comment=None):
        """
        Create the group

        :param str name: Name of element
        :param list members: group members by element names
        :type members: str,Element 
        :param str comment: optional comment
        :raises CreateElementFailed: element creation failed with reason
        :return: instance with meta
        :rtype: Group
        """
        elements = [] if members is None else element_resolver(members)
        json = {'name': name,
                'element': elements,
                'comment': comment}

        return ElementCreator(cls, json)


class ServiceGroup(GroupMixin, Element):
    """ 
    Represents a service group in SMC. Used for grouping
    objects by service. Services can be "mixed" TCP/UDP/ICMP/
    IPService, Protocol or other Service Groups.
    Element is an href to the location of the resource.

    Create a TCP and UDP Service and add to ServiceGroup::

        tcp1 = TCPService.create('api-tcp1', 5000)
        udp1 = UDPService.create('api-udp1', 5001)
        ServiceGroup.create('servicegroup', element=[tcp1, udp1])
    
    Available attributes:
    
    :ivar list element: list of elements by href. Call `~obtain_members` to
        retrieved the resolved list of elements.    
    """
    typeof = 'service_group'

    def __init__(self, name, **meta):
        super(ServiceGroup, self).__init__(name, **meta)
        pass

    @classmethod
    def create(cls, name, members=None, comment=None):
        """
        Create the TCP/UDP Service group element

        :param str name: name of service group
        :param list members: elements to add by href or Element
        :type members: list(str,Element)
        :raises CreateElementFailed: element creation failed with reason
        :return: instance with meta
        :rtype: ServiceGroup
        """
        elements = [] if members is None else element_resolver(members)
        json = {'name': name,
                'element': elements,
                'comment': comment}

        return ElementCreator(cls, json)


class TCPServiceGroup(GroupMixin, Element):
    """ 
    Represents a TCP Service group

    Create TCP Services and add to TCPServiceGroup::

        tcp1 = TCPService.create('api-tcp1', 5000)
        tcp2 = TCPService.create('api-tcp2', 5001)
        ServiceGroup.create('servicegroup', element=[tcp1, tcp2])
        
    Available attributes:
    
    :ivar list element: list of elements by href. Call `~obtain_members` to
        retrieved the resolved list of elements.
    """
    typeof = 'tcp_service_group'

    def __init__(self, name, **meta):
        super(TCPServiceGroup, self).__init__(name, **meta)
        pass

    @classmethod
    def create(cls, name, members=None, comment=None):
        """
        Create the TCP Service group

        :param str name: name of tcp service group
        :param list element: tcp services by element or href
        :type element: list(str,Element)
        :raises CreateElementFailed: element creation failed with reason
        :return: instance with meta
        :rtype: TCPServiceGroup
        """
        element = [] if members is None else element_resolver(members)
        json = {'name': name,
                'element': element,
                'comment': comment}

        return ElementCreator(cls, json)


class UDPServiceGroup(GroupMixin, Element):
    """ 
    UDP Service Group 
    Used for storing UDP Services or UDP Service Groups.

    Create two UDP Services and add to UDP service group::

        udp1 = UDPService.create('udp-svc1', 5000)
        udp2 = UDPService.create('udp-svc2', 5001)
        UDPServiceGroup.create('udpsvcgroup', element=[udp1, udp2])
        
    Available attributes:
    
    :ivar list element: list of elements by href. Call `~obtain_members` to
        retrieved the resolved list of elements.
    """
    typeof = 'udp_service_group'

    def __init__(self, name, **meta):
        super(UDPServiceGroup, self).__init__(name, **meta)
        pass

    @classmethod
    def create(cls, name, members=None, comment=None):
        """
        Create the UDP Service group

        :param str name: name of service group
        :param list element: UDP services or service group by reference
        :type members: list(str,Element)
        :raises CreateElementFailed: element creation failed with reason
        :return: instance with meta
        :rtype: UDPServiceGroup
        """
        element = [] if members is None else element_resolver(members)
        json = {'name': name,
                'element': element,
                'comment': comment}

        return ElementCreator(cls, json)


class IPServiceGroup(GroupMixin, Element):
    """ 
    IP Service Group
    Used for storing IP Services or IP Service Groups

    Available attributes:
    
    :ivar list element: list of elements by href. Call `~obtain_members` to
        retrieved the resolved list of elements.
    """
    typeof = 'ip_service_group'

    def __init__(self, name, **meta):
        super(IPServiceGroup, self).__init__(name, **meta)
        pass

    @classmethod
    def create(cls, name, members=None, comment=None):
        """
        Create the IP Service group element

        :param str name: name of service group
        :param list element: IP services or IP service groups by href
        :type members: list(str,Element)
        :raises CreateElementFailed: element creation failed with reason
        :return: instance with meta
        :rtype: IPServiceGroup
        """
        elements = [] if members is None else element_resolver(members)
        json = {'name': name,
                'element': elements,
                'comment': comment}

        return ElementCreator(cls, json)
        
