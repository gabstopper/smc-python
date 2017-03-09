"""
Classes representing basic models for data obtained or retrieved from the SMC

ElementBase is the top level parent class that provides the instance level
cache, meta data and basic methods operate on retrieved data.

Element is a top level class that exposes methods that are common to all
elements that have direct entry point in the SMC API. 
The href descriptor provides a transparent way to retrieve the object using
entry point filters. 

SubElements are derived from references of Element classes, for example, 
obtaining a reference to an engine interface and it's sub-interfaces. 
SubElements are not directly searchable through entry points like 
:class:`Element` instances.

A class attribute 'typeof' is used by a filter when an object needs to
be loaded. This value should be the elements entry point. SubElement 
classes may also have the typeof attribute which will then register
the class with the registry metaclass for use with factory functions.

Element class relationship::
   
                             ElementBase (object)
                                   |
                                cache = Cache()
                                meta = Meta(href,name,type)
                                attr_by_name()
                                describe()
                                delete()
                                modify_attribute()
                                   |
                         ----------------------
                         |                    |
    Element (ElementBase)                     SubElement (ElementBase)
        |-----------------------------------------------|
      href = ElementLocator()                         href
      name                                            name
      from_href()                                     
      export()

Classes that do not require state on retrieved json or provide basic 
container functionality may inherit from object.
"""
from collections import namedtuple
import functools
import smc.core
import smc.compat as compat
from smc.api.common import SMCRequest
import smc.actions.search as search
from smc.api.exceptions import ElementNotFound, LoadEngineFailed,\
    CreateElementFailed, ModificationFailed, ResourceNotFound,\
    DeleteElementFailed, FetchElementFailed, ActionCommandFailed
from .util import bytes_to_unicode, unicode_to_bytes, find_link_by_name
from .mixins import UnicodeMixin
from smc.base.resource import with_metaclass, Registry
from smc.base.util import find_type_from_self

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

@exception   
def prepared_request(*exception, **kwargs):
    """
    Prepared request is a wrapper to allow an exception to
    be thrown to wrap the SMCResult. Exception is optional. 
    If not provided, the SMCResult object is returned, 
    otherwise it is only thrown if SMC reports an error. 
    """ 
    return SMCRequest(**kwargs)

def ElementCreator(cls):
    """
    Helper method for create classmethods. Returns the href if
    creation is successful
    """
    result = SMCRequest(href=search.element_entry_point(cls.typeof), 
                        json=cls.json).create()
    if result.msg:
        raise CreateElementFailed(result.msg)
    return result.href

def ElementFactory(href):
    """
    Factory returns an object of type Element when only
    the href is provided.
    """
    element = prepared_request(href=href).read()
    if element.json:
        istype = find_type_from_self(element.json.get('link'))
        typeof = Registry[istype]
        e = typeof(name=element.json.get('name'),
                   meta=Meta(href=href,
                             type=istype))
        e._cache = Cache(e, element.json, element.etag)
        return e
                    
class Cache(object):
    """    
    Cache can be applied at the element level to provide an
    interface to the elements raw json. If modifications are
    made, they are made to the cache. When saved back to SMC,
    the cache is resolved against the element by re-fetching
    the element. If no changes occurred on the SMC, the changes
    are submitted, otherwise merged before submitting.
    """
    __slots__ = ('_cache', 'instance')
        
    def __init__(self, instance, json=None, etag=None):
        self.instance = instance
        if json is not None: 
            self._cache = (etag, json)
        else:
            self._cache = None
        
    def __call__(self, *args, **kwargs):
        if self._cache is None:
            result = prepared_request(href=self.instance.href).read()
            self._cache = (result.etag, result.json)
        elif self._cache and kwargs.get('force_refresh'):
            result = prepared_request(headers={'Etag': self._cache[0]}, 
                                      href=self.instance.href).read()
            if result.code != 304:
                result.json.update(self._cache[1])
                self._cache = (result.etag, result.json)
        return self._cache
    
class ElementLocator(object):
    """
    There are two ways to get an elements location, either through the 
    describe_xxx methods which returns the instance type with the populated
    meta attribute, or by loading the resource directly, i.e. Host('myhost'). 

    If the element is loaded directly, it should define a class attribute
    'typeof' to specify the element type. The 'typeof' attribute correlates
    to the SMC API entry point for the element. Classes deriving from 
    :class:`Element` will define this attribute. When loading via Host('myhost'),
    you will have an empty instance as the cache is not hydrated until some action
    is called on it that accesses the instance property 'data'. 
    Once hydrated, original json is stored in instance._cache.
    
    Classes deriving from :class:`SubElement` do not have valid entry points in
    the SMC API and will be typically created through a reference link.
    
    This descriptor is a non data descriptor and can be overridden if 'href'
    is defined in the instance dict.
    """
    def __get__(self, instance, cls=None):
        #Does the instance already have meta data
        if instance.meta:
            return instance.meta.href
        else:
            if hasattr(instance, 'typeof'):
                element = search.element_info_as_json_with_filter(
                                                instance.name, instance.typeof)
                if element:
                    instance.meta = Meta(**element[0])
                    return instance.meta.href
                raise ElementNotFound('Cannot find specified element: {}, type: {}'
                                      .format(unicode_to_bytes(instance.name), 
                                              instance.typeof))
            elif isinstance(instance, smc.core.engine.Engine):
                element = search.element_info_as_json_with_filter(instance.name, 
                                                                 'engine_clusters')
                if element:
                    instance.meta = Meta(**element[0])
                    return instance.meta.href
                raise LoadEngineFailed('Cannot load engine name: {}, ensure the '
                                       'name is correct and that the engine exists.'
                                       .format(instance.name))
            else:
                raise ElementNotFound('This class does not have the required attribute '
                                      'and cannot be referenced directly, type: {}'
                                      .format(instance))

