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
import collections
import smc.base.collection
from smc.compat import string_types
from smc.base.structs import NestedDict
from smc.base.decorators import cached_property, classproperty, exception,\
    create_hook, with_metaclass
from smc.api.common import SMCRequest, fetch_meta_by_name, fetch_entry_point
from smc.api.exceptions import ElementNotFound, \
    CreateElementFailed, ModificationFailed, ResourceNotFound,\
    DeleteElementFailed, FetchElementFailed, UpdateElementFailed,\
    UnsupportedEntryPoint
from .util import bytes_to_unicode, unicode_to_bytes, merge_dicts
from smc.base.mixins import RequestAction, UnicodeMixin
from smc.base.util import element_resolver


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
        result.json, etag=result.etag)


@create_hook
def ElementCreator(cls, json, **kwargs):
    """
    Helper method for creating elements. If the created element type is
    a SubElement class type, provide href value as kwargs since that class
    type does not have a direct entry point. This is a lazy load that will
    provide only the meta for the element. Additional attribute access
    will load the full data.

    :param Element,SubElement cls: class for creating
    :param dict json: json payload
    :param SMCException exception: exception class to override
    :return: instance of type Element with meta
    :rtype: Element
    """
    if 'exception' not in kwargs:
        kwargs.update(exception=CreateElementFailed)
    href = kwargs.pop('href') if 'href' in kwargs else cls.href
    
    result = SMCRequest(
        href=href,
        json=json,
        **kwargs).create()
    
    element = cls(
        name=json.get('name'),
        type=cls.typeof,
        href=result.href)
    
    if result.user_session.in_atomic_block:
        result.user_session.transactions.append(element)
    return element


def ElementFactory(href, smcresult=None, raise_exc=None):
    """
    Factory returns an object of type Element when only
    the href is provided.
    
    :param str href: string href to fetch
    :param SMCResult smcresult: optional SMCResult. If provided,
        the request fetch will be skipped
    :param Exception raise_exc: exception to raise if fetch
        failed
    """
    if smcresult is None:
        smcresult = SMCRequest(href=href).read()
    if smcresult.json:
        cache = ElementCache(smcresult.json, etag=smcresult.etag)
        typeof = lookup_class(cache.type)
        instance = typeof(
            name=cache.get('name'),
            href=href,
            type=cache.type)
        instance.data = cache
        return instance
    if raise_exc and smcresult.msg:
        raise raise_exc(smcresult.msg)


class ElementCache(NestedDict):
    def __init__(self, data=None, **kw):
        self._etag = kw.pop('etag', None)
        super(ElementCache, self).__init__(data=
            data if data else {})

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
    
    @property
    def type(self):
        for link in self.get('link', []):
            if link.get('rel') == 'self':
                return link.get('type')
    
    def get_link(self, rel):
        """
        Return link for specified resource
        """
        if rel in self.links:
            return self.links[rel]
        raise ResourceNotFound('Resource requested: %r is not available '
            'on this element.' % rel)
        

class ElementRef(object):
    """
    Descriptor to allow get/set operations on an element referenced in
    an Element.
    """
    def __init__(self, attr):
        self.attr = attr
    def __set__(self, obj, value):
        obj.data[self.attr] = element_resolver(value)
        return obj
    def __get__(self, obj, owner):
        if obj is None:
            return self
        return Element.from_href(obj.data.get(self.attr))


