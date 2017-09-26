"""
Query the current routing table entries.

Create a query to obtain all connections for a given engine::

    query = RoutingQuery('sg_vm')
    
Add a timezone to the query::

    query.format.timezone('CST')
    
Add a filter to only routes for destination network 192.168.4.0/24::

    query.add_in_filter(FieldValue(LogField.ROUTENETWORK), [IPValue('192.168.4.0')])

Only routes that use a specific gateway::

    query.add_in_filter(FieldValue(LogField.ROUTEGATEWAY), [IPValue('172.18.1.200')])
    
Execute query and return raw results::

    for records in query.fetch_batch():
        ...

Execute query and return as an :class:`.RoutingView` element::

    for records in query.fetch_as_element():
        ...

.. seealso:: :class:`smc_monitoring.models.filters` for more information on creating filters

"""

from smc_monitoring.models.query import Query
from smc_monitoring.models.constants import LogField


class RoutingQuery(Query):
    """
    Show all current dynamic and static routes on the specified target. 
    
    :ivar list field_ids: field IDs are the default fields for this entry type
        and are constants found in :class:`smc_monitoring.models.constants.LogField`
    
    :param str target: name of target engine/cluster
    """
    location = '/monitoring/session/socket'
    field_ids = [
        LogField.TIMESTAMP,
        LogField.DSTIF,
        LogField.DSTVLAN,
        LogField.DSTZONE,
        LogField.ROUTEGATEWAY,
        LogField.ROUTENETWORK,
        LogField.ROUTETYPE,
        LogField.ROUTEMETRIC]
    
    def __init__(self, target, **kw):
        super(RoutingQuery, self).__init__('ROUTING', target, **kw)

    def fetch_as_element(self, **kw):
        """
        Fetch the results and return as a RoutingView element. The original
        query is not modified.
        
        :return: generator of elements
        :rtype: :class:`.RoutingView`
        """
        clone = self.copy()
        clone.format.field_format('id')
        for custom_field in ['field_ids', 'field_names']:
            clone.format.data.pop(custom_field, None)

        for list_of_results in clone.fetch_raw(**kw):
            for entry in list_of_results:
                yield RoutingView(**entry)


class RoutingView(object):
    """
    A Routing View represents an entry in the current routing table.
    This is the result of making a :class:`.RoutingQuery` and using
    :meth:`~RoutingQuery.fetch_as_element`.
    """
    def __init__(self, **data):
        self.rt = data
        
    @property
    def timestamp(self):
        """
        Timestamp of this connection. It is recommended to set the timezone
        on the query to view this timestamp in the systems local time.
        For example::
            
            query.format.timezone('CST')
        
        :return timestamp in string format
        :rtype: str
        """
        return self.rt.get(str(LogField.RECEPTIONTIME))
    
    @property
    def engine(self):
        """
        The engine/cluster for this route
        
        :rtype: str
        """
        return self.rt.get(str(LogField.NODEID))
        
    @property
    def dest_if(self):
        """
        Destination interface for this route
        
        :rtype: str
        """
        return self.rt.get(str(LogField.DSTIF))
    
    @property
    def dest_vlan(self):
        """
        Destination VLAN for this route, if any.
        
        :rtype: str
        """
        return self.rt.get(str(LogField.DSTVLAN))
    
    @property
    def dest_zone(self):
        """
        Destination zone for this route, if any.
        
        :rtype: str
        """
        return self.rt.get(str(LogField.DSTZONE))
    
    @property
    def route_gw(self):
        """
        The route gateway for this route.
        
        :rtype: str
        """
        return self.rt.get(str(LogField.ROUTEGATEWAY))
    
    @property
    def route_network(self):
        """
        The route network for this route.
        
        :rtype: str
        """
        return self.rt.get(str(LogField.ROUTENETWORK))
    
    @property
    def route_type(self):
        """
        The type of route.
        
        :return: Static, Connection, Dynamic, etc.
        :rtype: str
        """
        return self.rt.get(str(LogField.ROUTETYPE))
    
    @property
    def route_metric(self):
        """
        Metric for this route.
        
        :return: route metric
        :rtype: int
        """
        return int(self.rt.get(str(LogField.ROUTEMETRIC)), 0)
    
    def __str__(self):
        return '{}(dest_if={},network={},type={})'.format(
            self.__class__.__name__,
            self.dest_if, self.route_network, self.route_type)
    
    def __repr__(self):
        return str(self)
