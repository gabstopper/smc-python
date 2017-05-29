"""
Decorators used in various areas throughout smc-python.
"""
import functools
from smc import session


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


def autocommit(now=False):
    """
    A method decorated with autocommit provides a mechanism to delay (or not)
    the update of an element. If methods decorated with autocommit should
    always update after completion, provide autocommit=True to the constructor
    or set session.AUTOCOMMIT = True.
    If autocommit is not set, you must make your changes and call .update() on
    the element.
    """
    def _decorator(func):
        @functools.wraps(func)
        def _wrapped_func(self, *args, **kwargs):
            as_kwarg = kwargs.pop('autocommit', None)
            func(self, *args, **kwargs)
            if as_kwarg is not None:
                if as_kwarg:
                    self.update()
            elif (now or session.AUTOCOMMIT):
                self.update()
        return _wrapped_func
    return _decorator


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
