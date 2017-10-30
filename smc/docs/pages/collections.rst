.. _collection-reference-label:

Collections
===========

Resource collections are designed to be similar to how Django query sets work and provide a similar API. 

ElementCollection
-----------------

ElementCollections are available on all elements that inherit from :py:class:`smc.base.model.Element`, and
are also available for general searching across any element with an SMC entry point.

An :py:class:`~smc.base.collection.ElementCollection` can be constructed without making a single query to the
SMC database. No query will occur until you do something to evaluate the collection.

You can evaluate a collection in the following ways:

* **Iteration**. An ElementCollection is iterable, and it executes the SMC query the first time you iterate over
  it. For example, this will retrieve all host elements::

	>>> for host in Host.objects.all():
	...    print(host.name, host.address)

* **list()**. Force evaluation of a collection by calling list() on it::

	>>> elements = list(Host.objects.all())

* :py:meth:`~smc.base.collection.ElementCollection.first`. Helper collection method to retrieve only the first element in the search query::

	>>> host = Host.objects.iterator()
	>>> host.first()
	Host(name=SMC)
	
If you don't need all results and only a single element, rather than getting an ElementCollection
iterator, you can obtain this directly from the CollectionManager::
	
	>>> Host.objects.first()
	Host(name=SMC)

* :py:meth:`~smc.base.collection.ElementCollection.last`. Helper collection method to retrieve only the last element in the search query::

	>>> host = Host.objects.iterator()
	>>> host.last()
	Host(name=kali3)
	
* :py:meth:`~smc.base.collection.ElementCollection.exists`. Helper collection method to evaluate whether there are results::

	>>> hosts = Host.objects.filter('1.1.1.1')
	>>> if hosts.exists():
	...   for host in list(hosts):
	...     print(host.name, host.address)
	... 
	('hax0r', '1.1.1.1')
	('host', '1.1.1.1')
	('hostelement', '1.1.1.1')
	('abcdefghijklmnop', '1.1.1.1')

* :py:meth:`~smc.base.collection.ElementCollection.count`. Helper collection method which returns the number of results.
  You can still obtain the results after::

	>>> it = Router.objects.iterator()
	>>> query1 = it.filter('10.10.10.1')
	>>> query1.count()
	3
	>>> list(query1)
	[Router(name=Router-110.10.10.10), Router(name=Router-10.10.10.10), Router(name=Router-10.10.10.1)]

* :py:meth:`~smc.base.collection.ElementCollection.batch`. Iterator returning batches of results with
  specific by quantity. If limit() is also chained, it is ignored as batch and limit are mutually
  exclusive operations.
  ::

	>>> for hosts in Host.objects.batch(2):
	...   print(hosts)
	... 
	[Host(name=SMC), Host(name=172.18.1.135)]
	[Host(name=172.18.2.254), Host(name=host)]
	[Host(name=host-54.76.110.156), Host(name=host-192.168.4.135)]
	[Host(name=external primary DNS resolver), Host(name=host-192.168.4.94)]
	...

Methods that return a new ElementCollection
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There are multiple methods in an ElementCollection that allow you to refine how the query or results are returned.
Each chained method returns a new ElementCollection with aggregated search parameters.

* :py:meth:`~smc.base.collection.ElementCollection.filter`. Provide a filter string to narrow the search to a string
  value that will be used in a 'contains' match::

	>>> host = Host.objects.filter('172.18.1')
	>>> list(host)
	[Host(name=172.18.1.135), Host(name=SMC)]

``filter`` can also take a keyword argument to filter specifically on an attribute. The keyword argument
should match a valid attribute for the element type, and value to match::

	>>> list(Router.objects.filter(address='10.10.10.1'))
	[Router(name=Router-10.10.10.1)]
	
.. note:: Two additional keyword arguments can be passed to filter, `exact_match=True` and/or
	`case_sensitive=False`. 

* :py:meth:`~smc.base.collection.ElementCollection.limit`. Limit the number of results to return.
  ::

	>>> list(Host.objects.all().limit(3))
	[Host(name=SMC), Host(name=172.18.1.135), Host(name=172.18.2.254)]

* :py:meth:`~smc.base.collection.ElementCollection.all`. Return all results.

	>>> list(Host.objects.all())

	
Basic rules on searching
^^^^^^^^^^^^^^^^^^^^^^^^

* By default searches use a 'contains' logic. If you specify a filter string, the SMC API will return elements that
  contain that string. Therefore, if partial searches are performed, you may receive multiple matches::
  
	>>> list(Router.objects.filter('10.10'))
	[Router(name=Router-110.10.10.10), Router(name=Router-10.10.10.10), Router(name=Router-10.10.10.1)]

* When the search is evaluated, the elements returned contain only meta data and not the full payload for each
  element matching the search. The search query is built based on provided parameters to narrow the scope and
  only a single query is made to SMC.
  
