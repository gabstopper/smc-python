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

It is also possible to access the elements directly if the element is known::

	>>> from smc.core.engine import Engine
	>>> engine = Engine('sg_vm')
	>>> print(list(engine.nodes))
	[Node(name=ngf-1065), Node(name=ngf-1035)]

	>>> print(list(engine.routing))
	[Routing(name=Interface 0,level=interface), Routing(name=Interface 1,level=interface), Routing(name=Interface 2,level=interface), Routing(name=Tunnel Interface 2000,level=interface), Routing(name=Tunnel Interface 2001,level=interface)]
   
When elements are referenced initially, they are lazy loaded until attributes or methods of the element are
used that require the data. Once an element has been 'inflated' due to a reference being called (property, method, etc), 
the resultant element data is stored in a per instance cache. 

.. note:: When modifications to the element are required, the changes are made to the elements cache first. 
		  Before submitting a change, a request is made using the original ETag to validate whether the
		  element has changed. If changed, the server side changes are made before merging in the local cache.
		 
Example of lazy loaded element data::

	>>> host = Host('kali')
	>>> print(vars(host))
	{'meta': None, '_name': 'kali'}     #Base class attributes only

	>>> print(host.address)             #Request the address for this host, inflates the instance
	55.44.44.44

	>>> print(vars(host))               #Cache populated
	{'_cache': <smc.base.model.Cache object at 0x1053e50d0>, 'meta': Meta(name='kali', href='http://1.1.1.1:8082/6.1/elements/host/978', type='host'), '_name': 'kali'}
	
Cache contents can be viewed in their raw json format by calling the 'data' property.
