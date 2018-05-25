import collections
from smc.base.model import Element
from smc.routing.access_list import AccessList


ASPathListEntry = collections.namedtuple('ASPathListEntry',
        'expression action comment')
"""
The ASPathAccessList is an iterable container and will return
instances of :class:`~ASPathListEntry`.

:ivar str expression: string expression identifying the AS path
:ivar str action: 'permit' or 'deny'
:ivar str comment: optional comment
"""
ASPathListEntry.__new__.__defaults__ = (None,) * len(ASPathListEntry._fields)


class ASPathAccessList(AccessList, Element):
    """
    An AS path is the autonomous systems that routing information passed
    through to get to a specified router. It indicates the origin of this
    route. The AS path is used to prevent routing loops in BGP.
    
    ASPathAccessLists can be used as a MatchCondition in a RouteMap::
    
        >>> aspath = ASPathAccessList.create(name='aspath', entries=[
        ...   {'expression': '123-456', 'action': 'permit'},
        ...   {'expression': '1234-567', 'action': 'deny'}])
        >>> aspath
        ASPathAccessList(name=aspath)
        >>> aspath.add_entry(expression='897', action='permit')
        >>> aspath.update()
        'https://172.18.1.151:8082/6.4/elements/as_path_access_list/28'
        ...
        >>> aspath.remove_entry(expression='123-456')
        >>> aspath.update()
        'https://172.18.1.151:8082/6.4/elements/as_path_access_list/28'
        >>> for entry in aspath:
        ...   entry
        ... 
        ASPathListEntry(expression=u'1234-567', action=u'deny', comment=None)
        ASPathListEntry(expression=u'897', action=u'permit', comment=None)

    This is an iterable container yielding :class:`ASPathListEntry`.
    
    .. seealso:: :class:`~ASPathListEntry` for valid `create` and add/remove parameters
    """
    typeof = 'as_path_access_list'
    _view = ASPathListEntry
        

CommunityListEntry = collections.namedtuple('CommunityListEntry',
    'community action comment')
"""
The CommunityAccessList represents the entries for the community
access lists.

:ivar str community: community id
:ivar str action: 'permit' or 'deny'
:ivar str comment: optional comment
"""
CommunityListEntry.__new__.__defaults__ = (None,) * len(CommunityListEntry._fields)


class CommunityAccessList(AccessList, Element):
    """
    A CommunityAccessList is used to provide specific rules for BGP
    configurations providing and permit/deny capability based on
    the community defined. 
    CommunityAccessLists can be used in a RouteMap match condition
    to refine the policy for a specific announced network.
    
    When creating a new community ACL, `entries` is expecting a list
    of dict items using the valid field and values of this class.
    For example::
    
        >>> from smc.routing.community_list import CommunityAccessList
        >>> comm = CommunityAccessList.create(name='commacl',
                entries=[{'community': 123, 'action': 'permit'},{'community': 456, 'action': 'deny'}],
                type='standard')
        >>> comm
        CommunityAccessList(name=commacl)

    You can optionally also create an empty access list and use :meth:`add_entry`
    to insert entries after::
        
        >>> comm.add_entry(community=789, action='permit')
        >>> comm.update()
    
    Iterating the access list will return :class:`~CommunityListEntry`::
    
        >>> for entries in comm:
        ...   entries
        ... 
        CommunityListEntry(community=u'789', action=u'permit', comment=None)
        CommunityListEntry(community=u'456', action=u'deny', comment=None)
        CommunityListEntry(community=u'123', action=u'permit', comment=None)    
    
    The `type` parameter for the `create` constructor can have values `standard` or
    `expanded`. If using `expanded`, the access list can then use a regex for matching
    the community string.
    
    This is an iterable container yielding :class:`CommunityListEntry`.
    
    .. seealso:: :class:`~CommunityListEntry` for valid `create` and add/remove parameters
    
    :ivar str type: 'standard' or 'expanded' (specify as kw when in `create` constructor when
        creating the top level access list.
    """
    typeof = 'community_access_list'
    _view = CommunityListEntry


ExtCommunityListEntry = collections.namedtuple('ExtCommunityListEntry',
    'community action type')
"""
The ExtCommunityListEntry represents the entries for the extended community
access lists.

:ivar str community: community id
:ivar str action: 'permit' or 'deny'
:ivar str type: 'rt' (Route Target) or 'soo' (Site of Origin) (required)
"""
ExtCommunityListEntry.__new__.__defaults__ = (None,) * len(ExtCommunityListEntry._fields)

    
class ExtendedCommunityAccessList(AccessList, Element):
    """
    Extended community access lists with the ability to specify
    route target or start of origin for an entry.
    
    ExtendedCommunityAccessLists can be used in a RouteMap match
    condition to refine the policy for a specific announced network::
    
        >>> comm = ExtendedCommunityAccessList.create(name='comm', entries=[
            ...   {'community': 123, 'action': 'permit', 'type': 'rt'},
            ...   {'community': 456, 'action': 'deny', 'type': 'soo'}],
            ...   type='standard')
            >>> comm
            ExtendedCommunityAccessList(name=comm)
            >>> comm.add_entry(community=789, action='permit', type='rt')
            >>> comm.update()
            ...
            >>> comm.remove_entry(community=123)
            >>> comm.update()
            'https://172.18.1.151:8082/6.4/elements/extended_community_access_list/25'
            >>> for entry in comm:
            ...   entry
            ... 
            ExtCommunityListEntry(community=u'456', action=u'deny', comment=None, type=u'soo')
            ExtCommunityListEntry(community=u'789', action=u'permit', comment=None, type=u'rt')

    This is an iterable container yielding :class:`ExtCommunityListEntry`.
    
    .. seealso:: :class:`~ExtCommunityListEntry` for valid `create` and add/remove parameters
    
    :ivar str type: 'standard' or 'expanded' (specify as kw when in `create` constructor when
        creating the top level access list.
    """
    typeof = 'extended_community_access_list'
    _view = ExtCommunityListEntry

    