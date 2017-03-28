from smc.base.model import Element, ElementCreator, prepared_request, SubElement
from smc.api.exceptions import CreatePolicyFailed, CreateElementFailed,\
    PolicyCommandFailed, ElementNotFound

class VPNPolicy(Element):
    """
    Create a new VPN Policy
    
    vpn = VPNPolicy.create('myVPN')
    print vpn.vpn_profile
    print vpn.describe()
    
    When making VPN Policy modifications, you must first call :py:func:`open`, 
    make your modifications and then call :py:func:`save` followed by 
    :py:func:`close`.
    
    :ivar name: name of policy
    :ivar vpn_profile: reference to used VPN profile
    :ivar nat: whether NAT is enabled on the VPN policy
    :ivar mobile_vpn_topology_mode: where to allow remote clients
    """
    typeof = 'vpn'
 
    def __init__(self, name, **meta):
        super(VPNPolicy, self).__init__(name, **meta)
        pass
    
    @classmethod
    def create(cls, name, nat=False, mobile_vpn_toplogy_mode=None,
               vpn_profile=None):
        """
        Create a new policy based VPN
        
        :param name: name of vpn policy
        :param boolean nat: whether to apply NAT to the VPN (default False)
        :param mobile_vpn_toplogy_mode: whether to allow remote vpn
        :param str vpn_profile: reference to VPN profile, or uses default
        :return: :py:class:`~VPNPolicy`
        """
        cls.json = {'mobile_vpn_topology_mode': None,
                    'name': name,
                    'nat': nat,
                    'vpn_profile': vpn_profile}
        
        try:
            ElementCreator(cls)
            return VPNPolicy(name)
        except CreateElementFailed as err:
            raise CreatePolicyFailed('VPN Policy create failed. Reason: {}'
                                     .format(err))
    
    @property
    def nat(self):
        """ 
        Is NAT enabled on this vpn policy
        
        :return: True|False
        """
        return self.data.get('nat')

    @property
    def vpn_profile(self):
        """
        Specified VPN Profile used by this VPN Policy
        
        :return: :py:class:`smc.vpn.elements.VPNProfile`
        """
        return self.data.get('vpn_profile')

    @property
    def central_gateway_node(self):
        """
        Central Gateway Node acts as the hub of a hub-spoke VPN. 
        
        :return: list :class:`CentralGatewayNode`
        """
        return CentralGatewayNode(href=self.resource.central_gateway_node)

    @property
    def satellite_gateway_node(self):
        """
        Node level settings for configured satellite gateways
        
        :return: list :class:`SatelliteGatewayNode`
        """
        return SatelliteGatewayNode(href=self.resource.satellite_gateway_node)
    
    @property
    def mobile_gateway_node(self):
        """
        Mobile Gateway's are represented by client endpoints connecting
        to the policy based VPN.
        
        :return: list :class:`MobileGatewayNode`
        """
        return MobileGatewayNode(href=self.resource.mobile_gateway_node)
    
    def open(self):
        """
        Open the policy for editing
        
        :return: None
        :raises: :py:class:`smc.api.exceptions.PolicyCommandFailed`
        """
        prepared_request(PolicyCommandFailed,
                         href=self.resource.open
                         ).create()

    def save(self):
        """
        Save the policy after editing
        
        :return: None
        :raises: :py:class:`smc.api.exceptions.PolicyCommandFailed`
        """
        prepared_request(PolicyCommandFailed,
                         href=self.resource.save
                         ).create()
    
    def close(self):
        """
        Close the policy 
        
        :return: None
        :raises: :py:class:`smc.api.exceptions.PolicyCommandFailed`
        """
        prepared_request(PolicyCommandFailed,
                         href=self.resource.close
                         ).create()
                
    def validate(self):
        """
        :method: GET
        """
        return self.resource.get('validate')
       
    def gateway_tunnel(self):
        """
        :method: GET
        """
        return self.resource.get('gateway_tunnel')
    
    def add_central_gateway(self, gateway):
        """ 
        Add SMC managed internal gateway to the Central Gateways of this VPN
        
        :param gateway: href for internal gateway or test_external gateway.
               If this is another SMC managed gateway, you can retrieve the 
               href after loading the engine. 
               See :py:class:`smc.core.engines.Engine.internal_gateway`
        :return: :py:class:`smc.api.web.SMCResult`
        """
        prepared_request(PolicyCommandFailed,
                         href=self.resource.central_gateway_node, 
                         json={'gateway': gateway,
                               'node_usage':'central'}
                         ).create()

    def add_satellite_gateway(self, gateway):
        """
        Add gateway node as a satellite gateway for this VPN. You must first
        have the gateway object created. This is typically used when you either 
        want a hub-and-spoke topology or the test_external gateway is a non-SMC 
        managed device.
        
        :param gateway: href for internal gateway or test_external gateway.
               If this is another SMC managed gateway, you can retrieve the 
               href after loading the engine. 
               See :py:class:`smc.core.engines.Engine.internal_gateway` 
        :return: :py:class:`smc.api.web.SMCResult`
        """
        prepared_request(PolicyCommandFailed,
                         href=self.resource.satellite_gateway_node,
                         json={'gateway': gateway,
                               'node_usage':'satellite'}
                         ).create() 
    
    @staticmethod
    def add_internal_gateway_to_vpn(internal_gateway_href, vpn_policy, 
                                    vpn_role='central'):
        """
        Add an internal gateway (managed engine node) to a VPN policy
        based on the internal gateway href.
        
        :param str internal_gateway_href: href for engine internal gw
        :param str vpn_policy: name of vpn policy
        :param str vpn_role: central|satellite
        :return: boolean True for success
        """
        try:
            vpn = VPNPolicy(vpn_policy)
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

class GatewayNode(object):
    """
    Top level VPN gateway node operations
    """
    @property
    def name(self):
        """
        Get the name from the gateway_profile reference
        """
        return self.resource.name(self.data.get('gateway'))
    
    def enabled(self):
        pass
    
    def disabled(self):
        pass
   
    def all(self):
        """
        Return all Gateways by type for this VPN Policy
        
        :return: list CentralGatewayNode: gateway nodes on this vpn
        """
        return [type(self)(**node)
                for node in self._get_resource(self.href)]

class CentralGatewayNode(GatewayNode, SubElement):
    def __init__(self, **meta):
        super(CentralGatewayNode, self).__init__(**meta)
        pass
   
class SatelliteGatewayNode(GatewayNode, SubElement):
    def __init__(self, **meta):
        super(SatelliteGatewayNode, self).__init__(**meta)
        pass

class MobileGatewayNode(GatewayNode, SubElement):
    def __init__(self, **meta):
        super(MobileGatewayNode, self).__init__(**meta)
        pass 
