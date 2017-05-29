"""
Properties provide helper functions to enable, disable or configure
features of an Engine after it has already been created. When a setting
is modified, the engine instance is updated, however not submitted to the
SMC until calling .update(). Alternatively, you can provide the kwarg 
'autocommit=True' to force the update immediately.

Once these settings have been modified, it is still required to update
the policy on the engine or install a policy for the first time.

For functions with the ``**kw`` parameter, you can optionally provide 
``autocommit=True`` which will save the change to the SMC at the end of
the function call. Otherwise the change is 'queued' in the elements cache
until self.update() is called.

To refresh policy::

    engine = Engine('vm')
    engine.add_dns_servers(['3.3.3.3', '4.4.4.4'])
    engine.enable_gti_file_reputation()
    engine.enable_antivirus(log_level='stored', autocommit=True)
    #engine.update()    <-- without 'autocommit=True', call .update() to save
    for status in engine.refresh().wait():
        print(status)

Installing new policy::

    engine = Engine('vm')
    engine.add_dns_servers(['3.3.3.3', '4.4.4.4'])
    engine.update()
    for status in engine.upload(policy='vm-fw').wait():
        print(status)

.. note::
    Many of these settings can also be set on the ``create`` method when
    creating the engine.

"""
from smc.base.model import Element
from smc.base.decorators import autocommit
from smc.routing.ospf import OSPFProfile
from smc.api.exceptions import UnsupportedEngineFeature
from smc.elements.profiles import DNSRelayProfile
from smc.routing.bgp import BGPProfile
from smc.base.util import element_resolver


