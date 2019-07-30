from smc.base.model import Element, ElementCreator, SubElement, ElementRef
from smc.api.exceptions import CreatePolicyFailed, CreateElementFailed,\
    PolicyCommandFailed, ElementNotFound
from smc.base.collection import sub_collection
from smc.vpn.elements import VPNProfile, VPNSite
from smc.base.decorators import cached_property
from smc.base.util import element_resolver
from smc.core.engine import InternalEndpoint


class PolicyVPN(Element):
    """
    Create a new VPN Policy.
    ::
    
        >>> PolicyVPN.create(name='myvpn')
        PolicyVPN(name=myvpn)
        >>> v = PolicyVPN('myvpn')
        >>> print(v.vpn_profile)
        VPNProfile(name=VPN-A Suite)

    When making VPN Policy modifications, you must first call :func:`open`, 
    make your modifications and then call :func:`save` followed by 
    :func:`close`.
    
    :ivar VPNProfile vpn_profile: VPN Profile used by this Policy VPN
    
    """
    typeof = 'vpn'
    vpn_profile = ElementRef('vpn_profile')

    @classmethod
    def create(cls, name, nat=False, mobile_vpn_toplogy_mode=None,
               vpn_profile=None):
        """
        Create a new policy based VPN

        :param name: name of vpn policy
        :param bool nat: whether to apply NAT to the VPN (default False)
        :param mobile_vpn_toplogy_mode: whether to allow remote vpn
        :param VPNProfile vpn_profile: reference to VPN profile, or uses default
        :rtype: PolicyVPN
        """
        vpn_profile = element_resolver(vpn_profile) or \
            VPNProfile('VPN-A Suite').href
        
        json = {'mobile_vpn_topology_mode': mobile_vpn_toplogy_mode,
                'name': name,
                'nat': nat,
                'vpn_profile': vpn_profile}

        try:
            return ElementCreator(cls, json)
        except CreateElementFailed as err:
            raise CreatePolicyFailed(err)

    @property
    def nat(self):
        """ 
        Is NAT enabled on this vpn policy

        :return: NAT enabled
        :rtype: bool
        """
        return self.data.get('nat')

    def enable_disable_nat(self):
        """
        Enable or disable NAT on this policy. If NAT is disabled, it
        will be enabled and vice versa.

        :return: None
        """
        if self.nat:
            self.data['nat'] = False
        else:
            self.data['nat'] = True

    @property
    def central_gateway_node(self):
        """
        Central Gateway Node acts as the hub of a hub-spoke VPN. 

        :rtype: SubElementCollection(GatewayNode)
        """
        return sub_collection(
            self.get_relation('central_gateway_node'),
            type('CentralGatewayNode', (GatewayNode,), {}))
        
    @property
    def satellite_gateway_node(self):
        """
        Node level settings for configured satellite gateways

        :rtype: SubElementCollection(GatewayNode)
        """
        return sub_collection(
            self.get_relation('satellite_gateway_node'),
            type('SatelliteGatewayNode', (GatewayNode,), {}))

    @property
    def mobile_gateway_node(self):
        """
        Mobile Gateway's are represented by client endpoints connecting
        to the policy based VPN.

        :rtype: SubElementCollection(GatewayNode)
        """
        return sub_collection(
            self.get_relation('mobile_gateway_node'),
            type('MobileGatewayNode', (GatewayNode,), {}))

    @property
    def tunnels(self):
        """
        Return all tunnels for this VPN. A tunnel is defined as two end
        points within the VPN topology. Endpoints are automatically
        configureed based on whether they are a central gateway or 
        satellite gateway. This provides access to enabling/disabling
        and setting the preshared key for the linked endpoints.
        List all tunnel mappings for this policy vpn::
        
            for tunnel in policy.tunnels:    
                tunnela = tunnel.tunnel_side_a
                tunnelb = tunnel.tunnel_side_b
                print(tunnela.gateway)
                print(tunnelb.gateway)
    
        :rtype: SubElementCollection(GatewayTunnel)
        """
        return sub_collection(
            self.get_relation('gateway_tunnel'), GatewayTunnel)

    def open(self):
        """
        Open the policy for editing. This is only a valid method for
        SMC version <= 6.1

        :raises PolicyCommandFailed: couldn't open policy with reason
        :return: None
        """
        self.make_request(
            PolicyCommandFailed,
            method='create',
            resource='open')

    def save(self):
        """
        Save the policy after editing. This is only a valid method for
        SMC version <= 6.1

        :raises PolicyCommandFailed: save failed with reason
        :return: None
        """
        self.make_request(
            PolicyCommandFailed,
            method='create',
            resource='save')
        self._del_cache()

    def close(self):
        """
        Close the policy. This is only a valid method for
        SMC version <= 6.1

        :raises PolicyCommandFailed: close failed with reason
        :return: None
        """
        self.make_request(
            PolicyCommandFailed,
            method='create',
            resource='close')

    def validate(self):
        """
        Return a validation string from the SMC after running validate on
        this VPN policy.
        
        :return: status as dict
        :rtype: dict
        """
        return self.make_request(resource='validate')

    @property
    def mobile_vpn_topology(self):
        """
        Is the policy VPN configured for mobile VPN gateways.
        Valid modes: 'Selected Gateways below', 'Only central Gateways from overall topology',
        'All Gateways from overall topology', 'None'
        """
        return self.data.get('mobile_vpn_topology_mode')
    
    def add_mobile_gateway(self, all_central_gateways=False, all_gateways=False,
                           gateways=None):
        """
        Add a mobile VPN gateway to this policy VPN. You can select all central
        gateways, all gateways in overall topology or specify a list of gateways
        to allow for mobile VPN.
        
        Example of adding or removing a mobile VPN gateway::
        
            policy_vpn = PolicyVPN('myvpn')
            policy_vpn.update(mobile_vpn_topology_mode='Selected Gateways below')
            policy_vpn.open()
            
            policy_vpn.add_mobile_vpn_gateway(gateways=Engine('azure'))
            
            policy_vpn.save()
            policy_vpn.close()
        
        :param Engine,ExternalGateway gateway: An external gateway, engine or
            href for the mobile gateway
        :raises PolicyCommandFailed: could not add gateway
        :rtype: None
        """
        if all_central_gateways:
            self.update(mobile_vpn_topology_mode='Only central Gateways from overall topology')
        elif all_gateways:
            self.update(mobile_vpn_topology_mode='All Gateways from overall topology')
        
        if gateways and self.mobile_vpn_topology != 'Selected Gateways below':
            raise PolicyCommandFailed('You must first update the policy VPN with '
                'the Selected Gateways below setting before adding members')
        
        if gateways:
            try:
                gateway = gateways.vpn.internal_gateway.href # Engine
            except AttributeError:
                raise PolicyCommandFailed('VPN endpoint does not appear to '
                    'be a managed engine: %s' % gateways)

            self.make_request(
                PolicyCommandFailed,
                method='create',
                resource='mobile_gateway_node',
                json={'gateway': gateway,
                      'node_usage': 'mobile'})

    def add_central_gateway(self, gateway):
        """ 
        Add SMC managed internal gateway to the Central Gateways of this VPN

        :param Engine,ExternalGateway gateway: An external gateway, engine or
            href for the central gateway
        :raises PolicyCommandFailed: could not add gateway
        :return: None
        """
        try:
            gateway = gateway.vpn.internal_gateway.href
        except AttributeError:
            gateway = element_resolver(gateway)
        self.make_request(
            PolicyCommandFailed,
            method='create',
            resource='central_gateway_node',
            json={'gateway': gateway,
                  'node_usage': 'central'})

    def add_satellite_gateway(self, gateway):
        """
        Add gateway node as a satellite gateway for this VPN. You must first
        have the gateway object created. This is typically used when you either 
        want a hub-and-spoke topology or the test_external gateway is a non-SMC 
        managed device.

        :param Engine,ExternalGateway gateway: An external gateway, engine or
            href for the central gateway
        :raises PolicyCommandFailed: could not add gateway
        :return: None
        """
        try:
            gateway = gateway.vpn.internal_gateway.href
        except AttributeError:
            gateway = element_resolver(gateway)
        self.make_request(
            PolicyCommandFailed,
            method='create',
            resource='satellite_gateway_node',
            json={'gateway': gateway,
                  'node_usage': 'satellite'})

    @staticmethod
    def add_internal_gateway_to_vpn(internal_gateway_href, vpn_policy,
                                    vpn_role='central'):
        """
        Add an internal gateway (managed engine node) to a VPN policy
        based on the internal gateway href.

        :param str internal_gateway_href: href for engine internal gw
        :param str vpn_policy: name of vpn policy
        :param str vpn_role: central|satellite
        :return: True for success
        :rtype: bool
        """
        try:
            vpn = PolicyVPN(vpn_policy)
            vpn.open()
            if vpn_role == 'central':
                vpn.add_central_gateway(internal_gateway_href)
            else:
                vpn.add_satellite_gateway(internal_gateway_href)
            vpn.save()
            vpn.close()
        except ElementNotFound:
            return False
        return True


