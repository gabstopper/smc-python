
def lazy_loader(f):
    def deco(self, *args, **kwargs):
        #Need the full json for element
        if not self.data.get('link'):
            self.load()
        return f(self, *args, **kwargs)
    return deco

def save_to_file(filename, content):
    """
    Save content to file. Used by node initial contact but
    can be used anywhere.
    
    :param str filename: name of file to save to
    :param str content: content to save
    :return: None
    :raises: IOError
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
        
            