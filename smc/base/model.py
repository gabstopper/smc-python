"""
Classes representing basic models for data obtained or retrieved from the SMC

ElementBase is the top level parent class that provides the instance level
cache, meta data and basic methods to model the retrieved elements.

Element is the common interface that exposes methods and a retrieval
descriptor for elements that have a direct entry point in the SMC API.
The href descriptor provides a transparent way to retrieve the object using
entry point filters based on providing only the ``name`` attribute on an
instance. All instance data is lazy loaded. When an element is first retrieved,
a single query is made to find the element and it's meta data. Subsequent access
to methods or properties that access the elements ``data`` attribute will cause
a second query to obtain the elements full json.

The SubElement interface defines elements without a direct entry point and instead
are references of Element classes, for example, obtaining a reference to an engine
interface and it's sub-interfaces. SubElements are therefore not directly searchable
through entry points like :class:`Element` instances.

A class attribute 'typeof' is used by a filter when an object needs to
be loaded. This value should be the elements entry point. SubElement
classes may also have the typeof attribute which will then register
the class with the registry metaclass for use with factory functions.

Element class relationship (abbreviated)::

                             ElementBase (object)
                                   |
                                data = ElementCache()
                                meta = Meta(href,name,type)
                                update()
                                delete()
                                modify_attribute()
                                 .....
                                   |
                         ----------------------
                         |                    |
    Element (ElementBase)                     SubElement (ElementBase)
        |------------------------------------------------------|
      href = ElementLocator()                                href
      name                                                   name
      objects                                                ....
      export()
      rename
      category_tags
      referenced_by
      ...

Classes that do not require state on retrieved json or provide basic
container functionality may inherit from object.
"""
from collections import namedtuple, MutableMapping
import smc.base.collection
from smc.compat import string_types
from smc.base.decorators import cached_property, classproperty, exception,\
    create_hook, with_metaclass
from smc.api.common import SMCRequest, fetch_href_by_name, fetch_entry_point
from smc.api.exceptions import ElementNotFound, \
    CreateElementFailed, ModificationFailed, ResourceNotFound,\
    DeleteElementFailed, FetchElementFailed, UpdateElementFailed
from .util import bytes_to_unicode, unicode_to_bytes, merge_dicts,\
    find_type_from_self
from smc.base.mixins import RequestAction, UnicodeMixin


@exception
def prepared_request(*exception, **kwargs):  # @UnusedVariable
    """
    Prepared request is a wrapper to allow an exception to
    be thrown to wrap the SMCResult. Exception is optional.
    If not provided, the SMCResult object is returned,
    otherwise it is only thrown if SMC reports an error.
    """
    return SMCRequest(**kwargs)


def LoadElement(href, only_etag=False):
    """
    Return an instance of a element as a ElementCache dict
    used as a cache.
    
    :rtype ElementCache
    """
    request = SMCRequest(href=href)
    request.exception = FetchElementFailed
    result = request.read()
    if only_etag:
        return result.etag
    return ElementCache(
        etag=result.etag, **result.json)


@create_hook
def ElementCreator(cls, json):
    """
    Helper method for create classmethods. Returns the href if
    creation is successful. This is a lazy load that will provide
    only the meta for the element. Additional attribute access
    will load the full data.

    :return: instance of type Element with meta
    :rtype: Element
    """
    result = SMCRequest(
        href=fetch_entry_point(cls.typeof),
        json=json).create()
    
    if result.msg:
        raise CreateElementFailed(result.msg)

    return cls(json.get('name'),
               type=cls.typeof,
               href=result.href)


