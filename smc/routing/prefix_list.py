"""
IP Prefix module represnts prefix lists that can be used to filter networks for
OSPF routing.
"""
import smc.actions.search as search
from smc.base.model import ElementCreator, Element, prepared_request

class PrefixList(Element):
    """
    PrefixList provides common methods utilized by all
    prefix list operations
    """
    @classmethod
    def create(cls, name, entries=None):
        """
        Create an IPv4 or IPv6 Prefix List

        Entries should be a 4-tuple consisting of
        (subnet, min_prefix_len, max_prefix_len, action).

        Action values are 'permit' or 'deny'.

        For example::

            IPPrefixList.create(
                            name='poo',
                            entries=[('10.0.0.0/8', 16, 32, 'deny'),
                                     ('192.16.1.0/24', 25, 32, 'permit')])

            IPv6PrefixList.create(
                            name='v6prefix',
                            entries=[('ab00::/64', 65, 128, 'deny')])
        """
        prefix_list_entry = []
        if entries:
            for entry in entries:
                subnet, min_len, max_len, action = entry
                prefix_list_entry.append(
                    {'{}_entry'.format(cls.typeof): {
                        'action': action,
                        'max_prefix_length': max_len,
                        'min_prefix_length': min_len,
                        'subnet': subnet}})
        cls.json = {'name': name,
                    'entries': prefix_list_entry}

        return ElementCreator(cls)

    def add_entry(self, subnet, min_prefix_length,
                  max_prefix_length, action):
        """
        Add an entry to an PrefixList

        :param str subnet: network address in cidr format
        :param int min_prefix_length: minimum mask bits
        :param int max_prefix_length: maximum mask bits
        :param str action: permit|deny
        :raises: :py:class:`smc.api.exceptions.ElementNotFound`
        :return: :py:class:`smc.api.web.SMCResult`
        """
        json = {'{}_entry'.format(self.typeof): {
                    'action': action,
                    'min_prefix_length': min_prefix_length,
                    'max_prefix_length': max_prefix_length,
                    'subnet': subnet}}

        acl = search.element_by_href_as_smcresult(self.href)
        acl.json.get('entries').append(json)
        
        return prepared_request(href=self.href, json=acl.json,
                            etag=acl.etag).update()

    def remove_entry(self, subnet):
        """
        Remove an PrefixList entry by subnet

        :param str subnet: subnet match to remove
        """
        acl = search.element_by_href_as_smcresult(self.href)
        acl.json['entries'][:] = [entry
                                  for entry in acl.json.get('entries')
                                  if entry.get('{}_entry'.format(self.typeof))\
                                  .get('subnet') != subnet]
        
        return prepared_request(href=self.href, json=acl.json,
                            etag=acl.etag).update()

    def view(self):
        """
        Return a view of the IP Access List in tuple format:
        (subnet, min_prefix_length, max_prefix_length, action)

        :return: list tuple
        """
        acl = search.element_by_href_as_smcresult(self.href)
        acls=[]
        for entry in acl.json.get('entries'):
            e = entry.get('{}_entry'.format(self.typeof))
            acls.append((e.get('subnet'), e.get('min_prefix_length'),
                         e.get('max_prefix_length'), e.get('action')))
        return acls

class IPPrefixList(PrefixList):
    """
    An IP prefix list specifies a list of networks. When you apply an IP
    prefix list to a neighbor, the device sends or receives only a route
    whose destination is in the IP prefix list.
    This represents IPv4 prefix lists
    """
    typeof = 'ip_prefix_list'
    
    def __init__(self, name, meta=None):
        self._name = name
        self.meta = meta

class IPv6PrefixList(PrefixList):
    """
    An IP prefix list specifies a list of networks. When you apply an IP
    prefix list to a neighbor, the device sends or receives only a route
    whose destination is in the IP prefix list.
    This represents IPv6 prefix lists
    """
    typeof = 'ipv6_prefix_list'
  
    def __init__(self, name, meta=None):
        self._name = name
        self.meta = meta
