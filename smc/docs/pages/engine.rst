Engines
-------

Engines are the definitions for a layer 3 FW, layer 2 FW, IPS, Cluster Firewalls, Master Engines,
or Virtual Engines.

An engine defines the basic settings to make the device or virtual instance operational such as
interfaces, routes, ip addresses, networks, dns servers, etc. 

Creating engines are done using the Firewall specific base classes in :py:mod:`smc.core.engines`

Nodes are individual devices represented as properties of an engine element. 
In the case of single device deployments, there is only one node. For clusters, there will be at a minimum 
2 nodes, max of 16. The :py:mod:`smc.core.node` class represents the interface to managing and 
sending commands individually to a node in a cluster.

By default, each constructor will have default values for the interface used for management (interface 0).
This can be overridden as necessary.

Once engines are created, they can be retrieved directly by using :py:class:`smc.core.engine.Engine`
or directly by their engine type.
The __repr__ of Engine will show a descriptive view of the engine type regardless of how the context
was obtained. 

::

	>>> Engine('sg_vm')
	FirewallCluster(name=sg_vm)
	...
	>>> from smc.core.engines import FirewallCluster
	>>> FirewallCluster('sg_vm')
	FirewallCluster(name=sg_vm)	

.. note:: There is no difference between the two options. Loading from the Engine class tends to be easier
		  as you are not required to know the engine type to obtain the context.
	
Create
++++++

Layer3 Firewall
***************

For Layer 3 single firewall engines, the minimum requirements are to specify a name, management IP and
management network. By default, the Layer 3 firewall will use interface 0 as the management port. This can
be overridden in the constructor if a different interface is required. 

To create a layer 3 firewall::

	>>> from smc.core.engines import Layer3Firewall
	>>> Layer3Firewall.create(name='firewall', mgmt_ip='1.1.1.1', mgmt_network='1.1.1.0/24')
	Layer3Firewall(name=firewall)

See reference for more information: :py:class:`smc.core.engines.Layer3Firewall`

Layer 2 Firewall
****************

For Layer 2 Firewall and IPS engines, an inline interface pair will automatically be 
created using interfaces 1-2 but can be overridden in the constructor to use different
interface mappings. At least one inline pair or a capture interface is required to 
successfully create.

Creating a Layer2 Firewall with alternative management interface and DNS settings::

	>>> from smc.core.engines import Layer2Firewall
	>>> Layer2Firewall.create(name='myfirewall', mgmt_ip='1.1.1.1', mgmt_network='1.1.1.0/24', mgmt_interface=5, domain_server_address=['172.18.1.20'])
	Layer2Firewall(name=myfirewall)

See reference for more information: :py:class:`smc.core.engines.Layer2Firewall`
   									  
IPS Engine
**********

Similar to Layer2Firewall, at least one inline interface pair or a capture interface is required to 
successfully create.

Use alternative inline interface pair configuration (mgmt on interface 0)::

 	>>> from smc.core.engines import IPS
	>>> IPS.create(name='myips', 
	...            mgmt_ip='1.1.1.1', 
	...            mgmt_network='1.1.1.0/24', 
	...            inline_interface='5-6')
	IPS(name=myips)
 
See reference for more information: :py:class:`smc.core.engines.IPS`

Master Engine
*************

A Master Engine is used to manage virtual engine nodes and provides in system virtualization.
Master Engine controls administrative aspects and specifies how resources are allocated to 
the virtual engines.

Create a master engine with a single management interface, then add 2 more physical interface for
virtual engine allocation:

   	>>> from smc.core.engines import MasterEngine
	>>> engine = MasterEngine.create(name='api-master',
	...                              mgmt_ip='1.1.1.1',
	...                              mgmt_network='1.1.1.0/24',
	...                              master_type='firewall', 
	...                              domain_server_address=['8.8.4.4', '7.7.7.7'])
	>>> print(engine)
	>>> MasterEngine(name=api-master)
	>>> engine.physical_interface.add(1)	# add intefaces
	>>> engine.physical_interface.add(2)
	>>> for intf in engine.interface.all():
	...   print(intf)
	... 
	PhysicalInterface(name=Interface 1)
	PhysicalInterface(name=Interface 0)
	PhysicalInterface(name=Interface 2)