class GatewayNode(SubElement):
    """
    Top level VPN gateway node operations. A gateway node is characterized
    by a Central Gateway, Satellite Gateway or Mobile Gateway node.
    This template class will return these as a collection. Gateway Node
    references need to be obtained from a VPN Policy reference::

        >>> vpn = PolicyVPN('sg_vm_vpn')
        >>> vpn.open()
        >>> for gw in vpn.central_gateway_node.all():
        ...   list(gw.enabled_sites)
        ... 
        [GatewayTreeNode(name=Automatic Site for sg_vm_vpn)]
        >>> vpn.close()
    """

    @cached_property
    def gateway(self):
        """
        The VPN gateway for this node. This is either an internal gateway
        or an external gateway
        
        :return: the VPN gateway
        :rtype: Element
        """ 
        return Element.from_href(self.data['gateway'])
        
    @property
    def name(self):
        """
        Get the name from the gateway_profile reference
        """
        return self.gateway.name
    
    @property
    def enabled_sites(self):
        """
        Return a collection of VPN Site elements that are enabled
        for this VPN gateway.

        :rtype: SubElementCollection(VPNSite)
        """
        return sub_collection(
            self.get_relation('enabled_vpn_site'), GatewayTreeNode)

    @property
    def disabled_sites(self):
        """
        Return a collection of VPN Site elements that are disabled
        for this VPN gateway.

        :rtype: SubElementCollection(VPNSite)
        """
        return sub_collection(
            self.get_relation('disabled_vpn_site'), GatewayTreeNode)


