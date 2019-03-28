"""
Collections module provides interfaces to obtain resources from this API
and provides searching mechanisms to auto-load resources into the
correct class type.

An ElementCollection is bound to :class:`smc.base.model.Element` as the
`objects` class property and provides the ability to use an element as
the base for iterating elements of that type::

    for hosts in Host.objects.all():
        ...

SubElementCollections are used when references to element data require
a fetch from the SMC, but these element references do not have a direct
SMC entry point.

See :ref:`collection-reference-label` for examples on search capabilities.
"""
import re
import copy
from itertools import islice
import smc.base.model
from smc.base.decorators import cached_property, classproperty
from smc.api.exceptions import FetchElementFailed, InvalidSearchFilter
from smc.api.common import entry_point
    

class SubElementCollection(object):
    """
    Collection class providing an iterable interface to sub elements
    referenced from a top level Element resource. Return types for this
    collection will be based on the class where the collection was obtained.
    Elements returned will be serialized into their Element types and
    only contain the top level meta for each element. The element cache
    will only be inflated (resulting in an additional query) if an
    operation is performed that requires the `data` (cache) attribute.
    
    Helper methods are provided to simplify fetching from the collection
    without having to iterate and code the matching yourself. Fetching from
    the collection has the limitation that only the returned `name` field is
    used to find a match (to prevent inflating every element before it is
    needed). If you want to match an available attribute in the resulting class
    that requires the elements full json, use a loop to attempt your match.
    
    Example of using SubElementCollection results to obtain matches from the
    collection::

        >>> from smc.administration.system import System
        >>> system = System()
        >>> upgrades = system.engine_upgrade()
        >>> upgrades
        EngineUpgradeCollection(items: 29)
        >>> list(upgrades)
        [EngineUpgrade(name=Security Engine upgrade 6.1.2 build 17037 for x86-64), EngineUpgrade(name=Security Engine upgrade 6.2.3 build 18067 for x86-64),  ....]
        >>> upgrades.get(5)
        EngineUpgrade(name=Security Engine upgrade 5.8.8 build 12093 for i386)
        >>> upgrades.get_contains('6.2')
        EngineUpgrade(name=Security Engine upgrade 6.2.3 build 18067 for x86-64)
        >>> upgrades.get_contains('6.1')
        EngineUpgrade(name=Security Engine upgrade 6.1.2 build 17037 for x86-64)
        >>> upgrades.get_all_contains('6.2')
        [EngineUpgrade(name=Security Engine upgrade 6.2.3 build 18067 for x86-64), EngineUpgrade(name=Security Engine upgrade 6.2.2 build 18062 for x86-64), ...]
        >>> 

    :raises FetchElementFailed: If the resource could not be retrieved
    """
    def __init__(self, href, cls):
        self.href = href
        self.cls = cls
        self._result_cache = None
        
    def __iter__(self):
        self._fetch_all()
        return iter(self._result_cache)
    
    def __getitem__(self, key):
        return self._result_cache[key]
    
    def _load_from_engine(self, engine, reference):
        resources = []
        for r in engine.data.get(reference, []):
            for _, data in r.items():    
                cache = smc.base.model.ElementCache(data)
                res = self.cls(
                    name=cache.get('name'),
                    href=cache.get_link('self'),
                    type=cache.type)
                res.data = cache
                res._engine = engine
                resources.append(res)
        self._result_cache = resources
    
    def _fetch_all(self):
        if self._result_cache is None:
            results = smc.base.model.prepared_request(
                FetchElementFailed,
                href=self.href
            ).read().json
            self._result_cache = [self.cls(**r) for r in results]
    
    def __len__(self):
        self._fetch_all()
        return len(self._result_cache)

    def __repr__(self):
        return '{}Collection(items: {})'.format(self.cls.__name__, len(self))
    
    def count(self):
        """
        Return the number of results in this collection
        
        :return: int
        """
        return len(self)
    
    def get(self, index):
        """
        Get the element by index. If index is out of bounds for
        the internal list, None is returned. Indexes cannot be
        negative.
        
        :param int index: retrieve element by positive index in list
        :rtype: SubElement or None
        """
        if self and (index <= len(self) -1):
            return self._result_cache[index]
    
    def get_exact(self, value):
        """
        Get an element using an exact match based on the elements meta
        `name` field. The SMC is case sensitive so the name will need to
        honor the case for a valid value match.
        
        .. seealso:: :meth:`~get_contains` and :meth:`~get_all_contains` for
            partial matching
        
        :param str value: name to match
        :rtype: SubElement or None
        """
        for element in self:
            if element.name == value:
                return element
    
    def get_contains(self, value, case_sensitive=True):
        """
        A partial match on the name field. Does an `in` comparsion to
        elements by the meta `name` field. Sub elements created by SMC
        will generally have a descriptive name that helps to identify
        their purpose. Returns only the first entry matched even if there
        are multiple.
        
        .. seealso:: :meth:`~get_all_contains` to return all matches
        
        :param str value: searchable string for contains match
        :param bool case_sensitive: whether the match should consider case
            (default: True)
        :rtype: SubElement or None
        """
        for element in self:
            if not case_sensitive:
                if value.lower() in element.name.lower():
                    return element
            elif value in element.name:
                return element
    
    def get_all_contains(self, value, case_sensitive=True):
        """
        A partial match on the name field. Does an `in` comparsion to
        elements by the meta `name` field.
        Returns all elements that match the specified value.
        
        .. seealso:: :meth:`get_contains` for returning only a single item.
        
        :param str value: searchable string for contains match
        :param bool case_sensitive: whether the match should consider case
            (default: True)
        :return: element or empty list
        :rtype: list(SubElement)
        """
        elements = []
        for element in self:
            if not case_sensitive:
                if value.lower() in element.name.lower():
                    elements.append(element)
            elif value in element.name:
                elements.append(element)
        return elements
           
    def all(self):
        """
        Generator returning collection for sub element types.
        Return full contents as list or iterate through each.
        
        :return: element type based on collection
        :rtype: list(SubElement)
        """
        return iter(self)