class ElementList(object):
    """
    Descriptor defining a list of hrefs that can be resolved to an
    Element dynamically.
    """
    def __init__(self, attr): 
        self.attr = attr

    def __get__(self, obj, cls):
        if obj is None:
            return self 
        return [Element.from_href(href) for href in obj.data.get(self.attr, [])]
        

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
        if instance is not None and instance._meta:
            return instance._meta.href
        if hasattr(cls, 'typeof'):
            if instance is not None:
                element = fetch_meta_by_name(
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
                try:
                    element = fetch_entry_point(cls.typeof)
                except UnsupportedEntryPoint as e:
                    raise ElementNotFound(e)
                return element
        else: 
            raise ElementNotFound('This class does not have the required attribute '
                'and cannot be referenced directly, type: {}'.format(instance))


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
    
    @classmethod
    def from_href(cls, href):
        """
        Return an instance of an Element based on the href

        :rtype: Element
        """
        return ElementFactory(href) if href else None

    @classmethod
    def from_meta(cls, **meta):
        """
        Return an instance of an Element based on meta

        :param dict meta: raw dict meta from smc
        :rtype: Element
        """
        return lookup_class(meta.get('type'))(**meta)
    
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
        state.update(data=self.data.data)
        if '_cache' in state:
            del state['_cache']
        return state

    def __setstate__(self, state):
        if 'data' in state:
            cache = state.pop('data')
            state.update(data=ElementCache(cache))
        self.__dict__.update(state)
    
    def __getattr__(self, key):
        if 'typeof' not in key and key in self.data:
            return self.data[key]
        raise AttributeError("%r object has no attribute %r"
            % (self.__class__, key))
    
    def __unicode__(self):
        return u'{0}(name={1})'.format(self.__class__.__name__, self.name)

    def __repr__(self):
        return str(self)
    
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
        
        Calling update() with no args will assume the element has already
        been modified directly and the `data` cache will be used to update.
        You can also override the following attributes: href, etag, json and
        params. If json is sent, it is expected to the be a complete payload
        to satisfy the update.
        
        For kwargs, if attribute values are a list, you can pass
        'append_lists=True' to add to an existing list, otherwise overwrite
        the existing (default: overwrite)

        .. seealso:: To see different ways to utilize this method for updating,
            see: :ref:`update-elements-label`.

        :param exception: pass a custom exception to throw if failure
        :param kwargs: optional kwargs to update request data to server.
        :raises ModificationFailed: raised if element is tagged as System element
        :raises UpdateElementFailed: failed to update element with reason
        :return: href of the element modified
        :rtype: str
        """
        if self.data.get('system', False):
            raise ModificationFailed('Cannot modify system element: %s' % self.name)
        
        if not exception:
            exception = UpdateElementFailed
        else:
            exception = exception[0]

        params = {
            'href': self.href,
            'etag': self.etag
        }
        params.update(params=kwargs.pop('params', {})) # URI strings
        
        if 'href' in kwargs:
            params.update(href=kwargs.pop('href'))

        if 'etag' in kwargs:
            params.update(etag=kwargs.pop('etag'))

        json = kwargs.pop('json', self.data) #if 'json' in kwargs else self.data
        name = kwargs.get('name', json.get('name'))
        
        del self.data       # Delete the cache before processing attributes

        # If kwarg settings are provided AND instance variables, kwargs
        # will overwrite collected instance attributes with the same name.
        if kwargs:
            append_lists = kwargs.pop('append_lists', False)
            merge_dicts(json, kwargs, append_lists)

        params.update(json=json)

        request = SMCRequest(**params) 
        request.exception = exception
        result = request.update()
        
        if name: # Reset instance name
            self._meta = Meta(name=name, href=self.href, type=self._meta.type)
            self._name = name
        
        return result.href


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
    
    def __eq__(self, other):
        if isinstance(other, Element):
            return self.name == other.name and self.typeof == other.typeof
        return False
    
    def __ne__(self, other):
        return not self == other
    
    def __hash__(self):
        return hash((self.name, self.typeof))

    @classproperty
    def objects(self):
        """
        Return a Collection Manager of element type

        :return: CollectionManager of the current element type
        :rtype CollectionManager
        """
        return smc.base.collection.CollectionManager(self)

    @classmethod
    def get(cls, name, raise_exc=True):
        """
        Get the element by name. Does an exact match by element type.
        
        :param str name: name of element
        :param bool raise_exc: optionally disable exception. 
        :raises ElementNotFound: if element does not exist
        :rtype: Element
        """
        element = cls.objects.filter(name, exact_match=True).first() if \
            name is not None else None
        if not element and raise_exc:
            raise ElementNotFound('Cannot find specified element: %s, type: '
                '%s' % (name, cls.__name__))
        return element 
        
    @classmethod
    def get_or_create(cls, filter_key=None, with_status=False, **kwargs):
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
        :param bool with_status: if set to True, a tuple is returned with
            (Element, created), where the second tuple item indicates if
            the element has been created or not.
        :raises CreateElementFailed: could not create element with reason
        :raises ElementNotFound: if read-only element does not exist
        :return: element instance by type
        :rtype: Element
        """
        was_created = False
        if 'name' not in kwargs:
            raise ElementNotFound('Name field is a required parameter '
                'for all create or update_or_create type operations on an element')

        if filter_key:
            elements = cls.objects.filter(**filter_key)
            element = elements.first() if elements.exists() else None
        else:
            try:
                element = cls.get(kwargs.get('name'))
            except ElementNotFound:
                if not hasattr(cls, 'create'):
                    raise CreateElementFailed('%s: %r not found and this element '
                        'type does not have a create method.' %
                        (cls.__name__, kwargs['name']))
                element = None
        
        if not element:
            params = {k: v() if callable(v) else v
                      for k, v in kwargs.items()}
            try:
                element = cls.create(**params)
                was_created = True
            except TypeError:
                raise CreateElementFailed('%s: %r not found and missing '
                    'constructor arguments to properly create.' %
                    (cls.__name__, kwargs['name']))

        if with_status:
            return element, was_created
        return element
    
    @classmethod
    def update_or_create(cls, filter_key=None, with_status=False, **kwargs):
        """
        Update or create the element. If the element exists, update it using the
        kwargs provided if the provided kwargs after resolving differences from
        existing values. When comparing values, strings and ints are compared
        directly. If a list is provided and is a list of strings, it will be 
        compared and updated if different. If the list contains unhashable elements,
        it is skipped. To handle complex comparisons, override this method on
        the subclass and process the comparison seperately.
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
        :param bool with_status: if set to True, a 3-tuple is returned with
            (Element, modified, created), where the second and third tuple
            items are booleans indicating the status
        :raises CreateElementFailed: could not create element with reason
        :raises ElementNotFound: if read-only element does not exist
        :return: element instance by type
        :rtype: Element
        """
        updated = False
        # Providing this flag will return before updating and require the calling
        # class to call update if changes were made.
        defer_update = kwargs.pop('defer_update', False)
        if defer_update:
            with_status = True
        
        element, created = cls.get_or_create(filter_key=filter_key, with_status=True, **kwargs)
        if not created:
            for key, value in kwargs.items():
                # Callable, Element or string
                if callable(value):
                    value = value()
                elif isinstance(value, Element):
                    value = value.href
                # Retrieve the 'type' of instance attribute. This is used to
                # serialize attributes that resolve href's to elements. It
                # provides a common structure but also prevents the fetching
                # of the href to element when doing an equality comparison
                attr_type = getattr(type(element), key, None)
                if isinstance(attr_type, ElementRef):
                    attr_name = getattr(attr_type, 'attr', None)
                    if element.data.get(attr_name) != value:
                        element.data[attr_name] = value
                        updated = True
                    continue
                elif isinstance(attr_type, ElementList):
                    value_hrefs = element_resolver(value) # Resolve the elements to href
                    attr_name = getattr(attr_type, 'attr', None)
                    if set(element.data.get(attr_name, [])) != set(value_hrefs):
                        element.data[attr_name] = value_hrefs
                        updated = True
                    continue
                
                # Type is not 'special', therefore we are expecting only strings,
                # integer types or list of strings. Complex data structures
                # will be handled later through encapsulation and __eq__, __hash__
                # for comparison. The keys value type here is going to assume the
                # provided value is of the right type as the key may not necessarily
                # exist in the cached json.
                if isinstance(value, (string_types, int)): # also covers bool
                    val = getattr(element, key, None)
                    if val != value:
                        element.data[key] = value
                        updated = True
                elif isinstance(value, list) and all(isinstance(s, string_types) for s in value):
                    # List of simple strings (assuming the attribute is also!)
                    if set(value) ^ set(element.data.get(key, [])):
                        element.data[key] = value
                        updated = True
                # Complex lists, objects, etc will fall down here and be skipped.
                # To process these, provide defer_update=True, override update_or_create,
                # process the complex object deltas and call update()
            
            if updated and not defer_update:
                element.update()
        
        if with_status:
            return element, updated, created
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

        :rtype: list(Category)
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
        from smc.administration.tasks import Task
        return Task.download(self, 'export', filename)

    @property
    def referenced_by(self):
        """
        Show all references for this element. A reference means that this
        element is being used, for example, in a policy rule, as a member of
        a group, etc.

        :return: list referenced elements
        :rtype: list(Element)
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
            Requires SMC version >= 6.3.2
        
        Duplicate this element. This is a shortcut method that will make
        a direct copy of the element under the new name and type.
        
        :param str name: name for the duplicated element
        :raises ActionCommandFailed: failed to duplicate the element
        :return: the newly created element
        :rtype: Element
        """
        dup = self.make_request(
            method='update',
            raw_result=True,
            resource='duplicate',
            params={'name': name})
        return type(self)(name=name, href=dup.href, type=type(self).typeof)

        
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


class UserElement(ElementBase):
    """
    User element mixin for LDAP of Internal Domains.
    """
    href = ElementLocator()
    
    def __init__(self, name, **meta):
        if meta:
            meta.update(name=name)
        super(UserElement, self).__init__(**meta)
        self._name = name  # <str>
    
    @property
    def name(self):
        return bytes_to_unicode(self._name)

    @property
    def unique_id(self):
        """
        Fully qualified unique DN for this entry
        
        :rtype: str
        """
        return self.data.get('unique_id')
    
    def __eq__(self, other):
        if isinstance(other, UserElement):
            if self.unique_id == other.unique_id:
                return True
        return False
    
    def __ne__(self, other):
        return not self.__eq__(other)


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


class Meta(collections.namedtuple('Meta', 'name href type')):
    """
    Internal namedtuple used to store top level element information. When
    doing base level searches, SMC API will return only meta data for the
    element that has name, href and type.
    Meta allows elements to be lazy loaded as they can be fetched to validate
    their existence without fetching the payload from the href location.
    """
    def __new__(cls, name=None, href=None, type=None):  # @ReservedAssignment
        return super(Meta, cls).__new__(cls, name, href, type)