class GatewayTreeNode(SubElement):
    """
    Gateway Tree node is a list of VPN Site elements returned when retrieving
    a VPN policies enabled or disabled site list. These provide an
    enable_disable link to the VPN site.
    ::
    
        for gw in policy.central_gateway_node.all():
            for site in list(gw.enabled_sites):
                site.enable_disable()
    """
    @property
    def name(self):
        return self.vpn_site.name
    
    """
    A gateway tree node is a VPN site within either the central or 
    satellite gateway configuration within a VPN.
    """
    def enable_disable(self):
        """
        Enable or disable this VPN Site from within the VPN policy context.
        
        :raises PolicyCommandFailed: enabling or disabling failed
        :return: None
        """
        self.make_request(
            PolicyCommandFailed,
            method='delete',
            resource='self')
    
    @property
    def vpn_site(self):
        """
        The VPN Site element associated with this gateway
        
        :return VPNSite element
        :rtype: VPNSite
        """
        return VPNSite(href=self.data.get('vpn_site'))
    
    def __str__(self):
        return '{0}(name={1})'.format(
            self.__class__.__name__, self.name)

    def __repr__(self):
        return str(self)
    

class GatewayTunnel(SubElement):
    """
    A gateway tunnel represents the point to point connection
    between two IPSEC endpoints in a PolicyVPN configuration. 
    The tunnel arrangement is based on whether the nodes are placed
    as a central gateway or a satellite gateway. This provides access
    to see the point to point connections, whether the link is enabled,
    and setting the presharred key.
    
    .. note:: Setting the preshared key is only required if using an
        ExternalGateway element as one side of the VPN. Preshared keys
        are generated automatically but read only, therefore if two
        gateways are internally managed by SMC, the key is generated and
        shared between the gateways automatically. However for external
        gateways, you must set a new key to provide the same value to
        the remote gateway.
    """

    def enable_disable(self):
        """
        Enable or disable the tunnel link between endpoints.
        
        :raises UpdateElementFailed: failed with reason
        :return: None
        """
        if self.enabled:
            self.update(enabled=False)
        else:
            self.update(enabled=True)
    
    @property
    def enabled(self):
        """          
        Whether the VPN link between endpoints is enabled
        
        :rtype: bool
        """
        return self.data.get('enabled', False)
    
    def preshared_key(self, key):
        """
        Set a new preshared key for the IPSEC endpoints.
        
        :param str key: shared secret key to use
        :raises UpdateElementFailed: fail with reason
        :return: None
        """
        self.update(preshared_key=key)
    
    @property
    def tunnel_side_a(self):
        """
        Return the gateway node for tunnel side A. This will
        be an instance of GatewayNode.
        
        :rtype: GatewayNode
        """
        return type('TunnelSideA', (GatewayNode,), {
            'href': self.data.get('gateway_node_1')})()
    
    @property
    def tunnel_side_b(self):
        """
        Return the gateway node for tunnel side B. This will
        be an instance of GatewayNode.
        
        :rtype: GatewayNode
        """
        return type('TunnelSideB', (GatewayNode,), {
            'href': self.data.get('gateway_node_2')})()
    
    @property
    def endpoint_tunnels(self):
        """
        Return all Endpoint tunnels for this gateway tunnel. A tunnel is defined as two end
        points within the VPN topology. Endpoints are automatically
        configureed based on whether they are a central gateway or 
        satellite gateway. This provides access to enabling/disabling
        and setting the preshared key for the linked endpoints.
        List all Endpoint tunnel mappings for this policy vpn::
        
            for tunnel in policy.tunnels:    
                tunnela = tunnel.tunnel_side_a
                tunnelb = tunnel.tunnel_side_b
                print(tunnela.gateway)
                print(tunnelb.gateway)
                for endpointtunnel in tunnel.endpoint_tunnels:
                    print(endpointtunnel)
    
        :rtype: SubElementCollection(GatewayTunnel)
        """
        return sub_collection(
            self.get_relation('gateway_endpoint_tunnel'), EndpointTunnel)
    
    def __str__(self):
        return '{0}(tunnel_side_a={1},tunnel_side_b={2})'.format(
            self.__class__.__name__, self.tunnel_side_a.name, self.tunnel_side_b.name)

    def __repr__(self):
        return str(self)
    

