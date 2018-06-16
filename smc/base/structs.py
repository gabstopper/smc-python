"""
Common structures
"""
import collections


class BaseIterable(object):
    """
    A collections container that provides a pre-filled container. This container
    type is used when an element retrieval returns all of an elements data in a
    single query and will contain multiple values for the same serialized type.
    Elements can be retrieved from the container through iteration,
    slicing, or by using `get` and providing either the index or an
    attribute / value pair.
    
    If subclassing, it may be useful to override `get` to provide a restricted
    interface to common attributes to fetch.
    
    Examples::
    
        >>> for status in engine.nodes[0].interface_status:
        ...   status
        ... 
        InterfaceStatus(aggregate_is_active=False, ....
    
    By index::
    
        >>> engine.nodes[0].interface_status[1]

    Slicing::
    
        >>> engine.nodes[0].interface_status[1:5:2]
        >>> engine.nodes[0].interface_status[::-1]
    
    Using get by index or attribute::
    
        >>> engine.nodes[0].interface_status.get(1)
        >>> engine.nodes[0].interface_status.get(interface_id=2)
        
    :param iterable item: items for which to perform iteration. Can be
        another class with an __iter__ method also to chain iterators.
    """
    def __init__(self, items):
        self.items = items
    
    def __getitem__(self, index):
        if not isinstance(index, (int, slice)):
            raise TypeError('Invalid index specified. Must be int or slice.')
        if isinstance(index, slice):
            return self.items[index.start:index.stop:index.step]
        else:
            return self.items[index]
    
    def get(self, *args, **kwargs):
        """
        Get an element from the iterable by an arg or kwarg.
        Args can be a single positional argument that is an index
        value to retrieve. If the specified index is out of range,
        None is returned. Otherwise use kwargs to provide a  key/value.
        The key is expected to be a valid attribute of the iterated class.
        For example, to get an element that has a attribute name of 'foo',
        pass name='foo'.
        
        :raises ValueError: An argument was missing
        :return: the specified item, type is based on what is
            returned by this iterable, may be None
        """
        if self:
            if args:
                index = args[0]
                if index <= len(self) -1:
                    return self[args[0]]
                return None
            elif kwargs:
                key, value = kwargs.popitem()
                for item in self.items:
                    if getattr(item, key, None) == value:
                        return item
            else:
                raise ValueError('Missing argument. You must provide an '
                    'arg or kwarg to fetch an element from the collection.')
        
    def __iter__(self):
        return iter(self.items)
        
    def __bool__(self):
        return bool(self.items)
    __nonzero__ = __bool__

    def __len__(self):
        return len(self.items)

    def __repr__(self):
        return "%s(items: %s)" % (self.__class__.__name__, len(self))
    
    def count(self):
        """
        Return the number of entries
        
        :rtype: int
        """
        return len(self)

    def all(self):
        """
        Return the iterable as a list
        """
        return list(self)

    
class SerializedIterable(BaseIterable):
    """
    A pre-serialized list of elements. This is used when it's easier to
    provide a pre-serialized class as long as all elements are of the
    same type.
    
    :param iterable item: items for which to perform iteration. Can be
        another class with an __iter__ method also to chain iterators.
    :param model: optional class to serialize each iteration. 
    """
    def __init__(self, items, model):
        items = [model(**r) for r in items]
        super(SerializedIterable, self).__init__(items)


class NestedDict(collections.MutableMapping): 
    """ 
    Generic dict structure that can be used to objectify 
    complex json. This dict allows attribute access for data
    stored in the data dict by overridding getattr.
    """ 
    def __init__(self, data=None, **kwargs):
        self.data = data if data else {}
        self.update(self.data, **kwargs)

    def __setitem__(self, key, value):
        self.data[key] = value
    def __getitem__(self, key):
        return self.data[key]
    def __delitem__(self, key):
        del self.data[key]
    def __iter__(self):
        return iter(self.data)
    def __len__(self):
        return len(self.data)
    def __getattr__(self, key):
        if key in self:
            return self[key]
        raise AttributeError("%r object has no attribute %r" 
            % (self.__class__, key)) 
            
