"""
IP Prefix module represents prefix lists that can be used to filter networks for
OSPF routing.
"""
import collections
from smc.base.model import Element
from smc.routing.access_list import AccessList


PrefixListEntry = collections.namedtuple('PrefixListEntry',
    'subnet action min_prefix_length max_prefix_length comment')
"""
A PrefixListEntry defines a simple entry for an PrefixList used in dynamic
routing configurations.

:ivar str subnet: subnet associated with this entry
:ivar str action: action for the entry
:ivar int min_prefix_length: minimum mask bits
:ivar int max_prefix_length: maximum mask bits
:ivar str comment: optional comment for the entry
"""
PrefixListEntry.__new__.__defaults__ = (None,) * len(PrefixListEntry._fields)


class IPPrefixList(AccessList, Element):
    """
    An IP prefix list specifies a list of networks. When you apply an IP
    prefix list to a neighbor, the device sends or receives only a route
    whose destination is in the IP prefix list.
    
    Creating and modifying an IPAccessList is similar to other access list
    methods::
    
        >>> prefix = IPPrefixList.create(name='mylist', entries=[
        ...   {'subnet': '10.0.0.0/8', 'min_prefix_length': 16, 'max_prefix_length': 32, 'action': 'deny'},
        ...   {'subnet': '192.16.1.0/24', 'min_prefix_length': 25, 'max_prefix_length': 32, 'action': 'permit'}])
        >>> prefix
        IPPrefixList(name=mylist)
        ...
        >>> prefix.add_entry(subnet='192.17.1.0/24', min_prefix_length=25, max_prefix_length=32, action='deny')
        >>> prefix.update()
        'https://172.18.1.151:8082/6.4/elements/ip_prefix_list/16'
        >>> prefix.remove_entry(subnet='192.16.1.0/24')
        >>> prefix.update()
        'https://172.18.1.151:8082/6.4/elements/ip_prefix_list/16'
        >>> for entry in prefix:
        ...   entry
        ... 
        PrefixListEntry(subnet=u'10.0.0.0/8', action=u'deny', min_prefix_length=16, max_prefix_length=32, comment=None)
        PrefixListEntry(subnet=u'192.17.1.0/24', action=u'deny', min_prefix_length=25, max_prefix_length=32, comment=None)
        
    You can also create a PrefixList without using the min_prefix_length and max_prefix_length fields::
    
        >>> prefix = IPPrefixList.create(name='mylist', entries=[
        ...   {'subnet': '10.0.0.0/8', 'action': 'deny'},
        ...   {'subnet': '192.16.1.0/24', 'action': 'permit'}])

    This is an iterable container yielding :class:`~PrefixListEntry`
    
    .. seealso:: :class:`~PrefixListEntry` for valid `create` and add/remove parameters
    
    """
    typeof = 'ip_prefix_list'
    _view = PrefixListEntry


class IPv6PrefixList(AccessList, Element):
    """
    An IP prefix list specifies a list of networks. When you apply an IP
    prefix list to a neighbor, the device sends or receives only a route
    whose destination is in the IP prefix list.
    ::
    
        >>> prefix6 = IPv6PrefixList.create(name='myipv6', entries=[
        ...   {'subnet': 'ab00::/64', 'min_prefix_length': 65, 'max_prefix_length': 128, 'action': 'deny'}])
        >>> prefix6
        IPv6PrefixList(name=myipv6)
        >>> for entry in prefix6:
        ...   entry
        ... 
        PrefixListEntry(subnet=u'ab00::/64', action=u'deny', min_prefix_length=65, max_prefix_length=128, comment=None)
    
    You can also create a PrefixList without using the min_prefix_length and max_prefix_length fields::
    
        >>> prefix = IPPrefixList.create(name='mylist', entries=[
        ...   {'subnet': 'ab00::/64', 'action': 'deny'}
        
    This is an iterable container yielding :class:`~PrefixListEntry`
    
    .. seealso:: :class:`~IPPrefixList` for other common operations

    """
    typeof = 'ipv6_prefix_list'
    _view = PrefixListEntry