* When using a filter, the SMC API will search the name, comment and relevant field/s for the element type selected.

  Each element type will have it's own searchable fields. For example, in addition to the name and comment field, a Host
  element will search the address and secondary address fields. This is automatic.

  For example, the following would find Host elements with this value in any of the Host fields specified above::

	>>> Host.objects.filter('111.111.111.111')

* Setting ``exact_match=True`` on the filter query will only match on an element's name or comment field and is a case
  sensitive match. The SMC is case sensitive, so unless you need an element by exact case, this field is not required.
  By default, ``exact_match=False``.
  
* In v0.5.6, ``case_sensitive=False`` can be set on the filter query to change the behavior of case sensitive matches.
  If not set, case_sensitive=True.

* Using a keyword argument with 'filter' will provide element introspection against the attributes to perform an exact match.
  In general, using a kwarg is most effective when searching for network elements. Since the default search is a 'contains' match,
  a search for '10.10.10.1' may return elements with values: '10.10.10.1', '10.10.10.10', and '110.10.10.1'. Using an attribute/value
  would override the default search behavior and attempt to only match on the specified attribute::
  
	>>> list(Router.objects.filter('10.10.10.1'))
	[Router(name=Router-110.10.10.10), Router(name=Router-10.10.10.10), Router(name=Router-10.10.10.1)]
	
The above query returns multiple elements contains matches. To explicitly define the attribute to make an
exact match, change the filter to use a kwarg (the ``address`` attribute is the defined ipaddress for
:class:`smc.elements.network.Router`)::
	
	>>> list(Router.objects.filter(address='10.10.10.1'))
	[Router(name=Router-10.10.10.1)]

.. note:: When using keyword matching with ``filter``, a single query will be performed using the attribute value,
	returning a list of 'contains' matches. For each element match returned from the first query, an additional query
	is performed to retrieve the element attributes.
		  
To reduce the number of additional queries performed when using keyword matching, use a limit on the number
of return elements::
	
	>>> list(Router.objects.filter(address='10.10.10.1').limit(1))
	[Router(name=Router-10.10.10.1)]
	

Additional Examples
^^^^^^^^^^^^^^^^^^^

Obtain an iterator from the collection manager for re-use::

	>>> iterator = Router.objects.iterator()
	>>> query1 = iterator.filter('10.10.10.1')
	>>> list(query1)
	[Router(name=Router-110.10.10.10), Router(name=Router-10.10.10.10), Router(name=Router-10.10.10.1)]
	>>> query2 = query1.filter(address='10.10.10.1')
	>>> list(query2)
	[Router(name=Router-10.10.10.1)]
	
Access a collection directly on an Element type::

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
	[Host(name=172.18.1.135), Host(name=SMC), Host(name=TIE Server), Host(name=172.18.1.93)]

Get a host collection when partial IP address known::

  >>> list(Host.objects.filter('192.168'))
  [Host(name=aws-192.168.4.254), Host(name=host-192.168.4.135), Host(name=host-192.168.4.94), Host(name=host-192.168.4.79)]

When filtering is performed, by default search queries will 'wildcard' the results. To only return an exact match of the search query,
use the optional flag 'exact_match'::

  >>> list(TCPService.objects.filter('8080'), exact_match=True))
  [TCPService(name=TCP_8080), TCPService(name=HTTP proxy), TCPService(name=SSH), TCPService(name=SSM SSH)]

Additional convenience functions are provided on the collections to simplify navigating
through results such as ``count``, ``first``, and ``last``::

	>>> query1 = iterator.filter('10.10.10.1')
	>>> if query1.exists():
	...   list(query1.all())
	... 
	[Router(name=Router-110.10.10.10), Router(name=Router-10.10.10.10), Router(name=Router-10.10.10.1)]
	        
	>>> list(query1)
	[Router(name=Router-110.10.10.10), Router(name=Router-10.10.10.10), Router(name=Router-10.10.10.1)]
	>>> query1.first()
	Router(name=Router-110.10.10.10)
	>>> query1.last()
	Router(name=Router-10.10.10.1)
	>>> query1.count()
	3
	>>> query2 = query1.filter(address='10.10.10.1')  # Add kwarg to new query
	>>> list(query2)
	[Router(name=Router-10.10.10.1)]

General Search
--------------

If a search is required for an element type that is not a pre-defined class of :py:class:`smc.base.model.Element` type 
in the API, it is still possible to search any valid entry point using :py:class:`smc.base.collections.Search`.

Search extends ElementCollection and provides additional methods:

* :py:meth:`~smc.base.collection.Search.entry_point`. Entry points are top level collections available from the SMC.


* :py:meth:`~smc.base.collection.Search.context_filter`. Context filters are special filters that can return more generalized results such as all engines, etc.

  Available context filters:

    * *fw_clusters* - list all firewalls

    * *engine_clusters* - all clusters

    * *ips_clusters* - ips only clusters

    * *layer2_clusters* - layer2 only clusters
                    
    * *network_elements* - all network element types

    * *services* - all service types

    * *services_and_applications* - all services and applications

    * *tags* - element tags

    * *situations* - inspection situations

