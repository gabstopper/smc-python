Release History
===============

0.5.6
-----

.. note:: For older release release history information, see CHANGELOG. All future documentation will be logged
	in this document.

**Improvements**

- Support SMC 6.3:
    - Support for L2 interface policies (Inline L2, IPS and Capture interfaces on L3 engine)
    - Route based VPN support
- Rename :py:class:`smc.vpn.policy.VPNPolicy` to :py:class:`smc.vpn.policy.PolicyVPN`
- Simplified generic Search (:py:class:`smc.base.collections.Search`) to be uniform with ElementCollection.
- Simplify API reference documentation
- SMC login using environment variables. See session documentation for more info.


**Bugfixes**

- HTTP GET was treating a 204 response as an error, fix to treat No Content response as success.
- Fix help() on dynamic `create_collection` class so constructor methods are proxied properly
- Raise SMCConnectionError when non-HTTP 200 error code presented from SMC when retrieving entry points

