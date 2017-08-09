Resources
---------

Resources in the Stonesoft Management Center are typically accessed in a couple different ways.

The first would be by using the elements collection interface to search for elements of a specific
type.

For example, if you are looking for Hosts by a given IP address::

	>>> from smc.elements.network import Host
	>>> list(Host.objects.filter('192.168'))
	[Host(name=aws-192.168.4.254), Host(name=host-192.168.4.135), Host(name=host-192.168.4.94), Host(name=host-192.168.4.79)]

See :ref:`collection-reference-label` for more information on search capabilities.

It is also possible to access resources directly::

	>>> from smc.core.engine import Engine
	>>> engine = Engine('sg_vm')
	>>> print(list(engine.nodes))
	[Node(name=ngf-1065), Node(name=ngf-1035)]

	>>> print(list(engine.routing))
	[Routing(name=Interface 0,level=interface), Routing(name=Interface 1,level=interface), Routing(name=Interface 2,level=interface), Routing(name=Tunnel Interface 2000,level=interface), Routing(name=Tunnel Interface 2001,level=interface)]

Retrieving a specific host element by name::

	>>> from smc.elements.network import Host
	>>> host = Host('kali')
	>>> print(host.href)
	http://172.18.1.150:8082/6.2/elements/host/978
  
When elements are referenced initially, they are lazy loaded until attributes or methods of the element are
used that require the data. Once an element has been 'inflated' due to a reference being called (property, method, etc), 
the resultant element data is stored in a per instance cache. 
		 
Example of how elements are lazy loaded::

	>>> from smc.elements.network import Host
	>>> host = Host('kali')
	>>> vars(host)
	{'_meta': None, '_name': 'kali'}	#Base level attributes, only instance created
	>>> host.href	# Call to retrieve this resource link reference loads instance meta (1 SMC query)
	u'http://172.18.1.150:8082/6.2/elements/host/978'
	>>> vars(host)
	{'_meta': Meta(name=u'kali', href=u'http://172.18.1.150:8082/6.2/elements/host/978', type=u'host'), '_name': 'kali'}
	>>> host.data	# Request to a method/attribute that requires the data attribute inflates the instance (1 SMC query)
	{u'comment': u'this is a searchable comment', u'read_only': False, u'ipv6_address': u'2001:db8:85a3::8a2e:370:7334', u'name': u'kali', u'third_party_monitoring': {u'netflow': False, u'snmp_trap': False}, u'system': False, u'link': [{u'href': u'http://172.18.1.150:8082/6.2/elements/host/978', u'type': u'host', u'rel': u'self'}, {u'href': u'http://172.18.1.150:8082/6.2/elements/host/978/export', u'rel': u'export'}, {u'href': u'http://172.18.1.150:8082/6.2/elements/host/978/search_category_tags_from_element', u'rel': u'search_category_tags_from_element'}], u'key': 978, u'address': u'1.1.11.1', u'secondary': [u'7.7.7.7']}
	>>> vars(host)
	{'data': {u'comment': u'this is a searchable comment', u'read_only': False, u'ipv6_address': u'2001:db8:85a3::8a2e:370:7334', u'name': u'kali', u'third_party_monitoring': {u'netflow': False, u'snmp_trap': False}, u'system': False, u'link': [{u'href': u'http://172.18.1.150:8082/6.2/elements/host/978', u'type': u'host', u'rel': u'self'}, {u'href': u'http://172.18.1.150:8082/6.2/elements/host/978/export', u'rel': u'export'}, {u'href': u'http://172.18.1.150:8082/6.2/elements/host/978/search_category_tags_from_element', u'rel': u'search_category_tags_from_element'}], u'key': 978, u'address': u'1.1.11.1', u'secondary': [u'7.7.7.7']}, '_meta': Meta(name=u'kali', href=u'http://172.18.1.150:8082/6.2/elements/host/978', type=u'host'), '_name': 'kali'}

At most 2 queries will be required to retrieve an element as a resource.
		
Cache contents can be viewed in their raw json format by calling the 'data' property.

.. note:: When modifications are made to a specific element, they are submitted back to the SMC using the
		  originally retrieved ETag to ensure the element has not been modified since the original retrieval.