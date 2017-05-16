Elements
========

Elements are the building blocks for policy and include types such as Networks, Hosts, 
Services, Groups, Lists, Zones, etc. 

Create
------

Elements within the Stonesoft Management Server are common object types that are referenced
by other configurable areas of the system such as policy, routing, VPN, etc. 

This is not an exhaustive list, all supported element types can be found in the API reference
documentation: :ref:`element-reference-label`

* *Hosts*

* *AddressRange*

* *Networks*

* *Routers*

* *Groups*

* *DomainName*

* *IPList* (SMC API >= 6.1)

* *URLListApplication* (SMC API >= 6.1)

* *Zone*

* *LogicalInterface*

* *TCPService*

* *UDPService*

* *IPService*

* *EthernetService*

* *ServiceGroup*

* *TCPServiceGroup*

* *UDPServiceGroup*

* *IPServiceGroup*

* *ICMPService*

* *ICMPv6Service*

Oftentimes these objects are cross referenced within the configuration, like when creating rule or
NAT policy.
All calls to create() will return the href of the new element stored in the SMC or will raise an
exception for failure.

Examples of creating elements are as follows::

	>>> from smc.elements.network import Host, Network, AddressRange
	>>> host = Host.create(name='hostelement', address='1.1.1.1')
	
	>>> print(host)
	http://1.1.1.1:8082/6.1/elements/host/62618
	
	>>> host = Host('hostelement')  #Load the element and check IP
	>>> print(host.address)
	1.1.1.1
	
	>>> Network.create(name='networkelement', ipv4_network='1.1.1.0/24', comment='foo')
	'http://1.1.1.1:8082/6.1/elements/network/62619'
	
	>>> AddressRange.create(name='rangeelement', iprange='1.1.1.1-1.1.1.100')
	'http://1.1.1.1:8082/6.1/elements/address_range/62620'
	...

Check the various reference documentation for defined elements supported.

.. _update-elements-label:

Update
------  

Updating elements can be done in multiple ways. By default, any element can be updated
by setting the attribute on the class instance itself. The attributes should be a supported
attribute for the respective element type.

Once the element is set on the class instance and attributes are set, you must call
update() on the instance to submit the change to the SMC. 

For example, updating a host element::
        
	>>> host = Host.create(name='grace', address='1.1.1.1')
	>>> host
	Host(name=grace)
	>>> host.address
	'1.1.1.1'
	>>> host.secondary
	[]
	>>> host.address = '3.3.3.3'
	>>> host.secondary = ['3.3.3.4']
	>>> host.comment = 'test comment'
	>>> host.update()
	'http://172.18.1.150:8082/6.2/elements/host/117046'
	>>> host.address
	'3.3.3.3'
	>>> host.comment
	'test comment'

By default, only attributes defined in the elements cache are eligible for updating. 
For example, if you create a new attribute on a host element 'ipv4_network' and run
update, this attribute will be ignored from the update as it's not a valid attribute
for :class:`smc.elements.network.Host` elements.

You can override this behavior by providing the kwarg ``ignore_unknown_attr=True`` in
the call to update. This is generally not required but in some cases valid attributes
may not be present in the cached data.
	
.. note:: When updating attributes on an instance, you should prefix any custom attributes
	with '_'. Attributes without this prefix will merge into the cache and subsequently cause
	the update to fail.

Another way to update an element is by providing the kwarg values in the update() call.

Taking the example above, this could be done this way::

	host = Host('kali')
	host.update(
		address='3.3.3.3',
		secondary=['12.12.12.12'],
		comment='something about this host')

This also results in a single call to the SMC and allows the same functionality as the
first example.

.. note:: If providing an element update by modifying attributes and kwargs, kwargs will
	take precendence and overwrite any attributes set. It is recommended to choose one of
	the two methods rather than using both.

There is also a generic modify_attribute on :class:`smc.base.model.Element` which is
essentially the same as calling .update() above with the exception that it does not
look at instance attributes, only the attributes provided in the constructor::

	host = Host('kali')
	host.modify_attribute(
		address='3.3.3.3',
		secondary=['12.12.12.12'],
		comment='something about this host')

A much more low-level way of modifying an element is to modify the data in cache (dict)
directly. After making the modifications, you must also call .update() to submit the change.

Modifying a service element after reviewing the element cache::
   
	>>> service = TCPService.create(name='aservice', min_dst_port=9090)
	>>> service
	TCPService(name=aservice)
	...
	>>> pprint(service.data)
	{u'key': 3551,
	 u'link': [{u'href': u'http://172.18.1.150:8082/6.2/elements/tcp_service/3551',
	            u'rel': u'self',
	            u'type': u'tcp_service'},
	           {u'href': u'http://172.18.1.150:8082/6.2/elements/tcp_service/3551/export',
	            u'rel': u'export'},
	           {u'href': u'http://172.18.1.150:8082/6.2/elements/tcp_service/3551/search_category_tags_from_element',
	            u'rel': u'search_category_tags_from_element'}],
	 u'min_dst_port': 9090,
	 u'name': u'aservice',
	 u'read_only': False,
	 u'system': False}
	 ...
	>>> service.data['min_dst_port'] = 9091
	>>> service.update()	# Submit to SMC, cache is refreshed
	'http://172.18.1.150:8082/6.2/elements/tcp_service/3551'
	...
	>>> pprint(service.data)
	{u'key': 3551,
	 u'link': [{u'href': u'http://172.18.1.150:8082/6.2/elements/tcp_service/3551',
	            u'rel': u'self',
	            u'type': u'tcp_service'},
	           {u'href': u'http://172.18.1.150:8082/6.2/elements/tcp_service/3551/export',
	            u'rel': u'export'},
	           {u'href': u'http://172.18.1.150:8082/6.2/elements/tcp_service/3551/search_category_tags_from_element',
	            u'rel': u'search_category_tags_from_element'}],
	 u'min_dst_port': 9091,
	 u'name': u'aservice',
	 u'read_only': False,
	 u'system': False}

Attributes supported by elements are documented in the API Reference: :ref:`element-reference-label`



Delete
------

Deleting elements is done by using the base class delete method. It is not required to inflate the 
instance as only meta will be retrieved to perform the delete operation.

Deleting a host::

	>>> from smc.elements.network import Host
	>>> Host('kali').delete()
 