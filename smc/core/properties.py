"""
Miscellaneous functionality to control aspects of an engine such
as features specified under engine AddOns, default nat, and DNS
addressing.
"""
from collections import namedtuple
from smc.base.model import Element, SubDict
from smc.base.decorators import autocommit, deprecated
from smc.api.exceptions import UnsupportedEngineFeature, LoadPolicyFailed
from smc.policy.interface import InterfacePolicy
from smc.elements.network import Host
from smc.elements.servers import DNSServer
from smc.elements.profiles import DNSRelayProfile, SandboxService
from smc.base.util import element_resolver
from smc.compat import min_smc_version


def get_proxy(http_proxy):
    if http_proxy:
        proxies = [element_resolver(proxy) for proxy in http_proxy]
    else: 
        proxies = []
    return proxies


class Layer2Settings(SubDict):
    """
    Layer 2 Settings are only applicable on Layer 3 Firewall engines
    that want to run specific interfaces in layer 2 mode. This
    requires that a Layer 2 Interface Policy is applied to the engine.
    You can also set connection tracking and bypass on overload 
    settings for these interfaces as well.
    
    Set policy for the engine::
        
        engine.l2fw_settings.set_policy(InterfacePolicy('mylayer2'))
    
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
    
    def set_policy(self, policy):
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
        

class AntiVirus(SubDict):
    """
    Antivirus settings for the engine. In order to use AV,
    you must also have DNS server addresses configured on
    the engine.
    
    Enable AV, use a proxy for updates and adjust update
    schedule::
    
        engine.antivirus.enable()
        engine.antivirus.update_frequency('daily')
        engine.antivirus.update_day('tu')
        engine.antivirus.log_level('transient')
        engine.antivirus.http_proxy('10.0.0.1', proxy_port=8080, user='foo', password='password')
        engine.update()
    
    :ivar bool antivirus_enabled: is antivirus enabled
    :ivar str antivirus_http_proxy: http proxy settings
    :ivar bool antivirus_http_proxy_enabled: is http proxy enabled
    :ivar int antivirus_proxy_port: http proxy port
    :ivar str antivirus_proxy_user: http proxy user
    :ivar str antivirus_update: how often to update
    :ivar str antivirus_update_day: if update set to weekly, which day to update
    :ivar int antivirus_update_time: time to update av signatures
    :ivar str virus_log_level: antivirus logging level

    .. note:: You must call engine.update() to commit any changes.
    """
    def __init__(self, engine):
        av = engine.data.get('antivirus', {})
        super(AntiVirus, self).__init__(data=av)
    
    def update_frequency(self, when):
        """
        Set the update frequency. By default this is daily.
        
        :param str antivirus_update: how often to check for updates. Valid options
            are: 'never','1hour', 'startup', 'daily', 'weekly'
        """
        if when in ('never', '1hour', 'startup', 'daily', 'weekly'):
            self.update(antivirus_update=when)
    
    def update_day(self, day):
        """
        Update the day when updates should occur.
        
        :param str day: only used if 'weekly' is specified. Which day
            or week to perform update. Valid options: mo, tu, we, th,
            fr, sa, su.
        """
        if day in ('mo','tu','we','th','fr','sa','su'):
            self.update(antivirus_update_day=day)
    
    def log_level(self, level):
        """
        Set the log level for antivirus alerting.
        
        :param str log_level: none,transient,stored,essential,alert
        """
        if level in ('none', 'transient', 'stored' ,'essential','alert'):
            self.update(virus_log_level=level)
          
    def http_proxy(self, proxy, proxy_port, user=None, password=None):
        """
        .. versionadded:: 0.5.7
            Requires SMC and engine version >= 6.4
        
        Set http proxy settings for Antivirus updates.
        
        :param str proxy: proxy IP address
        :param str,int proxy_port: proxy port
        :param str user: optional user for authentication
        """
        self.update(
            antivirus_http_proxy=proxy,
            antivirus_proxy_port=proxy_port,
            antivirus_proxy_user=user if user else '',
            antivirus_proxy_password=password if password else '',
            antivirus_http_proxy_enabled=True)
    
    def disable(self):
        """
        Disable antivirus on the engine
        """
        self.update(antivirus_enabled=False)
    
    @property
    def status(self):
        """
        Status of AV on this engine
        
        :rtype: bool
        """
        return self.get('antivirus_enabled', False)
    
    def enable(self):
        """
        Enable antivirus on the engine
        """
        self.update(antivirus_enabled=True,
                    virus_mirror='update.nai.com/Products/CommonUpdater' if \
                        not self.get('virus_mirror') else self.virus_mirror,
                    antivirus_update_time=self.antivirus_update_time if \
                        self.get('antivirus_update_time') else 21600000)
        
    def __repr__(self):
        return '{0}(enabled={1})'.format(
            self.__class__.__name__, self.status)


class FileReputation(SubDict):
    """
    Configure the engine to use File Reputation capabilities.
    
    Enable file reputation and specify outbound http proxies for
    queries::
    
        engine.file_reputation.enable_gti(http_proxy=[HttpProxy('myproxy')])
        engine.update()
    
    :ivar str file_reputation_context: file reputation context, either
        gti_cloud_only or disabled
    
    .. note:: You must call engine.update() to commit any changes.
    """
    def __init__(self, engine):
        gti = engine.data.get('gti_settings', {})
        super(FileReputation, self).__init__(data=gti)
    
    def disable(self):
        """
        Disable any file reputation on the engine.
        """
        self.update(file_reputation_context='disabled')
    
    @property
    def status(self):
        """
        Return the status of File Reputation on this engine.
        
        :rtype: bool
        """
        if self.file_reputation_context == 'disabled':
            return False
        return True
    
    @property
    def http_proxy(self):
        """    
        Return any HTTP Proxies that are configured for File 
        Reputation.
        
        :return: list of http proxy instances
        :rtype: list(HttpProxy)
        """
        return [Element.from_href(proxy) for proxy in self.get('http_proxy')]
        
    def enable_gti(self, http_proxy=None):
        """
        Enable GTI reputation on the engine. If proxy servers
        are needed, provide a list of proxy elements.
        
        :param http_proxy: list of proxies for GTI connections
        :type http_proxy: list(str,HttpProxy)
        """
        self.update(file_reputation_context='gti_cloud_only',
                    http_proxy=get_proxy(http_proxy))
        
    def __repr__(self):
        return '{0}(enabled={1})'.format(
            self.__class__.__name__, self.status)


class SidewinderProxy(object):
    """
    Sidewinder status on this engine. Sidewinder proxy can only be
    enabled on specific engine types and also requires SMC and
    engine version >= 6.1.
    
    Enable Sidewinder proxy::
    
        engine.sidewinder_proxy.enable()
        
    .. note:: You must call engine.update() to commit any changes.
    """
    def __init__(self, engine):
        self.engine = engine
        
    def enable(self):
        """
        Enable Sidewinder proxy on the engine
        """
        self.engine.data['sidewinder_proxy_enabled'] = True
    
    def disable(self):
        """
        Disable Sidewinder proxy on the engine
        """
        self.engine.data['sidewinder_proxy_enabled'] = False
    
    @property
    def status(self):
        """
        Status of Sidewinder proxy on this engine
        
        :rtype: bool
        """
        return self.engine.data['sidewinder_proxy_enabled']
    
    def __repr__(self):
        return '{0}(enabled={1})'.format(
            self.__class__.__name__, self.status)
    

class UrlFiltering(SubDict):
    """
    Enable URL Filtering on the engine.
    
    Enable Url Filtering with next hop proxies::
    
        engine.url_filtering.enable(http_proxy=[HttpProxy('myproxy')])
        engine.update()
    
    Disable Url Filtering::

        engine.url_filtering.disable()
        engine.update()
        
    .. note:: You must call engine.update() to commit any changes.
    """
    def __init__(self, engine):
        ts = engine.data.get('ts_settings', {})
        super(UrlFiltering, self).__init__(data=ts)
    
    @property
    def http_proxy(self):
        """    
        Return any HTTP Proxies that are configured for Url
        Filtering.
        
        :return: list of http proxy instances
        :rtype: list(HttpProxy)
        """
        return [Element.from_href(proxy) for proxy in self.get('http_proxy')]

    def enable(self, http_proxy=None):
        """
        Enable URL Filtering on the engine. If proxy servers
        are needed, provide a list of HTTPProxy elements.
        
        :param http_proxy: list of proxies for GTI connections
        :type http_proxy: list(str,HttpProxy)
        """
        self.update(ts_enabled=True, http_proxy=get_proxy(http_proxy))
    
    def disable(self):
        """
        Disable URL Filtering on the engine
        """
        self.update(ts_enabled=False)
    
    @property
    def status(self):
        """
        Return the status of URL Filtering on the engine
        
        :rtype: bool
        """
        return self.get('ts_enabled', False)
    
    def __repr__(self):
        return '{0}(enabled={1})'.format(
            self.__class__.__name__, self.status)
    

class Sandbox(SubDict):
    """
    Engine based sandbox settings. Sandbox can be configured for
    local (on prem) or cloud based sandbox. To create file filtering
    policies that use sandbox, you must first enable it and
    provide license keys on the engine.
    
    Enable cloud sandbox on the engine, specifying a proxy for outbound
    connections::
    
        engine.sandbox.enable(
            license_key='123',
            license_token='456',
            http_proxy=[HttpProxy('myproxy')])
    
    .. note:: You must call engine.update() to commit any changes.
    """
    def __init__(self, engine):
        self.engine = engine
        sb = engine.data.get('sandbox_settings', {})
        super(Sandbox, self).__init__(data=sb)
            
    @property
    def status(self):
        """
        Status of sandbox on this engine
        
        :rtype: bool
        """
        if 'sandbox_type' in self.engine.data:
            if self.engine.sandbox_type == 'none':
                return False
            return True
        return False  # Tmp, attribute missing on newly created engines
    
    def disable(self):
        """
        Disable the sandbox on this engine.
        """
        self.engine.data.update(sandbox_type='none')
        self.pop('cloud_sandbox_settings', None) #pre-6.3
        self.pop('sandbox_settings', None)
    
    def enable(self, license_key, license_token,
               sandbox_type='cloud_sandbox', service=None,
               http_proxy=None):
        """
        Enable sandbox on this engine. Provide a valid license key
        and license token obtained from your engine licensing.
        
        .. note:: Cloud sandbox is a feature that requires an engine license

        :param str license_key: license key for specific engine
        :param str license_token: license token for specific engine
        :param str sandbox_type: 'local_sandbox' or 'cloud_sandbox'
        :param str,SandboxService service: a sandbox service element from SMC. The service
            defines which location the engine is in and which data centers to use.
            The default is to use the 'Automatic' profile if undefined.
        :return: None
        """
        if not service:
            service = SandboxService('Automatic').href
        else:
            service = element_resolver(service)
            
        if min_smc_version(6.3):
            self.update(sandbox_license_key=license_key,
                        sandbox_license_token=license_token,
                        sandbox_service=service,
                        http_proxy=get_proxy(http_proxy))
        else:
            self.update(cloud_sandbox_license_key=license_key,
                        cloud_sandbox_license_token=license_token,
                        sandbox_service=service,
                        http_proxy=get_proxy(http_proxy))
        
        if 'sandbox_settings' not in self.engine.data:
            self.engine.data['sandbox_settings'] = self.data
        
        self.engine.data.update(sandbox_type=sandbox_type)
    
    @property
    def http_proxy(self):
        """    
        Return any HTTP Proxies that are configured for Sandbox.
        
        :return: list of http proxy instances
        :rtype: list(HttpProxy)
        """
        return [Element.from_href(proxy) for proxy in self.get('http_proxy')]
            
    def __repr__(self):
        return '{0}(enabled={1})'.format(
            self.__class__.__name__, self.status)


class TLSInspection(object):
    """
    TLS Inspection settings control settings for doing inbound
    TLS decryption and outbound client TLS decryption. This
    provides an interface to manage TLSServerCredentials and
    TLSClientCredentials assigned to the engine.
    
    .. note:: You must call engine.update() to commit any changes.
    """
    def __init__(self, engine):
        self.engine = engine
        
    @property
    def server_credentials(self):
        """
        Return a list of assigned (if any) TLSServerCredentials
        assigned to this engine.
        
        :return: TLSServerCredential
        :rtype: list
        """
        return [Element.from_href(credential)
                for credential in self.engine.server_credential]
    
    def add_tls_credential(self, credentials):
        """        
        Add a list of TLSServerCredential to this engine.
        TLSServerCredentials can be in element form or can also
        be the href for the element.
        
        :param credentials: list of pre-created TLSServerCredentials
        :type credentials: list(str,TLSServerCredential)
        :return: None
        """
        for cred in credentials:
            href = element_resolver(cred)
            if href not in self.engine.server_credential:
                self.engine.server_credential.append(href)
    
    def remove_tls_credential(self, credentials):
        """    
        Remove a list of TLSServerCredentials on this engine.
        
        :param credentials: list of credentials to remove from the
            engine
        :type credentials: list(str,TLSServerCredential)
        :return: None
        """
        for cred in credentials:
            href = element_resolver(cred)
            if href in self.engine.server_credential:
                self.engine.server_credential.remove(href)
      
    @property
    def client_protection_ca(self):
        return self.engine.tls_client_protection


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


class DNSEntry(namedtuple('DNSEntry', 'value rank ne_ref')):
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

                                
def antivirus_options(**kw):
    """
    Antivirus options for more granular controls. Default setting is to update
    daily at midnight.
    
    :param str antivirus_update: how often to check for updates. Valid options
        are: 'never','1hour', 'startup', 'daily', 'weekly'.
    :param int antivirus_update_time: only used if 'daily' or 'weekly' is specified.
        Time is given as a long value value in a 24-hour format. (Default: 21600000,
        which is midnight) 
    :param str antivirus_update_day: only used if 'weekly' is specified. Which day
        or week to perform update. Valid options: 'mo','tu','we','th','fr','sa','su'.
    :param str log_level: none,transient,stored,essential,alert
    """
    antivirus = {
        'antivirus_enabled': True,
        'antivirus_update': 'daily',
        'antivirus_update_day': 'su',
        'antivirus_update_time': 21600000,
        'virus_log_level': 'stored',
        'virus_mirror': 'update.nai.com/Products/CommonUpdater'}
    
    for key, value in kw.items():
        antivirus[key] = value
    
    return antivirus
    
    
            
class AddOn:
    """
    Engine features that enable specific functionality and can be
    set or changed after the engine exists. Each setting requires
    that policy be refreshed to take effect.
    """
    @autocommit(now=False)
    def enable_dns_relay(self, interface_id, dns_relay_profile=None, **kw):
        """
        DNS Relay allows the engine to provide DNS caching or specific
        host, IP and domain replies to clients. It can also be used
        to sinkhole specific DNS requests.

        :param str,DNSRelayProfile dns_relay_profile: DNSRelayProfile element
            or str href
        :param int interface_id: interface id to enable relay
        :raises EngineCommandFailed: interface not found
        :raises ElementNotFound: profile not found
        :raises UpdateElementFailed: failure message from SMC
        :raises UnsupportedEngineFeature: unsupported engine type or version
        :return: None
        """
        if not self.is_dns_relay_enabled:
            if not dns_relay_profile:  # Use default
                dns_relay_profile = DNSRelayProfile('Cache Only').href
            else:
                dns_relay_profile = element_resolver(dns_relay_profile)

            data = self.interface.get(interface_id)

            d = dict(dns_relay_profile_ref=dns_relay_profile)
            d.update(dns_relay_interface=([{'address': ip, 'nicid': nicid}
                                           for ip, _, nicid in data.addresses]))
            self.data.update(**d)
    
    @autocommit(now=False)
    def disable_dns_relay(self, **kw):
        """
        Disable DNS Relay. This requires a policy push to update the
        engine settings.

        :raises UpdateElementFailed: failure message from SMC
        :raises UnsupportedEngineFeature: unsupported engine type or version
        :return: None
        """
        if self.is_dns_relay_enabled:
            self.data.update(dns_relay_interface=[])
            self.data.pop('dns_relay_profile_ref', None)

    @property
    def is_dns_relay_enabled(self):
        """
        Status of DNS Relay on this engine.

        :raises UnsupportedEngineFeature: unsupported engine type or version
        :rtype: bool
        """
        if 'dns_relay_interface' in self.data:
            if 'dns_relay_profile_ref' in self.data:
                return True
            return False
        raise UnsupportedEngineFeature(
            'DNS Relay requires a layer 3 engine and version >= v6.2.')

    @property
    @deprecated('engine.sidewinder_proxy')
    def is_sidewinder_proxy_enabled(self):
        """
        Status of Sidewinder Proxy on this engine

        :raises UnsupportedEngineFeature: requires engine >= v6.1
        :rtype: bool
        """
        if 'sidewinder_proxy_enabled' in self.data:
            return self.data['sidewinder_proxy_enabled']
        raise UnsupportedEngineFeature(
            'Sidewinder Proxy requires a layer 3 engine and version >= v6.1.')

    @autocommit(now=False)
    @deprecated('engine.sidewinder_proxy')
    def enable_sidewinder_proxy(self, **kw):
        """
        Enable Sidewinder Proxy on this engine. This requires
        engine version >= 6.2.

        :raises UpdateElementFailed: failure message from SMC
        :raises UnsupportedEngineFeature: unsupported engine type or version
        :return: None
        """
        if not self.is_sidewinder_proxy_enabled:
            self.data.update(sidewinder_proxy_enabled=True)

    @autocommit(now=False)
    @deprecated('engine.sidewinder_proxy')
    def disable_sidewinder_proxy(self, **kw):
        """
        Disable Sidewinder Proxy on this engine. This requires
        engine version >= 6.2.

        :raises UpdateElementFailed: failure message from SMC
        :raises UnsupportedEngineFeature: unsupported engine type or version
        :return: None
        """
        if self.is_sidewinder_proxy_enabled:
            self.data.update(sidewinder_proxy_enabled=False)

    @property
    @deprecated('engine.file_reputation')
    def is_gti_enabled(self):
        """
        Is McAfee GTI File Reputation enabled on this engine.

        :raises UnsupportedEngineFeature: unsupported engine type
        :rtype: bool
        """
        if not self.type.startswith('virtual'):
            gti = self.data['gti_settings'].get('file_reputation_context')
            if gti == 'disabled':
                return False
            return True
        raise UnsupportedEngineFeature(
            'GTI should be enabled on the Master Engine not directly on the '
            'virtual engine.')

    @autocommit(now=False)
    @deprecated('engine.file_reputation')
    def enable_gti_file_reputation(self, **kw):
        """
        Enable McAfee GTI File Reputation on this engine. Enabling
        GTI requires DNS server settings and GTI must be enabled on
        the global properties within SMC.

        :raises UnsupportedEngineFeature: unsupported engine type
        :raises UpdateElementFailed: failure message from SMC
        :return: None
        """
        if not self.is_gti_enabled:
            gti = self.data['gti_settings']
            gti.update(file_reputation_context='gti_cloud_only')
    
    @autocommit(now=False)
    @deprecated('engine.file_reputation')
    def disable_gti_file_reputation(self):
        """
        Disable McAfee GTI File Reputation on this engine.

        :raises UnsupportedEngineFeature: unsupported engine type
        :raises UpdateElementFailed: failure message from SMC
        :return: None
        """
        if self.is_gti_enabled:
            gti = self.data['gti_settings']
            gti.update(file_reputation_context='disabled')
    
    @property
    @deprecated('engine.antivirus')
    def is_antivirus_enabled(self):
        """
        Whether Anti-Virus is enable on this engine

        :raises UnsupportedEngineFeature: unsupported engine type
        :rtype: bool
        """
        if not self.type.startswith('virtual'):
            return self.data['antivirus'].get('antivirus_enabled', False)
        raise UnsupportedEngineFeature(
            'Antivirus is not supported directly on this engine type. If this '
            'is a virtual engine, AV is enabled on the master engine.')

    @autocommit(now=False)
    @deprecated('engine.antivirus')
    def enable_antivirus(self, **kw):
        """
        Enable Antivirus on this engine. Enabling anti-virus requires
        DNS server settings to resolve the AV update servers. Keyword arguments
        can be provided to further customize settings for updates.

        :param kw: see :func:`~antivirus_options` for documented optional keyword
            settings.
        :raises UnsupportedEngineFeature: unsupported engine type
        :raises UpdateElementFailed: failure message from SMC
        :return: None
        """
        if not self.is_antivirus_enabled:
            av = self.data['antivirus']
            options = antivirus_options(**kw)
            av.update(**options)
    
    
    @autocommit(now=False)
    @deprecated('engine.antivirus')
    def disable_antivirus(self, **kw):
        """
        Disable Anti-virus on this engine.

        :raises UnsupportedEngineFeature: unsupported engine type
        :raises UpdateElementFailed: failure message from SMC
        :return: None
        """
        if self.is_antivirus_enabled:
            av = self.data['antivirus']
            av.update(antivirus_enabled=False)
    
    @property
    @deprecated('engine.bgp')
    def is_bgp_enabled(self):
        """
        Is BGP enabled on this engine. BGP is only supported on layer 3
        engines (virtual included).

        :rtype: bool
        """
        return self.bgp.is_enabled

    @autocommit(now=False)
    @deprecated('engine.bgp')
    def enable_bgp(self, autonomous_system, announced_networks,
                   router_id=None, bgp_profile=None, **kw):
        """
        Enable BGP on this engine. On master engine, enable BGP on the
        virtual firewall.
        ::

            engine.enable_bgp(
                autonomous_system=AutonomousSystem('aws_as'),
                announced_networks=[Network('bgpnet'),Network('inside')],
                router_id='10.10.10.10')

        :param str,AutonomousSystem autonomous_system: provide the AS element
            or str href for the element
        :param str,BGPProfile bgp_profile: provide the BGPProfile element or
            str href for the element; if None, use system default
        :param list announced_networks: list of networks to advertise via BGP
        :type announced_networks: list(str,Network)
        :param str router_id: router id for BGP, should be an IP address
        :raises UpdateElementFailed: failure message from SMC
        :raises ElementNotFound: ospf profile not found
        :raises UnsupportedEngineFeature: unsupported engine type or version
        :return: None
        """
        self.bgp.enable(autonomous_system, announced_networks,
               router_id=None, bgp_profile=bgp_profile)

    @autocommit(now=False)
    @deprecated('engine.bgp')
    def disable_bgp(self, **kw):
        """
        Disable BGP on this engine.

        :raises UnsupportedEngineFeature: BGP not supported on this engine type
        :return: None
        """
        self.bgp.disable()

    @property
    @deprecated('engine.ospf')
    def is_ospf_enabled(self):
        """
        Is OSPF enabled on this engine

        :raises UnsupportedEngineFeature: unsupported engine type
        :rtype: bool
        """
        return self.ospf.is_enabled

    @autocommit(now=False)
    @deprecated('engine.ospf')
    def enable_ospf(self, ospf_profile=None, router_id=None, **kw):
        """
        Enable OSPF on this engine. For master engines, enable
        OSPF on the virtual firewall.

        Once enabled on the engine, add an OSPF area to an interface::

            engine.enable_ospf()
            interface = engine.routing.get(0)
            interface.add_ospf_area(OSPFArea('myarea'))


        :param str,OSPFProfile ospf_profile: OSPFProfile element or str
            href; if None, use default profile
        :param str router_id: single IP address router ID
        :raises ElementNotFound: ospf profile not found
        :return: None
        """
        self.ospf.enable(ospf_profile=ospf_profile, router_id=router_id)

    @autocommit(now=False)
    @deprecated('engine.ospf')
    def disable_ospf(self, **kw):
        """
        Disable OSPF on this engine.

        :raises UpdateElementFailed: failure message from SMC
        :return: None
        """
        self.ospf.disable()

    @autocommit(now=False)
    @deprecated('engine.dns')
    def add_dns_servers(self, dns_servers, **kw):
        """
        Add DNS servers to this engine.

        :param list dns_servers: DNS server addresses
        :return: None
        """
        for num, server in enumerate(dns_servers):
            if hasattr(server, 'href'):
                dns = {'rank': num, 'ne_ref': server.href}
            else:
                dns = {'rank': num, 'value': server}
            
            self.data['domain_server_address'].append(dns)

    @property
    @deprecated('engine.dns')
    def dns_servers(self):
        """
        DNS Servers for this engine (if any). DNS Servers are
        used to resolve specific features enabled on the engine
        such as Anti-Virus updates.

        :return: DNS Servers configured
        :rtype: list
        """
        servers = []
        for server in self.data.get('domain_server_address'):
            if 'value' in server:
                servers.append(server['value'])
            elif 'ne_ref' in server:
                servers.append(Element.from_href(server['ne_ref']))
        return servers

    @property
    @deprecated('engine.default_nat')
    def is_default_nat_enabled(self):
        """
        Default NAT provides NAT service by associating directly
        attached networks with a NAT address of the exiting interface.
        This simplifies how NAT is handled without creating specific
        NAT rules.

        :raises UnsupportedEngineFeature: for engines that do not support
            default NAT
        :rtype: bool
        """
        if 'default_nat' in self.data:
            return self.data['default_nat']
        raise UnsupportedEngineFeature(
            'This engine type does not support default NAT.')

    @autocommit(now=False)
    @deprecated('engine.default_nat')
    def enable_default_nat(self, **kw):
        """
        Enable default NAT at the engine level for engines that
        support NAT (i.e. layer 3 engines)

        :raises UnsupportedEngineFeature: for engines that do not support
            default NAT
        :return: None
        """
        if not self.is_default_nat_enabled:
            self.data.update(default_nat=True)

    @autocommit(now=False)
    @deprecated('engine.default_nat')
    def disable_default_nat(self, **kw):
        """
        Disable default NAT on this engine if supported.

        :raises UnsupportedEngineFeature: for engines that do not support
            default NAT
        :return: None
        """
        if self.is_default_nat_enabled:
            self.data.update(default_nat=False)

    @property
    @deprecated('engine.sandbox')
    def is_sandbox_enabled(self):
        """
        Whether sandbox is enabled on this engine.

        :raises UpdateElementFailed: requires engine version >= 6.2
        :rtype: bool
        """
        if not self.type.startswith('virtual'):
            if 'sandbox_type' in self.data:
                if self.data['sandbox_type'] == 'none':
                    return False
                return True
            return False  # Tmp, attribute missing on newly created engines
        raise UnsupportedEngineFeature(
            'Enabling sandbox should be done on the Master Engine, not '
            'directly on the virtual engine.')

    @autocommit(now=False)
    @deprecated('engine.sandbox')
    def enable_sandbox(self, license_key, license_token, sandbox_type='cloud_sandbox',
                       service=None, **kw):
        """
        Enable sandbox on this engine. Sandbox provides the ability to
        extract file type content and interrogate for behavioral purposes to
        discover malicious embedded content. Provide a valid license key and
        license token obtained from your engine licensing.
        
        .. note:: Cloud sandbox is a feature that requires an engine license

        :param str license_key: license key for specific engine
        :param str license_token: license token for specific engine
        :param str sandbox_type: 'local_sandbox' or 'cloud_sandbox'
        :param str,SandboxService service: a sandbox service element from SMC. The service
            defines which location the engine is in and which data centers to use.
            The default is to use the 'Automatic' profile if undefined.
        :return: None
        """
        if not self.is_sandbox_enabled:
            if not service:
                service = SandboxService('Automatic').href
            else:
                service = element_resolver(service)
            
            if min_smc_version(6.3):
                sandbox = dict(sandbox_license_key=license_key,
                               sandbox_license_token=license_token,
                               sandbox_service=service)
                self.data.update(sandbox_settings=sandbox,
                                 sandbox_type=sandbox_type)
            else:
                sandbox = dict(cloud_sandbox_license_key=license_key,
                               cloud_sandbox_license_token=license_token,
                               sandbox_service=service)
                self.data.update(cloud_sandbox_settings=sandbox,
                                 sandbox_type=sandbox_type)
                
            #self.data.update(cloud_sandbox_settings=sandbox)
            #self.data.update(sandbox_type='cloud_sandbox')

    @autocommit(now=False)
    @deprecated('engine.sandbox')
    def disable_sandbox(self, **kw):
        """
        Disable sandbox on this engine

        :raises UnsupportedEngineFeature: Requires engine version >= 6.2
        :return: None
        """
        if self.is_sandbox_enabled:
            self.data['sandbox_type'] = 'none'
            self.data.pop('cloud_sandbox_settings', None)
            self.data.pop('sandbox_settings', None)

    @property
    @deprecated('engine.url_filtering')
    def is_url_filtering_enabled(self):
        """
        Is URL Filtering enabled on this engine. This requires an additional
        engine license.

        :raises UnsupportedEngineFeature: Not allowed on virtual engine
        :rtype: bool
        """
        if not self.type.startswith('virtual'):
            return self.data['ts_settings'].get('ts_enabled')
        raise UnsupportedEngineFeature(
            'Enabling URL Filtering should be done on the Master Engine, not '
            'directly on the virtual engine.')

    @autocommit(now=False)
    @deprecated('engine.url_filtering')
    def enable_url_filtering(self, **kw):
        """
        Enable URL Filtering on this engine.

        .. note:: URL Filtering requires an engine feature license

        :raises UpdateElementFailed: failure enabling URL Filtering on engine
        :return: None
        """
        if not self.is_url_filtering_enabled:
            self.data.update(ts_settings={'ts_enabled': True})

    @autocommit(now=False)
    @deprecated('engine.url_filtering')
    def disable_url_filtering(self, **kw):
        """
        Disable URL Filtering on this engine.

        :raises UpdateElementFailed: failed disabling URL Filtering
        :return: None
        """
        if self.is_url_filtering_enabled:
            self.data.update(ts_settings={'ts_enabled': False})
