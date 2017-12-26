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
  
0.5.8
-----

**Improvements**

- Support for SMC version 6.3.0, 6.3.1 and 6.3.2
- Add ``case_sensitive`` key word to filtered queries. This requires SMC 6.3+. Set this as a kwarg when making
  the query: Host.objects.filter('myhost', case_sensitive=False). Default: case_sensitive=True.
- Optimize retrieval of nodes by serializing engine node data versus making a call to the engine links. This eliminates
  the query to get the node links and a query for each node that needs to be operated on, or node payload required.
- Add `smc.core.node.ApplianceInfo` and link on node to retrieve appliance related info:
	appliance = node.appliance_info()
	...
- GatewayTunnel implemented on PolicyVPN for setting preshared key, enabling/disabling specific tunnel endpoints
- BGP node added to engine. Add full create/modify/delete capability by reference: engine.bgp.is_enabled, etc. Added to
  provide modular configuration to BGP.
- OSPF node added to engine. Add full create/modify/delete capability by reference: engine.ospf.is_enabled, etc.
- merging lists on element update will now filter out duplicate entries before potentially updating. The SMC API protects
  against this but validation moved into element update function saving potential exception on PUT
- get_or_create and update_or_create return classmethod get for elements that are considered read-only; i.e. do not have
  a `create` classmethod.
- update_or_create will now check the provided key/value pairs before updating the specified element. This is to make
  the modification more idempotent. If the retrieved element exists and has the same value (based on current ETag), then
  do not modify.
- Optimization of resolved alias retrieval from the engine. Instead of retrieving all aliases and resolving the alias
  reference, first retrieve the entire list of aliases (1 query) and then correlate to resolved alias references. This
  amounts to reducing the number of queries to retrieve a single engines aliases from ~60 to 3.
- set_stream_logger and set_file_logger attached to smc.api.session.Session() as convenience functions.
- Optimize logging at request level, more clear output
- Simplify interface creating where zone or logical interface is needed. Now zone/logical interfaces can be provided
  as either name (if they don't exist, they will be created), as href, or as Zone/LogicalInterface instances.
- New engine level resources: antivirus, file_reputation, sidewinder_proxy, sandbox and url_filtering, policy_routing,
  dns and default nat added as engine resources. Previous functions nested in smc.core.properties.AddOns set to deprecated
  and will be removed in the near future.
- Added support for adding DNS Server entries to engines based on elements (previously only IP addresses were supported).
- TLS Server Credentials supported for inbound SSL decryption, add to engine from engine.tls_inspection resource.
- Add create_hook to ElementCreator to intercept json before submitting to SMC server. See smc.base.decorators.create_hook
  for more info.
- Added engine.interface_options node for settings related to setting primary mgt, backup mgt, primary hearbeat, and backup heartbeat
  rather than having them nested on the PhysicalInterface. These can be called directly from the engine which removes ambiguity in how
  these settings are modified. Previous versions they could be called directly (i.e. engine.physical_interface.set_primary_mgt() however
  required unnecessary plumbing. This more closely models the SMC UI configuration.
- All engine interface nodes now return InterfaceCollection as an iterable. Also included is a get(interface_id) method to 
  directly retrieve an interface of that type. Any 'add' methods are proxied from the collection manager to an instance.
- remove_vlan on interface no longer requires the interface reference, however now requires the interface context to run. Before:
  engine.physical_interface.remove_vlan(interface_id=100, vlan_id=1), now you need to load the interface, then delete the
  vlan: interface = engine.interface.get(100); interface.remove_vlan(1)
- history property on Element added
  
 **Bugfixes**
 
 - If a search is provided in format: Host.objects.filter(address='1.1.1.1').first(), and the search returns meta but the
   filtered results do not return a match, the method tries to pop from an empty list. Return None instead.

