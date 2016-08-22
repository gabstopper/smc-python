"""
VPN Configuration

Create a VPN external gateway to be used in a Policy Based VPN configuration.
An External Gateway is a non-SMC managed peer defining the remote IP connectivity
information as well as the remote network site information.
Sites are defined to identify the remote networks protected behind the VPN peer
network.

"""
from smc.elements.element import Network
from smc.elements.engines import Engine
from smc.elements.vpn import ExternalGateway, ExternalEndpoint, VPNPolicy
from smc.api.session import session

if __name__ == '__main__':
    
    session.login(url='http://172.18.1.150:8082', api_key='EiGpKD4QxlLJ25dbBEp20001')
    
    """
    An external gateway defines a non-SMC managed gateway device that acts as a 
    remote VPN peer. 
    First create the external gateway element
    """
    external_gateway = ExternalGateway.create('myextgw')
    
    """
    An external endpoint is defined within the external gateway and specifies the
    IP address settings and other VPN specific settings for this endpoint
    After creating, add to the external gateway
    """
    external_endpoint = ExternalEndpoint.create(name='myendpoint', 
                                                address='2.2.2.2')
    
    external_gateway.add_external_endpoint(external_endpoint)
    
    """
    Lastly, 'sites' need to be configured that identify the network/s on the
    other end of the VPN. You can either use pre-existing network elements, or create
    new ones as in the example below.
    Then add this site to the external gateway
    """    
    network = Network('remote-network', '1.1.1.0/24').create().href
    
    external_gateway.add_site('remote-site', [network])

    """
    Retrieve the internal gateway for SMC managed engine by loading the
    engine configuration. The internal gateway reference is located as
    engine.internal_gateway.href
    """
    engine = Engine('aws-02').load()

    """
    Create the VPN Policy
    """
    vpn = VPNPolicy.create(name='myVPN', nat=True)
    print vpn.name, vpn.vpn_profile
    
    vpn.open()
    vpn.add_central_gateway(engine.internal_gateway.href)
    vpn.add_satellite_gateway(external_gateway.href)
    vpn.save()
    vpn.close()
    
    session.logout()
    