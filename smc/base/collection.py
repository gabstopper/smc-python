"""
Collections module provides interfaces to obtain resources from this API
and provides searching mechanisms to auto-load resources into the
correct class type.

See :ref:`collection-reference-label` for examples on search capabilities.
"""
from smc import session
import smc.base.model
from smc.api.exceptions import FetchElementFailed, UnsupportedEntryPoint


class SubElementCollection(object):
    """
    Collection class providing an interface to iterate sub
    elements referenced as a resource. It also provides
    a proxy to methods that require the base collection href
    before an actual instance is created. References that return
    this collection type will always have an ``all()`` method
    and will be iterable.
    """

    def __init__(self, href, cls):
        self.href = href
        self.cls = cls

    def __iter__(self):
        for item in smc.base.model.prepared_request(
                FetchElementFailed,
                href=self.href
        ).read().json:
            yield self.cls(**item)

    def all(self):
        """
        Generator returning collection for sub element
        types. Return full contents as list or iterate through
        each.
        """
        return iter(self)


def sub_collection(href, cls):
    return type(
        cls.__name__, (SubElementCollection,), {})(href, cls)


def create_collection(href, cls):
    """
    This collection type inserts a 'create' method into the collection.
    This will proxy to the sub elements create method while restricting
    access to other attributes that woulnd't be initialized yet.
    """

    def create(self, *args, **kwargs):
        func = getattr(self.cls, 'create')
        return func(self.cls(href=href), *args, **kwargs)  # Proxy to instance

    create.__doc__ = cls.create.__doc__
    create.__name__ = cls.create.__name__
    return type(
        cls.__name__, (SubElementCollection,), {'create': create}
    )(href, cls)


class ElementCollection(object):
    """
    ElementCollection is generated dynamically from the
    connection manager and provides methods to obtain
    data from the SMC.
    """

    def __init__(self, **params):
        self._params = params

    def __iter__(self):
        limit = self._params.pop('limit', None)

        count = 0
        for item in self.items():
            yield smc.base.model.Element.from_meta(**item)

            # If the limit is set and has been reached, stop
            count += 1
            if limit is not None and count >= limit:
                return

    def items(self, **kwargs):
        # Return a collection
        try:
            return smc.base.model.prepared_request(
                FetchElementFailed,
                params=self._params,
            ).read().json
        except FetchElementFailed:
            return []

    def limit(self, count):
        """
        Limit provides the ability to limit the number of results returned
        from the collection.

        :param int count: number of records to page
        """
        self._params.update(limit=count)
        return self

    def all(self):
        """
        Retrieve all elements based on element type
        """
        self._params.pop('filter', None)
        return self

    def filter(self, filter, exact_match=False):  # @ReservedAssignment
        """
        Filter results for specific element type.

        :param str,list match_on: any parameter to attempt to match on.
            For example, if this is a service, you could match on service name
            'http' or ports of interest, '80'.
        :param bool exact_match: Whether match needs to be exact or not
        """
        self._params.update(filter=filter,
                            exact_match=exact_match)
        return self


class CollectionManager(object):
    """
    CollectionManager takes a class type as input and dynamically
    creates an ElementCollection for that class.

    :return: ElementCollection
    """

    def __init__(self, resource):
        self._cls = resource  # Class type

    def iterator(self, **kwargs):
        """
        Return an iterator from the collection manager. The connection
        manager itself is not iterable, you must call one of the
        methods below to get the collection

        :return: collection instance
        """
        cls_name = '{0}Collection'.format(self._cls.__name__)
        collection_cls = type(str(cls_name), (ElementCollection,), {})

        params = {'filter_context': self._cls.typeof}
        params.update(kwargs)
        return collection_cls(**params)

    def limit(self, count):
        return self.iterator(limit=count)
    limit.__doc__ = ElementCollection.limit.__doc__

    def all(self):
        return self.iterator()
    all.__doc__ = ElementCollection.all.__doc__

    def filter(self, match, exact_match=False):
        return self.iterator(filter=match,
                             exact_match=exact_match)
    filter.__doc__ = ElementCollection.filter.__doc__


class Search(object):
    """
    Search is an interface to the collection manager and provides a way to
    search for any object by type, as long as there is a valid entry point.
    The returned elements will be the defined class element if it exists,
    otherwise a dynamic class is returned deriving from
    :py:class:`smc.base.model.Element`

    :param str resource: name of resource, should be entry point name as found
        from called :func:`~Search.object_types()`
    """

    def __init__(self, resource):
        self._resource = resource.lower()  # Entry point as string
        self._validate(self._resource)  # Does entry point exist

    @property
    def objects(self):
        """
        A collection resource for the element selected. Search parameter
        generates a dynamic class that is registered in the global registry
        when it is created. It will only be registered once for any given
        search filter.
        If the class already exists (it's a pre-defined class of type Element),
        it will be retrieved from the registry.

        :return: :class:`~ElementCollection`
        """
        if smc.base.model.lookup_class(self._resource) is smc.base.model.Element:
            # Dynamic class of type Element for the Collection Manager
            # Class will be auto registered and then retrieved in the
            # collection
            attrs = {'typeof': self._resource}
            cls_name = '{0}Element'.format(
                self._resource.replace(',', '_').title())
            element_cls = type(str(cls_name), (smc.base.model.Element,), attrs)
        else:
            # Existing class of this type already exists, or it's a context
            # filter
            element_cls = smc.base.model.lookup_class(self._resource)
        # Return the collection from manager
        return CollectionManager(element_cls)

    def _validate(self, name):
        """
        Return dict of all entry points, dict will be {'href', 'rel', 'method'}
        This is used to filter out elements not bound to the elements URI.
        Note: Search filters may be combined by using comma, such as
        Search('router,host'), so split out and check each one.
        """
        extracted_filters = name.split(
            ',')  # Multiple filters, format: 'router,host'
        for filter_name in extracted_filters:
            if filter_name.lower() not in Search.object_types():
                raise UnsupportedEntryPoint(
                    'An entry point was specified that does '
                    'not exist. Entry point: %s' % filter_name)

    @staticmethod
    def object_types():
        """
        Return a list of all entry points within the SMC. These can be used to
        search for any elements using it's type::

            >>> list(Search('vpn').objects.all())
            [VPNPolicy(name=Amazon AWS), VPNPolicy(name=sg_vm_vpn)]

        And subsequently filtering as well::

            >>> list(Search('vpn').objects.filter('AWS'))
            [VPNPolicy(name=Amazon AWS)]

        :return: list of entry points
        """
        # Return all elements from the root of the API nested under elements
        # URI
        element_uri = str(
            '{}/{}/elements'.format(session.url, session.api_version))
        types = [element.get('rel')
                 for element in session.cache.get_all_entry_points()
                 if element.get('href').startswith(element_uri)]
        types.extend(list(_context_filters))
        return types


_context_filters = ('fw_clusters', 'engine_clusters', 'ips_clusters',
                    'layer2_clusters', 'network_elements', 'services',
                    'services_and_applications', 'tags', 'situations')
