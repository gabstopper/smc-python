"""
AccessList module represents functionality that support dynamic routing
filters based on IPv4 or IPv6 access lists such as OSPF and BGP.
"""
import collections
from smc.base.model import Element, ElementCreator
from smc.api.exceptions import ElementNotFound


AccessListEntry = collections.namedtuple('AccessListEntry', 'subnet action comment')
"""
An AccessListEntry defines a simple entry for an IPAccessList used in dynamic
routing configurations.

:ivar str subnet: subnet associated with this entry
:ivar str action: action for the entry
:ivar str comment: optional comment for the entry
"""
AccessListEntry.__new__.__defaults__ = (None,) * len(AccessListEntry._fields)


class AccessList(object):
    """
    AccessList provides an iterable container that allows simple
    iteration over existing IPAccessList (v4 and v6), IPPrefixList
    (v4 and v6), CommunityAccessList and ExtendedCommunityAccessList
    entries.
    When using the `create` constructor, validate the keyword arguments
    based on the specific access list requirements.
    
    :return: namedtuple based on access list type
    """
    @classmethod
    def create(cls, name, entries=None, comment=None, **kw):
        """
        Create an Access List Entry.

        Depending on the access list type you are creating (IPAccessList,
        IPv6AccessList, IPPrefixList, IPv6PrefixList, CommunityAccessList,
        ExtendedCommunityAccessList), entries will define a dict of the
        valid attributes for that ACL type. Each class has a defined list
        of attributes documented in it's class.
        
        You can optionally leave entries blank and use the :meth:`~add_entry`
        method after creating the list container.
        
        :param str name: name of IP Access List
        :param list entries: access control entry
        :param kw: optional keywords that might be necessary to create the ACL
            (see specific Access Control List documentation for options)
        :raises CreateElementFailed: cannot create element
        :return: The access list based on type
        """
        access_list_entry = []
        if entries:
            for entry in entries:
                access_list_entry.append(
                    {'{}_entry'.format(cls.typeof): entry})

        json = {'name': name,
                'entries': access_list_entry,
                'comment': comment}
        json.update(kw)
        
        return ElementCreator(cls, json)

    def __len__(self):
        return len(self.data.get('entries', []))
    
    def __iter__(self):
        for entry in self.data.get('entries', []):
            value = entry.get('{}_entry'.format(self.typeof))
            data = {}
            for field in self._view._fields:
                data.update({field: value.get(field, None)})
            yield self._view(**data)

    def add_entry(self, **kw):
        """
        Add an entry to an AccessList. Use the supported arguments
        for the inheriting class for keyword arguments.

        :raises UpdateElementFailed: failure to modify with reason
        :return: None
        """
        self.data.setdefault('entries', []).append(
            {'{}_entry'.format(self.typeof): kw})

    def remove_entry(self, **field_value):
        """
        Remove an AccessList entry by field specified. Use the supported
        arguments for the inheriting class for keyword arguments.

        :raises UpdateElementFailed: failed to modify with reason
        :return: None
        """
        field, value = next(iter(field_value.items()))
        self.data['entries'][:] = [entry
            for entry in self.data.get('entries')
            if entry.get('{}_entry'.format(self.typeof))
            .get(field) != str(value)]
    
    @classmethod
    def update_or_create(cls, with_status=False, overwrite_existing=False, **kw):
        """
        Update or create the Access List. This method will not attempt to 
        evaluate whether the access list has differences, instead it will
        update with the contents of the payload entirely. If the intent is
        to only add or remove a single entry, use `~add_entry` and `~remove_entry`
        methods.
        
        :param bool with_status: return with 3-tuple of (Element, modified, created)
            holding status
        :param bool overwrite_existing: if the access list exists but instead of an
            incremental update you want to overwrite with the newly defined entries,
            set this to True (default: False)
        :return: Element or 3-tuple with element and status
        """
        created = False
        modified = False
        try:
            element = cls.get(kw.get('name'))
        except ElementNotFound:
            element = cls.create(**kw)
            created = True
        
        if not created:
            if overwrite_existing:
                element.data['entries'] = [
                    {'{}_entry'.format(element.typeof): entry}
                    for entry in kw.get('entries')]
                modified = True
            else:
                if 'comment' in kw and kw['comment'] != element.comment:
                    element.comment = kw['comment']
                    modified = True
                for entry in kw.get('entries', []):
                    if cls._view(**entry) not in element:
                        element.add_entry(**entry)
                        modified = True

        if modified:
            element.update()
            
        if with_status:
            return element, modified, created
        return element
        
        
        
class IPAccessList(AccessList, Element):
    """
    IPAccessList is used by dynamic routing protocols to allow filtering of
    routes. 
    Protocols like OSPF and BGP allow inbound and outbound filters using these.
    
    Create an IPAccessList. When providing values for `entries` to the create
    constructor, use valid attributes as defined in :class:`~AccessListEntry`::
    
        >>> ip = IPAccessList.create(name='mylist', entries=[
            {'subnet': '1.1.1.0/24', 'action': 'permit'}, {'subnet': '2.2.2.0/24', 'action': 'deny'}])
        ...
        >>> ip.add_entry(subnet='3.3.3.0/24', action='permit')
        >>> ip.remove_entry(subnet='1.1.1.0/24')
        >>> ip.update()
        'https://172.18.1.151:8082/6.4/elements/ip_access_list/13'
        >>> for entry in ip:
        ...   entry
        ... 
        AccessListEntry(subnet=u'2.2.2.0/24', action=u'deny', comment=None)
        AccessListEntry(subnet=u'3.3.3.0/24', action=u'permit', comment=None)
        ...
        >>> ip.delete()
        
    This is an iterable container yielding :class:`~AccessListEntry`
    
    .. seealso:: :class:`~AccessListEntry` for valid `create` and add/remove parameters
    """
    typeof = 'ip_access_list'
    _view = AccessListEntry


class IPv6AccessList(AccessList, Element):
    """
    IPv6AccessList is used by dynamic routing protocols to allow filtering of
    routes. Protocols like OSPF and BGP allow inbound and outbound filters
    using these.
    ::
    
        >>> acl6 = IPv6AccessList.create(name='aclv6', entries=[
        ...           {'subnet': '2001:db8:1::1/128', 'action': 'permit'}])
        >>> acl6
        IPv6AccessList(name=aclv6)
        >>> for entry in acl6:
        ...   entry
        ... 
        AccessListEntry(subnet=u'2001:db8:1::1/128', action=u'permit', comment=None)

    This is an iterable container yielding :class:`~AccessListEntry`
    
    .. seealso:: :class:`~IPAccessList` for using this element.
    """
    typeof = 'ipv6_access_list'
    _view = AccessListEntry
    