class CreateCollection(SubElementCollection):
    """
    A CreateCollection extends SubElementCollection by dynamically
    proxying the elements `create` method into the collection. This
    provides a simplified way to create sub elements and also iterate
    through existing.
    
    For example, obtaining VPN Sites from an engine returns a
    CreateCollection so existing sites can be iterated while still being
    able to create new sites::
    
        >>> engine = Engine('dingo')
        >>> print(engine.vpn.sites)
        <smc.base.collection.VPNSite object at 0x1098a9ed0>
        >>> print(help(engine.vpn.sites))
        Help on VPNSite in module smc.base.collection object:

        class VPNSite(CreateCollection)
         |  Method resolution order:
         |      VPNSite
         |      CreateCollection
         |      SubElementCollection
         |      __builtin__.object
         |  
         |  Methods defined here:
         |  
         |  create(self, name, site_element) from smc.vpn.elements.VPNSite
         |      Create a VPN site for an internal or external gateway
         |      
         |      :param str name: name of site
         |      :param list site_element: list of protected networks/hosts
         |      :type site_element: list[str,Element]
         |      :raises CreateElementFailed: create element failed with reason
         |      :return: href of new element
         |      :rtype: str
         |  
         ....
        
    List existing sites::
        
        list(engine.vpn.sites.all())
        
    Creating new VPN sites::
        
        engine.vpn.sites.create('mynewsite') 
    """
    
    def create(self, *args, **kwargs):
        """
        The create function from the sub element is proxied by
        this collections class to provide the iterable functionality
        from the parent container, but also protected access to the
        create method of the instance.
        """
        pass
        

def sub_collection(href, cls):
    """
    Helper method to generate a SubElementCollection dynamically
    using the SubElement constructor.
    """
    return type(
        cls.__name__, (CreateCollection,), {})(href, cls)


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


