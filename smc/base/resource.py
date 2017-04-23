"""
Metaclass used as a registry to classes that have direct
mappings to SMC API entry points. Any classes that need
to be obtained can be found in the registry. Add the metaclass
to the class hierarchy where you may need to dynamically
retrieve the class based on entry point. This is tied to the
top level base class Element.
"""


def with_metaclass(mcls):
    def decorator(cls):
        body = vars(cls).copy()
        # clean out class body
        body.pop('__dict__', None)
        body.pop('__weakref__', None)
        return mcls(cls.__name__, cls.__bases__, body)
    return decorator


class Registry(type):
    _registry = {}

    def __new__(meta, name, bases, clsdict):  # @NoSelf
        cls = super(Registry, meta).__new__(meta, name, bases, clsdict)
        if 'typeof' in clsdict:
            meta._registry[clsdict['typeof']] = cls
        return cls
