"""
Utility functions used in different areas of smc-python
"""
from ..compat import PY3

def save_to_file(filename, content):
    """
    Save content to file. Used by node initial contact but
    can be used anywhere.
    
    :param str filename: name of file to save to
    :param str content: content to save
    :return: None
    :raises: :py:class:`IOError`
    """ 
    import os.path
    path = os.path.abspath(filename)
    with open(path, "w") as text_file:
        text_file.write("{}".format(content))
    
def find_link_by_name(link_name, linklist):
    """
    Utility method to find the reference link based on 
    the link name and provided the list of link references
    provided by the SMC API
    
    :param link_name: name of link
    :param list linklist: list of references
    :return fully qualified href
    """
    assert(isinstance(linklist, list)), 'List required as input'
    for entry in linklist:
        if entry.get('rel') == link_name:
            return entry.get('href')

def unicode_to_bytes(s, encoding='utf-8', errors='replace'):
    """
    Helper to convert unicode strings to bytes for data that needs to be written to
    on output stream (i.e. terminal)
    For Python 3 this should be called str_to_bytes
    
    :param str s: string to encode
    :param str encoding: utf-8 by default
    :param str errors: what to do when encoding fails
    :return: byte string utf-8 encoded
    """
    return s if isinstance(s, str) else s.encode(encoding, errors)
    

def bytes_to_unicode(s, encoding='utf-8', errors='replace'):
    """
    Helper to convert byte string to unicode string for user based input
    
    :param str s: string to decode
    :param str encoding: utf-8 by default
    :param str errors: what to do when decoding fails
    :return: unicode utf-8 string
    """
    if PY3:
        return str(s,'utf-8') if isinstance(s, bytes) else s
    else:
        return s if isinstance(s, unicode) else s.decode(encoding, errors)  # @UndefinedVariable