VPN
---

It is possible to create VPN policy, all gateway elements and configurations related to
Policy Based VPN. Gateway's in the VPN configuration can be either managed engines or
remote gateawys (ExternalGateway).

There are several components or terminology required to set up a VPN.

- External Gateway: Non-SMC managed VPN endpoint
- External Endpoint: VPN Endpoint/s defined in external gateway (IP addresses, profiles)
- Sites: sites define the protected network/s for both sides of the VPN
- Internal Gateway: SMC managed layer 3 engine.

When creating a VPN to a non-managed device, an external gateway is required. This is a container
object used to encapsulate the remote endpoints where the VPN will terminate::

	>>> gateway = ExternalGateway.create('remoteside')
	
An external endpoint specifies the IP address settings and other VPN specific settings
for the external gateway.

Create the external endpoint from the gateway resource::

	>>> gateway.external_endpoint.create(name='remoteendpoint', address='2.2.2.2')
	'http://1.1.1.1:8082/6.1/elements/external_gateway/22961/external_endpoint/26740'
    
Lastly, 'sites' need to be configured that identify the network/s for the external gateway
side of the VPN. You can use pre-existing network elements, or create new ones as in the 
example below.

	>>> network = Network('internal-network')
	>>> print(network.href)
	http://1.1.1.1:8082/6.1/elements/network/17911
	...
	>>> gateway.vpn_site.create('remote-site', [network.href])
	'http://1.1.1.1:8082/6.1/elements/external_gateway/22961/vpn_site/22994'


Retrieve the engine internal gateway resource for the managed engine by obtaining the engine
context.

::

	>>> engine = Engine('testfw')
	>>> print(engine.internal_gateway.href)	#Internal gateway resource
	http://1.1.1.1:8082/6.1/elements/single_fw/39550/internal_gateway/11476
	
Create the VPN Policy and apply the internal gateway as the 'Central Gateway' and the
ExternalGateway as the 'Satellite Gateway'::
    
	>>> vpn = PolicyVPN.create(name='myVPN', nat=True)
	>>> print(vpn.name, vpn.vpn_profile)
	(u'myVPN', u'http://172.18.1.150:8082/6.1/elements/vpn_profile/2')
   	...
	>>> vpn.open()
	>>> vpn.add_central_gateway(engine.internal_gateway.href)
	>>> vpn.add_satellite_gateway(external_gateway.href)
	>>> vpn.save()
	>>> vpn.close()

.. note:: You must call :func:`smc.vpn.policy.PolicyVPN.open` before modifications can be
	      made. You also must call :func:`smc.vpn.policy.PolicyVPN.save` and 
	      :func:`smc.vpn.policy.PolicyVPN.close`
	  
See :py:mod:`smc.examples.vpn_to_external` for a full example 