def rule_collection(href, cls):
    """
    Rule collections insert a ``create`` and ``create_rule_section`` method
    into the collection. This collection type is returned when accessing rules
    through a reference, as::

        policy = FirewallPolicy('mypolicy')
        policy.fw_ipv4_access_rules.create(....)
        policy.fw_ipv4_access_rules.create_rule_section(...)
    
    See the class types documentation, or use help()::
    
        print(help(policy.fw_ipv4_access_rules))

    :rtype: SubElementCollection
    """
    instance = cls(href=href)
    meth = getattr(instance, 'create')
    return type( 
        cls.__name__, (SubElementCollection,), {
            'create': meth,
            'create_rule_section': instance.create_rule_section})(href, cls)

                
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
    ElementCollection is generated dynamically from the CollectionManager
    and provides methods to obtain data from the SMC. Filters can be chained
    together to generate more complex queries. Each time a filter is added,
    a clone is returned to preserve the parent query parameters.
    
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
    
    def __bool__(self):
        return bool(self._list)
    __nonzero__ = __bool__
    
    def __len__(self):
        return len(self._list)
    
    def __repr__(self):
        query = ['{}={}'.format(q,v) for q,v in self._params.items()]
        return '{}(GET /elements?{})'.format(self.__class__.__name__, '&'.join(query) if \
            query else '')
    
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
        
        # Only strip metachars from network and address range
        if not exact_match and self._params.get('filter_context', {})\
            in ('network', 'address_range', 'network_elements'):
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
        if len(self):
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
        if len(self):
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
        return bool(self)
            
    def count(self):
        """
        Return number of results
        
        :rtype: int
        """
        return len(self)

    def between(self, start, end):
        """
        Specify a batch of records to return. Start and end correlate to
        which records to return from a batch. Convenience method to capture
        only a specific number of records, i.e::
        
            >>> objects = situation.objects.between(1, 2)
            >>> print(list(objects))
            >>>
            [InspectionSituation(name=MySQL_Oracle-MySQL-Dumpfile-DLL-Upload)]
        
        .. note:: Limit is ignored if also chained to the iterator query.
        
        :param str,int start: starting record
        :param str,int end: ending record
        :return: :class:`.ElementCollection`
        """
        return self._clone(start=start, end=end)
        
    def flatten(self):
        return self._clone(flatten=True)
    
    
class CollectionManager(object):
    """
    CollectionManager takes a class type as input and dynamically
    creates an ElementCollection for that class. All classes of type
    Element have an `objects` property which returns a manager. You can
    consume the manager as a re-usable iterator or just called it and
    it's methods directly.
    
    To get an iterator object that can be re-used, obtain an iterator()
    from the manager::
    
        it = Host.objects.iterator()
        it.filter(....)
        ...
    
    Or more simply call the managers proxied methods to return the
    ElementCollection for the class type it was called for::
    
        >>> from smc.elements.network import Host
        >>> for host in Host.objects.all():
        ...   host
        ... 
        Host(name=IGMP v3)
        Host(name=ALL-PIM-ROUTERS)
        Host(name=Microsoft Lync Online Servers)
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
    
    def between(self, start, end):
        return self.iterator(start=start, end=end)
    between.__doc__ = ElementCollection.between.__doc__
    
    def flatten(self):
        return self.iterator(flatten=True)
    flatten.__doc__ = ElementCollection.flatten.__doc__
    
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
        
        # Only strip metachars from network and address range
        if not exact_match and hasattr(self, '_cls') and \
            self._cls.typeof in ('network', 'address_range'):
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
        self._resource = entry_point()
    
    @classproperty
    def objects(self):
        """
        :rtype: Search
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
                href=self._resource.get(entry_point))
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
            href=self._resource.get('search_unused'))
        return self
        
    def duplicates(self):
        """
        Return duplicate user-created elements.
        
        :rtype: list(Element)
        """
        self._params.update(
            href=self._resource.get('search_duplicate'))
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
        #element_uri = str(
        types = [element.rel for element in entry_point()]
        types.extend(list(CONTEXTS))
        return types
