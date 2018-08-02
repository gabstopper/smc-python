"""
Decorators used in various areas throughout smc-python.
"""
import warnings
import functools


def deprecated(func_replacement):
    """
    Use this decorator on functions that are marked as deprecated.
    It takes a single argument of the function name it's being
    replaced with.
    """
    def _deprecated(func):
        @functools.wraps(func)
        def new_func(*args, **kwargs):
            warnings.simplefilter('always', DeprecationWarning) #turn off filter 
            warnings.warn(
                'Call to deprecated function {}. Use new function: {}() instead.'
                .format(func.__name__, func_replacement),
                category=DeprecationWarning, stacklevel=2)
            warnings.simplefilter('default', DeprecationWarning) #reset filter
            return func(*args, **kwargs)
        return new_func
    return _deprecated


class classproperty(object):
    """
    Used for collection manager so objects can be accessed as a
    class property and also from the instance
    """

    def __init__(self, fget):
        self.fget = fget

    def __get__(self, instance, owner_cls):
        return self.fget(owner_cls)


def memoize(f):
    memo = {}
    def helper(x):
        if x not in memo:
            memo[x] = f(x)
        return memo[x]
    return helper


def cacheable_resource(func):
    @functools.wraps(func)
    def get(self):
        try:
            return self._cache[func]
        except AttributeError:
            self._cache = {}
        except KeyError:
            pass
        ret = self._cache[func] = func(self)
        return ret
    return property(get)


class cached_property(object):
    """
    Use for caching a property value on the instance. If the
    attribute is deleted, it will be recreated when called.
    """

    def __init__(self, func):
        self.func = func
        #self.__doc__ = func.__doc__

    def __get__(self, obj, cls):
        if obj is None:
            return self
        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value


def create_hook(function):
    """
    Provide a pre-filter to the create function that provides the ability
    to modify the element json before submitting to the SMC. To register
    a create hook, set on the class or top level Element class to enable
    this on any descendent of Element::
    
        Element._create_hook = classmethod(myhook)
    
    The hook should be a callable and take two arguments, cls, json and 
    return the json after modification. For example::
    
        def myhook(cls, json):
            print("Called with class: %s" % cls)
            if 'address' in json:
                json['address'] = '2.2.2.2'
            return json
    """
    @functools.wraps(function)
    def run(cls, json, **kwargs):
        if hasattr(cls, '_create_hook'):
            json = cls._create_hook(json)
        return function(cls, json, **kwargs)
    return run


def exception(function):
    """
    If exception was specified for prepared_request,
    inject this into SMCRequest so it can be used for
    return if needed.
    """
    @functools.wraps(function)
    def wrapper(*exception, **kwargs):
        result = function(**kwargs)
        if exception:
            result.exception = exception[0]
        return result
    return wrapper


def with_metaclass(mcls):
    """
    Metaclass class decorator for py2 and py3
    """
    def decorator(cls):
        body = vars(cls).copy()
        # clean out class body
        body.pop('__dict__', None)
        body.pop('__weakref__', None)
        return mcls(cls.__name__, cls.__bases__, body)
    return decorator