def SubElementCreator(cls, *exception, **kwargs):
    """
    Helper method for creating sub elements. SubElements do not
    have direct entry points in the SMC API and require a direct
    href reference. This is a lazy load that will provide
    only the meta for the element. Additional attribute access
    will load the full data.

    :return: instance of type SubElement with meta
    :rtype: SubElement
    """
    exc = exception[0] if exception else CreateElementFailed
    if 'href' not in kwargs:
        raise exc('Cannot create SubElement: %s. Missing the href value'
            % cls.__name__)
    
    result = SMCRequest(**kwargs).create()
    if result.msg:
        raise exc(result.msg)
    
    name = kwargs.get('json')
    return cls(name=name.get('name'),
               type=cls.typeof,
               href=result.href)


def ElementFactory(href):
    """
    Factory returns an object of type Element when only
    the href is provided.
    """
    element = SMCRequest(href=href).read()
    if element.json:
        istype = find_type_from_self(element.json.get('link'))
        typeof = lookup_class(istype)
        e = typeof(name=element.json.get('name'),
                   href=href,
                   type=istype)
        e.data = ElementCache(
            etag=element.etag, **element.json)
        return e

    
class SubDict(MutableMapping): 
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


class ElementCache(dict):
    """
    Basic container for retrieved element. Can be inserted
    where a cached copy is needed. Also provides methods to
    retrieve element links and json by link name
    """
    def __init__(self, *arg, **kw):
        self._etag = kw.pop('etag', None)
        super(ElementCache, self).__init__(*arg, **kw)

    def etag(self, href):
        """
        ETag can be None if a subset of element json is using
        this container, such as the case with Routing.
        """
        if self and self._etag is None:
            self._etag = LoadElement(href, only_etag=True)
        return self._etag
    
    @cached_property
    def links(self):
        return {link['rel']:link['href'] for link in self['link']}
    
    def get_link(self, rel):
        """
        Return link for specified resource
        """
        if rel in self.links:
            return self.links[rel]
        raise ResourceNotFound('Resource requested: %r is not available '
            'on this element.' % rel)


class ElementLocator(object):
    """
    There are two ways to get an elements location, either through
    collections which returns the instance type with the populated
    meta attribute, or by loading the resource directly, i.e. Host('myhost').

    If the element is loaded directly, it should define a class attribute
    'typeof' to specify the element type. The 'typeof' attribute correlates
    to the SMC API entry point for the element. Classes deriving from
    :class:`Element` will define this attribute. When loading via
    Host('myhost'), you will have an empty instance as the cache is not
    hydrated until some action is called on it that accesses the instance
    property 'data'.
    Once hydrated, original json is stored in instance.data.

    Classes deriving from :class:`SubElement` do not have valid entry points in
    the SMC API and will be typically created through a reference link.

    This descriptor is a non data descriptor and can be overridden if 'href'
    is defined in the instance dict.
    """

    def __get__(self, instance, cls=None):
        # Does the instance already have meta data
        if instance._meta:
            return instance._meta.href
        else:
            if hasattr(instance, 'typeof'):
                element = fetch_href_by_name(
                    instance.name,
                    filter_context=instance.typeof)
                if element.json:
                    instance._meta = Meta(**element.json[0])
                    return instance._meta.href
                raise ElementNotFound(
                    'Cannot find specified element: {}, type: {}'
                    .format(unicode_to_bytes(instance.name),
                            instance.typeof))
            else:
                raise ElementNotFound(
                    'This class does not have the required attribute '
                    'and cannot be referenced directly, type: {}'
                    .format(instance))


class ElementMeta(type):
    """
    Element metaclass that registers classes with the typeof
    attribute into a registry for later lookups.
    """
    _map = {}
    def __new__(meta, name, bases, clsdict):  # @NoSelf
        cls = super(ElementMeta, meta).__new__(meta, name, bases, clsdict)
        if 'typeof' in clsdict:
            meta._map[clsdict['typeof']] = cls
        return cls


