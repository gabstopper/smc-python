"""
Classes representing basic models for data obtained or retrieved from the SMC

ElementBase is the top level parent class that provides the instance level
cache, meta data and basic methods operate on retrieved data.

Element is the common interface that exposes methods that and a retrieval 
descriptor for elements that have direct entry point in the SMC API. 
The href descriptor provides a transparent way to retrieve the object using
entry point filters based on providing only the ``name`` attribute on an 
instance.

The SubElement interface defines references of Element classes, for example, 
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
                                delete()
                                modify_attribute()
                                   |
                         ----------------------
                         |                    |
    Element (ElementBase)                     SubElement (ElementBase)
        |------------------------------------------------------|
      href = ElementLocator()                                href
      name                                                   name
      from_href()
      from_meta()                                   
      export()
      category_tags
      referenced_by

Classes that do not require state on retrieved json or provide basic 
container functionality may inherit from object.
"""
import copy
from collections import namedtuple
import functools
import smc.compat as compat
from smc.api.web import counters   
from smc.api.common import SMCRequest, fetch_href_by_name, fetch_entry_point
from smc.api.exceptions import ElementNotFound, \
    CreateElementFailed, ModificationFailed, ResourceNotFound,\
    DeleteElementFailed, FetchElementFailed, ActionCommandFailed,\
    UpdateElementFailed
from .util import bytes_to_unicode, unicode_to_bytes
from .mixins import UnicodeMixin
from smc.base.resource import with_metaclass, Registry
from smc.base.util import find_type_from_self, merge_dicts

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

def fetch_collection(href):
    """
    Return json for element using href provided
        
    :raises FetchElementFailed: failure during GET request
    """
    return prepared_request(
        FetchElementFailed,
        href=href
        ).read().json
                                
@exception   
def prepared_request(*exception, **kwargs):
    """
    Prepared request is a wrapper to allow an exception to
    be thrown to wrap the SMCResult. Exception is optional. 
    If not provided, the SMCResult object is returned, 
    otherwise it is only thrown if SMC reports an error. 
    """ 
    return SMCRequest(**kwargs)
    
def ElementCreator(cls, json):
    """
    Helper method for create classmethods. Returns the href if
    creation is successful
    """
    result = SMCRequest(
                href=fetch_entry_point(cls.typeof),  
                json=json
                ).create()
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
        typeof = lookup_class(istype)
        e = typeof(name=element.json.get('name'),
                   href=href,
                   type=istype)
        e._cache = Cache(e, element.json, element.etag)
        return e

class ElementResource:
    """
    Convenience class to provide dotted access to resource links.
    Resource links are referenced in the element as a list with
    dict items in format {'href', 'rel'}. Attributes are added
    dynamically using 'rel' as name and href as the value. This 
    makes it possible to access a link via self.resource.rel
    """
    def name(self, href):
        """
        Have the href, reverse call to get name of element
        """
        resource = prepared_request(FetchElementFailed, 
                                    href=href).read().json 
        if resource: 
            return resource.get('name')
    
    def get(self, resource, as_smcresult=False):
        """
        Get the json for the resource. This can be either an
        href or the 'rel' link name which will retrieve the
        href from this class.
        Set as_smcresult if you need to retrieve the full
        SMCResult object. In some cases, nested ETag's are
        required for certain elements, such as interface contact
        addresses.
        """
        if not resource.startswith('http'):
            resource = getattr(self, resource)
        result = prepared_request(href=resource
                                  ).read()
        if result.msg:
            raise FetchElementFailed(result.msg)
        if as_smcresult:
            return result
        else:
            return result.json
        
    def __getattr__(self, link):
        raise ResourceNotFound('Resource requested: %r is not '
                               'available on this element.' % link)
             
