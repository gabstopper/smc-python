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

    def update_members(self, members, append=False):
        """
        Update group members with member list. Set append=True
        to append to existing members, or append=False to overwrite.

        :param list members: new members for group by href or Element
        :type members: list[str, Element]
        :param bool append: whether to append
        :return: None
        """
        if not append:
            self.data['element'] = []

        for member in element_resolver(members):
            self.data['element'].append(member)

        self.update()

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
        self.modify_attribute(element=[])


class Group(GroupMixin, Element):
    """ 
    Class representing a Group object used in access rules
    Groups can hold other network element types as well as
    other groups.

    Create a group element::

        Group.create('mygroup') #no members

    Group with members::

        Group.create('mygroup', ['member1-href','member2-href'])
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
        :param str comment: optional comment
        :raises CreateElementFailed: element creation failed with reason
        :return: href of new element
        :rtype: str
        """
        comment = None if comment is None else comment
        members = [] if members is None else members
        json = {'name': name,
                'element': members,
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
        ServiceGroup.create('servicegroup', element=[tcp1.href, udp1.href])
    """
    typeof = 'service_group'

    def __init__(self, name, **meta):
        super(ServiceGroup, self).__init__(name, **meta)
        pass

    @classmethod
    def create(cls, name, element=None, comment=None):
        """
        Create the TCP/UDP Service group element

        :param str name: name of service group
        :param list element: list of elements to add to service group
        :raises CreateElementFailed: element creation failed with reason
        :return: href of new element
        :rtype: str
        """
        elements = [] if element is None else element
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
        ServiceGroup.create('servicegroup', element=[tcp1.href, tcp2.href])
    """
    typeof = 'tcp_service_group'

    def __init__(self, name, **meta):
        super(TCPServiceGroup, self).__init__(name, **meta)
        pass

    @classmethod
    def create(cls, name, element=None, comment=None):
        """
        Create the TCP Service group

        :param str name: name of tcp service group
        :param list element: tcp services by href
        :raises CreateElementFailed: element creation failed with reason
        :return: href of new element
        :rtype: str
        """
        elements = [] if element is None else element
        json = {'name': name,
                'element': elements,
                'comment': comment}

        return ElementCreator(cls, json)


class UDPServiceGroup(GroupMixin, Element):
    """ 
    UDP Service Group 
    Used for storing UDP Services or UDP Service Groups.

    Create two UDP Services and add to UDP service group::

        udp1 = UDPService.create('udp-svc1', 5000)
        udp2 = UDPService.create('udp-svc2', 5001)
        UDPServiceGroup.create('udpsvcgroup', element=[udp1.href, udp2.href])
    """
    typeof = 'udp_service_group'

    def __init__(self, name, **meta):
        super(UDPServiceGroup, self).__init__(name, **meta)
        pass

    @classmethod
    def create(cls, name, element=None, comment=None):
        """
        Create the UDP Service group

        :param str name: name of service group
        :param list element: UDP services or service group by reference
        :raises CreateElementFailed: element creation failed with reason
        :return: href of new element
        :rtype: str
        """
        elements = [] if element is None else element
        json = {'name': name,
                'element': elements,
                'comment': comment}

        return ElementCreator(cls, json)


class IPServiceGroup(GroupMixin, Element):
    """ 
    IP Service Group
    Used for storing IP Services or IP Service Groups

    """
    typeof = 'ip_service_group'

    def __init__(self, name, **meta):
        super(IPServiceGroup, self).__init__(name, **meta)
        pass

    @classmethod
    def create(cls, name, element=None, comment=None):
        """
        Create the IP Service group element

        :param str name: name of service group
        :param list element: IP services or IP service groups by ref
        :raises CreateElementFailed: element creation failed with reason
        :return: href of new element
        :rtype: str
        """
        elements = [] if element is None else element
        json = {'name': name,
                'element': elements,
                'comment': comment}

        return ElementCreator(cls, json)


class SecurityGroup(Element):
    pass
