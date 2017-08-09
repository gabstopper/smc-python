"""
.. versionadded:: 0.5.6
    Route based VPNs with multi-domain support, requires SMC >=6.3

Module for configuring Route Based VPN.
When creating RBVPN local and remote endpoints, use the TunnelEndpoint
create classmethods based on GRE or IPSEC VPN. 

List all existing route based VPNs::

    print(list(RouteVPN.objects.all()))
    
Example of creating an IPSEC wrapped RBVPN using a third party remote GW::

    engine = Engine('fw1')
    
    # Internal Gateway and Tunnel Interface
    gw = engine.internal_gateway
    tunnel_if = engine.tunnel_interface.get(1000)
    local_gateway = TunnelEndpoint.create_ipsec_endpoint(gw, tunnel_if)
    
    # Specify the pre-created 3rd party external gateway
    external = ExternalGateway('mygw')
    remote_gateway = TunnelEndpoint.create_ipsec_endpoint(external)
    
    RouteVPN.create_ipsec_tunnel(
        name='avpn', 
        local_endpoint=local_gateway, 
        remote_endpoint=remote_gateway)

Create a GRE Tunnel Mode RBVPN with a remote gateway (non-SMC managed)::

    engine = Engine('foo')
    
    # Enable VPN endpoint on interface 0
    # Note: An interface can have multiple IP addresses in which case you
    # may want to get the VPN endpoint match by address
    vpn_endpoint = None
    for endpoint in list(engine.vpn_endpoint):
        if endpoint.physical_interface.interface_id == '0':
            endpoint.enabled = True
            endpoint.update()
            vpn_endpoint = endpoint
    
    # Create a new Tunnel Interface for the engine
    engine.tunnel_interface.add_single_node_interface(
        tunnel_id=3000, address='30.30.30.30', network_value='30.30.30.0/24')
    
    local_endpoint = TunnelEndpoint.create_gre_tunnel_endpoint(
        endpoint=vpn_endpoint, tunnel_interface=engine.tunnel_interface.get(3000))

    # Create GRE tunnel endpoint for remote gateway
    remote_endpoint = TunnelEndpoint.create_gre_tunnel_endpoint(
        remote_address='1.1.1.1')
    
    policy_vpn = PolicyVPN.create(name='myIPSEC')
    
    RouteVPN.create_gre_tunnel(
        name='mytunnelvpn', 
        local_endpoint=local_endpoint, 
        remote_endpoint=remote_endpoint, 
        policy_vpn=policy_vpn)
        
"""
from smc.base.model import Element, ElementCreator
from smc.core.interfaces import TunnelInterface
from smc.core.engine import InternalEndpoint
from smc.vpn.elements import VPNProfile
from smc.api.exceptions import CreateElementFailed, CreateVPNFailed


class RouteVPN(Element):
    typeof = 'rbvpn_tunnel'
    
    def __init__(self, name, **meta):
        super(RouteVPN, self).__init__(name, **meta)
    
    @classmethod
    def create_ipsec_tunnel(cls, name, local_endpoint, remote_endpoint,
                            monitoring_group=None, vpn_profile=None,
                            mtu=0, pmtu_discovery=True, ttl=0,
                            comment=None):
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
        :param str comment: optional comment
        :raises CreateVPNFailed: failed to create the VPN with reason
        :return RouteVPN
        """
        group = monitoring_group if monitoring_group else \
            TunnelMonitoringGroup('Uncategorized')
        profile = vpn_profile if vpn_profile else VPNProfile('VPN-A Suite')
        
        json = {
            'name': name,
            'mtu': mtu,
            'ttl': ttl,
            'monitoring_group_ref': group.href,
            'pmtu_discovery': pmtu_discovery,
            'rbvpn_tunnel_side_a': local_endpoint.data,
            'rbvpn_tunnel_side_b': remote_endpoint.data,
            'tunnel_mode': 'vpn',
            'vpn_profile_ref': profile.href,
            'virtual_interface_vpn_ref': 'http://172.18.1.154:8082/6.3/elements/vpn/2'
            }
        
        try:
            return ElementCreator(cls, json)
        except CreateElementFailed as err:
            raise CreateVPNFailed(err)
        
    @classmethod
    def create_gre_tunnel(cls, name, local_endpoint, remote_endpoint,
                          policy_vpn, monitoring_group=None, mtu=0,
                          pmtu_discovery=True, ttl=0, preshared_key=None,
                          comment=None):
        """
        Create a GRE based route VPN.
        
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
        :return RouteVPN
        """
        group = monitoring_group if monitoring_group else \
            TunnelMonitoringGroup('Uncategorized')
        
        json = {
            'name': name,
            'ttl': ttl,
            'mtu': mtu,
            'pmtu_discovery': pmtu_discovery,
            'preshared_key': '',
            'tunnel_encryption': 'tunnel_mode',
            'tunnel_mode': 'gre',
            'tunnel_mode_vpn_ref': policy_vpn.href,
            'monitoring_group_ref': group.href,
            'rbvpn_tunnel_side_a': local_endpoint.data,
            'rbvpn_tunnel_side_b': remote_endpoint.data
            }
        
        from pprint import pprint
        pprint(json)
        try:
            return ElementCreator(cls, json)
        except CreateElementFailed as err:
            raise CreateVPNFailed(err)
            
    @classmethod
    def create_gre_transport(cls, name, local_endpoint, remote_endpoint,
                             preshared_key, monitoring_group=None,
                             vpn_profile=None, mtu=0, ttl=0,
                             pmtu_discovery=True, comment=None):
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
        :return RouteVPN
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
            'vpn_profile_ref': profile.href
            }
        
        try:
            return ElementCreator(cls, json)
        except CreateElementFailed as err:
            raise CreateVPNFailed(err)
      
    @property
    def local_endpoint(self):
        """
        The local endpoint for this RBVPN
        
        :return TunnelEndpoint
        """
        return TunnelEndpoint(**self.rbvpn_tunnel_side_a)
    
    @property
    def remote_endpoint(self):
        """
        The remote endpoint for this RBVPN
        
        :return TunnelEndpoint
        """
        return TunnelEndpoint(**self.rbvpn_tunnel_side_b)
    
    @property
    def tunnel_mode(self):
        """
        The tunnel mode for this RBVPN
        
        :rtype str
        """
        return self.data.get('tunnel_mode')
    
    @property
    def monitoring_group(self):
        """
        Each RBVPN can be placed into a monitoring group for
        visibility from the Home page. This RBVPN monitoring
        group.
        
        :return TunnelMonitoringGroup
        """
        return Element.from_href(self.monitoring_group_ref)
    
    @property
    def vpn_profile(self):
        """
        VPN profile for this RBVPN
        
        :return VPNProfile
        """
        if self.data.get('vpn_profile_ref'):
            return Element.from_href(self.vpn_profile_ref)


class TunnelMonitoringGroup(Element):
    """
    A tunnel monitoring group is used to group route based VPNs
    for monitoring on the Home->VPN dashboard.
    """
    typeof = 'rbvpn_tunnel_monitoring_group'
    
    def __init__(self, name, **meta):
        super(TunnelMonitoringGroup, self).__init__(name, **meta)


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
        :rtype: TunnelEndpoint
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
        :rtype: TunnelEndpoint
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
        :rtype: TunnelEndpoint
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
            return TunnelInterface(href=self.tunnel_interface_ref)
   
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
        Show the remote address for GRE RBVPN for Tunnel Mode or No
        Encryption Mode configurations.
        """
        return self.ip_address
    