class Cache(object):
    """    
    Cache is applied at the element level to provide an interface
    to the element raw json. Caching is used to reduce the number
    of SMC calls required to find linked resources or access element
    attributes. When modifications are made that change the element
    cache, the _cache attribute is cleared on the instance, although
    meta and resource links remain. This will cause a cache refresh 
    if resources requiring the 'data' attribute are requested after
    a change. When an element is sent for modification, the retrieved
    ETag is used and an exception will be raised if the server side 
    ETag has changed, requiring the request to be made again.
    """
    __slots__ = ('_cache', 'instance', '_resource')
        
    def __init__(self, instance, json=None, etag=None):
        self.instance = instance
        if json is not None: 
            self._cache = (etag, json)
        else:
            self._cache = None
            
        self._resource = None #Expanded link references
        
    def __call__(self, *args, **kwargs):
        counters.update(cache=1)
        if self._cache is None or kwargs.get('force_refresh'):
            result = prepared_request(href=self.instance.href).read()
            self._cache = (result.etag, result.json)
        return self._cache
    
    @property
    def data(self):
        return self()[1]
    
    @property
    def etag(self):
        #Etag can be none if cache was manually set using add_cache
        if self()[0] is None: 
            etag = prepared_request(href=self.instance.href).read()
            self._cache = (etag.etag, self._cache[1])
        return self._cache[0]
    
    def clear(self):
        # This forces a refresh on next attribute access
        self._cache = None
    
    @property
    def resource(self):
        """
        Once resource links are retrieved the first time, they will be 
        preserved even if cache is flushed.
        """
        if self._resource is None:
            data = self()[1]
            self._resource = ElementResource() 
            for x in data.get('link'): 
                setattr(self._resource, 
                        x.get('rel'), x.get('href')) 
        return self._resource
                 