See :py:class:`smc.core.engines.MasterEngine` for more details.

Layer3Virtual Engine
********************

A virtual engine is a host that resides on a Master Engine node used for multiple FW contexts. Stonesoft
maps a 'virtual resource' to a virtual engine as a way to map the master engine interface to the individual
instance residing within the physical device. 

In order to create a virtual engine, you must first manually create the Master Engine from the SMC, then 
create the interfaces that will be used for the virtual instances.

The first step in creating the virtual engine is to create the virtual resource and map that to a physical interface
or VLAN on the master engine. Once that has been created, add IP addresses to the virtual engine interfaces as necessary.

First create the virtual resource on the already created Master Engine::

	>>> from smc.core.engines import MasterEngine
	>>> engine = MasterEngine('api-master')
	>>> engine.virtual_resource.create('ve-1', vfw_id=1)
	'http://1.1.1.1:8082/6.1/elements/master_engine/62629/virtual_resource/756'
           
See :py:func:`smc.core.engine.VirtualResource.create` for more information.

Creating a layer 3 virtual engine with two single physical interfaces::

	>>> from smc.core.engines import Layer3VirtualEngine
	>>> Layer3VirtualEngine.create(name='myvirtual', 
	...                            master_engine='api-master',
	...                            virtual_resource='ve-1',
	...                            interfaces=[{'address':'5.5.5.5','network_value':'5.5.5.0/24','interface_id':0},
	...                                        {'address':'6.6.6.6','network_value':'6.6.6.0/24','interface_id':1}]
	Layer3VirtualEngine(name=myvirtual)	

.. note:: Virtual engine interface numbering takes into account the dedicated interface
          for the master engine.
          For example, if the master engine is using physical interface 0 for 
          management, the virtual engine may be assigned physical interface 1 
          for use. From an indexing perspective, the naming within the virtual engine 
          configuration will start at interface 0 but be using physical interface 1.

See reference for more information: :py:class:`smc.core.engines.Layer3VirtualEngine`
                            
Firewall Cluster
****************

Creating a layer 3 firewall cluster requires additional interface related information to bootstrap the
engine properly.
With NGFW clusters, a "cluster virtual interface" is required (if only one interface is used) to specify 
the cluster address as well as each engine specific node IP address. In addition, a macaddress is required 
for packetdispatch functionality (recommended HA configuration).

By default, the FirewallCluster class will allow as many nodes as needed (up to 16 per cluster) for the
singular interface. The node specific interfaces are defined by passing in the 'nodes' argument to the
constructor as follows:

Create a 3 node cluster::

	>>> from smc.core.engines import FirewallCluster
	>>> FirewallCluster.create(name='mycluster',
	...                        cluster_virtual='1.1.1.1',
	...                        cluster_mask='1.1.1.0/24',
	...                        cluster_nic=0,
	...                        macaddress='02:02:02:02:02:02',
	...                        nodes=[{'address':'1.1.1.2','network_value':'1.1.1.0/24','nodeid':1},
	...                               {'address':'1.1.1.3','network_value':'1.1.1.0/24','nodeid':2},
	...                               {'address':'1.1.1.4','network_value':'1.1.1.0/24','nodeid':3}],
	...                        domain_server_address=['8.8.8.8'])
	FirewallCluster(name=mycluster)

See :py:class:`smc.core.engines.FirewallCluster` for more info
                            
MasterEngine Cluster
********************

Create a master engine cluster for redundancy. Master Engine clusters support active/standby
mode.

Create the cluster and add a second interface for each cluster node::

	>>> MasterEngineCluster.create(name='engine-cluster',
	...                            master_type='firewall',
	...                            macaddress='22:22:22:22:22:22',
	...                            nodes=[{'address':'5.5.5.2','network_value':'5.5.5.0/24','nodeid':1},
	...                                   {'address':'5.5.5.3','network_value':'5.5.5.0/24','nodeid':2}])
	MasterEngine(name=engine-cluster)

Adding an interface after creation::
      
	>>> from smc.core.engine import Engine
	>>> engine = Engine('engine-cluster')
	>>> engine.physical_interface.add_cluster_interface_on_master_engine(
	...                                         interface_id=1,
	...                                         macaddress='22:22:22:22:22:33',
	...                                         nodes=[{'address':'6.6.6.2','network_value':'6.6.6.0/24','nodeid':1},
	...                                                {'address':'6.6.6.3','network_value':'6.6.6.0/24','nodeid':2}])
                                             
See :py:class:`smc.core.engines.MasterEngineCluster` for more info

Nodes
+++++

Managed engines have many options for controlling the behavior of the device or virtual through
the SMC API. Once an engine has been created, The engine is represented with 'nodes' that map to
the individual firewall/IPS's. For example, a cluster will have 2 or more nodes. 


Engine hierarchy resembles the following:

::

	Engine 
	   | - ---> Node1
	   | - ---> Node2
	   | - ---> Node3
	   \ - .... (up to 16)
	   
Engine level commands allow operations like refresh policy, upload new policy, generating snapshots,
export configuration, blacklisting, adding routes, route monitoring, and add or delete a physical interfaces

Some example engine level commands::

	>>> engine = Engine('testfw')
	>>> for node in engine.nodes:
	>>> engine.generate_snapshot() #generate a policy snapshot
	>>> engine.export(filename='/Users/davidlepage/export.xml') #generate policy export
	>>> engine.refresh() #refresh policy
	>>> engine.routing_monitoring() 	#get route table status
	....

For all available commands for engines, see :py:class:`smc.core.engine.Engine`
   
Node level commands are specific commands targeted at individual nodes directly. In the case of a cluster, you
can control the correct node by iterating :py:class:`smc.core.engine.Engine.nodes` list.

Node level commands allow actions such as fetch license, bind license, initial contact, appliance status, 
go online, go offline, go standby, lock online, lock offline, reset user db, diagnostics, reboot, sginfo, 
ssh (enable/disable/change pwd), and time sync.

View nodes and reboot a node by name::

	>>> engine = Engine('testfw')
	>>> print(engine.nodes)
	[Node(name=testfw node 1)]
	...
	>>> for node in engine.nodes:
	...   if node.name == 'testfw':
	...     node.reboot()

Bind license, then generate initial contact for each node for a specific engine::

	>>> for node in engine.nodes:
	...   node.initial_contact(filename='/Users/davidlepage/engine.cfg')
	...   node.bind_license() 

For all available commands for node, see :py:class:`smc.core.node.Node`
                                 
Interfaces
++++++++++

After your engine has been successfully created with the default interfaces, you can add and remove 
interfaces as needed.

From an interface perspective, there are several different interface types that are have subtle differences.
The supported physical interface types available are:

* Single Node Dedicated Interface (Single Layer 3 Firewall)
* Node Dedicated Interface (Used on Clusters, IPS, Layer 2 Firewall)
* Inline Interface (IPS / Layer2 Firewall)
* Capture Interface (IPS / Layer2 Firewall)
* Cluster Virtual Interface 
* Virtual Physical Interface (used for Layer 3 Virtual Engines)
* Tunnel Interface

The distinction is subtle but straightforward. A single node interface is used on a single layer 3 firewall
instance and represents a unique interface with dedicated IP Address.

A node dedicated interface is used on Layer 2 and IPS engines as management based interfaces and may also be used as
a heartbeat (for example). 

It is a unique IP address for each machine. It is not used for operative traffic in Firewall Clusters, 
IPS engines, and Layer 2 Firewalls. 
Firewall Clusters use a second type of interface, Cluster Virtual IP Address (CVI), for operative traffic. 

IPS engines have two types of interfaces for traffic inspection: the Capture Interface and the Inline Interface. 
Layer 2 Firewalls only have Inline Interfaces for traffic inspection.

.. note:: When creating your engine instance, the correct type/s of interfaces are created automatically
          without having to specify the type. However, this may be relavant when adding interfaces to an
          existing device after creation.

To access interface information on existing engines, or to add to an existing engine, you must obtain the
engine context object. It is not required to know the engine type (layer3, layer2, ips) as you can load 
by the parent class :py:class:`smc.core.engines.Engine`.

For example, if I know I have an engine named 'myengine' (despite the engine 'role'), it can be
obtained via::

	>>> from smc.core.engine import Engine
	>>> engine = Engine('sg_vm')
	>>> print(engine.nodes)
	[Node(name=ngf-1065), Node(name=ngf-1035)]
	
It is not possible to add certain interface types based on the node type. For example, it is not 
possible to add inline or capture interfaces to layer 3 FW engines. This is handled automatically 
and will raise an exception if needed.

Adding interfaces are handled by property methods on the engine class. 

To add a single node interface to an existing engine as Interface 10::

	>>> engine = Engine('sg_vm')
	>>> engine.physical_interface.add_single_node_interface(10, '33.33.33.33', '33.33.33.0/24')

Node Interface's are used on IPS, Layer2 Firewall, Virtual and Cluster Engines and represent either a
single interface or a cluster member interface used for communication.

To add a node interface to an existing engine:

	>>> engine = Engine('sg_vm')
	>>> engine.physical_interface.add_node_interface(10, '32.32.32.32', '32.32.32.0/24')
   
Inline interfaces can only be added to Layer 2 Firewall or IPS engines. An inline interface consists
of a pair of interfaces that do not necessarily have to be contiguous. Each inline interface requires
that a 'logical interface' is defined. This is used to identify the interface pair and can be used to
simplify policy. See :py:class:`smc.elements.other.LogicalInterface` for more details.

To add an inline interface to an existing engine::
   
	>>> from smc.core.engine import Engine
	>>> engine = Engine('sg_vm')
	...
	>>> from smc.elements.helpers import logical_intf_helper
	>>> logical_interface = logical_intf_helper('MyLogicalInterface') #get logical interface reference
	>>> engine.physical_interface.add_inline_interface('5-6', logical_interface_ref=logical_intf)
   
.. note:: Use :py:func:`smc.elements.helpers.logical_intf_helper('name')` to find the existing
		  logical interface reference by name or create it automatically
		     
Capture Interfaces are used on Layer 2 Firewall or IPS engines as SPAN interfaces. 
   
To add a capture interface to a layer2 FW or IPS::

	>>> logical_interface = logical_intf_helper('MyLogicalInterface')
   	>>> engine = Engine('myengine')
	>>> engine.physical_interface.add_capture_interface(10, logical_interface_ref=logical_interface)

Cluster Virtual Interfaces are used on clustered engines and require a defined "CVI" (sometimes called a 'VIP'),
as well as node dedicated interfaces for the engine initiated communications. Each clustered interface will therefore
have 3 total address for a cluster of 2 nodes. 

To add a cluster virtual interface on a layer 3 FW cluster with a zone::

    >>> engine = Engine('myengine')
    >>> engine.physical_interface.add_cluster_virtual_interface(
    ...                             interface_id=1,
    ...                             cluster_virtual='5.5.5.1', 
    ...                             cluster_mask='5.5.5.0/24', 
    ...                             macaddress='02:03:03:03:03:03', 
    ...                             nodes=[{'address':'5.5.5.2', 'network_value':'5.5.5.0/24', 'nodeid':1},
    ...                                    {'address':'5.5.5.3', 'network_value':'5.5.5.0/24', 'nodeid':2},
    ...                                    {'address':'5.5.5.4', 'network_value':'5.5.5.0/24', 'nodeid':3}],
    ...                             zone_ref=zone_helper('Heartbeat'))

.. warning:: Make sure the cluster virtual netmask matches the node level networks
                                           
Nodes specified are the individual node dedicated addresses for the cluster members.

VLANs can be applied to layer 3 or inline interfaces. For inline interfaces, these will not have assigned
IP addresses, however layer 3 interfaces will require addressing.

To add a VLAN to a generic physical interface for single node (layer 3 firewall) or a node interface, 
independent of engine type::

	>>> engine = Engine('myengine').load()
	>>> engine.physical_interface.add_vlan_to_node_interface(23, 154)
	>>> engine.physical_interface.add_vlan_to_node_interface(23, 155)
	>>> engine.physical_interface.add_vlan_to_node_interface(23, 156)

This will add 3 VLANs to physical interface 23. If this is a layer 3 routed firewall, you may still need
to add addressing to each VLAN. 

.. note:: In the case of Virtual Engines, it may be advisable to create the physical interfaces with 
	      VLANs on the Master Engine and allocate the IP addressing scheme to the Virtual Engine.
	      

To add layer 3 interfaces with a VLAN and IP address::

    >>> engine = Engine('myengine')
    >>> engine.physical_interface.add_single_node_interface_to_vlan(interface_id=2, 
    ...                                                             address='3.3.3.3',
    ...                                                             network_value='3.3.3.0/24', 
    ...                                                             vlan_id=3,
    ...                                                             zone_ref=zone_helper('Internal')

.. note:: The physical interface will be created if it doesn't already exist
   
To add VLANs to layer 2 or IPS inline interfaces::

	>>> logical_interface = logical_intf_helper('default_eth') #find logical intf or create it
	...
	>>> engine = Engine('myengine')
	>>> engine.physical_interface.add_vlan_to_inline_interface(interface_id='5-6',
	...                                                        vlan_id=56, 
	...                                                        logical_interface_ref=logical_interface)
	...
	>>> engine.physical_interface.add_vlan_to_inline_interface(interface_id='5-6',
	...                                                        vlan_id=57, 
	...                                                        logical_interface_ref=logical_interface)
	...
	>>> engine.physical_interface.add_vlan_to_inline_interface(interface_id='5-6',
	...                                                        vlan_id=58, 
	...                                                        logical_interface_ref=logical_interface)
 

.. note:: The physical interface will be created if it doesn't already exist
   
To see additional information on interfaces, :py:class:`smc.core.interfaces` reference documentation 

Sub-Interface and VLAN
**********************

Top level interface types hold basic settings about the interface, and sub-interfaces define the actual
configuration itself, such as IP Addresses, Netmask, which node the interface is assigned to, etc.
To obtain more information about a given interface such as sub-interfaces or vlans, use the interface
vlan_interfaces() and sub_interfaces() resources. 

To show all vlan interfaces::

	>>> for interface in engine.interface.all():
	...   if interface.has_vlan:
	...     print(interface.vlan_interfaces())
	[PhysicalVlanInterface(address=None,vlan_id=14), PhysicalVlanInterface(address=45.45.45.50,vlan_id=13)]

Interfaces that have IP addresses assigned are considered 'sub interfaces'. There may be multiple
sub interfaces on a given physical interface if multiple IP's are assigned.

Display addresses for a specific interface (showing the sub-interfaces)::

	>>> for interface in engine.interface.all():
	...   if interface.name == 'Interface 0':
	...     print(interface.sub_interfaces())
	[SingleNodeInterface(name=172.18.1.55)]
	
It is not required to traverse the physical or sub-interface hierarchy to view properties of
an interface. 

Show IP addresses and networks for all interfaces::

	>>> for interface in engine.interface.all():
	...   print(interface.name, interface.addresses)
	('Tunnel Interface 2001', [('169.254.9.22', '169.254.9.20/30', '2001')])
	('Tunnel Interface 2000', [('169.254.11.6', '169.254.11.4/30', '2000')])
	('Interface 2', [('192.168.1.252', '192.168.1.0/24', '2'), ('192.168.1.253', '192.168.1.0/24', '2')])
	('Interface 1', [('10.0.0.254', '10.0.0.0/24', '1'), ('10.0.0.253', '10.0.0.0/24', '1'), ('10.0.0.252', '10.0.0.0/24', '1')])
	('Interface 0', [('172.18.1.254', '172.18.1.0/24', '0'), ('172.18.1.252', '172.18.1.0/24', '0'), ('172.18.1.253', '172.18.1.0/24', '0')])
            

See :py:class:`smc.core.interfaces.Interface` for more info.

Modifying Interfaces
********************

To modify an existing interface, you will first need to obtain a reference to the interface. There are some
modifications that may have dependencies on other settings. For example, when an interface is 
configured with an IP address, the SMC will automatically create a route entry mapping that physical interface
to the directly connected network. Changing the IP will leave the old network definition from the previously
assigned interface and would also need to be removed. 

.. note:: Save must be called on the interface itself or changes will only be made to a local copy of
	      the element.
	      
Example of changing the IP address of an existing single node interface (for layer 3 firewalls)::

	>>> for interface in engine.interface.all():
	...   if interface.name == 'Interface 0':
	...     for intf in interface.sub_interfaces():
	...       intf.address = '172.18.1.60'
	...     interface.save()
	... 
	>>> intf = engine.interface.get(0)
	>>> print(intf.addresses)
	[('172.18.1.60', '172.18.1.0/24', '0')]

       
Change the zone on the top level Physical Interface::

	>>> intf = engine.interface.get(0)
	>>> intf.zone_ref=zone_helper('My New Zone')
	>>> intf.save()


Change a VLAN on a single FW node under Interface 2:

	>>> intf = engine.interface.get(2)
	>>> for vlan in intf.vlan_interfaces():
	...   if vlan.vlan_id == '14':
	...     vlan.vlan_id = '15'
	...     intf.save()

Deleting Interfaces
*******************

Deleting interfaces by referencing the interface from the engine context.

Once you have loaded the engine, you can display all available interfaces by calling using the 
engine level property interface:
:py:func:`smc.core.engine.Engine.interface` to view all interfaces for the engine.

The name of the interface is the name the NGFW gives the interface based on interface index. For example, 
physical interface 1 would be "Interface 1" and so on.

Viewing all interfaces and removing one by id::

	>>> engine = Engine('testfw')
	>>> for interface in engine.interface.all():
	...     print(interface)
	... 
	PhysicalInterface(name=Interface 12)
	TunnelInterface(name=Tunnel Interface 2000)
	PhysicalInterface(name=Interface 10)
	TunnelInterface(name=Tunnel Interface 1001)
	TunnelInterface(name=Tunnel Interface 1000)
	PhysicalInterface(name=Interface 20)
	PhysicalInterface(name=Interface 11)
	PhysicalInterface(name=Interface 40)
	...
	>>> intf = engine.interface.get(20)	#Get interface 20
	>>> print(intf.name)
	Interface 20
	...
	>>> intf.delete()	#Delete interface

To see additional information on interfaces, :py:class:`smc.core.interfaces` reference documentation
            
Routing
+++++++

Adding routes to routed interfaces is done by loading the engine and providing the next hop
gateway and destination network as parameters. It is not necessary to specify the interface
to place the route, the mapping will be done automatically on the SMC based on the existing
IP addresses and networks configured on the engine. 

Show routes, and view specific interface details::

	>>> from smc.core.engine import Engine
	>>> engine = Engine('testfw')
	>>> for routes in engine.routing.all():
	...   print(routes)
	... 
	Routing(name=Interface 1,level=interface)
	Routing(name=Tunnel Interface 1000,level=interface)
	Routing(name=Interface 11,level=interface)
	Routing(name=Tunnel Interface 2000,level=interface)
	Routing(name=Interface 10,level=interface)

Details of interface 1 routes::

	>>> for routes in engine.routing.all():
	...   if routes.name == 'Interface 1':
	...     print(routes.all())
	... 
	[Routing(name=network-1.1.1.0/24,level=network), Routing(name=network-2.2.2.0/24,level=network)]
	
Add a route. It is not required to specify the interface in which to add the route, the gateway
will determine the interface as it is required to be directly connected::

	>>> engine = Engine('master-eng')
	>>> engine.add_route(gateway='172.18.1.200', network='192.168.17.0/24')

Licensing
+++++++++

Stonesoft engine licensing for physical appliances is done by having the SMC 'fetch' the license
POS from the appliance and auto-assign the license. If the engine is running on a platform that doesn't
have a POS (Proof-of-Serial) such as a virtual platform, then the fetch will fail. In this case, it is 
possible to do an auto bind which will look for unassigned dynamic licenses available in the SMC.

Example of attempting an auto-fetch and falling back to auto binding a dynamic license::

	>>> engine = Engine('testfw')
	>>> for node in engine.nodes:
	...   node.bind_license()
