"""
Module storing entry points for a session
"""

import collections
from smc.base.structs import SerializedIterable
from smc.api.exceptions import UnsupportedEntryPoint


class _EntryPoint(SerializedIterable):
    def __init__(self, entry_points):
        super(_EntryPoint, self).__init__(entry_points, EntryPoint)
    
    def get(self, rel):
        for link in iter(self):
            if link.rel == rel:
                return link.href
        raise UnsupportedEntryPoint(
            "The specified entry point '{}' was not found in this "
            "version of the SMC API. Check the element documentation "
            "to determine the correct version and specify the api_version "
            "parameter during session.login() if necessary.".format(rel))


EntryPoint = collections.namedtuple('EntryPoint', 'href rel')


class Resource(object):
    entry_point = _EntryPoint([])
    
    def __len__(self):
        return len(self.entry_point)
    
    @classmethod
    def add(cls, entry_points):
        cls.entry_point = _EntryPoint(entry_points)
    
    @classmethod
    def clear(cls):
        cls.entry_point = _EntryPoint([])
    
    def get(self, rel_name):
        """
        Get the resource by rel name
        
        :param str rel_name: name of rel
        :raises UnsupportedEntryPoint: entry point not found in this version
            of the API
        """
        return self.entry_point.get(rel_name)
    
    def all(self):
        """
        Return all resources
        
        :rtype: EntryPoint
        """
        for resource in self.entry_point:
            yield resource
    
    def all_by_name(self):
        """     
        Return all resources by rel name
        
        :rtype: str
        """
        for resource in self.entry_point:
            yield resource.rel
    
