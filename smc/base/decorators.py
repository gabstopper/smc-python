"""
Decorators used in various areas throughout smc-python.
"""
import functools


class cached_property(object):
    """
    Use for caching a property value on the instance. If the
    attribute is deleted, it will be recreated when called.
    """

    def __init__(self, func):
        self.func = func

    def __get__(self, obj, cls):
        if obj is None:
            return self
        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value
    

def autocommit(method):
    """
    Decorate a method with this to invoke self.update() at the
    end of the function call. Otherwise calling update would be
    required after functions that make modifications to elements.
    """
    @functools.wraps(method)
    def inner(self, *args, **kwargs):
        commit = kwargs.pop('autocommit', False)
        method(self, *args, **kwargs)
        if commit:
            self.update()
    return inner


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