@with_metaclass(Registry) 
class ElementBase(UnicodeMixin):
    """
    Element base provides a meta data container and an
    instance cache as well as methods to retrieve aspects
    of an element such as href, etag and full json.
    """
    def __init__(self, meta):
        self.meta = meta
        
    @property
    def cache(self):
        attr = getattr(self, '_cache', None)
        if attr is None:
            attr = self._cache = Cache(self)
        return attr
    
    def add_cache(self, data, etag=None):
        self._cache = Cache(self, data, etag)
        
    @property
    def data(self):
        return self.cache()[1]
        
    @property
    def etag(self):
        """
        ETag for this element
        """
        return self.cache(force_refresh=True)[0]
    
    def describe(self):
        """
        Display the element cache as dict
        """
        return self.data
    
    def attr_by_name(self, attr):
        """
        Retrieve a specific attribute by name
        
        :return: value or None if it doesn't exist
        """
        return self.data.get(attr)
    
    def delete(self):
        """
        Delete the element
        
        :raises: :py:class:`smc.api.exception.DeleteElementFailed`
        :return: None
        """
        prepared_request(DeleteElementFailed,
                         href=self.href).delete()
        
    def modify_attribute(self, **kwargs):
        """
        Modify the attribute by key / value pair. 
        
        :param dict kwargs: key=value pair to change
        :raises: :py:class:`smc.api.exceptions.ElementNotFound`
        :raises: :py:class:`smc.api.exceptions.ModificationFailed`  
        :return: None
        """
        element = self.data
        if element.get('system') == True:
            raise ModificationFailed('Cannot modify system element: %s' % self.name)
        for k, v in kwargs.items():
            target_value = element.get(k)
            if isinstance(target_value, dict): #update dict leaf
                element[k].update(v)
            elif isinstance(target_value, list): #replace list
                element[k] = v
            else: #single key/value
                element.update({k: v}) #replace str
                
        prepared_request(ModificationFailed,
                         href=self.href,
                         json=element,
                         etag=self.etag).update()
    
    def _get_resource(self, href):
        """
        Return json for element using href provided
        
        :raises: FetchElementFailed
        """
        return prepared_request(FetchElementFailed,
                                href=href).read().json
        
    def _get_resource_by_link(self, link):
        """
        Return json for element using resources link
        
        :raises: FetchElementFailed
        """
        return prepared_request(FetchElementFailed,
                                href=self._link(link)).read().json
    
    def _get_resource_name(self, href):
        """
        Get name of resource when only given href
        
        :raises: FetchElementFailed
        """
        resource = prepared_request(FetchElementFailed,
                                    href=href).read().json    
        if resource:
            return resource.get('name')
               
    def _link(self, link):
        """
        Get resource link
        
        :raises: ResourceNotFound
        """
        return find_link_by_name(link, self.data.get('link'))
        
class Element(ElementBase):
    """
    Base element with common methods shared by inheriting classes
    """
    href = ElementLocator()

    def __init__(self, name, meta=None):
        super(Element, self).__init__(meta)
        self._name = name #<str>
    
    @classmethod
    def from_href(cls, href):
        """
        Return an instance of an Element based on the href
        
        :return: :py:class:`smc.base.model.Element` type
        """
        return ElementFactory(href)
    
    @property
    def name(self):
        """
        Name of element
        """
        if compat.PY3:
            return self._name
        else:
            return bytes_to_unicode(self._name)
  
    def export(self, filename='element.zip', wait_for_finish=False):
        """
        Export this element
        
        :param str filename: filename to store exported element
        :param boolean wait_for_finish: wait for update msgs (default: False)
        :raises: ActionCommandFailed
        :return: generator yielding updates on progress, or [] if element cannot
                 be exported, like for system elements
        """
        from smc.administration.tasks import Task, task_handler
        try:
            element = prepared_request(ActionCommandFailed,
                                       href=self._link('export'),
                                       filename=filename).create()
            
            return task_handler(Task(**element.json), 
                                wait_for_finish=wait_for_finish, 
                                filename=filename)
        except ResourceNotFound:
            return []

    def __unicode__(self):
        return u'{0}(name={1})'.format(self.__class__.__name__, self.name)
    
    def __repr__(self):
        return str(self)

class SubElement(ElementBase):
    """
    SubElement is the base class for elements that do not 
    have direct entry points in the SMC and instead are obtained
    through a reference. They are not 'loaded' directly as are
    classes that inherit from :class:`Element`. 
    """
    def __init__(self, meta=None, **kwargs):
        super(SubElement, self).__init__(meta)
        pass
        
    @property
    def name(self):
        return self.meta.name if self.meta else None
        
    @property
    def href(self):
        return self.meta.href if self.meta else None
        
    def __unicode__(self):
        return u'{0}(name={1})'.format(self.__class__.__name__, self.name)
        
    def __repr__(self):
        return str(self)
        
class Meta(namedtuple('Meta', 'name href type')):
    """
    Internal namedtuple used to store top level element information. When 
    doing base level searches, SMC API will return only meta data for the
    element that has name, href and type.
    Meta has the same data structure returned from 
    :py:func:`smc.actions.search.element_info_as_json`
    """
    def __new__(cls, href, name=None, type=None): # @ReservedAssignment
        return super(Meta, cls).__new__(cls, name, href, type)
