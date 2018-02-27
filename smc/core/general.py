"""
General configuration areas for an engine. This correlates to service level
settings such as DNSRelay, SNMP, etc.
"""

import collections
from smc.base.model import Element
from smc.base.util import element_resolver
from smc.elements.profiles import DNSRelayProfile
from smc.base.structs import NestedDict
from smc.policy.interface import InterfacePolicy
from smc.api.exceptions import LoadPolicyFailed
from smc.elements.network import Host
from smc.elements.servers import DNSServer


class SNMP(object):
    """
    SNMP configuration details for applying SNMP on an engine.
    SNMP requires at minimum an assigned SNMPAgent configuration
    which defines the SNMP specific settings (version, community
    string, etc). You can also define specific interfaces to enable
    SNMP on. By default, if no addresses are specified, SNMP will
    be defined on all interfaces.
    
    .. seealso:: :class:`smc.elements.profiles.SNMPAgent`
    """
    def __init__(self, engine):
        self.engine = engine
        
    @property
    def agent(self):
        """
        The SNMP agent profile used for this engine.
        
        :rtype: SNMPAgent
        """
        return self.engine.from_href(
            getattr(self.engine, 'snmp_agent_ref', None))
    
    @property
    def status(self):
        return bool(getattr(self.engine, 'snmp_agent_ref', False))
    
    def enable(self, snmp_agent, snmp_location=None, snmp_interface=None):
        """
        Enable SNMP on the engine. Specify a list of interfaces
        by ID to enable only on those interfaces. Only interfaces
        that have NDI's are supported.
        
        :param str,Element snmp_agent: the SNMP agent reference for this engine
        :param str snmp_location: the SNMP location identifier for the engine
        :param list snmp_interface: list of interface IDs to enable SNMP
        :raises ElementNotFound: unable to resolve snmp_agent
        :raises InterfaceNotFound: specified interface by ID not found
        """
        agent = element_resolver(snmp_agent)
        snmp_interface = [] if not snmp_interface else snmp_interface
        interfaces = [values for interface in snmp_interface
                      for values in self.engine.interface.get(interface).ndi_interfaces]
    
        self.engine.data.update(
            snmp_agent_ref=agent,
            snmp_location=snmp_location if snmp_location else '',
            snmp_interface=interfaces)
               
    def disable(self):
        """
        Disable SNMP on this engine. You must call `update` on the engine
        for this to take effect.

        :return: None
        """
        self.engine.data.update(
            snmp_agent_ref=None,
            snmp_location='',
            snmp_interface=[])

    @property
    def location(self):
        """
        Return the SNMP location string
        
        :rtype: str
        """
        return getattr(self.engine, 'snmp_location', None)
    
    @property
    def interface(self):
        """
        Return a list of physical interfaces that the SNMP
        agent is bound to.
        
        :rtype: list(PhysicalInterface)
        """
        nics = set([nic.get('nicid') for nic in \
            getattr(self.engine, 'snmp_interface', [])])
        return [self.engine.interface.get(nic) for nic in nics]
    
    def __repr__(self):
        return '{0}(enabled={1})'.format(
            self.__class__.__name__, self.status)
        

class DNSRelay(object):
    """
    DNS Relay allows the engine to provide DNS caching or specific
    host, IP and domain replies to clients. It can also be used
    to sinkhole specific DNS requests.
    
    .. seealso:: :class:`smc.elements.profiles.DNSRelayProfile`
    """
    def __init__(self, engine):
        self.engine = engine
        
    @property
    def status(self):
        """
        Status of DNS Relay on this engine.

        :rtype: bool
        """
        return getattr(self.engine, 'dns_relay_profile_ref', False)
        
    def enable(self, interface_id, dns_relay_profile=None):
        """
        Enable the DNS Relay service on this engine.

        :param int interface_id: interface id to enable relay
        :param str,DNSRelayProfile dns_relay_profile: DNSRelayProfile element
            or str href
        :raises EngineCommandFailed: interface not found
        :raises ElementNotFound: profile not found
        :return: None
        """
        if not dns_relay_profile:  # Use default
            href = DNSRelayProfile('Cache Only').href
        else:
            href = element_resolver(dns_relay_profile)

        intf = self.engine.interface.get(interface_id)
        
        self.engine.data.update(dns_relay_profile_ref=href)
        self.engine.data.update(dns_relay_interface=intf.ndi_interfaces)
        #self.engine.data.update(dns_relay_interface=
        #    ([{'address': ip, 'nicid': nicid}
        #        for ip, _, nicid in data.addresses]))
        
    def disable(self):
        """
        Disable DNS Relay on this engine
        
        :return: None
        """
        self.engine.data.update(dns_relay_interface=[])
        self.engine.data.pop('dns_relay_profile_ref', None)
    
    def __repr__(self):
        return '{0}(enabled={1})'.format(
            self.__class__.__name__, self.status)


