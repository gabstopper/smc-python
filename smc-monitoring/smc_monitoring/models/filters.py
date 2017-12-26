"""
Filters are used by queries to refine how results are returned.

QueryFilter is the top level 'interface' for all filter types. The ``filter``
attribute of a QueryFilter provides access to the compiled query string used
to build the filter. Each QueryFilter also has an ``update_filter`` method 
that can be used to swap new filters in and out of an existing query.

Filters can be added to queries using the add_XXX methods of the query, or by 
building the filters and adding to the query using query.update_filter(). Filters
can be swapped in and out of a query.

Examples:

Build a query to return all records of alert severity high or critical::

    query = LogQuery(fetch_size=50)
    query.add_in_filter(
        FieldValue(LogField.ALERTSEVERITY), [ConstantValue(Alerts.HIGH, Alerts.CRITICAL)])

If you prefer building your filters individually, it is not required to call the
add_XX_filter methods of the query. You can also insert filters by building the filter
and calling the ``update_filter`` method on the query::

    query = LogQuery(fetch_size=50)
    query.update_filter(
        InFilter(FieldValue(LogField.SERVICE), [ServiceValue('UDP/53', 'TCP/80')])

You can also replace existing query filters with new filters to re-use the base level
query parameters such as fetch_size, format style, time/date ranges, etc.

Replace the existing query filter with a different filter::

    new_filter = InFilter(FieldValue(LogField.SERVICE), [ServiceValue('UDP/53', 'TCP/80')])
    query.update_filter(new_filter)

.. note:: it is also possible to update a filter by calling query.add_XX_filter methods
    multiple times. Each time will replace an existing filter if it exists.
    
For example, calling add_XX_filter methods multiple times to refine filter results::

    query = LogQuery(fetch_size=50)
    query.add_in_filter(    # First filter query - look for alert severity high and critical
        FieldValue(LogField.ALERTSEVERITY), [ConstantValue(Alerts.HIGH, Alerts.CRITICAL)])

    query.add_and_filter([    # Change filter to AND filter for further granularity
        InFilter(FieldValue(LogField.ALERTSEVERITY), [ConstantValue(Alerts.HIGH, Alerts.CRITICAL)]),
        InFilter(FieldValue(LogField.SRC), [IPValue('192.168.4.84')])])
    
"""

class QueryFilter(object):
    def __init__(self, filter_type):
        self.filter = {
            'type': filter_type}
    
    def update_filter(self, value):
        self.filter.update(value=value)
        

class InFilter(QueryFilter):
    """
    InFilter's are made up of two parts, a left and a right. An InFilter
    is considered a match if evaluation of the left part is equivalent to
    one of the elements of the right part. The left part of an InFilter
    is made up of a target of type :class:`smc.monitoring.values.Value`.
    The right part is made up of a list of the same type.
    
    Search the Source field for IP addresses 192.168.4.84 or 10.0.0.252::
    
        query = LogQuery(fetch_size=50)
        query.add_in_filter(
            FieldValue(LogField.SRC), [IPValue('192.168.4.84', '10.0.0.252')])
            
    Reverse the logic and search for IP address 192.168.4.84 in source and
    dest log fields::
        
        query = LogQuery(fetch_size=50)
        query.add_in_filter(
            IPValue('192.168.4.84'), [FieldValue(LogField.SRC, LogField.DST)])
    
    InFilter's are one of the most common filters and are often added to AND, OR
    or NOT filters for more specific matching.
    
    :param left: single value for leftmost portion of filter
    :type left: Values: any value type in :py:mod:`smc_monitoring.models.values`
    :param right: list of values for rightmost portion of filter
    :type right: list(Values): any value type in :py:mod:`smc_monitoring.models.values`
    """
    def __init__(self, left, right):
        super(InFilter, self).__init__('in')
        self.update_filter(left, right)
        
    def update_filter(self, left_filter, right_filter):
        right_side = []
        for filters in right_filter:
            right_side.extend(filters.value)
        self.filter.update(
            left=left_filter.value[0],
            right=right_side)


class AndFilter(QueryFilter):
    """
    An AND filter combines other filter types and requires that each filter
    matches. An AND filter is a collection of QueryFilter's, typically IN
    or NOT filters that are AND'd together.
    
    Example of fetching 50 records for sources matching '192.168.4.84' and
    a service of 'TCP/80'::
    
        query = LogQuery(fetch_size=50)
        query.add_and_filter([
            InFilter(FieldValue(LogField.SRC), [IPValue('192.168.4.84')]),
            InFilter(FieldValue(LogField.SERVICE), [ServiceValue('TCP/80')])])
    
    :param QueryFilter filters: Any filter type in :py:mod:`smc.monitoring.filters`.
    :type filters: list or tuple
    """
    def __init__(self, *filters):
        super(AndFilter, self).__init__('and')
        if filters:
            self.update_filter(*filters)

    def update_filter(self, filters):
        self.filter.update(
            values=[value.filter for value in filters])

    
class OrFilter(QueryFilter):
    """
    An OR filter matches if any of the combined filters match. An OR filter
    is a collection of QueryFilter's, typically IN or NOT filters that are
    OR'd together.
    
    Example of fetching 50 records for sources matching '192.168.4.84' or
    a service of 'TCP/80'::
    
        query = LogQuery(fetch_size=50)
        query.add_or_filter([
            InFilter(FieldValue(LogField.SRC), [IPValue('192.168.4.84')]),
            InFilter(FieldValue(LogField.SERVICE), [ServiceValue('TCP/80')])])

    :param QueryFilter filters: Any filter type in :py:mod:`smc.monitoring.filters`.
    :type filters: list or tuple
    """
    def __init__(self, *filters):
        super(OrFilter, self).__init__('or')
        if filters:
            self.update_filter(*filters)
    
    def update_filter(self, filters):
        self.filter.update(
            values=[value.filter for value in filters])


