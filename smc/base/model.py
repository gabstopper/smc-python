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
                                delete()
                                modify_attribute()
                                   |
                         ----------------------
                         |                    |
    Element (ElementBase)                     SubElement (ElementBase)
        |------------------------------------------------------|
      href = ElementLocator()                                href
      name                                                   name
      objects
      export()
      rename
      category_tags
      referenced_by
      ...

Classes that do not require state on retrieved json or provide basic
container functionality may inherit from object.
"""
from collections import namedtuple
import smc.compat as compat
import smc.base.collection
from smc.base.decorators import cached_property, exception
from smc.api.web import counters
from smc.api.common import SMCRequest, fetch_href_by_name, fetch_entry_point
from smc.api.exceptions import ElementNotFound, \
    CreateElementFailed, ModificationFailed, ResourceNotFound,\
    DeleteElementFailed, FetchElementFailed, ActionCommandFailed,\
    UpdateElementFailed
from smc.base.resource import with_metaclass, Registry
from .util import bytes_to_unicode, unicode_to_bytes, merge_dicts,\
    find_type_from_self
from .mixins import UnicodeMixin


@exception
def prepared_request(*exception, **kwargs):
    """
    Prepared request is a wrapper to allow an exception to
    be thrown to wrap the SMCResult. Exception is optional.
    If not provided, the SMCResult object is returned,
    otherwise it is only thrown if SMC reports an error.
    """
    return SMCRequest(**kwargs)


class classproperty(object):
    """
    Used for collection manager so objects can be accessed as a
    class property and also from the instance
    """

    def __init__(self, fget):
        self.fget = fget

    def __get__(self, instance, owner_cls):
        return self.fget(owner_cls)


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
        json=json
    ).create()
    if result.msg:
        raise CreateElementFailed(result.msg)

    return cls(json.get('name'),
               type=cls.typeof,
               href=result.href)


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
    makes it possible to access a link via self._resource.rel
    """

    def name(self, href):
        """
        Have the href, reverse call to get name of element
        """
        resource = prepared_request(
            FetchElementFailed,
            href=href
        ).read().json
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
        result = prepared_request(
            href=resource
        ).read()
        if result.msg:
            raise FetchElementFailed(result.msg)
        if as_smcresult:
            return result
        return result.json

    def __repr__(self):
        return "%s(id=%r)" % (self.__class__.__name__, id(self))

    def __getattr__(self, link):
        raise ResourceNotFound('Resource requested: %r is not '
                               'available on this element.' % link)