* :py:meth:`~smc.base.collection.Search.unused`. Search for all unused elements::

	>>> list(Search.objects.unused())
	[RouteVPN(name=myvpn), RouteVPN(name=mygre), RouteVPN(name=avpn), RouteVPN(name=avpn)]
	...

* :py:meth:`~smc.base.collection.Search.duplicates()`. Search for all duplicate elements::

	>>> list(Search.objects.duplicates())
	[Host(name=foohost), Router(name=router-1.1.1.1)]
	...

Using ``Search`` is useful if there is not a direct class representation of the element you
are attempting to retrieve. If there is an entry point for the target element type, you can 
return any element.

First, find all available searchable objects (also known as 'entry points')::

  >>> from smc.elements.resources import Search
  >>> Search.object_types()
  ['elements', 'sub_ipv6_fw_policy', 'ids_alert', 'application_not_specific_tag', 'fw_alert', 'virtual_ips', 'sidewinder_tag', 'os_specific_tag', 'eia_application_usage_group_tag', 'external_bgp_peer', 'local_cluster_cvi_alias', 'ssl_vpn_service_profile', 'active_directory_server', 'eia_golden_image_tag', 'client_gateway', 'situation_tag', 'api_client', 'tls_match_situation', 'ssl_vpn_policy', 'category_group_tag', 'ip_list', 'vpn_profile', 'ipv6_access_list', 'appliance_information', 'single_layer2', 'ei_executable', 'community_access_list']
  ...
 
Once the type of interest is found, the elements can be retrieved using the entry point::

  >>> list(Search.objects.entry_point('vpn'))
  [PolicyVPN(name=Amazon AWS), PolicyVPN(name=sg_vm_vpn), PolicyVPN(name=TRITON AP-WEB Cloud VPN)]

And subsequently add a filter as well::

  >>> list(Search.objects.entry_point('vpn').filter('AWS'))
  [PolicyVPN(name=Amazon AWS)]

----

Additional examples:

Searching all services for port 80::

	>>> list(Search.objects.entry_point('services').filter('80'))
	[TCPService(name=tcp80443), TCPService(name=HTTP to Web SaaS), EthernetService(name=IPX over Ethernet 802.2), UDPService(name=udp_10070-10080), Protocol(name=HTTP8080), TCPService(name=tcp_10070-10080), TCPService(name=TCP_8080), TCPService(name=tcp_3478-3480), EthernetService(name=IPX over Ethernet 802.3 (Novell)), TCPService(name=HTTP), TCPService(name=SSM HTTP), TCPService(name=HTTP (SafeSearch)), IPService(name=ISO-IP), UDPService(name=udp_3478-3480), TCPService(name=HTTP (with URL Logging))]

Only Network elements with '172.18.1'::

	>>> list(Search.objects.context_filter('network_elements').filter('172.18.1'))
	[Host(name=172.18.1.135), Host(name=SMC), Network(name=Any network), FirewallCluster(name=sg_vm), Element(name=dc-smtp), Network(name=network-172.18.1.0/24), LogServer(name=LogServer 172.18.1.150), Layer3Firewall(name=testfw), Element(name=SecurID), Element(name=Windows 2003 DHCP), AddressRange(name=range-172.18.1.100-172.18.1.120), ManagementServer(name=Management Server)]

Only firewall clusters::

	>>> list(Search.objects.context_filter('fw_clusters'))
	[FirewallCluster(name=sg_vm), Layer3VirtualEngine(name=ve-8), Layer3Firewall(name=testfw), Layer3Firewall(name=i-04eec8f019adf818e (us-east-2a)), MasterEngine(name=master)]

In addition to using more generic filters, with general searches, you can also specify multiple valid entry points by 
specifying the string filter comma separated.

For example, finding all hosts and routers::

	>>> list(Search.objects.entry_point('router,host'))
	[Host(name=172.18.2.254), Router(name=router-172.18.3.129), Host(name=All Routers (Site-Local))]
	
Filter based on hosts and routers::

	>>> list(Search.objects.entry_point('router,host').filter('172.18.1'))
	[Host(name=172.18.1.135), Host(name=SMC), Host(name=ePolicy Orchestrator), Router(name=router-172.18.1.225), Host(name=fw-internal-primary), Router(name=router-172.18.1.209)]

.. note:: If an element of class :py:class:`smc.base.model.Element` exists, it will 
   be returned as that type to enable access to the objects instance methods. If there is no element defined,
   a dynamic class is produced from type Element.

For example, searching for object of type 'ids_alert' will produce a dynamic class as type Element and will have access to the base class methods::

  >>> list(Search.objects.entry_point('ids_alert'))
  [IdsAlertDynamic(name=Default alert), IdsAlertDynamic(name=Test alert), IdsAlertDynamic(name=System alert)]
  
Classes deriving from :py:class:`smc.base.model.Element` are found in the API reference, for example: :ref:`element-reference-label`
