Collections
-----------

Resource collections are designed to be similar to how Django query sets work and provide a similar API. 

Collections are available on all elements that inherit from :py:class:`smc.base.model.Element`, and are also available for general searching
purposes. 

To access a collection directly on an Element type::

	>>> list(Host.objects.all())
 	[Host(name=SMC), Host(name=172.18.1.135), Host(name=172.18.2.254), Host(name=host)]
	...
	>>> list(TCPService.objects.filter('HTTP'))
 	[TCPService(name=HTTPS_No_Decryption), TCPService(name=Squid HTTP proxy), TCPService(name=HTTP to Web SaaS)]
 	
Limit number of return entries::

	>>> list(Host.objects.limit(3))
 	[Host(name=SMC), Host(name=172.18.1.135), Host(name=172.18.2.254)]

Limit and filter the results using a chainable syntax::

	>>> list(Host.objects.filter('172.18.1').limit(5))
	[Host(name=172.18.1.135), Host(name=SMC), Host(name=ePolicy Orchestrator), Host(name=TIE Server), Host(name=172.18.1.93)]
 
You can also obtain the iterator from the connection manager to re-use::

	>>> iterator = Host.objects
	>>> list(iterator.filter('kali'))
	[Host(name=kali)]
	>>> list(iterator.filter('host').limit(3))
	[Host(name=host), Host(name=host-54.76.110.156), Host(name=host-192.168.4.135)]

Filtering can also be done using keys of a given element. For example, TCP Services define ports for the services and can be filtered::

  >>> list(TCPService.objects.filter('8080'))
  [TCPService(name=TCP_8080), TCPService(name=HTTP proxy)]

Likewise, an example filtering Host collections based on IP address::

  >>> list(Host.objects.filter('192.168'))
  [Host(name=aws-192.168.4.254), Host(name=host-192.168.4.135), Host(name=host-192.168.4.94), Host(name=host-192.168.4.79)]

Filtering is not limited to a single filter item, it is also possible to provide a list of filterable fields. All matches will be returned::

  >>> list(TCPService.objects.filter(['8080', '22']))
  [TCPService(name=TCP_8080), TCPService(name=HTTP proxy), TCPService(name=SSH), TCPService(name=ssh_2222), TCPService(name=SSM SSH), TCPService(name=ssh_2200), TCPService(name=H.323 (Call Signaling))]

When filtering is performed, by default search queries will 'wildcard' the results. To only return an exact match of the search query,
use the optional flag 'exact_match'::

  >>> list(TCPService.objects.filter(['8080', '22'], exact_match=True))
  [TCPService(name=TCP_8080), TCPService(name=HTTP proxy), TCPService(name=SSH), TCPService(name=SSM SSH)]

----

If a search is reuqired for an element type that is not a pre-defined class of :py:class:`smc.base.model.Element` type 
in the API, it is still possible to search any valid entry point using :py:class:`smc.elements.resources.Search`.

First, find all available searchable objects::

  >>> from smc.elements.resources import Search
  >>> Search.object_types()
  ['elements', 'sub_ipv6_fw_policy', 'ids_alert', 'application_not_specific_tag', 'fw_alert', 'virtual_ips', 'sidewinder_tag', 'os_specific_tag', 'eia_application_usage_group_tag', 'external_bgp_peer', 'local_cluster_cvi_alias', 'ssl_vpn_service_profile', 'active_directory_server', 'eia_golden_image_tag', 'client_gateway', 'situation_tag', 'api_client', 'tls_match_situation', 'ssl_vpn_policy', 'category_group_tag', 'ip_list', 'vpn_profile', 'ipv6_access_list', 'appliance_information', 'single_layer2', 'ei_executable', 'community_access_list']
  ...
 
Once the type of interest is found, the elements can be retrieved using the object type as the filter::

  >>> list(Search('vpn').objects.all())
  [VPNPolicy(name=Amazon AWS), VPNPolicy(name=sg_vm_vpn), VPNPolicy(name=TRITON AP-WEB Cloud VPN)]

And subsequently filtering as well::

  >>> list(Search('vpn').objects.filter('AWS'))
  [VPNPolicy(name=Amazon AWS)]

There are additional search filters that provide the ability to generalize your searches:

*fw_clusters* - list all firewalls

*engine_clusters* - all clusters

*ips_clusters* - ips only clusters

*layer2_clusters* - layer2 only clusters
                    
*network_elements* - all network element types

*services* - all service types

*services_and_applications* - all services and applications

*tags* - element tags

*situations* - inspection situations

----

Searching all services for port 80::

	>>> list(Search('services').objects.filter('80'))
	[TCPService(name=tcp80443), TCPService(name=HTTP to Web SaaS), EthernetService(name=IPX over Ethernet 802.2), UDPService(name=udp_10070-10080), Protocol(name=HTTP8080), TCPService(name=tcp_10070-10080), TCPService(name=TCP_8080), TCPService(name=tcp_3478-3480), EthernetService(name=IPX over Ethernet 802.3 (Novell)), TCPService(name=HTTP), TCPService(name=SSM HTTP), TCPService(name=HTTP (SafeSearch)), IPService(name=ISO-IP), UDPService(name=udp_3478-3480), TCPService(name=HTTP (with URL Logging))]

Only Network elements with '172.18.1'::

	>>> list(Search('network_elements').objects.filter('172.18.1'))
	[Host(name=172.18.1.135), Host(name=SMC), Network(name=Any network), FirewallCluster(name=sg_vm), Element(name=dc-smtp), Network(name=network-172.18.1.0/24), LogServer(name=LogServer 172.18.1.150), Layer3Firewall(name=testfw), Element(name=SecurID), Element(name=Windows 2003 DHCP), AddressRange(name=range-172.18.1.100-172.18.1.120), ManagementServer(name=Management Server)]

Only firewall clusters::

	>>> list(Search('fw_clusters').objects.all())
	[FirewallCluster(name=sg_vm), Layer3VirtualEngine(name=ve-8), Layer3Firewall(name=testfw), Layer3Firewall(name=i-04eec8f019adf818e (us-east-2a)), MasterEngine(name=master)]

In addition to using more generic filters, with general searches, you can also specify multiple valid entry points by 
specifying the string filter comma seperated.

For example, finding all hosts and routers::

	>>> list(Search('router,host').objects.all())
	[Host(name=172.18.2.254), Router(name=router-172.18.3.129), Host(name=All Routers (Site-Local))]
	
Filter based on hosts and routers::

	>>> list(Search('router,host').objects.filter('172.18.1'))
	[Host(name=172.18.1.135), Host(name=SMC), Host(name=ePolicy Orchestrator), Router(name=router-172.18.1.225), Host(name=fw-internal-primary), Router(name=router-172.18.1.209)]

.. note:: If an element of class :py:class:`smc.base.model.Element` exists, it will 
   be returned as that type to enable access to the objects instance methods. If there is no element defined,
   a dynamic class is produced from type Element.

For example, searching for object of type 'ids_alert' will produce a dynamic class as type Element and will have access to the base class methods::

  >>> list(Search('ids_alert').objects.all())
  [Ids_AlertElement(name=Default alert), Ids_AlertElement(name=Test alert), Ids_AlertElement(name=System alert)]
  
Classes deriving from :py:class:`smc.base.model.Element` are found in the API reference, for example: :ref:`element-reference-label`