class Cache(object):
    """
    Cache is applied at the element level as a dynamic attribute and
    provides an interface to the elements raw data. Caching is also
    implemented on the dynamic attribute ``resource``. Resource provides
    a container for dotted access to a retrieved elements resource links.
    If an update is made to an element, the cache attribute can be
    deleted which will cause a refresh on subsequent access to that
    attribute (or through a reference to it).

    When an element is sent for modification, the cached ETag is used
    and an exception will be raised if the server side ETag has changed,
    requiring the request to be made again.
    """
    __slots__ = ('_cache', 'instance')

    def __init__(self, instance, json=None, etag=None):
        self.instance = instance
        if json is not None:
            self._cache = (etag, json)
        else:
            self._cache = None
    
    def __call__(self, *args, **kwargs):
        counters.update(cache=1)
        if self._cache is None or kwargs.get('force_refresh'):
            result = prepared_request(
                FetchElementFailed,
                href=self.instance.href
            ).read()
            self._cache = (result.etag, result.json)
            getattr(self.instance, '_resource')
        return self._cache

    @property
    def data(self):
        return self.__call__()[1]

    @property
    def etag(self):
        # Etag can be none if cache was manually set
        if self.__call__()[0] is None:
            etag = prepared_request(
                FetchElementFailed,
                href=self.instance.href
            ).read()
            self._cache = (etag.etag, self._cache[1])
        return self._cache[0]


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
    Once hydrated, original json is stored in instance._cache.

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
            self._meta = Meta(**meta_as_kw)
        else:
            self._meta = Meta(**meta) if meta else None

    def _add_cache(self, data, etag=None):
        self._cache = Cache(self, data, etag)
        
    @cached_property
    def _cache(self):
        return Cache(self)

    @cached_property
    def _resource(self):
        res = ElementResource()
        for link in self.data.get('link'):
            setattr(res, link.get('rel'), link.get('href'))
        return res
        
    @property
    def data(self):
        return self._cache.data

    @property
    def etag(self):
        """
        ETag for this element
        """
        return self._cache.etag

    def delete(self):
        """
        Delete the element

        :raises DeleteElementFailed: possible dependencies, record locked, etc
        :return: None
        """
        prepared_request(
            DeleteElementFailed,
            href=self.href,
            headers={'if-match': self.etag}
        ).delete()

    def update(self, *exception, **kwargs):
        """
        Update the existing element and clear the instance cache.
        Removing the cache will ensure subsequent calls requiring element
        attributes will force a new fetch to obtain the latest copy.
        
        If attributes are set via kwargs and instance attributes are also
        set, instance attributes are updated first, then kwargs. Typically
        you will want to use either instance attributes OR kwargs, not both.
        
        For kwargs, if attribute values are a list, you can pass
        'append_lists=True' to add to an existing list, otherwise overwrite
        (default: overwrite)
        
        If using attributes, the attribute value can be a callable and it
        will be evaluated and merged.
        
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
        
        instance_attr = {k: v() if callable(v) else v
                         for k, v in vars(self).items()
                         if not k.startswith('_')}
        
        if instance_attr:
            self.data.update(**instance_attr)
 
        # If kwarg settings are provided AND instance variables, kwargs
        # will overwrite collected instance attributes with the same name.
        if kwargs:
            append_lists = kwargs.pop('append_lists', False)
            merge_dicts(self.data, kwargs, append_lists)
        
        params.update(json=self.data)
        
        del self._cache
        
        # Remove attributes from instance if previously set
        if instance_attr:
            for attr in instance_attr.keys():
                delattr(self, attr)

        result = prepared_request(
            exception,
            **params
            ).update().href
        
        if name: # Reset instance name
            self._name = name
        
        return result
    
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
        :return: None
        """
        if self.data.get('system') is True:
            raise ModificationFailed(
                'Cannot modify system element: %s' % self.name)

        append_lists = kwargs.pop('append_lists', False)
        merge_dicts(self.data, kwargs, append_lists)
        self.update()
    
    def __getattr__(self, attr):
        if attr not in ['typeof']:
            try:
                return self.data[attr]
            except KeyError:
                pass
        raise AttributeError("%r object has no attribute %r"
            % (self.__class__, attr))            

class Element(ElementBase):
    """
    Base element with common methods shared by inheriting classes
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
        return ElementFactory(href)

    @classmethod
    def from_meta(cls, **meta):
        """
        Return an instance of an Element based on meta

        :param dict meta: raw dict meta from smc
        :return: :py:class:`smc.base.model.Element` type
        """
        return lookup_class(meta.get('type'))(**meta)

    @classmethod
    def get_or_create(cls, filter_key=None, **kwargs):
        """
        Convenience method to retrieve an Element or create if it does not
        exist. This is useful for network elements where you may know the
        value and type but not name of if it already exists. If filter_key
        is provided, this should define an attribute and value to use for an
        exact match on the element. Valid attributes are ones required on the
        elements ``create`` method or can be viewed by obtaining the element
        and examining the ``data`` attribute. If no filter_key is provided,
        the name field will be used to find the element.
        
        Example of getting an element of type Network::
        
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
        :return: element instance by type
        :rtype: Element
        """
        if filter_key:
            network = cls.objects.filter(**filter_key)
            if network.exists():
                return network.first()
            element = cls.create(**kwargs)
        else:
            try:
                element = cls(
                    kwargs.get('name')); element.href
            except ElementNotFound:
                element = cls.create(**kwargs)
        
        return element
    
    @property
    def name(self):
        """
        Name of element
        """
        if compat.PY3:
            return self._name
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
        will be created.
        
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
                for tag in
                prepared_request(
                    href=self._resource.search_category_tags_from_element
                ).read().json]

    def export(self, filename='element.zip', wait_for_finish=False):
        """
        Export this element

        :param str filename: filename to store exported element
        :param bool wait_for_finish: wait for update msgs (default: False)
        :raises ActionCommandFailed: invalid permissions, invalid directory..
        :return: generator yielding updates on progress, or [] if element
            cannot be exported, like for system elements
        """
        from smc.administration.tasks import Task, task_handler
        try:
            element = prepared_request(
                ActionCommandFailed,
                href=self._resource.export,
                filename=filename
                ).create()

            return task_handler(
                Task(**element.json),
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
    return Registry._registry.get(typeof, default)


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