@with_metaclass(ElementMeta)
class ElementBase(RequestAction, UnicodeMixin):
    """
    Element base provides a meta data container and an
    instance cache as well as methods to retrieve aspects
    of an element.
    Meta is passed in to Element and SubElement types to provide
    links to resources. When a top level query is made to the SMC
    API, meta is returned for the element (unless a direct link query
    is made). The meta format include 'href','type','name'.
    For example::
    
        "href":"http://1.1.1.1:8082/6.4/elements/host/707","name":"foobar","type":"host"
    
    Methods of the element classes are designed to expose any links or
    attributes of the specific element to simplify manipulation. If a method,
    etc is accessed that requires the elements data, the element is fetched
    and the elements cache (stored in `data` attribute) is inflated. The ETag
    is also retained in the element and is used when updating or deleting the
    element to ensure we are operating on the latest version.
    
    Meta can be passed to constructor through as key value pairs
    kwargs, href=.... (only partial meta), or meta={.....} (as dict)

    If meta is not provided, the meta attribute will be None
    """

    def __init__(self, **meta):
        meta_as_kw = meta.pop('meta', None)
        if meta_as_kw:
            self._meta = Meta(**meta_as_kw)
        else:
            self._meta = Meta(**meta) if meta else None

    @cached_property
    def data(self):
        return LoadElement(self.href)

    @property
    def etag(self):
        return self.data.etag(self.href)
    
    def get_relation(self, rel, exception=None):
        """
        Get a relational link. Provide optional exception to be
        returned instead of ResourceNotFound.
        """
        try:
            return self.data.get_link(rel)
        except ResourceNotFound as e:
            if exception:
                raise exception(e)
            raise
    
    def _del_cache(self):
        try:
            del self.data
        except AttributeError:
            pass
    
    def __getstate__(self):
        state = self.__dict__.copy()
        if '_cache' in state:
            del state['_cache']
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
    
    def __getattr__(self, key):
        if key not in ('typeof',):
            try:
                return self.data[key]
            except KeyError:
                pass
        raise AttributeError("%r object has no attribute %r"
                % (self.__class__, key))
    
    def delete(self):
        """
        Delete the element

        :raises DeleteElementFailed: possible dependencies, record locked, etc
        :return: None
        """
        request = SMCRequest(
            href=self.href,
            headers={'if-match': self.etag}) 
        request.exception = DeleteElementFailed
        request.delete()

    def update(self, *exception, **kwargs):
        """
        Update the existing element and clear the instance cache.
        Removing the cache will ensure subsequent calls requiring element
        attributes will force a new fetch to obtain the latest copy.

        If attributes are set via kwargs and instance attributes are also
        set, instance attributes are updated first, then kwargs. Typically
        you will want to use either instance attributes OR kwargs, not both.
        
        Calling update() with no args will assume the element has already
        been modified directly and the data cache will be used to update.
        You can also override the following attributes: href, etag and
        json. If json is sent, it is expected to the be a complete payload
        to satisfy the update.
        
        For kwargs, if attribute values are a list, you can pass
        'append_lists=True' to add to an existing list, otherwise overwrite
        (default: overwrite)

        If using instance attributes, the attribute value can be a callable
        and it will be evaluated and merged.

        .. seealso:: To see different ways to utilize this method for updating,
            see: :ref:`update-elements-label`.

        :param exception: pass a custom exception to throw if failure
        :param kwargs: optional kwargs to update request data to server.
        :return: href of the element modified
        :rtype: str
        """
        if not exception:
            exception = UpdateElementFailed
        else:
            exception = exception[0]

        params = {
            'href': self.href,
            'etag': self.etag
        }

        if 'href' in kwargs:
            params.update(href=kwargs.pop('href'))

        if 'etag' in kwargs:
            params.update(etag=kwargs.pop('etag'))

        name = kwargs.get('name', None)
        
        json = kwargs.pop('json') if 'json' in kwargs else self.data
        del self.data       # Delete the cache before processing attributes
        
        instance_attr = {k: v() if callable(v) else v
                         for k, v in vars(self).items()
                         if not k.startswith('_')}
        
        if instance_attr:
            json.update(**instance_attr)

        # If kwarg settings are provided AND instance variables, kwargs
        # will overwrite collected instance attributes with the same name.
        if kwargs:
            append_lists = kwargs.pop('append_lists', False)
            merge_dicts(json, kwargs, append_lists)

        params.update(json=json)
        
        # Remove attributes from instance if previously set
        if instance_attr:
            for attr in instance_attr:
                delattr(self, attr)
        
        request = SMCRequest(**params) 
        request.exception = exception
        result = request.update()
        
        if name: # Reset instance name
            self._meta = Meta(name=name, href=self.href, type=self._meta.type)
            self._name = name
        
        return result.href

    def modify_attribute(self, **kwargs):
        """
        Modify the attribute by key / value pair.
        Add append_lists=True kwarg if dict leaf is a list
        and you want to append, default: replace

        :param dict kwargs: key=value pair to change
        :param bool append_lists: if change is a list, append or overwrite
        :raises ElementNotFound: cannot find element specified
        :raises ModificationFailed, UpdateElementFailed: failure applying
            change with reason
        :return: href of the element modified
        :rtype: str
        """
        if self.data.get('system', False):
            raise ModificationFailed(
                'Cannot modify system element: %s' % self.name)

        params = {
            'href': self.href,
            'etag': self.etag
        }
        append_lists = kwargs.pop('append_lists', False)
        merge_dicts(self.data, kwargs, append_lists)
        params.update(json=self.data)
        del self.data

        request = SMCRequest(**params) 
        request.exception = UpdateElementFailed
        return request.update().href


