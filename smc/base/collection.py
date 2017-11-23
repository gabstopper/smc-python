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
from smc.base.decorators import cached_property, classproperty
from smc.api.exceptions import FetchElementFailed, InvalidSearchFilter


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
    This collection type inserts a ``create`` method into the collection.
    This will proxy to the sub elements create method while restricting
    access to other attributes that wouldn't be initialized yet.
    
    .. py:method:: create(...)
    
        Create method is inserted dynamically for the collection class type.
        See the class types documentation, or use help().

    :rtype: SubElementCollection    
    """
    instance = cls(href=href)
    meth = getattr(instance, 'create')
    return type(
         cls.__name__, (SubElementCollection,), {'create': meth})(href, cls)


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

    .. note:: ``exists`` does not perform filtering when using ``filter_key``.
        Results on filter(kwargs) are only done by retrieving the list of
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
            params = {k:self._params[k] for k in self._params if 'href' not in k}
            _list = smc.base.model.prepared_request(
                FetchElementFailed,
                href=self._params.get('href'),
                params=params,
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
        :param bool exact_match: Can be passed as a keyword arg. Specifies whether
            the match needs to be exact or not (default: False)
        :param bool case_sensitive: Can be passed as a keyword arg. Specifies
            whether the match is case sensitive or not. (default: True) 
        :param kw: keyword args can specify an attribute=value to use as an
            exact match against the elements attribute.
        :return: :class:`.ElementCollection`
        """
        iexact = None
        if filter:
            _filter = filter[0]
            
        exact_match = kw.pop('exact_match', False)
        case_sensitive = kw.pop('case_sensitive', True)
        
        if kw:
            _, value = next(iter(kw.items()))
            _filter = value
            iexact = kw
        
        if not exact_match:
            _filter = _strip_metachars(_filter)
        
        return self._clone(
            filter=_filter,
            iexact=iexact,
            exact_match=exact_match,
            case_sensitive=case_sensitive)
    
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
            self._params.update(limit=1)
            if 'filter' not in self._params:
                return list(self)[0]
            else: # Filter may not return results
                result = list(self)
                if result:
                    return result[0]
    
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
            self._params.update(limit=1)
            if 'filter' not in self._params:
                return list(self)[-1]
            else: # Filter may not return results
                result = list(self)
                if result:
                    return result[-1]

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
        case_sensitive = kw.pop('case_sensitive', True)
        
        if kw:
            _, value = next(iter(kw.items()))
            _filter = value
            iexact = kw
        
        if not exact_match:
            _filter = _strip_metachars(_filter)
        
        return self.iterator(
            filter=_filter,
            iexact=iexact,
            exact_match=exact_match,
            case_sensitive=case_sensitive)

    filter.__doc__ = ElementCollection.filter.__doc__


CONTEXTS = frozenset(['fw_clusters', 'engine_clusters', 'ips_clusters',
                      'layer2_clusters', 'network_elements', 'services',
                      'services_and_applications', 'tags', 'situations'])

    
class Search(ElementCollection):
    """
    .. versionchanged:: 0.5.6
        Added entry_point and context_filter chaining to make search syntax
        the same as direct element object searches.
    
    Search extends ElementCollection and provides a way to search for any object
    by type, as long as there is a valid entry point. Syntax for general searches
    are the same as initializing a search by a specific element::
    
        Search.object_types()    # Get all available search entry points
        ...
        Search.objects.entry_point('ips_alert') # Search for IPS Alerts
        ...
        Search.objects.entry_point('network').filter('1.1.1') # Network with filter
        ...
        Search.objects.context_filter('engine_clusters') # by context filter
        ...
        Search.objects.filter('2.2.2.2') # All element types with filter
        ...
        Search.objects.entry_point('router,host')) # Search using multiple element types
        ...
        Search.objects.entry_point('router,host').filter('2.2.2.2') # with filter
        
    Search also provides convenience shortcuts to find duplicate and unused elements::
    
        Search.objects.unused()
        ...
        Search objects.duplicates()
    
    If searching a broad range of elements, it is advisable to return results in
    batches::
    
        for batch in Search.objects.batch(100): # All elements search
            ...
    
    .. note:: If no entry point is specified, the search is done at the 'elements'
        entry point which contains all SMC elements. It is recommended
        to use ``filter`` and possibly ``batch`` to control the result set.
    """

    def __init__(self, **params):
        super(Search, self).__init__(**params)
    
    @classproperty
    def objects(self):
        """
        :rtype: SearchE
        """
        return self()
    
    def entry_point(self, entry_point):
        """
        Provide an entry point for element types to search.
        
        :param str entry_point: valid entry point. Use `~object_types()`
            to find all available entry points.
        """
        if len(entry_point.split(',')) == 1:
            self._params.update(
                href=session.entry_points.get(entry_point))
            return self
        else:
            self._params.update(
                filter_context=entry_point)
            return self

    def context_filter(self, context):
        """
        Provide a context filter to search.
        
        :param str context: Context filter by name
        """
        if context in CONTEXTS:
            self._params.update(filter_context=context)
            return self
        raise InvalidSearchFilter(
            'Context filter %r was invalid. Available filters: %s' %
            (context, CONTEXTS))

    def unused(self):
        """
        Return unused user-created elements.
        
        :rtype: list(Element)
        """
        self._params.update(
            href=session.entry_points.get('search_unused'))
        return self
        
    def duplicates(self):
        """
        Return duplicate user-created elements.
        
        :rtype: list(Element)
        """
        self._params.update(
            href=session.entry_points.get('search_duplicate'))
        return self

    @staticmethod
    def object_types():
        """
        Show all available 'entry points' available for searching. An entry
        point defines a uri that provides unfiltered access to all elements
        of the entry point type.

        :return: list of entry points by name
        :rtype: list(str)
        """
        # Return all elements from the root of the API nested under elements URI
        element_uri = str(
            '{}/{}/elements'.format(session.url, session.api_version))
        types = [element.rel
                 for element in session.entry_points
                 if element.href.startswith(element_uri)]
        types.extend(list(CONTEXTS))
        return types
