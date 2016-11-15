from smc.base.util import find_link_by_name
from smc.base.model import Element, ElementCreator, prepared_request
from smc.base.model import Meta
from smc.api.exceptions import CreatePolicyFailed
import smc.actions.search as search

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
 
    def __init__(self, name, meta=None):
        self._name = name
        self.meta = meta
    
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
        
        result = ElementCreator(cls)
        if result.href:
            return VPNPolicy(name)
        else:
            raise CreatePolicyFailed('VPN Policy create failed. Reason: {}'
                                     .format(result.msg))
    
    @property
    def nat(self):
        """ 
        Is NAT enabled on this vpn policy
        
        :return: True|False
        """
        result = search.element_by_href_as_json(self.href)
        return result.get('nat')

    @property
    def vpn_profile(self):
        """
        Specified VPN Profile used by this VPN Policy
        
        :return: :py:class:`smc.vpn.elements.VPNProfile`
        """
        result = search.element_by_href_as_json(self.href)
        return result.get('vpn_profile')

    @property
    def central_gateway_node(self):
        """
        Central Gateway Node acts as the hub of a hub-spoke VPN. 
        
        :method: GET
        :return: list `~CentralGatewayNode`
        """
        href = find_link_by_name('central_gateway_node', self.link)
        return CentralGatewayNode(meta=Meta(href=href))

    @property
    def satellite_gateway_node(self):
        """
        Node level settings for configured satellite gateways
        
        :method: GET
        :return: list `~SatelliteGatewayNode`
        """
        href = find_link_by_name('satellite_gateway_node', self.link)
        return SatelliteGatewayNode(meta=Meta(href=href))
    
    @property
    def mobile_gateway_node(self):
        """
        Mobile Gateway's are represented by client endpoints connecting
        to the policy based VPN.
        
        :method: GET
        :return: list `~MobileGatewayNode`
        """
        href = find_link_by_name('mobile_gateway_node', self.link)
        return MobileGatewayNode(meta=Meta(href=href))
    
    def open(self):
        """
        Open the policy for editing
        
        :method: POST
        :return: :py:class:`smc.api.web.SMCResult`
        """
        return prepared_request(
                    href=find_link_by_name('open', self.link)).create()

    def save(self):
        """
        Save the policy after editing
        
        :method: POST
        :return: :py:class:`smc.api.web.SMCResult`
        """
        return prepared_request(
                    href=find_link_by_name('save', self.link)).create()
    
    def close(self):
        """
        Close the policy 
        
        :method: POST
        :return: :py:class:`smc.api.web.SMCResult`
        """
        return prepared_request(
                    href=find_link_by_name('close', self.link)).create()
                
    def validate(self):
        """
        :method: GET
        """
        return search.element_by_href_as_json(
                    find_link_by_name('validate', self.link))
       
    def gateway_tunnel(self):
        """
        :method: GET
        """
        return search.element_by_href_as_json(
                    find_link_by_name('gateway_tunnel', self.link))
    
    def add_central_gateway(self, gateway):
        """ 
        Add SMC managed internal gateway to the Central Gateways of this VPN
        
        :param gateway: href for internal gateway or external gateway.
               If this is another SMC managed gateway, you can retrieve the 
               href after loading the engine. 
               See :py:class:`smc.core.engines.Engine.internal_gateway`
        :return: :py:class:`smc.api.web.SMCResult`
        """
        gateway_node = find_link_by_name('central_gateway_node', self.link)
        return prepared_request(href=gateway_node, 
                            json={'gateway': gateway,
                                  'node_usage':'central'}).create()

    def add_satellite_gateway(self, gateway):
        """
        Add gateway node as a satellite gateway for this VPN. You must first
        have the gateway object created. This is typically used when you either 
        want a hub-and-spoke topology or the external gateway is a non-SMC 
        managed device.
        
        :param gateway: href for internal gateway or external gateway.
               If this is another SMC managed gateway, you can retrieve the 
               href after loading the engine. 
               See :py:class:`smc.core.engines.Engine.internal_gateway` 
        :return: :py:class:`smc.api.web.SMCResult`
        """
        gateway_node = find_link_by_name('satellite_gateway_node', self.link)
        return prepared_request(href=gateway_node,
                            json={'gateway': gateway,
                                  'node_usage':'satellite'}).create() 
    
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
        from smc.elements.collection import describe_vpn
        success=False
        for vpn in describe_vpn():
            if vpn.name.startswith(vpn_policy):
                vpn.open()
                if vpn_role == 'central':
                    vpn.add_central_gateway(internal_gateway_href)
                else:
                    vpn.add_satellite_gateway(internal_gateway_href)
                vpn.save()
                vpn.close()
                success=True
                break
        return success

class GatewayNode(Element):
    """
    Top level VPN gateway node operations
    """
    @property
    def name(self):
        """
        Get the name from the gateway_profile reference
        """
        gateway = search.element_by_href_as_json(self.href).get('gateway')
        return search.element_by_href_as_json(gateway).get('name')

    def enabled(self):
        pass
    
    def disabled(self):
        pass
    
    def internal_gateway(self):
        pass
    
    def all(self):
        """
        Return all Central Gateways for this VPN Policy
        
        :return: list CentralGatewayNode: gateway nodes on this vpn
        """
        return [type(self)(meta=Meta(**node))
                for node in search.element_by_href_as_json(self.href)]

class CentralGatewayNode(GatewayNode):
    def __init__(self, meta=None):
        self.meta = meta
   
class SatelliteGatewayNode(GatewayNode):
    def __init__(self, meta=None):
        self.meta = meta

class MobileGatewayNode(GatewayNode):
    def __init__(self, meta=None):
        self.meta = meta  
