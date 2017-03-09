"""
AccessList module represents functionality that support dynamic routing
filters based on IPv4 or IPv6 access lists such as OSPF and BGP.
"""
from smc.base.model import Element, ElementCreator, prepared_request
import smc.actions.search as search
from smc.api.exceptions import ModificationFailed

class AccessList(object):
    """
    AccessListMixin provides methods that are common to all access list
    operations.
    """
    @classmethod
    def create(cls, name, entries=None):
        """
        Create an IPv4 or IPv6 Access List

        Entries should be a tuple consisting of (subnet, action).
        Subnet can be a /32 host entry as well as network address.
        Action values are 'permit' or 'deny'.

        For example::

            IPAccessList.create(name='foo',
                                entries=[('172.18.1.0/24', 'permit'),
                                         ('192.16.3.0/24', 'deny')])

            IPv6AccessList.create(name='foo',
                                  entries=[('2001:db8:1::1/128', 'permit')])

        :param str name: name of IP Access List
        :param list entries: access control entry
        :return: str href: href location of new element
        :raises: :py:class:`smc.api.exceptions.CreateElementFailed`
        """
        access_list_entry = []
        if entries:
            for entry in entries:
                subnet, action = entry
                access_list_entry.append(
                    {'{}_entry'.format(cls.typeof): {
                        'action': action,
                        'subnet': subnet}})           
        cls.json = {'name': name,
                    'entries': access_list_entry}

        return ElementCreator(cls)

    def add_entry(self, subnet, action):
        """
        Add an entry to an AccessList

        :param str subnet: network address in cidr format
        :param str action: permit|deny
        :raises: :py:class:`smc.api.exceptions.ElementNotFound`
        :raises: :py:class:`smc.api.exceptions.ModificationFailed`
        :return: None
        """
        json = {'{}_entry'.format(self.typeof): {
                    'action': action,
                    'subnet': subnet}}

        acl = search.element_by_href_as_smcresult(self.href)
        acl.json.get('entries').append(json)
        
        prepared_request(ModificationFailed,
                         href=self.href, json=acl.json,
                         etag=acl.etag).update()

    def remove_entry(self, subnet):
        """
        Remove an AccessList entry by subnet

        :param str subnet: subnet match to remove
        :raises: :py:class:`smc.api.exceptions.ModificationFailed`
        :return: None
        """
        acl = search.element_by_href_as_smcresult(self.href)
        acl.json['entries'][:] = [entry
                                  for entry in acl.json.get('entries')
                                  if entry.get('{}_entry'.format(self.typeof))\
                                  .get('subnet') != subnet]

        prepared_request(ModificationFailed,
                         href=self.href, json=acl.json,
                         etag=acl.etag).update()

    def view(self):
        """
        Return a view of the IP Access List in tuple format:
        (subnet, action)

        :return: list tuple
        """
        acl = search.element_by_href_as_smcresult(self.href)
        acls=[]
        for entry in acl.json.get('entries'):
            e = entry.get('{}_entry'.format(self.typeof))
            acls.append((e.get('subnet'), e.get('action')))
        return acls

class IPAccessList(AccessList, Element):
    """
    IPAccessList is used by dynamic routing protocols to allow filtering of
    routes.
    Protocols like OSPF and BGP allow inbound and outbound filters using these.
    """
    typeof = 'ip_access_list'
  
    def __init__(self, name, meta=None):
        super(IPAccessList, self).__init__(name, meta)
        pass
       
class IPv6AccessList(AccessList, Element):
    """
    IPv6AccessList is used by dynamic routing protocols to allow filtering of
    routes.
    Protocols like OSPF and BGP allow inbound and outbound filters using these.
    """
    typeof = 'ipv6_access_list'
  
    def __init__(self, name, meta=None):
        super(IPv6AccessList, self).__init__(name, meta)
        pass
    