class ElementLocator(object):
    """
    There are two ways to get an elements location, either through
    collections which returns the instance type with the populated
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
                element = fetch_href_by_name(
                    instance.name, filter_context=instance.typeof)
                if element.json:
                    instance.meta = Meta(**element.json[0])
                    return instance.meta.href
                raise ElementNotFound('Cannot find specified element: {}, type: {}'
                                      .format(unicode_to_bytes(instance.name), 
                                              instance.typeof))
            else:
                raise ElementNotFound('This class does not have the required attribute '
                                      'and cannot be referenced directly, type: {}'
                                      .format(instance))

@with_metaclass(Registry) 
class ElementBase(UnicodeMixin):
    """
    Element base provides a meta data container and an
    instance cache as well as methods to retrieve aspects
    of an element.
    Meta is passed in to Element and SubElement types to provide 
    links to resources. Meta format: {'href','type','name'}.
    Meta can be passed to constructor through as key value pairs
    kwargs, href=.... (only partial meta), or meta={.....} (as dict)
            
    If meta is not provided, the meta attribute will be None 
    """
    def __init__(self, **meta):
        meta_as_kw = meta.pop('meta', None)
        if meta_as_kw:
            self.meta = Meta(**meta_as_kw)
        else:
            self.meta = Meta(**meta) if meta else None
        
    @property
    def cache(self):
        attr = getattr(self, '_cache', None)
        if attr is None:
            setattr(self, '_cache', Cache(self))
        return self._cache
    
    def add_cache(self, data, etag=None):
        self._cache = Cache(self, data, etag)
        
    @property
    def data(self):
        return self.cache.data
        
    @property
    def etag(self):
        """
        ETag for this element
        """
        return self.cache.etag
    
    @property
    def resource(self):
        return self.cache.resource

    def attr_by_name(self, attr):
        """
        Retrieve a specific attribute by name
        
        :return: value or None if it doesn't exist
        """
        return self.data.get(attr)
    
    def delete(self):
        """
        Delete the element
        
        :raises DeleteElementFailed: possible dependencies, record locked, etc
        :return: None
        """
        prepared_request(DeleteElementFailed,
                         href=self.href,
                         headers={'if-match': self.etag}
                         ).delete()
    
    def update(self, *exception, **kwargs):
        """
        Update wrapper around cache to handle modifications 
        requests and clear element cache. This is called in
        various places to ensure the cache stays current.
        """
        if not 'href' in kwargs:
            kwargs.update(href=self.href)
            
        if not 'json' in kwargs:
            # update from copy of cache before clearing
            kwargs.update(json=copy.deepcopy(self.data))
        
        # Etag taken from instance
        if not 'etag' in kwargs:
            kwargs.update(etag=self.etag)
        
        self.cache.clear()
        
        if not exception:
            exception = UpdateElementFailed
        else:
            exception = exception[0]
        # Return href from SMC        
        return prepared_request(exception,
                                **kwargs
                                ).update().href
              
    def modify_attribute(self, **kwargs):
        """
        Modify the attribute by key / value pair. 
        Add append_lists=True kwarg if dict leaf is a list
        and you want to append, default: replace
        
        :param dict kwargs: key=value pair to change
        :param boolean append_lists: if change is a list, append or overwrite
        :raises ElementNotFound: cannot find element specified
        :raises ModificationFailed, UpdateElementFailed: failure applying change
            with reason  
        :return: None
        """
        if self.data.get('system') == True:
            raise ModificationFailed('Cannot modify system element: %s' % self.name)
        
        append_lists = kwargs.pop('append_lists', False)
        merge_dicts(self.data, kwargs, append_lists)
        self.update()
                
class Element(ElementBase):
    """
    Base element with common methods shared by inheriting classes
    
    :ivar objects: :py:class:`smc.elements.resources.ElementCollection`
    """
    href = ElementLocator()

    def __init__(self, name, **meta):
        if meta:
            meta.update(name=name)
        super(Element, self).__init__(**meta)
        self._name = name #<str>
    
    @classmethod
    def from_href(cls, href):
        """
        Return an instance of an Element based on the href
        
        :return: :py:class:`smc.base.model.Element` type
        """
        return ElementFactory(href)
    
    @classmethod
    def from_meta(cls, **meta):
        """
        Return an instance of an Element based on meta
        
        :param dict meta: raw dict meta from smc
        :return: :py:class:`smc.base.model.Element` type
        """
        return lookup_class(meta.get('type'))(**meta)
    
    @property
    def name(self):
        """
        Name of element
        """
        if compat.PY3:
            return self._name
        else:
            return bytes_to_unicode(self._name)
    
    @property
    def category_tags(self):
        """
        Search category tags assigned to this element
        ::
        
            >>> from smc.elements.network import Host
            >>> Host('kali').category_tags
            [CategoryTag(name=foo), CategoryTag(name=foocategory)]
        
        :return: list :py:class:`smc.elements.other.CategoryTag`
        """
        return [Element.from_meta(**tag)
                for tag in 
                prepared_request(
                    href=self.resource.search_category_tags_from_element
                    ).read().json]
                      
    def export(self, filename='element.zip', wait_for_finish=False):
        """
        Export this element
        
        :param str filename: filename to store exported element
        :param boolean wait_for_finish: wait for update msgs (default: False)
        :raises ActionCommandFailed: invalid permissions, invalid directory, etc
        :return: generator yielding updates on progress, or [] if element cannot
                 be exported, like for system elements
        """
        from smc.administration.tasks import Task, task_handler
        try:
            element = prepared_request(ActionCommandFailed,
                                       href=self.resource.export,
                                       filename=filename
                                       ).create()
            
            return task_handler(Task(**element.json), 
                                wait_for_finish=wait_for_finish, 
                                filename=filename)
        except ResourceNotFound:
            return []
    
    @property
    def referenced_by(self):
        """    
        Show all references for this element. A reference means that this
        element is being used, for example, in a policy rule, as a member of
        a group, etc.
        
        :return: list referenced elements
        """
        href = fetch_entry_point('references_by_element')
        return [Element.from_meta(**ref)
                for ref in prepared_request(
                    FetchElementFailed,
                    href=href,
                    json={'value': self.href}
                    ).create().json]
    
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
    def __init__(self, **meta):
        super(SubElement, self).__init__(**meta)
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

def lookup_class(typeof, default=Element):
    return Registry._registry.get(typeof, default)
        
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
