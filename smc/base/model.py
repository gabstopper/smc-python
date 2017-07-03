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
                                data = SimpleElement()
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
import smc.base.collection
from smc.base.decorators import cached_property, exception
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


def load_element(href, only_etag=False):
    """
    Return an instance of a SimpleElement used
    as a cache for the element
    """
    result = prepared_request(
        FetchElementFailed,
        href=href
        ).read()
    if only_etag:
        return result.etag
    return SimpleElement(
        etag=result.etag, **result.json)


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
        e.data = SimpleElement(
            etag=element.etag, **element.json)
        return e


class SimpleElement(dict):
    """
    Basic container for retrieved element. Can be inserted
    where a cached copy is needed. Also provides methods to
    retrieve element links and json by link name
    """
    def __init__(self,*arg,**kw):
        self._etag = kw.pop('etag', None)
        super(SimpleElement, self).__init__(*arg, **kw)

    def etag(self, href):
        """
        ETag can be None if a subset of element json is using
        this container, such as the case with Routing.
        """
        if self and self._etag is None:
            self._etag = load_element(href, only_etag=True)
        return self._etag

    def get_link(self, rel):
        """
        Return link for specified resource
        """
        for link in self['link']:
            if link.get('rel') == rel:
                return link['href']
        raise ResourceNotFound('Resource requested: %r is not available '
                               'on this element.' % rel)

    def get_json(self, res):
        """
        Provided the link, return the resources raw json
        """
        return prepared_request(
            FetchElementFailed,
            href=self.get_link(res)).read().json


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

    @cached_property
    def data(self):
        return load_element(self.href)

    @property
    def etag(self):
        return self.data.etag(self.href)

    def __getattr__(self, key):
        if key not in ['typeof']:
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

        json = self.data    # Get element data
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

        return prepared_request(
            UpdateElementFailed,
            **params
            ).update().href


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
        elements ``create`` method or can be viewed by the elements class
        docs. If no filter_key is provided, the name field will be used to
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
        :return: element instance by type
        :rtype: Element
        """
        if filter_key:
            elements = cls.objects.filter(**filter_key)
            if elements.exists():
                return elements.first()
            element = cls.create(**kwargs)
        else:
            try:
                element = cls(
                    kwargs.get('name')); element.href
            except ElementNotFound:
                element = cls.create(**kwargs)

        return element

    @classmethod
    def update_or_create(cls, filter_key=None, **kwargs):
        """
        Update or create the element. If the element exists, update
        it using the kwargs provided, otherwise create new. Provide a
        ``filter_key`` dict key/value if you want to match the element
        by a specific attribute and value. If no filter_key is provided,
        the name field will be used to find the element.
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
        :return: element instance by type
        :rtype: Element
        """
        element = None
        if filter_key:
            elements = cls.objects.filter(**filter_key)
            if elements.exists():
                element = elements.first()
        else:
            try:
                element = cls(
                    kwargs.get('name')); element.href
            except ElementNotFound:
                element = None

        params = {k: v() if callable(v) else v
                  for k, v in kwargs.items()}

        if element:
            element.update(**params)
        else:
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
                for tag in self.data.get_json(
                    'search_category_tags_from_element')]

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
        :raises ActionCommandFailed: invalid permissions, invalid directory..
        :return: DownloadTask
        """
        from smc.administration.tasks import DownloadTask
        try:
            task = prepared_request(
                ActionCommandFailed,
                href=self.data.get_link('export'),
                filename=filename
                ).create().json

            return DownloadTask(
                filename=filename, task=task
            )

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
