"""
Get all active VPN SA's.

Create a query to obtain all connections for a given engine::

    query = VPNSAQuery('sg_vm')
    
Add a timezone to the query::

    query.format.timezone('CST')
    
Execute query and return raw results::

    for records in query.fetch_batch():
        ...

Execute query and return as a :class:`.VPNSecurityAssoc` element::

    for records in query.fetch_as_element():
        ...

.. seealso:: :class:`smc_monitoring.models.filters` for more information on creating filters

"""
from smc_monitoring.models.query import Query
from smc_monitoring.models.constants import LogField


class VPNSAQuery(Query):
    """
    Show all current VPN SA's on the specified target.
    
    :ivar list field_ids: field IDs are the default fields for this entry type
        and are constants found in :class:`smc_monitoring.models.constants.LogField`
    
    :param str target: name of target engine/cluster
    """
    location = '/monitoring/session/socket'
    field_ids = [
        LogField.TIMESTAMP,
        LogField.NODEID,
        LogField.VPNID,
        LogField.SECURITYGATEWAY,
        LogField.PEERSECURITYGATEWAY,
        LogField.ENDPOINT,
        LogField.PEERENDPOINT,
        LogField.SACLASS,
        LogField.NEGOTIATIONROLE,
        LogField.SRCADDRS,
        LogField.DSTADDRS,
        LogField.PROTOCOL,
        LogField.NUMBYTESSENT,
        LogField.NUMBYTESRECEIVED,
        LogField.EXPIRATIONTIME]
        
    def __init__(self, target, **kw):
        super(VPNSAQuery, self).__init__('VPN_SA', target, **kw)
    
    def fetch_as_element(self, **kw):
        """
        Fetch the results and return as a VPNSecurityAssoc element.
        The original query is not modified.
        
        :return: generator of elements
        :rtype: :class:`~VPNSecurityAssoc`
        """
        clone = self.copy()
        clone.format.field_format('id')
        for custom_field in ['field_ids', 'field_names']:
            clone.format.data.pop(custom_field, None)

        for list_of_results in clone.fetch_raw(**kw):
            for entry in list_of_results:
                yield VPNSecurityAssoc(**entry)

                       
class VPNSecurityAssoc(object):
    """
    A VPN Security Association represents a currently connected VPN
    endpoint. This is the result of making a :class:`.VPNSAQuery` and
    using :meth:`~VPNSAQuery.fetch_as_element`.
    """
    def __init__(self, **data):
        self.vpn = data

    @property
    def timestamp(self):
        """
        Timestamp of this connection. It is recommended to set the timezone
        on the query to view this timestamp in the systems local time.
        For example::
            
            query.format.timezone('CST')
        
        :rtype: str
        """
        return self.vpn.get(str(LogField.TIMESTAMP))
    
    @property
    def engine(self):
        """
        The engine/cluster for this VPN
        
        :rtype: str
        """
        return self.vpn.get(str(LogField.NODEID))
    
    @property
    def local_gateway(self):
        """
        Local gateway for this VPN.
        
        :rtype: str
        """
        return self.vpn.get(str(LogField.SECURITYGATEWAY))
    
    @property
    def peer_gateway(self):
        """
        Peer gateway for this VPN.
        
        :rtype: str
        """
        return self.vpn.get(str(LogField.PEERSECURITYGATEWAY))
    
    @property
    def local_endpoint(self):
        """
        Local endpoint (IP address) for this VPN tunnel.
        
        :rtype: str
        """
        return self.vpn.get(str(LogField.ENDPOINT))
    
    @property
    def peer_endpoint(self):
        """
        Peer endpoint element and IP Address for this tunnel.
        
        :rtype: str
        """
        return self.vpn.get(str(LogField.PEERENDPOINT))
    
    @property
    def local_networks(self):
        """
        Local protected networks
        
        :rtype: str
        """
        return self.vpn.get(str(LogField.SRCADDRS))
    
    @property
    def peer_networks(self):
        """
        Remote protected networks
        
        :rtype: str
        """
        return self.vpn.get(str(LogField.DSTADDRS))
    
    @property
    def vpn_id(self):
        return self.vpn.get(str(LogField.VPNID))
    
    @property
    def sa_type(self):
        """
        SA Type for this VPN tunnel. Each VPN tunnel will typically have
        at least two entries, one for IPSEC and another for IKE.
        
        :rtype: str
        """
        return self.vpn.get(str(LogField.SACLASS))
    
    @property
    def protocol(self):
        """
        WHich protocol is associated with this tunnel entry.
        
        :return: IP protocol for tunnel, i.e. ESP/UDP
        :rtype: str
        """
        return self.vpn.get(str(LogField.PROTOCOL))
    
    @property
    def negotiation_role(self):
        """
        Role for this tunnel entry.
        
        :return: Negotiation role, i.e. Initiator, Responder, etc.
        :rtype: str
        """
        return self.vpn.get(str(LogField.NEGOTIATIONROLE))
    
    @property
    def bytes_sent(self):
        """
        Number of bytes sent.
        
        :rtype: int
        """
        return int(self.vpn.get(str(LogField.NUMBYTESSENT), 0))
    
    @property
    def bytes_received(self):
        """
        Number of bytes received.
        
        :rtype: int
        """
        return int(self.vpn.get(str(LogField.NUMBYTESRECEIVED), 0))
    
    @property
    def expiration(self):
        """
        Expiration time for this tunnel Security Association
        
        :rtype: str
        """
        return self.vpn.get(str(LogField.EXPIRATIONTIME))

    def __str__(self):
        return '{}(local={},peer={},localip={},peerip={},satype={})'.format(
            self.__class__.__name__, self.local_gateway, self.peer_gateway,
            self.local_endpoint, self.peer_endpoint, self.sa_type)
    
    def __repr__(self):
        return str(self)