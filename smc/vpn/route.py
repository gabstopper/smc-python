"""
.. versionadded:: 0.5.6
    Route based VPNs with multi-domain support, requires SMC >=6.3

Module for configuring Route Based VPN.
Creating a route based VPN consists of creating a local and remote tunnel
endpoint. Once you have the required endpoints, use TunnelEndpoint
classmethods to create the VPN by type (i.e. GRE, IPSEC).

List all existing route based VPNs::

    print(list(RouteVPN.objects.all()))
    
Example of fully provisioning an IPSEC wrapped RBVPN using a third
party remote GW::

    engine = Layer3Firewall.create(
        name='fw1', mgmt_ip='1.1.1.1', mgmt_network='1.1.1.0/24')
    
    # RBVPN requires a tunnel interface
    engine.tunnel_interface.add_single_node_interface(
        tunnel_id=1000,
        address='2.2.2.2',
        network_value='2.2.2.0/24')
    
    # Enable the internal VPN gateway
    for vpn in engine.vpn_endpoint:
        vpn.update(enabled=True)
        
    # Create the local Tunnel Endpoint using the engine internal gateway
    # and previously created tunnel interface
    tunnel_if = engine.tunnel_interface.get(1000)
    local_gateway = TunnelEndpoint.create_ipsec_endpoint(engine.vpn.internal_gateway, tunnel_if)
    
    # Create the remote side network elements
    Network.create(name='remotenet', ipv4_network='172.18.10.0/24')
    
    # An ExternalGateway defines the remote side details
    # Create the element, define the remote IP and network on other end
    gw = ExternalGateway.create(name='remotegw')
    gw.external_endpoint.create(name='endpoint1', address='10.10.10.10')
    gw.vpn_site.create(name='remotesite', site_element=[Network('remotenet')])
    
    # Create the remote Tunnel Endpoint using the external gateway
    remote_gateway = TunnelEndpoint.create_ipsec_endpoint(gw)
    
    RouteVPN.create_ipsec_tunnel(
        name='myvpn', 
        local_endpoint=local_gateway, 
        remote_endpoint=remote_gateway)
        

Create a GRE Tunnel Mode RBVPN with a remote gateway (non-SMC managed)::

    engine = Engine('fw') 
    
    # Enable VPN endpoint on interface 0 
    # Note: An interface can have multiple IP addresses in which case you 
    # may want to get the VPN endpoint match by address 
    vpn_endpoint = None 
    for endpoint in engine.vpn_endpoint: 
        if endpoint.physical_interface.interface_id == '0': 
            endpoint.update(enabled=True) 
            vpn_endpoint = endpoint
            break
     
    # Create a new Tunnel Interface for the engine 
    engine.tunnel_interface.add_single_node_interface( 
        tunnel_id=3000, address='30.30.30.30', network_value='30.30.30.0/24') 
    
    tunnel_interface =  engine.tunnel_interface.get(3000)
    local_endpoint = TunnelEndpoint.create_gre_tunnel_endpoint( 
        endpoint=vpn_endpoint, tunnel_interface=tunnel_interface) 
 
    # Create GRE tunnel endpoint for remote gateway 
    remote_endpoint = TunnelEndpoint.create_gre_tunnel_endpoint( 
        remote_address='10.1.1.2') 
    
    # Create the top level IPSEC tunnel to encapsulate RBVPN 
    policy_vpn = PolicyVPN.create(name='myIPSEC') 
     
    RouteVPN.create_gre_tunnel_mode( 
        name='mytunnelvpn',  
        local_endpoint=local_endpoint,  
        remote_endpoint=remote_endpoint,  
        policy_vpn=policy_vpn) 

Create a no-encryption GRE route based VPN between two managed NGFWs::

    engine1 = Layer3Firewall.create(name='engine1', mgmt_ip='1.1.1.1', mgmt_network='1.1.1.0/24')
    engine1.tunnel_interface.add_single_node_interface( 
        tunnel_id=1000, 
        address='2.2.2.2', 
        network_value='2.2.2.0/24')
    
    # Obtain the 'internal endpoint' from the NGFW and enable VPN
    for vpn in engine1.vpn_endpoint:
        internal_endpoint = vpn
        vpn.update(enabled=True)
        
    tunnel_if = engine1.tunnel_interface.get(1000) 
    local_gateway = TunnelEndpoint.create_gre_tunnel_endpoint(
        internal_endpoint, tunnel_if)
    
    engine2 = Layer3Firewall.create(name='engine2', mgmt_ip='1.1.1.1', mgmt_network='1.1.1.0/24')
    engine2.tunnel_interface.add_single_node_interface( 
        tunnel_id=1000, 
        address='2.2.2.2', 
        network_value='2.2.2.0/24')
    
    # Obtain the 'internal endpoint' from the NGFW and enable VPN
    for vpn in engine2.vpn_endpoint:
        internal_endpoint = vpn
        vpn.update(enabled=True)
    
    tunnel_if = engine2.tunnel_interface.get(1000) 
    remote_gateway = TunnelEndpoint.create_gre_tunnel_endpoint(
        internal_endpoint, tunnel_if)
    
    RouteVPN.create_gre_tunnel_no_encryption(
        name='openvpn', 
        local_endpoint=local_gateway,
        remote_endpoint=remote_gateway)

"""
from smc.base.model import Element, ElementCreator
from smc.core.engine import InternalEndpoint
from smc.vpn.elements import VPNProfile
from smc.api.exceptions import CreateElementFailed, CreateVPNFailed


