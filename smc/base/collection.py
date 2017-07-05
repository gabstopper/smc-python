"""
Collections module provides interfaces to obtain resources from this API
and provides searching mechanisms to auto-load resources into the
correct class type.

See :ref:`collection-reference-label` for examples on search capabilities.
"""
import re
import copy
from itertools import islice
from smc import session
import smc.base.model
from smc.base.decorators import cached_property
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


def _strip_metachars(val):
    """
    When a filter uses a / or - in the search, only the elements
    name and comment field is searched. This can cause issues if
    searching a network element, i.e. 1.1.1.0/24 where the /24 portion
    is not present in the name and only the elements ipv4_network
    attribute. If exact_match is not specified, strip off the /24
    portion. Queries of this nature should instead use a kw filter
    of: ipv4_network='1.1.1.0/24'.
    """
    ignore_metachar = r'(.+)([/-].+)'
    match = re.search(ignore_metachar, str(val))
    if match:
        left_half = match.group(1)
        return left_half
    return val


class ElementCollection(object):
    """
    ElementCollection is generated dynamically from the connection 
    manager and provides methods to obtain data from the SMC. Filters
    can be chained together to generate more complex queries. Each time
    a filter is added, a clone is returned to preserve the parent query
    parameters.
    
    Chaining filters do not affect the parent iterator::
    
        >>> iterator = Host.objects.iterator()    <-- Obtain iterator from CollectionManager
        >>> query1 = iterator.filter('10.10.10.1')
        >>> query1._params, query1._iexact
        ({'filter': '10.10.10.1', 'exact_match': False, 'filter_context': 'router'}, None)
        >>> query2 = query1.limit(2)
        >>> query2._params, query2._iexact
        ({'filter': '10.10.10.1', 'exact_match': False, 'filter_context': 'router', 'limit': 2}, None)
        >>> query3 = query2.filter(address='10.10.10.1')
        >>> query3._params, query3._iexact
        ({'filter': '10.10.10.1', 'exact_match': False, 'filter_context': 'router', 'limit': 2}, {'address': '10.10.10.1'})
        
    
    Searcb operations can access a collection directly through chained syntax::
    
        >>> for router in Router.objects.filter('192.168'):
        ...   print(router)
        ... 
        Router(name=router-192.168.19.241)
        Router(name=router-192.168.21.241)
        Router(name=router-192.168.5.241)
        Router(name=router-192.168.15.241)
        
    Adding additional filtering via kwargs::
    
        >>> print(list(Router.objects.filter(address='10.10.10.1')))
        [Router(name=Router-10.10.10.1)]

    Checking if items from the query exist before accessing::
    
        >>> query1 = iterator.filter('10.10.10.1')
        >>> if query1.exists():
        ...   list(query1.all())
        ... 
        [Router(name=Router-110.10.10.10), Router(name=Router-10.10.10.10), Router(name=Router-10.10.10.1)]
    
    Helper methods ``first``, ``last`` and ``exists`` are provided to simplify retrieving a
    result from the collection::
    
        >>> query1 = iterator.filter('10.10.10.1')
        >>> list(query1)
        [Router(name=Router-110.10.10.10), Router(name=Router-10.10.10.10), Router(name=Router-10.10.10.1)]
        >>> query1.first()
        Router(name=Router-110.10.10.10)
        >>> query1.last()
        Router(name=Router-10.10.10.1)
        >>> query1.count()
        3
        >>> query2 = query1.filter(address='10.10.10.1')  # change filter to kwarg
        >>> list(query2)
        [Router(name=Router-10.10.10.1)]

    .. note:: ``first``, ``last`` and ``exists`` do not perform filtering when using
        ``filter_key``. Results on filter(kwargs) are only done by retrieving the list of
        results or iterating.
    """
    def __init__(self, **params):
        self._params = params
        self._iexact = params.pop('iexact', None)

    def __iter__(self):
        
        limit = self._params.pop('limit', None)
        count = 0
        
        for item in self._list:
            element = smc.base.model.Element.from_meta(**item)
            if self._iexact:
                #if all([element.data.get(k) == v for k, v in self._iexact.items()]):
                if all(element.data.get(k) == v for k, v in self._iexact.items()):
                    yield element
                    count += 1
            else:
                yield element
                count += 1
                
            if limit and count >= limit:
                return
    
    @cached_property
    def _list(self):
        try:        
            _list = smc.base.model.prepared_request(
                FetchElementFailed,
                params=self._params,
                ).read().json
        except FetchElementFailed:
            _list = list()
        return _list  
    
    def _clone(self, **kwargs):
        """
        Create a clone of this collection. The only param in the
        initial collection is the filter context. Each chainable
        filter is added to the clone and returned to preserve
        previous iterators and their returned elements.
        
        :return: :class:`.ElementCollection`
        """
        params = copy.deepcopy(self._params)
        if self._iexact:
            params.update(iexact=self._iexact)
        params.update(**kwargs)
        clone = self.__class__(**params)
        return clone

    def limit(self, count):
        """
        Limit provides the ability to limit the number of results returned
        from the collection.

        :param int count: number of records to page
        :return: :class:`.ElementCollection`
        """
        return self._clone(limit=count)

    def all(self):
        """
        Retrieve all elements based on element type. When using the ``all``
        option, any filters are automatically removed.
        
        :return: :class:`.ElementCollection`
        """
        return self._clone()

    def filter(self, *filter, **kw):  # @ReservedAssignment
        """
        Filter results for specific element type.
            
        keyword arguments can be used to specify a match against the
        elements attribute directly. It's important to note that if the
        search filter contains a / or -, the SMC will only search the
        name and comment fields. Otherwise other key fields of an element
        are searched. In addition, SMC searches are a 'contains' search
        meaning you may return more results than wanted. Use a key word
        argument to specify the elements attribute and value expected.
        ::
            
            >>> list(Router.objects.filter('10.10.10.1'))
            [Router(name=Router-110.10.10.10), Router(name=Router-10.10.10.10), Router(name=Router-10.10.10.1)]
            >>> list(Router.objects.filter(address='10.10.10.1'))
            [Router(name=Router-10.10.10.1)]
    
        :param str filter: any parameter to attempt to match on.
            For example, if this is a service, you could match on service name
            'http' or ports of interest, '80'.
        :param bool exact_match: Whether match needs to be exact or not. An
            exact match is a case sensitive match.
        :param kw: keyword args can specify an attribute=value to use as an
            exact match against the elements attribute.
        :return: :class:`.ElementCollection`
        """
        iexact = None
        if filter:
            _filter = filter[0]
            
        exact_match = kw.pop('exact_match', False)
    
        if kw:
            _, value = next(iter(kw.items()))
            _filter = value
            iexact = kw
        
        if not exact_match:
            _filter = _strip_metachars(_filter)
        
        return self._clone(filter=_filter,
                           iexact=iexact,
                           exact_match=exact_match)
    
    def batch(self, num):
        """
        Iterator returning results in batches. When making more general queries
        that might have larger results, specify a batch result that should be
        returned with each iteration.
        
        :param int num: number of results per iteration
        :return: iterator holding list of results
        """
        self._params.pop('limit', None) # Limit and batch are mutually exclusive
        it = iter(self)
        while True:
            chunk = list(islice(it, num))
            if not chunk:
                return
            yield chunk
                
    def first(self):
        """
        Returns the first object matched or None if there is no
        matching object.
        ::
                
            >>> iterator = Host.objects.iterator()
            >>> c = iterator.filter('kali')
            >>> if c.exists():
            >>>    print(c.count())
            >>>    print(c.first())
            7
            Host(name=kali67)
        
        If results are not needed and you only 1 result, this can be called
        from the CollectionManager::
        
            >>> Host.objects.first()
            Host(name=SMC)
        
        :return: element or None
        """
        if self._list:
            return list(self)[0]
    
    def last(self):
        """
        Returns the last object matched or None if there is no
        matching object.
        ::
                
            >>> iterator = Host.objects.iterator()
            >>> c = iterator.filter('kali')
            >>> if c.exists():
            >>>    print(c.last())
            Host(name=kali-foo)
        
        :return: element or None
        """
        if self._list:
            return list(self)[-1]

    def exists(self):
        """
        Returns True if the query contains any results, and False
        if not. This is handy for checking existence without having
        to iterate.
        ::
            
            >>> host = Host.objects.filter('1.1.1.1')
            >>> if host.exists():
            ...   print(host.first())
            ... 
            Host(name=hax0r)
        
        :rtype: bool
        """
        if self._list:
            return True
        return False
            
    def count(self):
        """
        Return number of results
        
        :rtype: int
        """
        if self._list:
            return len(self._list)


