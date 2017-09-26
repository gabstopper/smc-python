"""
Blacklist Query provides the ability to view current blacklist entries in the
SMC by target. Target is defined as the cluster or engine. Retrieved results
will have a reference to the entry and hence be possible to remove the entry.
::
    
    query = BlacklistQuery('sg_vm')
    query.format.timezone('CST')

Optionally add an "InFilter" to restrict search to a specific field::
 
    query.update_filter(FieldValue(LogField.BLACKLISTENTRYSOURCEIP), [IPValue('2.2.2.2')])

An InFilter can also use a network based syntax::

    query.update_filter(FieldValue(LogField.BLACKLISTENTRYSOURCEIP), [IPValue('2.2.2.0/24')])

Or combine filters using "AndFilter" or "OrFilter". Find an entry with
source IP 2.2.2.2 OR 2.2.2.5::

    ip1 = InFilter(FieldValue(LogField.BLACKLISTENTRYSOURCEIP), [IPValue('2.2.2.2')])
    ip2 = InFilter(FieldValue(LogField.BLACKLISTENTRYSOURCEIP), [IPValue('2.2.2.5')])
    query.add_or_filter([in_filter, or_filter])

Get the results of the query in the default TableFormat::

    for entry in query.fetch_batch():
        print(entry)

Delete any blacklist entries with a source IP within a network range of 3.3.3.0/24::
    
        query = BlacklistQuery('sg_vm')
        query.add_in_filter(
            FieldValue(LogField.BLACKLISTENTRYSOURCEIP), [IPValue('3.3.3.0/24')])
        
        for record in query.fetch_as_element():    # <-- must get as element to obtain delete() method
            record.delete()
        
.. seealso:: :class:`smc_monitoring.models.filters` for more information on creating filters
        
"""
from smc_monitoring.models.query import Query
from smc_monitoring.models.formats import TextFormat, CombinedFormat,\
    DetailedFormat
from smc_monitoring.models.constants import LogField
from smc.base.model import prepared_request
from smc.api.exceptions import DeleteElementFailed


class BlacklistQuery(Query):
    """
    Query existing blacklist entries for a given cluster/engine.
    It is generally recommended to set your local timezone when making a
    query to convert the timestamp into a relevant format.
    
    :param str target: NAME of the engine or cluster
    :param str timezone: timezone for timestamps.
        
    .. note:: Timezone can be in the following formats: 'US/Eastern',
        'PST', 'Europe/Helsinki'. More example time zone formats are
        available in the SMC Log Viewer -> Settings.        
    """
    location = '/monitoring/session/socket'
    field_ids = [
        LogField.TIMESTAMP,
        LogField.BLACKLISTENTRYID,
        LogField.BLACKLISTER,
        LogField.BLACKLISTENTRYSOURCEIP,
        LogField.BLACKLISTENTRYDESTINATIONIP,
        LogField.PROTOCOL,
        LogField.BLACKLISTENTRYDURATION]

    def __init__(self, target, timezone=None, **kw):
        bldata = TextFormat(field_format='name')
        if timezone is not None:
            bldata.set_resolving(timezone=timezone)
    
        blid = TextFormat(field_format='pretty')
        blid.field_ids([LogField.BLACKLISTENTRYID])
        
        combined = CombinedFormat(bldata=bldata, blid=blid)
        
        super(BlacklistQuery, self).__init__('BLACKLIST', target, format=combined, **kw)
    
    def fetch_as_element(self, **kw):
        """
        Fetch the blacklist and return as an instance of Element.
        
        :return generator returning element instances
        :rtype: BlacklistEntry
        """
        for list_of_results in self.fetch_raw(**kw):
            for entry in list_of_results:
                data = entry.get('bldata')
                data.update(**entry.get('blid'))
                yield BlacklistEntry(**data)
    
    
class BlacklistEntry(object):
    """
    A blacklist entry represents an entry in the engines kernel table
    indicating that a source/destination/port/protocol mapping is currently
    being blocked by the engine. To remove a blacklist entry from an engine,
    retrieve all entries as element and remove the entry of interest by
    called ``delete`` on the element.
    
    The simplest way to use search filters with a blacklist entry is to
    examine the BlacklistQuery ``field_ids`` and use these constant fields
    as InFilter definitions on the query.
    """
    def __init__(self, **kw):
        self.blacklist = kw
    
    @property
    def blacklist_id(self):
        """
        Blacklist entry ID. Useful if you want to locate the entry
        within the SMC UI.
        
        :rtype: str
        """
        return self.blacklist.get('Blacklist Entry ID')

    @property
    def timestamp(self):
        """
        Timestamp when this blacklist entry was added.
        
        :rtype: str
        """
        return self.blacklist.get('Timestamp')
    
    @property
    def engine(self):
        """
        The engine for this blacklist entry.
        
        :rtype: str
        """
        return self.blacklist.get('NodeId')
    
    @property
    def href(self):
        """
        The href for this blacklist entry. This is the reference to the
        entry for deleting the entry.
        
        :rtype: str
        """
        return self.blacklist.get('blacklist_href')
    
    @property
    def source(self):
        """
        Source address/netmask for this blacklist entry.
        
        :rtype: str
        """
        return '{}/{}'.format(
            self.blacklist.get('BlacklistEntrySourceIp'),
            self.blacklist.get('BlacklistEntrySourceIpPrefixlen'))
    
    @property
    def destination(self):
        """
        Destination network/netmask for this blacklist entry.
        
        :rtype: str
        """
        return '{}/{}'.format(
            self.blacklist.get('BlacklistEntryDestinationIp'),
            self.blacklist.get('BlacklistEntryDestinationIpPrefixlen'))

    @property
    def protocol(self):
        """
        Specified protocol for the blacklist entry. If none is specified,
        'ANY' is returned.
        
        :rtype: str
        """
        proto = self.blacklist.get('BlacklistEntryProtocol')
        if proto is None:
            return 'ANY'
        return proto

    @property
    def source_ports(self):
        """
        Source ports for this blacklist entry. If no ports are specified (i.e. ALL
        ports), 'ANY' is returned.
        
        :rtype: str
        """
        start_port = self.blacklist.get('BlacklistEntrySourcePort')
        if start_port is not None:
            return '{}-{}'.format(
                start_port, self.blacklist.get('BlacklistEntrySourcePortRange'))
        return 'ANY'

    @property
    def dest_ports(self):
        """
        Destination ports for this blacklist entry. If no ports are specified,
        'ANY' is returned.
        
        :rtype: str
        """
        start_port = self.blacklist.get('BlacklistEntryDestinationPort')
        if start_port is not None:
            return '{}-{}'.format(
                start_port, self.blacklist.get('BlacklistEntryDestinationPortRange'))
        return 'ANY'  

    @property
    def duration(self):
        """
        Duration for the blacklist entry.
        
        :rtype: int
        """
        return int(self.blacklist.get('BlacklistEntryDuration'))

    def delete(self):
        """
        Delete the entry from the engine where the entry is applied.
        
        :raises: DeleteElementFailed
        :return: None
        """
        return prepared_request(
            DeleteElementFailed,
            href=self.href).delete()

    def __str__(self):
        return '{0}(id={1},src={2},dst={3})'.format(
            self.__class__.__name__, self.blacklist_id, self.source,
            self.destination) 
        
    def __repr__(self): 
        return str(self)  
    