class RouteVPN(Element):
    """
    Route based VPN in NGFW.
    """
    typeof = 'rbvpn_tunnel'
    
    @classmethod
    def create_ipsec_tunnel(cls, name, local_endpoint, remote_endpoint,
                            preshared_key, monitoring_group=None,
                            vpn_profile=None, mtu=0, pmtu_discovery=True,
                            ttl=0, enabled=True, comment=None):
        """
        The VPN tunnel type negotiates IPsec tunnels in the same way
        as policy-based VPNs, but traffic is selected to be sent into
        the tunnel based on routing.
        
        :param str name: name of VPN
        :param TunnelEndpoint local_endpoint: the local side endpoint for
            this VPN.
        :param TunnelEndpoint remote_endpoint: the remote side endpoint for
            this VPN.
        :param TunnelMonitoringGroup monitoring_group: the group to place
            this VPN in for monitoring. Default: 'Uncategorized'.
        :param VPNProfile vpn_profile: VPN profile for this VPN.
            (default: VPN-A Suite)
        :param int mtu: Set MTU for this VPN tunnel (default: 0)
        :param boolean pmtu_discovery: enable pmtu discovery (default: True)
        :param int ttl: ttl for connections on the VPN (default: 0)
        :param bool enabled: enable the RBVPN or leave it disabled
        :param str comment: optional comment
        :raises CreateVPNFailed: failed to create the VPN with reason
        :return: RouteVPN
        """
        group = monitoring_group if monitoring_group else \
            TunnelMonitoringGroup('Uncategorized')
        profile = vpn_profile if vpn_profile else VPNProfile('VPN-A Suite')
        
        json = {
            'name': name,
            'mtu': mtu,
            'ttl': ttl,
            'enabled': enabled,
            'monitoring_group_ref': group.href,
            'pmtu_discovery': pmtu_discovery,
            'preshared_key': preshared_key,
            'rbvpn_tunnel_side_a': local_endpoint.data,
            'rbvpn_tunnel_side_b': remote_endpoint.data,
            'tunnel_mode': 'vpn',
            'comment': comment,
            'vpn_profile_ref': profile.href
        }
        
        try:
            return ElementCreator(cls, json)
        except CreateElementFailed as err:
            raise CreateVPNFailed(err)
        
    @classmethod
    def create_gre_tunnel_mode(cls, name, local_endpoint, remote_endpoint,
                          policy_vpn, mtu=0, pmtu_discovery=True, ttl=0,
                          enabled=True, comment=None):
        """
        Create a GRE based tunnel mode route VPN. Tunnel mode GRE wraps the
        GRE tunnel in an IPSEC tunnel to provide encrypted end-to-end
        security. Therefore a policy based VPN is required to 'wrap' the
        GRE into IPSEC. 
        
        :param str name: name of VPN
        :param TunnelEndpoint local_endpoint: the local side endpoint for
            this VPN.
        :param TunnelEndpoint remote_endpoint: the remote side endpoint for
            this VPN.
        :param PolicyVPN policy_vpn: reference to a policy VPN
        :param TunnelMonitoringGroup monitoring_group: the group to place
            this VPN in for monitoring. (default: 'Uncategorized')
        :param int mtu: Set MTU for this VPN tunnel (default: 0)
        :param boolean pmtu_discovery: enable pmtu discovery (default: True)
        :param int ttl: ttl for connections on the VPN (default: 0)
        :param str comment: optional comment
        :raises CreateVPNFailed: failed to create the VPN with reason
        :return: RouteVPN
        """
        json = {
            'name': name,
            'ttl': ttl,
            'mtu': mtu,
            'pmtu_discovery': pmtu_discovery,
            'tunnel_encryption': 'tunnel_mode',
            'tunnel_mode': 'gre',
            'enabled': enabled,
            'comment': comment,
            'rbvpn_tunnel_side_a': local_endpoint.data,
            'rbvpn_tunnel_side_b': remote_endpoint.data
        }
        if policy_vpn is None:
            json['tunnel_encryption'] = 'no_encryption'
        else:
            json['tunnel_mode_vpn_ref'] = policy_vpn.href
          
        try:
            return ElementCreator(cls, json)
        except CreateElementFailed as err:
            raise CreateVPNFailed(err)
    
    @classmethod
    def create_gre_tunnel_no_encryption(cls, name, local_endpoint, remote_endpoint,
                          mtu=0, pmtu_discovery=True, ttl=0,
                          enabled=True, comment=None):
        """
        Create a GRE Tunnel with no encryption. See `create_gre_tunnel_mode` for
        constructor descriptions.
        """
        return cls.create_gre_tunnel_mode(
            name, local_endpoint, remote_endpoint, policy_vpn=None,
            mtu=mtu, pmtu_discovery=pmtu_discovery, ttl=ttl,
            enabled=enabled, comment=comment)
               
    @classmethod
    def create_gre_transport_mode(cls, name, local_endpoint, remote_endpoint,
                             preshared_key, monitoring_group=None,
                             vpn_profile=None, mtu=0, ttl=0,
                             pmtu_discovery=True, enabled=True, comment=None):
        """
        Create a transport based route VPN. This VPN type uses IPSEC
        for protecting the payload, therefore a VPN Profile is specified.
        
        :param str name: name of VPN
        :param TunnelEndpoint local_endpoint: the local side endpoint for
            this VPN.
        :param TunnelEndpoint remote_endpoint: the remote side endpoint for
            this VPN.
        :param str preshared_key: preshared key for RBVPN
        :param TunnelMonitoringGroup monitoring_group: the group to place
            this VPN in for monitoring. (default: 'Uncategorized')
        :param VPNProfile vpn_profile: VPN profile for this VPN.
            (default: VPN-A Suite)
        :param int mtu: Set MTU for this VPN tunnel (default: 0)
        :param boolean pmtu_discovery: enable pmtu discovery (default: True)
        :param int ttl: ttl for connections on the VPN (default: 0)
        :param str comment: optional comment
        :raises CreateVPNFailed: failed to create the VPN with reason
        :return: RouteVPN
        """
        group = monitoring_group if monitoring_group else \
            TunnelMonitoringGroup('Uncategorized')
        profile = vpn_profile if vpn_profile else VPNProfile('VPN-A Suite')
        
        json = {
            'name': name,
            'mtu': mtu,
            'ttl': ttl,
            'preshared_key': preshared_key,
            'pmtu_discovery': pmtu_discovery,
            'monitoring_group_ref': group.href,
            'rbvpn_tunnel_side_a': local_endpoint.data,
            'rbvpn_tunnel_side_b': remote_endpoint.data,
            'tunnel_encryption': 'transport_mode',
            'vpn_profile_ref': profile.href,
            'tunnel_mode': 'gre',
            'enabled': enabled,
            'comment': comment
        }
        
        try:
            return ElementCreator(cls, json)
        except CreateElementFailed as err:
            raise CreateVPNFailed(err)
    
    def enable(self):
        """
        Enable this route based VPN
        
        :return: None
        """
        if not self.enabled:
            self.update(enabled=True)
    
    def disable(self):
        """
        Disable this route based VPN
        
        :return: None
        """
        if self.enabled:
            self.update(enabled=False)
    
    def set_preshared_key(self, new_key):
        """
        Set the preshared key for this VPN. A pre-shared key is only
        present when the tunnel type is 'VPN' or the encryption mode
        is 'transport'.
        
        :return: None
        """
        if self.data.get('preshared_key'):
            self.update(preshared_key=new_key)
      
    @property
    def local_endpoint(self):
        """
        The local endpoint for this RBVPN
        
        :return: TunnelEndpoint
        """
        return TunnelEndpoint(**self.rbvpn_tunnel_side_a)
    
    @property
    def remote_endpoint(self):
        """
        The remote endpoint for this RBVPN
        
        :return: TunnelEndpoint
        """
        return TunnelEndpoint(**self.rbvpn_tunnel_side_b)
    
    @property
    def tunnel_mode(self):
        """
        The tunnel mode for this RBVPN
        
        :rtype: str
        """
        return self.data.get('tunnel_mode')
    
    @property
    def monitoring_group(self):
        """
        Each RBVPN can be placed into a monitoring group for
        visibility from the Home page. This RBVPN monitoring
        group.
        
        :return: TunnelMonitoringGroup
        """
        return Element.from_href(self.monitoring_group_ref)
    
    @property
    def vpn_profile(self):
        """
        VPN profile for this RBVPN
        
        :return: VPNProfile
        """
        if self.data.get('vpn_profile_ref'):
            return Element.from_href(self.vpn_profile_ref)