class ClientGateway(Element):
    typeof = 'client_gateway'

class EndpointTunnel(SubElement):
    """
    A Endpoint tunnel represents the point to point connection
    between two IPSEC endpoints in a PolicyVPN configuration. 
    The tunnel arrangement is based on whether the nodes are placed
    as a central gateway or a satellite gateway. This provides access
    to see the point to point connections, whether the link is enabled,
    and setting the presharred key.
    """

    def enable_disable(self):
        """
        Enable or disable the tunnel link between endpoints.
        
        :raises UpdateElementFailed: failed with reason
        :return: None
        """
        if self.enabled:
            self.update(enabled=False)
        else:
            self.update(enabled=True)
    
    @property
    def enabled(self):
        """          
        Whether the VPN link between endpoints is enabled
        
        :rtype: bool
        """
        return self.data.get('enabled', False)
    
    
    @property
    def internal_endpoint_side_a(self):
        """
        Return the Internal Endpoint for tunnel side A. This will
        be an instance of InternalEndpoint.
        
        :rtype: InternalEndpoint
        """
        return type('TunnelSideA', (InternalEndpoint,), {
            'href': self.data.get('endpoint_1')})()
    
    @property
    def internal_endpoint_side_b(self):
        """
        Return the Internal Endpoint for tunnel side B. This will
        be an instance of InternalEndpoint.
        
        :rtype: InternalEndpoint
        """
        return type('TunnelSideB', (InternalEndpoint,), {
            'href': self.data.get('endpoint_2')})()
    
    def __str__(self):
        return '{0}(internal_endpoint_side_a={1},internal_endpoint_side_b={2})'.format(
            self.__class__.__name__, self.internal_endpoint_side_a.name, self.internal_endpoint_side_b.name)

    def __repr__(self):
        return str(self)