class Element(ElementBase):
    """
    Base element with common methods shared by inheriting classes.
    If stashing attributes on this class, be sure to prefix with
    an underscore to avoid having the attributes serialized when
    calling update.
    """
    href = ElementLocator()  # : href of this resource

    def __init__(self, name, **meta):
        if meta:
            meta.update(name=name)
        super(Element, self).__init__(**meta)
        self._name = name  # <str>

    @classproperty
    def objects(self):
        """
        Return a Collection Manager of element type

        :return: CollectionManager of the current element type
        :rtype CollectionManager
        """
        return smc.base.collection.CollectionManager(self)

    @classmethod
    def from_href(cls, href):
        """
        Return an instance of an Element based on the href

        :return: :py:class:`smc.base.model.Element` type
        """
        return ElementFactory(href) if href else None

    @classmethod
    def from_meta(cls, **meta):
        """
        Return an instance of an Element based on meta

        :param dict meta: raw dict meta from smc
        :return: :py:class:`smc.base.model.Element` type
        """
        return lookup_class(meta.get('type'))(**meta)

    @classmethod
    def get(cls, name, raise_exc=True):
        """
        Get the element by name. Does an exact match by element type.
        
        :param str name: name of element
        :param bool raise_exc: optionally disable exception. 
        :raises ElementNotFound: if element does not exist
        :return: :py:class:`smc.base.model.Element` type
        """
        element = cls.objects.filter(name, exact_match=True).first() if name \
            is not None else None
        if not element and raise_exc:
            raise ElementNotFound('Cannot find specified element: %s, type: %s' %
                (name, cls.__name__))
        return element 
        
    @classmethod
    def get_or_create(cls, filter_key=None, **kwargs):
        """
        Convenience method to retrieve an Element or create if it does not
        exist. If an element does not have a `create` classmethod, then it
        is considered read-only and the request will be redirected to :meth:`~get`.
        Any keyword arguments passed except the optional filter_key
        will be used in a create() call. If filter_key is provided, this
        should define an attribute and value to use for an exact match on
        the element. Valid attributes are ones required on the elements
        ``create`` method or can be viewed by the elements class docs.
        If no filter_key is provided, the name field will be used to
        find the element.
        ::

            >>> Network.get_or_create(
                    filter_key={'ipv4_network': '123.123.123.0/24'},
                    name='mynetwork',
                    ipv4_network='123.123.123.0/24')
            Network(name=mynetwork)

        The kwargs should be used to satisfy the elements ``create``
        classmethod parameters to create in the event it cannot be found.

        :param dict filter_key: filter key represents the data attribute and
            value to use to find the element. If none is provided, the name
            field will be used.
        :param kwargs: keyword arguments mapping to the elements ``create``
            method.
        :raises CreateElementFailed: could not create element with reason
        :raises ElementNotFound: if read-only element does not exist
        :return: element instance by type
        :rtype: Element
        """
        if not hasattr(cls, 'create'):
            return cls.get(kwargs.get('name'))
        elif 'name' not in kwargs:
            raise ElementNotFound('Name field is a required parameter '
                'for all create type operations on an element')

        if filter_key:
            elements = cls.objects.filter(**filter_key)
            element = elements.first()
            if not element:
                element = cls.create(**kwargs)
        else:
            try:
                element = cls.get(kwargs.get('name'))
            except ElementNotFound:
                element = cls.create(**kwargs)
        
        return element

    @classmethod
    def update_or_create(cls, filter_key=None, **kwargs):
        """
        Update or create the element. If the element exists, update
        it using the kwargs provided if the provided kwargs are new. Note
        that when checking kwargs against attributes, only string values are
        compared. Lists and dicts are automatically merged.
        If an element does not have a `create` classmethod, then it
        is considered read-only and the request will be redirected to
        :meth:`~get`. Provide a ``filter_key`` dict key/value if you want to
        match the element by a specific attribute and value. If no
        filter_key is provided, the name field will be used to find the
        element.
        ::

            >>> host = Host('kali')
            >>> print(host.address)
            12.12.12.12
            >>> host = Host.update_or_create(name='kali', address='10.10.10.10')
            >>> print(host, host.address)
            Host(name=kali) 10.10.10.10

        :param dict filter_key: filter key represents the data attribute and
            value to use to find the element. If none is provided, the name
            field will be used.
        :param kwargs: keyword arguments mapping to the elements ``create``
            method.
        :raises CreateElementFailed: could not create element with reason
        :raises ElementNotFound: if read-only element does not exist
        :return: element instance by type
        :rtype: Element
        """
        if not hasattr(cls, 'create'):
            return cls.get(kwargs.get('name'))
        elif 'name' not in kwargs:
            raise ElementNotFound('Name field is a required parameter '
                'for all create type operations on an element')
        
        element = None
        if filter_key:
            elements = cls.objects.filter(**filter_key)
            if elements.exists():
                element = elements.first()
        else:
            try:
                element = cls.get(kwargs.get('name'))
            except ElementNotFound:
                element = None

        if element: 
            params = {}
            for key, value in kwargs.items():
                value = value() if callable(value) else value
                val = getattr(element, key, None)
                if isinstance(val, (string_types, int)):
                    if val != value:
                        params[key] = value
                else:
                    params[key] = value
            
            if params:
                element.update(**params)
        else:
            params = {k: v() if callable(v) else v
                      for k, v in kwargs.items()}
            element = cls.create(**params)

        return element

    @property
    def name(self):
        """
        Name of element
        """
        return bytes_to_unicode(self._name)

    @property
    def comment(self):
        """
        Comment for element
        """
        return self.data.get('comment', None)

    @comment.setter
    def comment(self, comment):
        self.data['comment'] = comment

    def rename(self, name):
        """
        Rename this element.

        :param str name: new name of element
        :raises UpdateElementFailed: update failed with reason
        :return: None
        """
        self.update(name=name)

    def add_category(self, category):
        """
        Category Tags are used to characterize an element by a type
        identifier. They can then be searched and returned as a group
        of elements. If the category tag specified does not exist, it
        will be created. This change will take effect immediately.

        :param list tags: list of category tag names to add to this
            element
        :type tags: list(str)
        :raises ElementNotFound: Category tag element name not found
        :return: None

        .. seealso:: :class:`smc.elements.other.Category`
        """
        assert isinstance(category, list), 'Category input was expecting list.'
        from smc.elements.other import Category
        for tag in category:
            category = Category(tag)
            try:
                category.add_element(self.href)
            except ElementNotFound:
                Category.create(name=tag)
                category.add_element(self.href)

    @property
    def categories(self):
        """
        Search categories assigned to this element
        ::

            >>> from smc.elements.network import Host
            >>> Host('kali').categories
            [Category(name=foo), Category(name=foocategory)]

        :return: list :py:class:`smc.elements.other.Category`
        """
        return [Element.from_meta(**tag)
                for tag in self.make_request(
                    resource='search_category_tags_from_element')]

    def export(self, filename='element.zip'):
        """
        Export this element.

        Usage::

            engine = Engine('myfirewall')
            extask = engine.export(filename='fooexport.zip')
            while not extask.done():
                extask.wait(3)
            print("Finished download task: %s" % extask.message())
            print("File downloaded to: %s" % extask.filename)

        :param str filename: filename to store exported element
        :raises TaskRunFailed: invalid permissions, invalid directory, or this
            element is a system element and cannot be exported.
        :return: DownloadTask
        
        .. note:: It is not possible to export system elements
        """
        from smc.administration.tasks import DownloadTask, TaskRunFailed
        task = self.make_request(
            TaskRunFailed,
            method='create',
            resource='export',
            filename=filename)

        return DownloadTask(
            filename=filename, task=task
        )

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
                for ref in self.make_request(
                    method='create',
                    href=href,
                    json={'value': self.href})]

    @property
    def history(self):
        """
        .. versionadded:: 0.5.7
            Requires SMC version >= 6.3.2
        
        Obtain the history of this element. This will not chronicle every
        modification made over time, but instead a current snapshot with
        historical information such as when the element was created, by
        whom, when it was last modified and it's current state.
        
        :raises ResourceNotFound: If not running SMC version >= 6.3.2
        :rtype: History
        """
        from smc.core.resource import History
        return History(**self.make_request(resource='history'))
        
    def duplicate(self, name):
        """
        .. versionadded:: 0.5.8
            Requires SMC version >- 6.3.2
        
        Duplicate this element. This is a shortcut method that will make
        a direct copy of the element under the new name and type.
        
        :param str name: name for the duplicated element
        :raises ActionCommandFailed: failed to duplicate the element
        :return: the newly created element
        """
        dup = self.make_request(
            method='update',
            raw_result=True,
            resource='duplicate',
            params={'name': name})
        return type(self)(name=name, href=dup.href, type=type(self).typeof)
       
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

    @property
    def name(self):
        return self._meta.name if self._meta else None

    @property
    def href(self):
        return self._meta.href if self._meta else None

    def __unicode__(self):
        return u'{0}(name={1})'.format(self.__class__.__name__, self.name)

    def __repr__(self):
        return str(self)


def lookup_class(typeof, default=Element):
    cls = ElementMeta._map.get(typeof, None)
    if cls is None: # Create a dynamic class from meta type field
        attrs = {'typeof': typeof}
        # There are multiple entry points for specific aliases
        # that should derive from the smc.elements.network.Alias
        # class so it has access to Alias class methods like ``resolve``.
        if 'alias' in typeof:
            default = ElementMeta._map.get('alias')
        cls_name = '{0}Dynamic'.format(typeof.title())
        return type(cls_name.replace('_',''), (default,), attrs)
        
    return ElementMeta._map.get(typeof, default)


class Meta(namedtuple('Meta', 'name href type')):
    """
    Internal namedtuple used to store top level element information. When
    doing base level searches, SMC API will return only meta data for the
    element that has name, href and type.
    Meta has the same data structure returned from
    :py:func:`smc.actions.search.element_info_as_json`
    """
    def __new__(cls, href, name=None, type=None):  # @ReservedAssignment
        return super(Meta, cls).__new__(cls, name, href, type)