class EngineProperty:
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
    def is_sidewinder_proxy_enabled(self):
        """
        Status of Sidewinder Proxy on this engine

        :raises UnsupportedEngineFeature: feature requires >= v6.1
        :rtype: bool
        """
        if 'sidewinder_proxy_enabled' in self.data:
            return self.data['sidewinder_proxy_enabled']
        raise UnsupportedEngineFeature(
            'Sidewinder Proxy requires a layer 3 engine and version >= v6.1.')

    @autocommit(now=False)
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
    def enable_antivirus(self, log_level='stored', **kw):
        """
        Enable Antivirus on this engine. Enabling anti-virus requires
        DNS server settings to resolve the AV update servers.

        :param str log_level: none,transient,stored,essential,alert
        :raises UnsupportedEngineFeature: unsupported engine type
        :raises UpdateElementFailed: failure message from SMC
        :return: None
        """
        if not self.is_antivirus_enabled:
            av = self.data['antivirus']
            av.update(antivirus_enabled=True,
                      virus_log_level=log_level)
    
    @autocommit(now=False)
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
    def is_bgp_enabled(self):
        """
        Is BGP enabled on this engine. BGP is only supported on layer 3
        engines (virtual included).

        :raises UnsupportedEngineFeature: unsupported engine type
        :rtype: bool
        """
        if 'dynamic_routing' in self.data:
            routing = self.data['dynamic_routing']
            ospf = routing.get('bgp')
            return ospf.get('enabled', False)
        raise UnsupportedEngineFeature(
            'Dynamic routing is only supported on layer 3 engine types')

    @autocommit(now=False)
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
        if not self.is_bgp_enabled:
            autonomous_system = element_resolver(autonomous_system)

            if not bgp_profile:
                bgp_profile = BGPProfile('Default BGP Profile').href
            else:
                bgp_profile = element_resolver(bgp_profile)

            announced = [{'announced_ne_ref': network}
                         for network in element_resolver(announced_networks)]

            routing = self.data['dynamic_routing']
            routing['bgp'] = {
                'enabled': True,
                'bgp_as_ref': autonomous_system,
                'bgp_profile_ref': bgp_profile,
                'announced_ne_setting': announced,
                'router_id': router_id}

    @autocommit(now=False)
    def disable_bgp(self, **kw):
        """
        Disable BGP on this engine.

        :raises UnsupportedEngineFeature: BGP not supported on this engine type
        :return: None
        """
        if self.is_bgp_enabled:
            routing = self.data['dynamic_routing']
            routing['bgp'] = {
                'enabled': False,
                'announced_ne_setting': []}

    @property
    def is_ospf_enabled(self):
        """
        Is OSPF enabled on this engine

        :raises UnsupportedEngineFeature: unsupported engine type
        :rtype: bool
        """
        if 'dynamic_routing' in self.data:
            routing = self.data['dynamic_routing']
            ospf = routing.get('ospfv2')
            return ospf.get('enabled', False)
        raise UnsupportedEngineFeature(
            'Dynamic routing is only supported on layer 3 engine types')

    @autocommit(now=False)
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
        :raises UpdateElementFailed: failure message from SMC
        :raises ElementNotFound: ospf profile not found
        :raises UnsupportedEngineFeature: unsupported engine type or version
        :return: None
        """
        if not self.is_ospf_enabled:
            if not ospf_profile:
                ospf_profile = OSPFProfile('Default OSPFv2 Profile').href
            else:
                ospf_profile = element_resolver(ospf_profile)

            routing = self.data['dynamic_routing']
            routing['ospfv2'] = {
                'enabled': True,
                'ospfv2_profile_ref': ospf_profile,
                'router_id': router_id}

    @autocommit(now=False)
    def disable_ospf(self, **kw):
        """
        Disable OSPF on this engine.

        :raises UpdateElementFailed: failure message from SMC
        :raises UnsupportedEngineFeature: unsupported engine type or version
        :return: None
        """
        if self.is_ospf_enabled:
            routing = self.data['dynamic_routing']
            routing['ospfv2'] = {'enabled': False}

    @autocommit(now=False)
    def add_dns_servers(self, dns_servers, **kw):
        """
        Add DNS servers to this engine.

        :param list dns_servers: DNS server addresses
        :return: None
        """
        for num, server in enumerate(dns_servers):
            self.data['domain_server_address'].append(
                {'rank': num, 'value': server})

    @property
    def dns_servers(self):
        """
        DNS Servers for this engine (if any). DNS Servers are
        used to resolve specific features enabled on the engine
        such as Anti-Virus updates.

        :return: DNS Servers configured
        :rtype: list
        """
        return [server.get('value')
                for server in self.data.get('domain_server_address')]

    @property
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
    def enable_sandbox(self, license_key, license_token,
                       service=None, **kw):
        """
        Enable cloud sandbox on this engine. Cloud sandbox provides the ability to
        extract file type content and interrogate for behavioral purposes to
        discover malicious embedded content. Provide a valid license key and
        license token obtained from your engine licensing.

        .. note:: Cloud sandbox is a feature that requires an engine license

        :param str license_key: license key for specific engine
        :param str license_token: license token for specific engine
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

            sandbox = dict(cloud_sandbox_license_key=license_key,
                           cloud_sandbox_license_token=license_token,
                           sandbox_service=service)
            self.data.update(cloud_sandbox_settings=sandbox)
            self.data.update(sandbox_type='cloud_sandbox')

    @autocommit(now=False)
    def disable_sandbox(self, **kw):
        """
        Disable sandbox on this engine

        :raises UnsupportedEngineFeature: Requires engine version >= 6.2
        :return: None
        """
        if self.is_sandbox_enabled:
            self.data['sandbox_type'] = 'none'
            self.data.pop('cloud_sandbox_settings')

    @property
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
    def disable_url_filtering(self, **kw):
        """
        Disable URL Filtering on this engine.

        :raises UpdateElementFailed: failed disabling URL Filtering
        :return: None
        """
        if self.is_url_filtering_enabled:
            self.data.update(ts_settings={'ts_enabled': False})

    @property
    def location(self):
        """
        The location for this engine (may be Default).

        :return: :class:`smc.elements.other.Location` or None
        """
        return Element.from_href(self.data.get('location_ref'))

    @autocommit(now=False)
    def set_location(self, location, **kw):
        """
        Set the location for this engine.
        ::

            Location.create(name='mylocation')
            engine.set_location(Location('mylocation'))

        :param str,Element location: provide Location element or href of
            location to set. If setting back to default, use None.
        :raises ElementNotFound: if location provided is not found
        :raises UpdateElementFailed: failure to update element
        :return: None
        """
        location = element_resolver(location)
        self.data['location_ref'] = location

    @property
    def log_server(self):
        """
        Log server for this engine.

        :return: :class:`smc.elements.servers.LogServer`
        """
        return Element.from_href(self.data.get('log_server_ref'))

    @property
    def gateway_setting_profile(self):
        """
        A gateway settings profile defines VPN specific settings related
        to timers such as negotiation retries (min, max) and mobike
        settings. Gateway settings are only present on layer 3 FW
        types.

        :return: :class:`smc.vpn.elements.GatewaySettings`

        .. note::
            This can return None on layer 3 firewalls if VPN is not
            enabled.
        """
        gw_settings = self.data.get('gateway_settings_ref')
        if gw_settings:
            return Element.from_href(gw_settings)

    def add_vpn_site(self, name, site_elements):
        """
        Add a new VPN Site element to this engine.
        Provide site elements to add. Site elements are the networks, hosts,
        etc resources that specify the protected VPN networks for this
        engine. Once the site is created, it can be modified through an
        engine reference::
        
            for x in engine.internal_gateway.vpn_site.all():
                .....
        
        :param str name: name for VPN site
        :param list site_elements: network elements for VPN site
        :type site_elements: list(str,Element)
        :raises ElementNotFound: if site element is not found
        :raises UpdateElementFailed: failed to add vpn site
        :return: href of new element
        :rtype: str
        
        .. note:: As this is a create operation, this function does not require
            an additional call to save the operation.
        """
        site_elements = site_elements if site_elements else []
        return self.internal_gateway.vpn_site.create(
            name, site_elements)
        
    
class SandboxService(Element):
    typeof = 'sandbox_service'

    def __init__(self, name, **meta):
        super(SandboxService, self).__init__(name, **meta)
        pass
