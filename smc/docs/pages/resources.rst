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
	{'meta': None, '_name': 'kali'}		#Base level attributes, only instance created
	>>> host.href	#Call to retrieve this resource link reference loads instance meta (1 SMC query)
	'http://172.18.1.150:8082/6.2/elements/host/978'
	>>> vars(host)
	{'meta': Meta(name='kali', href='http://172.18.1.150:8082/6.2/elements/host/978', type='host'), '_name': 'kali'}
	>>> host.data		# Request to a method/attribute that requires the data attribute inflates the instance (1 SMC query)
	{'third_party_monitoring': {'netflow': False, 'snmp_trap': False}, 'ipv6_address': '2001:db8:85a3::8a2e:370:7334', 'key': 978, 'address': '23.23.23.23', 'secondary': ['7.7.7.7'], 'read_only': False, 'link': [{'rel': 'self', 'href': 'http://172.18.1.150:8082/6.2/elements/host/978', 'type': 'host'}, {'rel': 'export', 'href': 'http://172.18.1.150:8082/6.2/elements/host/978/export'}, {'rel': 'search_category_tags_from_element', 'href': 'http://172.18.1.150:8082/6.2/elements/host/978/search_category_tags_from_element'}], 'system': False, 'name': 'kali'}
	>>> vars(host)
	{'meta': Meta(name='kali', href='http://172.18.1.150:8082/6.2/elements/host/978', type='host'), '_name': 'kali', '_cache': <smc.base.model.Cache object at 0x109f23348>}
	>>> host._cache._cache		# Cache maintains original ETag and raw json data
	('"OTc4MzExMjcxNDg5NTAyNzk0OTE0"', {'third_party_monitoring': {'netflow': False, 'snmp_trap': False}, 'ipv6_address': '2001:db8:85a3::8a2e:370:7334', 'key': 978, 'address': '23.23.23.23', 'secondary': ['7.7.7.7'], 'read_only': False, 'link': [{'rel': 'self', 'href': 'http://172.18.1.150:8082/6.2/elements/host/978', 'type': 'host'}, {'rel': 'export', 'href': 'http://172.18.1.150:8082/6.2/elements/host/978/export'}, {'rel': 'search_category_tags_from_element', 'href': 'http://172.18.1.150:8082/6.2/elements/host/978/search_category_tags_from_element'}], 'system': False, 'name': 'kali'})
		
Cache contents can be viewed in their raw json format by calling the 'data' property.

.. note:: When modifications are made to a specific element, they are submitted back to the SMC using the
		  originally retrieved ETag to ensure the element has not been modified since the original retrieval.