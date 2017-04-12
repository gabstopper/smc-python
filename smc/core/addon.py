"""
Add-Ons provide helper functions to enable, disable or configure 
features of an Engine after it has already been created.

Once these settings have been modified, it is still required to update
the policy on the engine or install a policy for the first time. 

To refresh policy::

    engine = Engine('vm')
    engine.add_dns_servers(['3.3.3.3', '4.4.4.4'])
    engine.enable_gti_file_reputation()
    engine.enable_antivirus(log_level='stored')
    for status in engine.refresh():
        print(status)

Installing new policy::

    engine = Engine('vm')
    engine.add_dns_servers(['3.3.3.3', '4.4.4.4'])
    for status in engine.upload(policy='vm-fw', wait_for_finish=True):
        print(status)

.. note::
    Many of these settings can also be set on the ``create`` method when
    creating the engine.
    
"""
from smc.base.model import Element
from smc.routing.ospf import OSPFProfile
from smc.api.exceptions import UnsupportedEngineFeature
from smc.elements.profiles import DNSRelayProfile

class EngineFeature:
    """
    Engine features that enable specific functionality and can be
    set or changed after the engine exists. Each setting requires
    that policy be refreshed to take effect.
    """
    def enable_dns_relay(self, interface_id, dns_relay_profile=None):
        """
        DNS Relay allows the engine to provide DNS caching or specific
        host, IP and domain replies to clients. It can also be used 
        to sinkhole specific DNS requests.
        
        :param str,Element dns_relay_profile: DNSRelayProfile or href
        :param int interface_id: interface id to enable relay
        :raises EngineCommandFailed: interface not found
        :raises ElementNotFound: profile not found
        :raises UpdateElementFailed: failure message from SMC
        :raises UnsupportedEngineFeature: unsupported engine type or version
        :return: None
        """
        if not self.is_dns_relay_enabled:
            if dns_relay_profile is None: #Use default
                dns_relay_profile = DNSRelayProfile('Cache Only')
    
            if isinstance(dns_relay_profile, Element):
                dns_relay_profile = dns_relay_profile.href
            else:
                dns_relay_profile = dns_relay_profile
            
            data = self.physical_interface.get(interface_id)
            
            d = dict(dns_relay_profile_ref=dns_relay_profile)
            d.update(dns_relay_interface=([{'address':ip,'nicid':nicid} 
                                            for ip,_,nicid in data.addresses]))
            self.data.update(**d)
            self.update()
       
    def disable_dns_relay(self):
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
            self.update()
    
    @property
    def is_dns_relay_enabled(self):
        """
        Status of DNS Relay on this engine.
        
        :raises UnsupportedEngineFeature: unsupported engine type or version
        :return: boolean is the service enabled
        """
        if 'dns_relay_interface' in self.data:
            if 'dns_relay_profile_ref' in self.data:
                return True
            return False
        raise UnsupportedEngineFeature('DNS Relay requires engine version '
                                       '>= v6.2')

    @property
    def is_sidewinder_proxy_enabled(self):
        """
        Status of Sidewinder Proxy on this engine
        
        :raises UnsupportedEngineFeature: feature requires >= v6.1
        :return: boolean is enabled
        """
        if 'sidewinder_proxy_enabled' in self.data:
            return self.data['sidewinder_proxy_enabled']
        raise UnsupportedEngineFeature('Sidewinder Proxy is only supported '
                                       'on engines version >= 6.1')
        
    def enable_sidewinder_proxy(self):
        """
        Enable Sidewinder Proxy on this engine. This requires
        engine version >= 6.2.
        
        :raises UpdateElementFailed: failure message from SMC
        :raises UnsupportedEngineFeature: unsupported engine type or version
        :return: None
        """
        if not self.is_sidewinder_proxy_enabled:
            self.data.update(sidewinder_proxy_enabled=True)
            self.update()
        
    def disable_sidewinder_proxy(self):
        """
        Disable Sidewinder Proxy on this engine. This requires
        engine version >= 6.2.
        
        :raises UpdateElementFailed: failure message from SMC
        :raises UnsupportedEngineFeature: unsupported engine type or version
        :return: None
        """
        if self.is_sidewinder_proxy_enabled:
            self.data['sidewinder_proxy_enabled'] = False
            self.update()
    
    @property    
    def is_gti_enabled(self):
        """
        Is McAfee GTI File Reputation enabled on this engine.
        
        :return: boolean is enabled
        """
        gti = self.data['gti_settings'].get('file_reputation_context')
        if gti == 'disabled':
            return False
        return True
    
    def enable_gti_file_reputation(self):
        """
        Enable McAfee GTI File Reputation on this engine. Enabling
        GTI requires DNS server settings and GTI must be enabled on
        the global properties within SMC.
        
        :raises UpdateElementFailed: failure message from SMC
        :return: None
        """
        if not self.is_gti_enabled:
            gti = self.data['gti_settings']
            gti.update(file_reputation_context='gti_cloud_only')
            self.update()
    
    def disable_gti_file_reputation(self):
        """
        Disable McAfee GTI File Reputation on this engine.
        
        :raises UpdateElementFailed: failure message from SMC
        :return: None
        """
        if self.is_gti_enabled:
            gti = self.data['gti_settings']
            gti.update(file_reputation_context='disabled')
            self.update()
    
    @property
    def is_antivirus_enabled(self):
        return self.data['antivirus'].get('antivirus_enabled', False)
    
    def enable_antivirus(self, log_level='stored'):
        """
        Enable Antivirus on this engine. Enabling anti-virus requires
        DNS server settings to resolve the AV update servers.
        
        :raises UpdateElementFailed: failure message from SMC
        :param str log_level: none,transient,stored,essential,alert
        :return: None
        """
        if not self.is_antivirus_enabled:
            av = self.data['antivirus']
            av.update(antivirus_enabled=True,
                      virus_log_level=log_level)
            self.update()
    
    def disable_antivirus(self):
        """
        Disable Antivirus on this engine. 
        
        :raises UpdateElementFailed: failure message from SMC
        :return: None
        """
        if self.is_antivirus_enabled:
            av = self.data['antivirus']
            av.update(antivirus_enabled=False)
            self.update()

    @property
    def is_ospf_enabled(self):
        """
        Is OSPF enabled on this engine
        
        :raises UnsupportedEngineFeature: unsupported engine type
        :return: boolean is enabled
        """
        if 'dynamic_routing' in self.data:
            routing = self.data['dynamic_routing']
            ospf = routing.get('ospfv2')
            return ospf.get('enabled', False)
        raise UnsupportedEngineFeature('Dynamic routing is only supported '
                                       'on layer 3 engine types')
    
    def enable_ospf(self, ospf_profile=None, router_id=None):
        """
        Enable OSPF on this engine. Required field is
        an :py:class:`smc.routing.ospf.OSPFProfile`. Uses
        built in profile by default.
        
        :param str,OSPFProfile ospf_profile: profile element or href
        :param str router_id: single IP address router ID
        :raises UpdateElementFailed: failure message from SMC
        :raises ElementNotFound: ospf profile not found
        :raises UnsupportedEngineFeature: unsupported engine type or version
        :return: None
        """
        if not self.is_ospf_enabled:
            if ospf_profile is None:
                ospf_profile = OSPFProfile('Default OSPFv2 Profile') #Default
            
            if isinstance(ospf_profile, Element):
                profile = ospf_profile.href
            else:
                profile = ospf_profile
            routing = self.data['dynamic_routing']
            routing['ospfv2'] = {'enabled': True,
                                 'ospfv2_profile_ref': profile,
                                 'router_id': router_id}
            self.update()
            
    def disable_ospf(self):
        """
        Disable OSPF on this engine.
        
        :raises UpdateElementFailed: failure message from SMC
        :raises UnsupportedEngineFeature: unsupported engine type or version
        :return: None
        """
        if self.is_ospf_enabled:
            routing = self.data['dynamic_routing']
            routing['ospfv2'] = {'enabled': False}
            self.update()
    
    def add_dns_servers(self, dns_servers):
        """
        Add DNS servers to this engine.
        
        :param list dns_servers: DNS server addresses
        :return: None
        """
        for num, server in enumerate(dns_servers):
            self.data['domain_server_address'].append(
                {'rank': num, 'value': server})
        self.update()
    
    @property
    def dns_servers(self):
        """
        DNS Servers for this engine (if any). DNS Servers are
        used to resolve specific features enabled on the engine
        such as Anti-Virus updates.
        
        :return list DNS Servers configured
        """
        return [server.get('value')
                for server in self.data.get('domain_server_address')]

    @property
    def is_default_nat(self):
        """
        Default NAT provides NAT service by associating directly 
        attached networks with a NAT address of the exiting interface.
        This simplifies how NAT is handled without creating specific
        NAT rules.
        
        :return boolean is default nat enabled
        """
        if 'default_nat' in self.data:
            return self.data['default_nat']
        raise UnsupportedEngineFeature('This engine type does not support '
                                       'default NAT')
    
    def enable_default_nat(self):
        """
        Enable default NAT at the engine level for engines that
        support NAT (i.e. layer 3 engines)
        
        :raises UnsupportedEngineFeature: for engines that do not support
            default NAT
        :return: None
        """
        if not self.is_default_nat:
            self.data['default_nat'] = True
            self.update()
    
    def disable_default_nat(self):
        """
        Disable default NAT on this engine if supported.
        
        :raises UnsupportedEngineFeature: for engines that do not support
            default NAT
        :return: None
        """
        if self.is_default_nat:
            self.data['default_nat'] = False
            self.update()