class CollectionManager(object):
    """
    CollectionManager takes a class type as input and dynamically
    creates an ElementCollection for that class. To get an iterator
    object that can be re-used, obtain an iterator() from the
    manager::
    
        it = Host.objects.iterator()
        it.filter(....)
        ...

    :return: :class:`.CollectionManager`
    """

    def __init__(self, resource):
        self._cls = resource  # Class type

    def iterator(self, **kwargs):
        """
        Return an iterator from the collection manager. The iterator can
        be re-used to chain together filters, each chaining event will be
        it's own unique element collection.

        :return: :class:`ElementCollection`
        """
        cls_name = '{0}Collection'.format(self._cls.__name__)
        collection_cls = type(str(cls_name), (ElementCollection,), {})

        params = {'filter_context': self._cls.typeof}
        params.update(kwargs)
        return collection_cls(**params)
    
    def first(self):
        return self.iterator().first()
    first.__doc__ = ElementCollection.first.__doc__
    
    def batch(self, num):
        return self.iterator().batch(num)
    batch.__doc__ = ElementCollection.batch.__doc__
    
    def limit(self, count):
        return self.iterator(limit=count)
    limit.__doc__ = ElementCollection.limit.__doc__

    def all(self):
        return self.iterator()
    all.__doc__ = ElementCollection.all.__doc__

    def filter(self, *filter, **kw): # @ReservedAssignment
        iexact = None
        if filter:
            _filter = filter[0]
            
        exact_match = kw.pop('exact_match', False)
        if kw:
            _, value = next(iter(kw.items()))
            _filter = value
            iexact = kw

        if not exact_match:
            _filter = _strip_metachars(_filter)
        
        return self.iterator(filter=_filter,
                             iexact=iexact,
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
        types = [element.rel
                 for element in session.entry_points
                 if element.href.startswith(element_uri)]
        types.extend(list(_context_filters))
        return types


_context_filters = ('fw_clusters', 'engine_clusters', 'ips_clusters',
                    'layer2_clusters', 'network_elements', 'services',
                    'services_and_applications', 'tags', 'situations')
