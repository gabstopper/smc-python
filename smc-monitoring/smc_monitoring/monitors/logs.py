'''
LogQuery provides an interface to the SMC Log Viewer to retrieve data
in real time or by batch. 

There are a variety of settings you can configure on a query such as whether
to execute a real time query versus a stored log fetch, time frame for the
query, fetch size quantity, returned format style, specify which fields to
return and adding filters to make a very specific query.

To make queries, first obtain a query object and optionally (recommended)
specify a maximum number of records to fetch (for non-real time fetches).
The default log query type is 'stored', and if a ``fetch_size`` is not
provided, one batch of 200 records will be returned::

    query = LogQuery(fetch_size=50)

If real time logs are preferred and set ``fetch_type='current'``
(default is fetch 'stored' logs)::

    query = LogQuery(fetch_type='current')
    
You can also use the shortcut ``fetch_live`` on the query::

    query = LogQuery()
    for result in query.fetch_live():
        ...
    
.. note:: If selecting ``fetch_size='current'`` log queries will be
    real-time and ignore the ``fetch_size``, ``time_range``, and
    ``backwards`` values if provided on the query.

You can also set a time_range on the query. There are convenience methods
on a TimeFormat object to simplify adding a time range. When using time ranges,
you should set the timezone on the query to the clients timezone::

    query = LogQuery(fetch_size=50)
    query.time_range.last_five_minutes()
    query.format.timezone('CST')

You can also use custom time ranges to search between a specific period of time.
This is done by providing a :class:`smc_monitoring.models.calendar.TimeFormat`
instance to the Query constructor, or by modifying the query ``time_range``
attribute.
The TimeFormat object takes a 'naive' datetime object for start and end times.
The start and end times must also be in milliseconds.

Example of finding all records on 9/2/2017 from 06:25:30 to 06:26:30
in the local time zone CST::
    
    dt_start = datetime(2017, 9, 2, 6, 25, 30, 0)
    dt_end = datetime(2017, 9, 2, 6, 26, 30, 0)

    query = LogQuery()
    query.format.timezone('CST')    # <--- Set the timezone on the query!
    query.time_range.custom_range(
        datetime_to_ms(dt_start),
        datetime_to_ms(dt_end))

.. seealso:: :class:`smc_monitoring.models.calendar.TimeFormat` for more examples
    and information on using a TimeFormat in a query.

Adding filters to a query can be achieved by using add_XX_filter convenience
methods or by calling ``update_filter`` with the filter object.

For example, customizing the fields returned using ``query.format.field_ids``, and 
filtering for only HIGH alerts with a source address of 192.168.4.84::

    query = LogQuery(fetch_size=10)
    query.format.timezone('CST')
    
    query.format.field_ids([LogField.TIMESTAMP, LogField.ACTION, LogField.SRC, LogField.DST])
    
    query.add_and_filter(
        [InFilter(FieldValue(LogField.ALERTSEVERITY), [ConstantValue(Alerts.HIGH)]),
         InFilter(FieldValue(LogField.SRC), [IPValue('192.168.4.84')])])
       
.. seealso:: :py:mod:`smc.monitoring.filters` for information on how to use and
    combine filters for a query.

'''
from smc_monitoring.models.calendar import TimeFormat
from smc_monitoring.models.query import Query
from smc_monitoring.models.constants import LogField
from smc_monitoring.models.formatters import TableFormat


class LogQuery(Query):
    """
    Make a Log Query to the SMC to fetch stored log data or monitor logs in
    real time.
    
    :ivar list field_ids: field IDs are the default fields for this entry type
        and are constants found in :class:`smc_monitoring.models.constants.LogField`
    
    :param str fetch_type: 'stored' or 'current'
    :param int fetch_size: max number of logs to fetch
    :param bool backwards: by default records are returned from newest to oldest
        (backwards=True). To return in opposite direction, set backwards=False.
        Default: True
    :param format: A format object specifying format of return data
    :type format: format type from :py:mod:`smc_monitoring.models.formats`
        (default: TextFormat)
    :param TimeFormat time_range: time filter to add to query
    """
    location = '/monitoring/log/socket'
    field_ids = [
        LogField.TIMESTAMP,
        LogField.ALERTSEVERITY,
        LogField.ACTION,
        LogField.NODEID,
        LogField.SRC,
        LogField.SPORT,
        LogField.DST,
        LogField.DPORT,
        LogField.PROTOCOL,
        LogField.EVENT,
        LogField.INFOMSG]

    def __init__(self, fetch_type='stored', fetch_size=None,
                 backwards=True, format=None, time_range=None, **kw):  # @ReservedAssignment
        super(LogQuery, self).__init__(format=format, **kw)
        
        fetch = {'quantity': fetch_size} if fetch_size is not None else {}
        fetch.update(backwards=backwards)

        self.time_range = time_range if time_range else TimeFormat()
        
        query = self.time_range.data
        query.update(type=fetch_type)
        
        self.request.update(
            fetch=fetch,
            query=query)
    
    @property
    def fetch_size(self):
        """
        Return the fetch size for this query. If fetch size is set
        to 0, the query will be aborted after the first response message.
        If the fetch_size is None, it is considered undefined which
        indicates there is no fetch bound set on this query (i.e. fetch
        all).
        
        ..note:: It is recommended to provide a fetch_size to limit the
            results when doing a 'stored' query.
            
        :return: configured fetch size for this query
        :rtype: int
        """
        if 'quantity' in self.request['fetch']:
            return self.request['fetch']['quantity']
        
    def fetch_raw(self):
        """
        Execute the query and return by batches.
        Optional keyword arguments are passed to Query.execute(). Whether
        this is real-time or stored logs is dependent on the value of
        ``fetch_type``.
        
        :return: generator of dict results
        """
        for results in super(LogQuery, self).execute():
            if 'records' in results and results['records']:
                yield results['records']
    
    def fetch_batch(self, formatter=TableFormat):
        """
        Fetch a batch of logs and return using the specified formatter. 
        Formatter is class type defined in :py:mod:`smc_monitoring.models.formatters`.
        This fetch type will be a single shot fetch (this method forces
        ``fetch_type='stored'``). If ``fetch_size`` is not already set on the
        query, the default fetch_size will be 200.
        
        :param formatter: Formatter type for data representation. Any type
            in :py:mod:`smc_monitoring.models.formatters`.
        :return: generator returning data in specified format
        """
        clone = self.copy()
        clone.update_query(type='stored')
        if not clone.fetch_size or clone.fetch_size <= 0:
            clone.request['fetch'].update(quantity=200)
        
        fmt = formatter(clone)
        for result in clone.fetch_raw():
            yield fmt.formatted(result)
                
    def fetch_live(self, formatter=TableFormat):
        """
        View logs in real-time. If previous filters were already set on
        this query, they will be preserved on the original instance (this
        method forces ``fetch_type='current'``).
        
        :param formatter: Formatter type for data representation. Any type
            in :py:mod:`smc_monitoring.models.formatters`.
        :return: generator of formatted results
        """
        clone = self.copy()
        clone.update_query(type='current')
        fmt = formatter(clone)
        for result in clone.fetch_raw():
            yield fmt.formatted(result)
        
