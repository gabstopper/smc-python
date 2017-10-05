Release History
===============

0.5.6
-----

.. note:: For older release release history information, see CHANGELOG. All future documentation will be logged
	in this document.

**Improvements**

- Support SMC 6.3:
    - Support for L2 interface policies (Inline L2, IPS and Capture interfaces on L3 engine)
    - Route based VPN support, IPSEC wrapped RBVPN and GRE Tunnel/Transport/No Encryption VPN.
- SMC 6.3 API only supports TLSv1.2 or greater, ensure your openssl version supports TLSv1.2. This can be done
  by: openssl s_client -connect <smc_ip>:8082 -tls1_2
- Simplified generic Search (`smc.base.collections.Search`) to be uniform with ElementCollection.
- Simplify API reference documentation
- SMC login using environment variables. See session documentation for more info.
- Rule counters on all Policy types
- Proxy or static type required when adding arp entry to interface
- Add simple .get() method on Element. This simplifies determining if the element by name exists. For example,
  Host.get('kali') would raise ElementNotFound if it doesn't exist. Prior to this, you would have to search
  for the element and attempt to access and element resource before receiving the ElementNotFound message,
  i.e. host = Host('kali'); host.address. The 'get()' method still returns an 'un-inflated' instance (only meta
  data).
- Deprecation warnings are now generated for functions in `smc.core.engine.interfaces`:
  `add_single_node_interface`, `add_node_interface`, `add_vlan_to_node_interface`, `add_ipaddress_to_vlan_interface`.
  These functions will eventually be deprecated. As of version 6.3, SMC engines can now support both layer 2 and
  layer 3 interfaces on the same engine. New interface functions added: `add_layer3_vlan_interface`, `add_layer3_interface`,
  `add_inline_ips_interface`, `add_inline_l2fw_interface`.
- New element types: URLCategory, URLCategoryGroup, ICMPServiceGroup


.. important:: Renamed `smc.vpn.policy.VPNPolicy` to `smc.vpn.policy.PolicyVPN`

**Bugfixes**

- HTTP GET was treating a 204 response as an error, fix to treat No Content response as success.
- Fix help() on dynamic `create_collection` class so constructor methods are proxied properly
- Raise SMCConnectionError when non-HTTP 200 error code presented from SMC when retrieving entry points
- Sending empty payload on POST request with parameters might cause validation error. Do not submit empty
  dict with POST requests.
