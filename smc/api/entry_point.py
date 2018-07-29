"""
Module storing entry points for a session
"""

import collections
from smc.api.exceptions import UnsupportedEntryPoint


EntryPoint = collections.namedtuple('EntryPoint', 'href rel method')
EntryPoint.__new__.__defaults__ = (None,) * len(EntryPoint._fields) # Version 5.10 compat


class Resource(object):
    def __init__(self, entry_point_list):
        self._entry_points = entry_point_list
        
    def __iter__(self):
        for entry in self._entry_points:
            yield EntryPoint(**entry)
    
    def __len__(self):
        return len(self._entry_points)
    
    def clear(self):
        self._entry_points[:] = []
    
    def all(self):
        """
        Return all resources
        
        :rtype: EntryPoint
        """
        for resource in self:
            yield resource
    
    def all_by_name(self):
        """     
        Return all resources by rel name
        
        :rtype: str
        """
        for resource in self:
            yield resource.rel
    
    def get(self, rel):
        """
        Get the resource by rel name
        
        :param str rel_name: name of rel
        :raises UnsupportedEntryPoint: entry point not found in this version
            of the API
        """
        for link in self._entry_points:
            if link.get('rel') == rel:
                return link.get('href')
        raise UnsupportedEntryPoint(
            "The specified entry point '{}' was not found in this "
            "version of the SMC API. Check the element documentation "
            "to determine the correct version and specify the api_version "
            "parameter during session.login() if necessary.".format(rel))