class DefaultNAT(object):
    """
    Default NAT on the engine is used to automatically create NAT
    configurations based on internal routing. This simplifies the
    need to create specific NAT rules, primarily for outbound traffic.
    
    .. note:: You must call engine.update() to commit any changes.
    """
    def __init__(self, engine):
        self.engine = engine
        
    @property
    def status(self):
        """
        Status of default nat on the engine. 
        
        :rtype: bool
        """
        return self.engine.data['default_nat']
        
    def enable(self):
        """
        Enable default NAT on this engine
        """
        self.engine.data['default_nat'] = True
        
    def disable(self):
        """
        Disable default NAT on this engine
        """
        self.engine.data['default_nat'] = False
    
    def __repr__(self):
        return '{0}(enabled={1})'.format(
            self.__class__.__name__, self.status)


class DNSAddress(object):
    """
    DNS Address represents a DNS address entry assigned to the engine.
    DNS entries can be added as raw IP addresses, or as elements of type
    :class:`smc.elements.network.Host` or :class:`smc.elements.servers.DNSServer`
    (or combination of both). This is an iterable class yielding namedtuples of
    type :class:`.DNSEntry`.
    Normal access is done through an engine reference::
    
        >>> list(engine.dns)
        [DNSEntry(rank=0,value=8.8.8.8,ne_ref=None),
         DNSEntry(rank=1,value=None,ne_ref=DNSServer(name=mydnsserver))]
         
        >>> engine.dns.add(['8.8.8.8', '9.9.9.9'])
        >>> engine.dns.remove(['8.8.8.8', DNSEntry('mydnsserver')])
    
    .. note:: You must call engine.update() to commit any changes.
    """
    def __init__(self, engine):
        self.engine = engine

    def __iter__(self):
        for server in self.engine.domain_server_address:
            yield DNSEntry(**server)
    
    def add(self, dns_server):
        """
        Add a DNS entry to the engine. A DNS entry can be either
        a raw IP Address, or an element of type :class:`smc.elements.network.Host`
        or :class:`smc.elements.servers.DNSServer`.
        
        :param list dns_server: list of IP addresses, Host and/or DNSServer elements.
        :return: None
        
        .. note:: If the DNS entry added already exists, it will not be
            added. It's not a valid configuration to enter the same DNS IP
            multiple times. This is also true if the element is assigned the
            same address as a raw IP address already defined.
        """
        rank = self._max_rank
        uniq = self._unique_addr
        dns = self.engine.domain_server_address
        for server in dns_server:
            if hasattr(server, 'href'):
                if isinstance(server, (Host, DNSServer)):
                    if server.address not in uniq:
                        rank += 1
                        dns.append({'rank': rank, 'ne_ref': server.href})
                        uniq.append(server.address)
                else: # alias?
                    dns.append({'rank': rank, 'ne_ref': server.href})
            else: # ip address
                if server not in uniq:
                    rank += 1
                    dns.append({'rank': rank, 'value': server})
                    uniq.append(server)
    
    def remove(self, dns_server):
        """
        Remove a DNS entry from the engine. Note that when removing, you
        can provide either an element or a raw IP address. Generally it's
        best to first iterate the existing DNS entries to identify which
        one/s should be removed.
        
        :param list dns_server: list of DNS server entries to remove
        :return: None
        """
        dns = list(iter(self))
        for server in dns_server:
            if hasattr(server, 'href'):
                dns = [rec for rec in dns if rec.ne_ref != server.href]
            else:
                dns = [rec for rec in dns if rec.value != server]
                
        self.engine.domain_server_address = self._rank(dns)
    
    def _rank(self, tup_lst):
        # Re-rank after removing to maintain sequential order
        for i, entry in enumerate(tup_lst):
            if entry.ne_ref:
                tup_lst[i] = {'rank': i, 'ne_ref': entry.ne_ref}
            else:
                tup_lst[i] = {'rank': i, 'value': entry.value}
        return tup_lst
    
    @property
    def _unique_addr(self):
        # All unique IP addresses
        addr = []
        for entry in iter(self):
            if entry.value:
                addr.append(entry.value)
            elif entry.ne_ref:
                elem = entry.element
                if isinstance(elem, (Host, DNSServer)):
                    addr.append(elem.address)
        return addr
    
    @property
    def _max_rank(self):
        if self.engine.domain_server_address:
            return max([entry.rank for entry in iter(self)])
        return -1