class NotFilter(QueryFilter):
    """
    A NOT filter provides the ability to suppress auditing based on a specific
    filter. A NOT filter is typically added to an AND filter to remove unwanted
    entries from the response.
    
    Use only a NOT filter to a query and to ignore DNS traffic::
    
        query = LogQuery(fetch_size=50)
        query.add_not_filter(
            [InFilter(FieldValue(LogField.SERVICE), [ServiceValue('UDP/53')])])
    
    The above example by itself is not overly useful, however you can use NOT
    filters with AND filters to achieve a logic like "Find source IP 192.168.4.68
    and not service UDP/53 or TCP/80"::
    
        query = LogQuery(fetch_size=50)
        not_dns = NotFilter(
            [InFilter(FieldValue(LogField.SERVICE), [ServiceValue('UDP/53', 'TCP/80')])])
        by_ip = InFilter(
            FieldValue(LogField.SRC), [IPValue('172.18.1.20')])

        query.add_and_filter([not_dns, by_ip])
    
    :param QueryFilter filters: Any filter type in :py:mod:`smc.monitoring.filters`.
    :type filters: list or tuple    
    """
    def __init__(self, *filters):
        super(NotFilter, self).__init__('not')
        if filters:
            self.update_filter(*filters)
        
    def update_filter(self, filters):
        self.filter.update(
            value=filters[0].filter)


class DefinedFilter(QueryFilter):
    """
    A Defined Filter applied to a query will only match if the value
    specified has a value in the audit record/s.
    
    Show only records that have a defined Action (read as 'match if action
    has a value')::
        
        query = LogQuery(fetch_size=50)
        query.add_defined_filter(FieldValue(LogField.ACTION))
    
    DefinedFilter's can be used in AND, OR or NOT filter queries as well.
    Fetch the most recent 50 records for source 192.168.4.84 that have
    an application defined::
    
        query = LogQuery(fetch_size=50)
        query.add_and_filter([
            DefinedFilter(FieldValue(LogField.IPSAPPID)),
            InFilter(FieldValue(LogField.SRC), [IPValue('192.168.4.84')])])
    
    :param Value values: single value type to require on filter
    """
    def __init__(self, value=None):
        super(DefinedFilter, self).__init__('defined')
        if value is not None:
            self.update_filter(value)
    
    def update_filter(self, value):
        self.filter.update(
            value=value.value[0])

        
class CSLikeFilter(QueryFilter):
    """
    A CSLikeFilter is a case sensitive LIKE string match filter.
    """
    def __init__(self):
        super(CSLikeFilter, self).__init__('cs_like')
        pass


class CILikeFilter(QueryFilter):
    """
    A CILikeFilter is a case insensitive LIKE string match filter.
    """
    def __init__(self):
        super(CILikeFilter, self).__init__('cs_like')
        pass
            
        
class TranslatedFilter(QueryFilter):
    """
    Translated filters use the SMC internal name alias and builds expressions
    to make more complex queries.
    
    Example of using built in filter methods::
    
        query = LogQuery(fetch_size=50)
        query.format.timezone('CST')
        query.format.field_format('name')
    
        translated_filter = query.add_translated_filter()
        translated_filter.within_ipv4_network('$Dst', ['192.168.4.0/24'])
        translated_filter.within_ipv4_range('$Src', ['1.1.1.1-192.168.1.254'])
        translated_filter.exact_ipv4_match('$Src', ['172.18.1.152', '192.168.4.84'])
    
    """
    def __init__(self):
        super(TranslatedFilter, self).__init__('translated')

    def within_ipv4_network(self, field, values):
        """
        This filter adds specified networks to a filter to check
        for inclusion.
        
        :param str field: name of field to filter on. Taken from 'Show Filter
            Expression' within SMC.
        :param list values: network definitions, in cidr format, i.e: 1.1.1.0/24.
        """
        v = ['ipv4_net("%s")' % net for net in values]
        self.filter.update(
            value='{} IN union({})'.format(field, ','.join(v)))
            
    def within_ipv4_range(self, field, values):
        """
        Add an IP range network filter for relevant address fields.
        Range (between) filters allow only one range be provided.
        
        :param str field: name of field to filter on. Taken from 'Show Filter
            Expression' within SMC.
        :param list values: IP range values. Values would be a list of IP's
            separated by a '-', i.e. ['1.1.1.1-1.1.1.254']
        """
        v = ['ipv4("%s")' % part
             for iprange in values
             for part in iprange.split('-')]
    
        self.filter.update(
            value='{} IN range({})'.format(field, ','.join(v)))
    
    def exact_ipv4_match(self, field, values):
        """
        An exact IPv4 address match on relevant address fields.
        
        :param str field: name of field to filter on. Taken from 'Show Filter
            Expression' within SMC.
        :param list values: value/s to add. If more than a single value is
            provided, the query is modified to use UNION vs. ==
        :param bool complex: A complex filter is one which requires AND'ing
            or OR'ing values. Set to return the filter before committing.
        """
        if len(values) > 1:
            v = ['ipv4("%s")' % ip for ip in values]
            value='{} IN union({})'.format(field, ','.join(v))
        else:
            value='{} == ipv4("{}")'.format(field, values[0])
         
        self.filter.update(value=value)
                