class TunnelMonitoringGroup(Element):
    """
    A tunnel monitoring group is used to group route based VPNs
    for monitoring on the Home->VPN dashboard.
    """
    typeof = 'rbvpn_tunnel_monitoring_group'


class TunnelEndpoint(object):
    """
    A Tunnel Endpoint represents one side of a route based VPN.
    Based on the RBVPN type required, you must create the local
    and remote endpoints and pass them into the RouteVPN create
    classmethods.
    """
    def __init__(self, gateway_ref=None, tunnel_interface_ref=None,
                 endpoint_ref=None, ip_address=None):
        self.gateway_ref = gateway_ref
        self.tunnel_interface_ref= tunnel_interface_ref
        self.endpoint_ref = endpoint_ref
        self.ip_address = ip_address
        
    @classmethod
    def create_gre_tunnel_endpoint(cls, endpoint=None, tunnel_interface=None,
                                   remote_address=None):
        """
        Create the GRE tunnel mode or no encryption mode endpoint.
        If the GRE tunnel mode endpoint is an SMC managed device,
        both an endpoint and a tunnel interface is required. If the
        endpoint is externally managed, only an IP address is required.
        
        :param InternalEndpoint,ExternalEndpoint endpoint: the endpoint
            element for this tunnel endpoint.
        :param TunnelInterface tunnel_interface: the tunnel interface for
            this tunnel endpoint. Required for SMC managed devices.
        :param str remote_address: IP address, only required if the tunnel
            endpoint is a remote gateway.
        :return: TunnelEndpoint
        """
        tunnel_interface = tunnel_interface.href if tunnel_interface else None
        endpoint = endpoint.href if endpoint else None
        return TunnelEndpoint(
            tunnel_interface_ref=tunnel_interface,
            endpoint_ref=endpoint,
            ip_address=remote_address)
    
    @classmethod
    def create_gre_transport_endpoint(cls, endpoint, tunnel_interface=None):
        """
        Create the GRE transport mode endpoint. If the GRE transport mode
        endpoint is an SMC managed device, both an endpoint and a tunnel
        interface is required. If the GRE endpoint is an externally managed
        device, only an endpoint is required.
        
        :param InternalEndpoint,ExternalEndpoint endpoint: the endpoint
            element for this tunnel endpoint.
        :param TunnelInterface tunnel_interface: the tunnel interface for
            this tunnel endpoint. Required for SMC managed devices.
        :return: TunnelEndpoint
        """
        tunnel_interface = tunnel_interface.href if tunnel_interface else None
        return TunnelEndpoint(
            endpoint_ref=endpoint.href,
            tunnel_interface_ref=tunnel_interface)
    
    @classmethod
    def create_ipsec_endpoint(cls, gateway, tunnel_interface=None):
        """    
        Create the VPN tunnel endpoint. If the VPN tunnel endpoint
        is an SMC managed device, both a gateway and a tunnel interface
        is required. If the VPN endpoint is an externally managed
        device, only a gateway is required.
        
        :param InternalGateway,ExternalGateway gateway: the gateway
            for this tunnel endpoint
        :param TunnelInterface tunnel_interface: Tunnel interface for
            this RBVPN. This can be None if the gateway is a non-SMC
            managed gateway.
        :return: TunnelEndpoint
        """
        tunnel_interface = tunnel_interface.href if tunnel_interface else None
        return TunnelEndpoint(
            gateway_ref=gateway.href,
            tunnel_interface_ref=tunnel_interface)
    
    @property
    def data(self):
        return {k: v for k, v in vars(self).items() if v}
            
    @property
    def gateway(self):
        """
        The gateway referenced in this tunnel endpoint. Gateway will either
        be an InternalGateway (SMC managed) or ExternalGateway (non-SMC managed)
        element. Gateway references are used in IPSEC wrapped RBVPN's.
        
        :return InternalGateway,ExternalGateway: gateway reference for the VPN
        """
        if self.gateway_ref:
            return Element.from_href(self.gateway_ref)
    
    @property
    def tunnel_interface(self):
        """
        Show the tunnel interface for this TunnelEndpoint.
        
        :return TunnelInterface: interface for this endpoint
        """
        if self.tunnel_interface_ref:
            return Element.from_href(self.tunnel_interface_ref)
   
    @property
    def endpoint(self):
        """
        Endpoint is used to specify which interface is enabled for
        VPN. This is the InternalEndpoint property of the
        InternalGateway.
        
        :return InternalEndpoint: internal endpoint where VPN is enabled.
        """
        if self.endpoint_ref:
            return InternalEndpoint(href=self.endpoint_ref)
    
    @property
    def remote_address(self):
        """
        Show the remote IP address configured for a GRE RBVPN using Tunnel
        or No Encryption Mode configurations.
        """
        return self.ip_address
    