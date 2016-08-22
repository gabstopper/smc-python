"""
Helpers functions
"""

def find_link_by_name(link_name, linklist):
    """ 
    Find the href based on SMC API return rel
    """
    for entry in linklist:
        if entry.get('rel') == link_name:
            return entry.get('href')