class DNSEntry(collections.namedtuple('DNSEntry', 'value rank ne_ref')):
    """ 
    DNSEntry represents a single DNS entry within an engine
    DNSAddress list.
    
    :ivar str value: IP address value of this entry (None if type Element is used)
    :ivar int rank: order rank for the entry
    :ivar str ne_ref: network element href of entry. Use element property to resolve
        to type Element.
    :ivar Element element: If the DNS entry is an element type, this property
        will returned a resolved version of the ne_ref field.
    """
    __slots__ = () 
    def __new__(cls, rank, value=None, ne_ref=None):  # @ReservedAssignment 
        return super(DNSEntry, cls).__new__(cls, value, rank, ne_ref)
    
    @property 
    def element(self): 
        return Element.from_href(self.ne_ref)
    
    def __repr__(self): 
        return 'DNSEntry(rank={0},value={1},ne_ref={2})'\
            .format(self.rank, self.value, self.element)


class Layer2Settings(NestedDict):
    """
    Layer 2 Settings are only applicable on Layer 3 Firewall engines
    that want to run specific interfaces in layer 2 mode. This
    requires that a Layer 2 Interface Policy is applied to the engine.
    You can also set connection tracking and bypass on overload 
    settings for these interfaces as well.
    
    Set policy for the engine::
        
        engine.l2fw_settings.enable(InterfacePolicy('mylayer2'))
    
    :ivar bool bypass_overload_traffic: whether to bypass traffic on overload
    :ivar str tracking_mode: connection tracking mode
    
    .. note:: You must call engine.update() to commit any changes.
    
    .. warning:: This feature requires SMC and engine version >= 6.3
    """
    def __init__(self, engine):
        l2 = engine.data['l2fw_settings']
        super(Layer2Settings, self).__init__(data=l2)

    def connection_tracking(self, mode):
        """
        Set the connection tracking mode for these layer 2 settings.
        
        :param str mode: normal, strict, loose
        :return: None
        """
        if mode in ('normal', 'strict', 'loose'):
            self.update(tracking_mode=mode)
    
    def bypass_on_overload(self, value):
        """
        Set the l2fw settings to bypass on overload.
        
        :param bool value: boolean to indicate bypass setting
        :return: None
        """
        self.update(bypass_overload_traffic=value)
    
    def disable(self):
        """
        Disable the layer 2 interface policy
        """
        self.pop('l2_interface_policy_ref', None)
    
    def enable(self, policy):
        """
        Set a layer 2 interface policy.
        
        :param str,Element policy: an InterfacePolicy or str href
        :raises LoadPolicyFailed: Invalid policy specified
        :raises ElementNotFound: InterfacePolicy not found
        :return: None
        """
        if hasattr(policy, 'href'):
            if not isinstance(policy, InterfacePolicy):
                raise LoadPolicyFailed('Invalid policy type specified. The policy'
                    'type must be InterfacePolicy')
                
        self.update(l2_interface_policy_ref=element_resolver(policy))
    
    @property
    def policy(self):
        """
        Return the InterfacePolicy for this layer 3 firewall.
        
        :rtype: InterfacePolicy
        """
        return InterfacePolicy.from_href(self.get('l2_interface_policy_ref'))

    def __repr__(self):
        return '{0}(policy={1})'.format(
            self.__class__.__name__, self.policy)
