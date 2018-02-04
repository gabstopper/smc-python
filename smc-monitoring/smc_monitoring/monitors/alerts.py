"""
ActiveAlert Query provides the ability to view current alert entries from the
alert log viewer.
When creating the query, you must specify a target which speifies the SMC domain
for which to retrieve the alerts.

A basic alert query using a local timezone example::
    
    query = ActiveAlertQuery('Shared Domain')
    query.format.timezone('CST')

You can also use standard filters to specify a more exact match, for example, showing
alerts with a severity of CRITICAL::

    query.add_in_filter(
        FieldValue(LogField.ALERTSEVERITY), [ConstantValue(Alerts.CRITICAL)])

"""

from smc_monitoring.models.query import Query
from smc_monitoring.models.constants import LogField


class ActiveAlertQuery(Query):
    """
    Active Alert Query is an interface to the alert log viewer in SMC.
    This query type provides the ability to fetch and filter on active
    alerts.
    
    You can create a new query specifying a valid timezone abbreviation::
    
        query = ActiveAlertQuery('Shared Domain', timezone='CST')
        
    Or alternatively no timezone::
    
        query = ActiveAlertQuery('DomainFoo')
    
    :param str target: domain for which to filter alerts. Default: 'Shared Domain'
    :param str timezone: timezone for timestamps, i.e. 'CST', etc
    """
    location = '/monitoring/session/socket'
    field_ids = [
        LogField.TIMESTAMP,
        LogField.ALERTSEVERITY,
        LogField.ACTION,
        LogField.NODEID,
        LogField.SRC,
        LogField.DST,
        LogField.SERVICE,
        LogField.PROTOCOL,
        LogField.SPORT,
        LogField.DPORT,
        LogField.SITUATION,
        LogField.VULNERABILITYREFERENCES]
    
    def __init__(self, target='Shared Domain', timezone=None):
        super(ActiveAlertQuery, self).__init__('ACTIVE_ALERTS', target)
        if timezone is not None:
            self.format.set_resolving(timezone=timezone)
        
    def fetch_as_element(self, **kw):
        """
        Fetch the results and return as a User element. The original
        query is not modified.
        
        :return: generator returning element instances 
        :rtype: Alert
        """
        clone = self.copy()
        clone.format.field_format('id')
        for custom_field in ['field_ids', 'field_names']:
            clone.format.data.pop(custom_field, None)

        for list_of_results in clone.fetch_raw(**kw):
            for entry in list_of_results:
                yield Alert(**entry)
        

class Alert(object):
    """
    Alert definition returned from specified domain.
    This is the result of making a :class:`.ActiveAlertQuery` and using
    :meth:`~ActiveAlertQuery.fetch_as_element`.
    """
    def __init__(self, **data):
        self.alert = data

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
        return self.alert.get(str(LogField.TIMESTAMP))
    
    @property
    def engine(self):
        """
        The engine/cluster for this state table entry
        
        :return: engine or cluster for this entry
        :rtype: str
        """
        return self.alert.get(str(LogField.NODEID))
    
    @property
    def severity(self):
        """
        Severity for this alert
        
        :rtype: str
        """
        return self.alert.get(str(LogField.ALERTSEVERITY))
        
    @property
    def action(self):
        """
        Action performed for the alert
        
        :rtype: str
        """
        return self.alert.get(str(LogField.ACTION))
    
    @property
    def source(self):
        """
        Source IP for the alert
        
        :rtype: str
        """
        return self.alert.get(str(LogField.SRC))
    
    @property
    def destination(self):
        """
        Destination IP for the alert
        
        :rtype: str
        """
        return self.alert.get(str(LogField.DST))
    
    @property
    def service(self):
        """
        Service associated with alert
        
        :rtype: str
        """
        return self.alert.get(str(LogField.SERVICE))
    
    @property
    def protocol(self):
        """
        Protocol for alert
        
        :rtype: str
        """
        return self.alert.get(str(LogField.PROTOCOL))
    
    @property
    def source_port(self):
        """
        Source port for alert
        
        :rtype: int
        """
        return int(self.alert.get(str(LogField.SPORT)))
    
    @property
    def destination_port(self):
        """
        Destination port for alert
        
        :rtype: int
        """
        return int(self.alert.get(str(LogField.DPORT)))
    
    @property
    def situation(self):
        """
        Situation defined for this alert
        
        :rtype: str
        """
        return self.alert.get(str(LogField.SITUATION))
    
    @property
    def vulnerability_refs(self):
        """
        Comma seperated string listing any vulnerability references for
        the alert, if any.
        
        :rtype: str
        """
        return self.alert.get(str(LogField.VULNERABILITYREFERENCES))
    
    def __str__(self):
        return '{}(severity={},src={},dst={},action={},situation={})'.format(
            self.__class__.__name__,
            self.severity, self.source, self.destination, self.action,
            self.situation)
    
    def __repr__(self):
        return str(self)
        