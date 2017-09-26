"""
SSLVPN currently connected users.

Create a query to obtain all connections for a given engine::

    query = SSLVPNQuery('sg_vm')
    
Add a timezone to the query::

    query.format.timezone('CST')
    
Execute query and return raw results::

    for records in query.fetch_batch():
        ...

Execute query and return as an :class:`.SSLVPNUser` element::

    for records in query.fetch_as_element():
        ...

.. seealso:: :class:`smc_monitoring.models.filters` for more information on creating filters

"""
from smc_monitoring.models.query import Query
from smc_monitoring.models.constants import LogField


class SSLVPNQuery(Query):
    """
    Show all current SSL VPN connections on the specified target.
    
    :ivar list field_ids: field IDs are the default fields for this entry type
        and are constants found in :class:`smc_monitoring.models.constants.LogField`
        
    :param str target: name of target engine/cluster
    """
    location = '/monitoring/session/socket'
    field_ids = [
        LogField.SSLVPNSESSIONMONRECEIVED,
        LogField.SSLVPNSESSIONMONTIMEOUT,
        LogField.NODEID,
        LogField.SRC,
        LogField.USERNAME]
    
    def __init__(self, target, **kw):
        super(SSLVPNQuery, self).__init__('SSLVPNV2', target, **kw)

    def fetch_as_element(self, **kw):
        """
        Fetch the results and return as an SSLVPNUser element. The original
        query is not modified.
        
        :return: generator of elements
        :rtype: :class:`.SSLVPNUser`
        """
        clone = self.copy()
        clone.format.field_format('id')
        for custom_field in ['field_ids', 'field_names']:
            clone.format.data.pop(custom_field, None)

        for list_of_results in clone.fetch_raw(**kw):
            for entry in list_of_results:
                yield SSLVPNUser(**entry)

                        
class SSLVPNUser(object):
    """
    Connection represents a state table entry. This is the result of 
    making a :class:`.SSLVPNQuery` and using
    :meth:`~SSLVPNQuery.fetch_as_element`.
    """
    def __init__(self, **data):
        self.user = data
        
    @property
    def engine(self):
        """
        The engine/cluster for this state table entry
        
        :return: engine or cluster for this entry
        :rtype: str
        """
        return self.user.get(str(LogField.NODEID))
    
    @property
    def source_addr(self):
        """
        Source IP address for the SSL VPN user
        
        :rtype: str
        """
        return self.user.get(str(LogField.SRC))
    
    @property
    def username(self):
        """
        Username for this SSL VPN user
        
        :rtype: str
        """
        return self.user.get(str(LogField.USERNAME))
    
    @property
    def session_start(self):
        """
        Time the session started. It is recommended that you add a
        timezone to the query to present this in human readable format::
        
            query.format.timezone('CST')
        
        :rtype: str
        """
        return self.user.get(str(LogField.SSLVPNSESSIONMONRECEIVED))
    
    @property
    def session_expiration(self):
        """
        Time the session expires. It is recommended that you add a
        timezone to the query to present this in human readable format::
        
            query.format.timezone('CST')
        
        :rtype: str
        """
        return self.user.get(str(LogField.SSLVPNSESSIONMONTIMEOUT))
    
    def __str__(self):
        return '{}(user={},ipaddress={},session_start={})'.format(
            self.__class__.__name__,
            self.username, self.source_addr, self.session_start)
    
    def __repr__(self):
        return str(self)