"""
Metaclass used as a registry to classes that have direct
mappings to SMC API entry points. Any classes that need
to be obtained can be found in the registry. Add the metaclass
to the class hierarchy where you may need to dynamically
retrieve the class based on entry point. This is tied to the
top level base class Element.
"""
import smc.base.model

def with_metaclass(mcls):
    def decorator(cls):
        body = vars(cls).copy()
        # clean out class body
        body.pop('__dict__', None)
        body.pop('__weakref__', None)
        return mcls(cls.__name__, cls.__bases__, body)
    return decorator

class RegistryMeta(type):
    def __getitem__(meta, key):  # @NoSelf
        try:
            return meta._registry[key]
        except KeyError:
            return smc.base.model.Element

@with_metaclass(RegistryMeta)
class Registry(type):
    _registry = {}

    def __new__(meta, name, bases, clsdict):  # @NoSelf
        cls = super(Registry, meta).__new__(meta, name, bases, clsdict)
        if 'typeof' in clsdict:
            #if isinstance(clsdict['typeof'], list):
            #    for attr in clsdict['typeof']:
            #        meta._registry[attr] = cls
            #else:
            meta._registry[clsdict['typeof']] = cls
        return cls
