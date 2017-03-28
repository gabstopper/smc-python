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

Modify
------  

Modifying elements can be done through either instance methods/properties (if they exist), or
also through the low-level API.
Attributes supported by elements are documented in the API Reference: :ref:`element-reference-label`

For example, modifying a Host element IP address::

	>>> from smc.elements.network import Host
	>>> host = Host('kali')
	>>> print(host.address)
	55.44.44.44
	>>> host.modify_attribute(address='12.12.12.12')
	>>> print(host.address)
	12.12.12.12
	
Modifying a service element after reviewing the element cache::
   
	>>> from smc.elements.service import TCPService
	>>> service = TCPService('api-tcp')
	>>> print(service.href)
	http://1.1.1.1:8082/6.1/elements/tcp_service/3505
	...
	>>> pprint(service.data)	#Show cache
	{'key': 3505,
 	 'link': [{'href': 'http://1.1.1.1:8082/6.1/elements/tcp_service/3505',
                'method': 'GET',
                'rel': 'self',
                'type': 'tcp_service'},
               {'href': 'http://1.1.1.1:8082/6.1/elements/tcp_service/3505/export',
                'method': 'POST',
                'rel': 'export'},
               {'href': 'http://1.1.1.1:8082/6.1/elements/tcp_service/3505/search_category_tags_from_element',
                'method': 'GET',
                'rel': 'search_category_tags_from_element'}],
 	'min_dst_port': 5000,
 	'name': 'myapi-tcpservice',
 	'read_only': False,
 	'system': False}
	... 
	>>> service.modify_attribute(min_dst_port='6000')	#Call modify_attribute
	>>> pprint(service.data)
	{'key': 3505,
 	 'link': [{'href': 'http://1.1.1.1:8082/6.1/elements/tcp_service/3505',
                'method': 'GET',
                'rel': 'self',
                'type': 'tcp_service'},
               {'href': 'http://1.1.1.1:8082/6.1/elements/tcp_service/3505/export',
                'method': 'POST',
                'rel': 'export'},
               {'href': 'http://1.1.1.1:8082/6.1/elements/tcp_service/3505/search_category_tags_from_element',
                'method': 'GET',
                'rel': 'search_category_tags_from_element'}],
 	'min_dst_port': 6000,
 	'name': 'myapi-tcpservice',
 	'read_only': False,
 	'system': False}

.. note:: Calling :func:`smc.base.model.ElementBase.modify_attribute` will make each change immediately
		  after it is called and cache refreshed.

Delete
------

Deleting elements is done by using the base class delete method. It is not required to inflate the 
instance as only meta will be retrieved to perform the delete operation.

Deleting a host::

	>>> from smc.elements.network import Host
	>>> Host('kali').delete()
 