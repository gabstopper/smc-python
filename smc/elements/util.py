'''
Created on Sep 16, 2016

@author: davidlepage
'''

"""
Temp lazy loader definition to check for loaded json
in classes that require it be loaded before specific 
operations are run
"""
def lazy_loader(f):
    def deco(self, *args, **kwargs):
        #Need the full json for element
        if not self.data.get('link'):
            self.load()
        return f(self, *args, **kwargs)
    return deco

"""
Utility method to find the reference link based on 
the link name and provided the list of link references
provided by the SMC API

:param link_name: name of link
:param list linklist: list of references
:return fully qualified href
"""
def find_link_by_name(link_name, linklist):
    """ 
    Find the href based on SMC API return rel
    """
    for entry in linklist:
        if entry.get('rel') == link_name:
            return entry.get('href')
        
            