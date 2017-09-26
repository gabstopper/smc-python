"""
A connection query returns all currently connected sessions on the
given target.

Create a query to obtain all connections for a given engine::

    query = ConnectionQuery('sg_vm')
    
Add a timezone to the query::

    query.format.timezone('CST')
    
Add a filter to only get connections if the source address is 172.18.1.252::

    query.add_in_filter(FieldValue(LogField.SRC), [IPValue('172.18.1.252')])

Only connections that match a specific service::

    query.add_in_filter(FieldValue(LogField.SERVICE), [ServiceValue('TCP/443', 'UDP/53')])
    
Execute query and return raw results::

    for records in query.fetch_raw():
        ...

Execute query and return as an :class:`.Connection` element::

    for records in query.fetch_as_element():
        ...

Retrieving live streaming results::

    for records in query.fetch_live():
        ...
    
.. seealso:: :class:`smc_monitoring.models.filters` for more information on creating filters

"""
from smc_monitoring.models.query import Query
from smc_monitoring.models.constants import LogField


class ConnectionQuery(Query):
    """
    Show all current connections on the specified target.
    
    :ivar list field_ids: field IDs are the default fields for this entry type
        and are constants found in :class:`smc_monitoring.models.constants.LogField`
    
    :param str target: name of target engine/cluster
    """
    location = '/monitoring/session/socket'
    field_ids = [
        LogField.TIMESTAMP,
        LogField.NODEID,
        LogField.SRC,
        LogField.DST,
        LogField.SERVICE,
        LogField.PROTOCOL,
        LogField.SPORT,
        LogField.DPORT,
        LogField.STATE]
    
    def __init__(self, target, **kw):
        super(ConnectionQuery, self).__init__('CONNECTIONS', target, **kw)
                
    def fetch_as_element(self, **kw):
        """
        Fetch the results and return as a Connection element. The original
        query is not modified.
        
        :return: generator of elements
        :rtype: :class:`.Connection`
        """
        clone = self.copy()
        clone.format.field_format('id')
        for custom_field in ['field_ids', 'field_names']:
            clone.format.data.pop(custom_field, None)

        for list_of_results in clone.fetch_raw(**kw):
            for entry in list_of_results:
                yield Connection(**entry)
    

class Connection(object):
    """
    Connection represents a state table entry. This is the result of 
    making a :class:`~ConnectionQuery` and using
    :meth:`~ConnectionQuery.fetch_as_element`.
    """
    
    def __init__(self, **data):
        self.cxn = data
        
    @property
    def timestamp(self):
        """
        Timestamp of this connection. It is recommended to set the timezone
        on the query to view this timestamp in the systems local time.
        For example::
            
            query.format.timezone('CST')
        
        :return: timestamp in string format
        :rtype: str
        """
        return self.cxn.get(str(LogField.TIMESTAMP))
    
    @property
    def engine(self):
        """
        The engine/cluster for this state table entry
        
        :return: engine or cluster for this entry
        :rtype: str
        """
        return self.cxn.get(str(LogField.NODEID))
    
    @property
    def source_addr(self):
        """
        Source address for this entry
        
        :rtype: str
        """
        return self.cxn.get(str(LogField.SRC))
    
    @property
    def dest_addr(self):
        """
        Destination address for this entry
        
        :rtype: str
        """
        return self.cxn.get(str(LogField.DST))
    
    @property
    def service(self):
        """
        Service for this entry
        
        :return: service (HTTP/HTTPS, etc)
        :rtype: str
        """
        return self.cxn.get(str(LogField.SERVICE))
    
    @property
    def protocol(self):
        """
        Protocol for this entry
        
        :return: protocol (UDP/TCP/ICMP, etc)
        :rtype: str
        """
        return self.cxn.get(str(LogField.PROTOCOL), 'ANY')
    
    @property
    def source_port(self):
        """
        Source port for the entry.
        
        :rtype: int
        """
        return int(self.cxn.get(str(LogField.SPORT), 0))
    
    @property
    def dest_port(self):
        """
        Destination port for the entry.
        
        :rtype: int
        """
        return int(self.cxn.get(str(LogField.DPORT),0))
    
    @property
    def state(self):
        """
        State of the connection.
        
        :return: state, i.e. UDP established, TCP established, etc.
        :rtype: str
        """
        return self.cxn.get(str(LogField.STATE))
    
    def __str__(self):
        return '{}(src={},dst={},proto={},dst_port={},state={})'.format(
            self.__class__.__name__,
            self.source_addr, self.dest_addr, self.protocol,
            self.dest_port, self.state)
    
    def __repr__(self):
        return str(self)