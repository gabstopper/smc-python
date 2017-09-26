"""
Get active users on target cluster/engine.

Create a query to obtain all users for a given engine::

    query = UserQuery('sg_vm')
    
Add a timezone to the query::

    query.format.timezone('CST')
    
Execute query and return raw results::

    for records in query.fetch_batch():
        ...

Execute query and return as a :class:`.User` element::

    for records in query.fetch_as_element():
        ...
    
.. seealso:: :class:`smc_monitoring.models.filters` for more information on creating filters

"""

from smc_monitoring.models.query import Query
from smc_monitoring.models.constants import LogField
from smc_monitoring.models.formats import TextFormat


class UserQuery(Query):
    """
    Show all authenticated users on the specified target.
    
    :ivar list field_ids: field IDs are the default fields for this entry type
        and are constants found in :class:`smc_monitoring.models.constants.LogField`
    
    :param str target: name of target engine/cluster
    """
    location = '/monitoring/session/socket'
    field_ids = [
        LogField.TIMESTAMP,
        LogField.SRC, 
        LogField.NODEID,
        LogField.SENDERDOMAIN,
        LogField.EXPIRATIONTIME,
        LogField.USERNAME]
    
    def __init__(self, target, **kw):
        super(UserQuery, self).__init__('USERS', target, **kw)

    def fetch_as_element(self, **kw):
        """
        Fetch the results and return as a User element. The original
        query is not modified.
        
        :return: generator of elements
        :rtype: :class:`~User`
        """
        clone = self.copy()
        clone.format.field_format('id')
        for custom_field in ['field_ids', 'field_names']:
            clone.format.data.pop(custom_field, None)

        for list_of_results in clone.fetch_raw(**kw):
            for entry in list_of_results:
                yield User(**entry)


class User(object):
    """
    User mapping currently in user cache on specified target. 
    This is the result of making a :class:`.UserQuery` and using
    :meth:`~UserQuery.fetch_as_element`.
    """
    def __init__(self, **data):
        self.user = data

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
        return self.user.get(str(LogField.TIMESTAMP))
    
    @property
    def engine(self):
        """
        The engine/cluster for this state table entry
        
        :return: engine or cluster for this entry
        :rtype: str
        """
        return self.user.get(str(LogField.NODEID))
    
    @property
    def username(self):
        """
        Username for entry
        
        :return: username value as fully qualified domain name
        :rtype: str
        """
        return self.user.get(str(LogField.USERNAME))
        
    @property
    def ipaddress(self):
        """
        IP address for the entry
        
        :rtype: str
        """
        return self.user.get(str(LogField.SRC))
    
    @property
    def domain(self):
        """
        SMC Domain that this user record belongs to
        
        :return: name of SMC domain, 'Shared' is default
        :rtype: str
        """
        return self.user.get(str(LogField.SENDERDOMAIN))
    
    @property
    def expiration(self):
        """
        Expiration time for this user entry. It is recommended to add
        a timezone to the query to display this field in the client local
        time.
        
        :return: expiration time for this user authentication entry
        :rtype: str
        """
        return self.user.get(str(LogField.EXPIRATIONTIME))
    
    def __str__(self):
        return '{}(id={},ipaddress={},expiration={})'.format(
            self.__class__.__name__,
            self.username, self.ipaddress, self.expiration)
    
    def __repr__(self):
        return str(self)
    