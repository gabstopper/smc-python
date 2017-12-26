#############
API Reference
#############

Session
-------

.. automodule:: smc.api.session
.. autoclass:: Session
   :members: 

	
Element
-------

.. automodule:: smc.base.model
	:exclude-members: from_meta, from_href

.. autoclass:: ElementBase
	:members:

.. autoclass:: Element
	:members:
	:show-inheritance:
	:exclude-members: from_meta, from_href

	.. automethod:: objects(self)

.. _element-reference-label:


Administration
--------------

Access Rights
+++++++++++++

Access Rights provide the ability to create administrative accounts and assign or create
specific access control lists and roles to these accounts.

AccessControlList
*****************

.. autoclass:: smc.administration.access_rights.AccessControlList
	:members:
	:show-inheritance:

Administrators
**************

.. automodule:: smc.elements.user
	:members:
	:show-inheritance:

Permission
**********

.. autoclass:: smc.administration.access_rights.Permission
	:members:

Roles
*****

.. automodule:: smc.administration.role
	:members:
	:show-inheritance:

Certificates
++++++++++++

TLSCommon
*********

.. automodule:: smc.administration.certificates.tls_common
	:members:

TLSServerCredential
*******************

.. automodule:: smc.administration.certificates.tls
	:members:
	:show-inheritance:

Domains
+++++++

.. autoclass:: smc.administration.system.AdminDomain
	:members:
	:show-inheritance:
	
License
+++++++

.. automodule:: smc.administration.license
	:members:

Scheduled Tasks
+++++++++++++++

.. automodule:: smc.administration.scheduled_tasks
	:members:
	:show-inheritance:

System
++++++

.. automodule:: smc.administration.system
	:members:

Tasks
+++++

.. automodule:: smc.administration.tasks
    :members:
    :show-inheritance:

Updates
++++++++

.. automodule:: smc.administration.updates
	:members: PackageMixin

Engine Upgrade
**************

.. autoclass:: EngineUpgrade
	:members:
	:show-inheritance:

Dynamic Update
**************

.. autoclass:: UpdatePackage
	:members:
	:show-inheritance:

Elements
--------
Elements used for various configuration areas within SMC. Element types are made up of
network, service groups and other.

Network
+++++++

.. automodule:: smc.elements.network

Alias
*****

.. autoclass:: Alias
	:members:
	:show-inheritance:

AddressRange
************

.. autoclass:: AddressRange
   :members:
   :show-inheritance:

DomainName
**********

.. autoclass:: DomainName
   :members:
   :show-inheritance:

Expression
**********

.. autoclass:: Expression
	:members:
	:show-inheritance:

Host
****

.. autoclass:: Host
   :members:
   :show-inheritance:

IPList
******

.. autoclass:: IPList
   :members:
   :show-inheritance:

Network
*******

.. autoclass:: Network
   :members:
   :show-inheritance:

Router
******

.. autoclass:: Router
   :members:
   :show-inheritance:

URLListApplication
******************

.. autoclass:: URLListApplication
	:members:
	:show-inheritance:

Zone
****

.. autoclass:: Zone
   :members:
   :show-inheritance:

Services
++++++++

.. automodule:: smc.elements.service
	:members: ProtocolAgentMixin

EthernetService
***************

.. autoclass:: EthernetService
   :members:
   :show-inheritance:

ICMPService
***********

.. autoclass:: ICMPService
   :members:
   :show-inheritance:

ICMPIPv6Service
***************

.. autoclass:: ICMPIPv6Service
   :members:
   :show-inheritance:

IPService
*********

.. autoclass:: IPService
   :members:
   :show-inheritance:

Protocol
********

.. autoclass:: Protocol
   :members:
   :show-inheritance:

TCPService
**********

.. autoclass:: TCPService
   :members:
   :show-inheritance:

UDPService
**********

.. autoclass:: UDPService
   :members:
   :show-inheritance:

URLCategory
***********

.. autoclass:: URLCategory
   :members:
   :show-inheritance:


Groups
++++++

.. automodule:: smc.elements.group
	:members: GroupMixin

ICMPServiceGroup
****************

.. autoclass:: ICMPServiceGroup
	:members:
	:show-inheritance:

IPServiceGroup
**************

.. autoclass:: IPServiceGroup
   :members:
   :show-inheritance:

Group
*****

.. autoclass:: Group
   :members:
   :show-inheritance:

ServiceGroup
************

.. autoclass:: ServiceGroup
   :members:
   :show-inheritance:

TCPServiceGroup
***************

.. autoclass:: TCPServiceGroup
   :members:
   :show-inheritance:

UDPServiceGroup
***************

.. autoclass:: UDPServiceGroup
   :members:
   :show-inheritance:

URLCategoryGroup
****************

.. autoclass:: URLCategoryGroup
   :members:
   :show-inheritance:
  
Servers
+++++++

.. automodule:: smc.elements.servers
	:members: ContactAddress

DNSServer
*********

.. autoclass:: DNSServer
	:members:

HttpProxy
*********

.. autoclass:: HttpProxy
	:members:

LogServer
*********

.. autoclass:: LogServer
	:members: add_contact_address, remove_contact_address, contact_addresses
	:show-inheritance:

ManagementServer
****************

.. autoclass:: ManagementServer
	:members: add_contact_address, remove_contact_address, contact_addresses

Other
+++++

.. automodule:: smc.elements.other
	:members: prepare_blacklist

Category
********

.. autoclass:: Category
	:members:
	:show-inheritance:

CategoryTag
***********

.. autoclass:: CategoryTag
	:members:
	:show-inheritance:

FilterExpression
****************

.. autoclass:: FilterExpression
   :members:
   :show-inheritance:

Location
********

.. autoclass:: Location
   :members:
   :show-inheritance:
 
LogicalInterface
****************

.. autoclass:: LogicalInterface
   :members:
   :show-inheritance:

MacAddress
**********

.. autoclass:: MacAddress
   :members:
   :show-inheritance:

Profiles
++++++++

.. automodule:: smc.elements.profiles

DNSRelayProfile
***************

.. autoclass:: DNSRelayProfile
	:members:
	:show-inheritance:

Engine
------

.. automodule:: smc.core.engine
   :members:
   :exclude-members: create, VirtualResource, InternalEndpoint, InternalGateway
   :show-inheritance:

AddOns
++++++

.. automodule:: smc.core.properties

AntiVirus
*********

.. autoclass:: smc.core.properties.AntiVirus
	:members:
	
FileReputation
**************

.. autoclass:: smc.core.properties.FileReputation
	:members:

SidewinderProxy
***************

.. autoclass:: smc.core.properties.SidewinderProxy
	:members:

UrlFiltering
************

.. autoclass:: smc.core.properties.UrlFiltering
	:members:

Sandbox
*******

.. autoclass:: smc.core.properties.Sandbox
	:members:

TLSInspection
*************

.. autoclass:: smc.core.properties.TLSInspection
	:members:

Dynamic Routing
+++++++++++++++
Represents classes responsible for configuring dynamic routing protocols

OSPF
****

.. automodule:: smc.routing.ospf
	:members:

BGP
***

.. automodule:: smc.routing.bgp
	:members:

AccessList
**********

.. automodule:: smc.routing.access_list
	:members:

PrefixList
**********

.. automodule:: smc.routing.prefix_list
	:members:
	:show-inheritance:

General
+++++++

DefaultNAT
**********

.. autoclass:: smc.core.properties.DefaultNAT
	:members:

DNSAddress
**********

.. autoclass:: smc.core.properties.DNSAddress
	:members:

.. autoclass:: smc.core.properties.DNSEntry
	:members:

Layer2Settings
**************

.. autoclass:: smc.core.properties.Layer2Settings
	:members:

VPN
+++

Provisioning a firewall for VPN consists of the following steps:

* Enable VPN an interface (`InternalEndpoint`)
* Optionally add VPN sites with protected networks

.. note:: By default Stonesoft FW's provide a capability that allows the protected 
  VPN networks to be identified based on the routing table.

It is still possible to override this setting and add your own custom VPN sites as needed.

Once the firewall has VPN enabled, you must also assign the FW to a specified Policy VPN as a central or satellite gateway.

The entry point for enabling the VPN on an engine is under the engine resource :class:`smc.core.engine.Engine.vpn`.

Enabling IPSEC on an interface is done by accessing the engine resource and finding the correct `InternalEndpoint` for which to enable the VPN. Internal Endpoints are not exactly interface maps, instead they identify all addresses on a given firewall capable for running VPN. It is possible for a single interface to have more than one internal endpoint if the interface has multiple IP addresses assigned.

.. code:: python

  >>> from smc.core.engine import Engine
  >>> engine = Engine('myfirewall')
  >>> for ie in engine.vpn.internal_endpoint:
  ...   ie
  ... 
  InternalEndpoint(name=6.6.6.6)
  InternalEndpoint(name=10.10.0.1)
  InternalEndpoint(name=11.11.11.11)
  InternalEndpoint(name=4.4.4.4)
  InternalEndpoint(name=10.10.10.1) 

Notice that internal endpoints are referenced by their IP address and not their interface. The interface is available as an attribute on the endpoint to make it easier to find the correct interface:

.. code:: python

  >>> for ie in engine.vpn.internal_endpoint:
  ...   print(ie, ie.interface_id)
  ... 
  (InternalEndpoint(name=6.6.6.6), u'6')
  (InternalEndpoint(name=10.10.0.1), u'0')
  (InternalEndpoint(name=11.11.11.11), u'11')
  (InternalEndpoint(name=4.4.4.4), u'2.200')
  (InternalEndpoint(name=10.10.10.1), u'1')

If I want to enable VPN on interface 0, you can obtain the right endpoint and enable:

.. code:: 

  >>> for ie in engine.vpn.internal_endpoint:
  ...   if ie.interface_id == '0':
  ...     ie.ipsec_vpn = True

.. note:: Once you've enabled the interface for VPN, you must also call engine.update() to commit the change.

The second step (optional) is to add VPN sites to the firewall. VPN Sites define a group of protected networks that can be applied to the VPN.

For example, add a new VPN site called wireless with a new network element that we'll create beforehand.

.. code:: python

  >>> net = Network.get_or_create(name='wireless', ipv4_network='192.168.5.0/24') 
  >>> engine.vpn.add_site(name='wireless', site_elements=[net]) 
  VPNSite(name=wireless) 
  >>> list(engine.vpn.sites) 
  [VPNSite(name=dingo - Primary Site), VPNSite(name=wireless)] 

Once the engine is enabled for VPN, see :class:`smc.vpn.policy.PolicyVPN` for information on how to create a PolicyVPN and add engines.
	
InternalEndpoint
****************

.. autoclass:: smc.core.engine.InternalEndpoint
   :members:
   :show-inheritance:

InternalGateway
***************

.. autoclass:: smc.core.engine.InternalGateway
   :members:
   :show-inheritance:
   
Interfaces
++++++++++
Represents classes responsible for configuring interfaces on engines

.. automodule:: smc.core.interfaces
	:members: Interface

InterfaceCollection
*******************

.. autoclass:: InterfaceCollection
	:members:

InterfaceOptions
****************

.. autoclass:: InterfaceOptions
    :members:

LoopbackInterface
*****************

.. autoclass:: LoopbackInterface
    :members:
    :exclude-members: create
    :show-inheritance:
    
.. autoclass:: LoopbackCollection
	:members:

LoopbackClusterInterface
************************

.. autoclass:: LoopbackClusterInterface
    :members:
    :exclude-members: create
    :show-inheritance:
    
PhysicalInterface
*****************

.. autoclass:: PhysicalInterface
    :members:
    :show-inheritance:

PhysicalVlanInterface
*********************

.. autoclass:: PhysicalVlanInterface
	:members:
	:exclude-members: create
	:show-inheritance:

VirtualPhysicalInterface
************************

.. autoclass:: VirtualPhysicalInterface
   :members:
   :show-inheritance:

TunnelInterface
***************

.. autoclass:: TunnelInterface
    :members:
    :show-inheritance:

ContactAddress
**************

.. automodule:: smc.core.contact_address
	:members:

Sub-Interface Types
*******************

.. automodule:: smc.core.sub_interfaces

ClusterVirtualInterface
^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: ClusterVirtualInterface
	:members:
	:exclude-members: create

InlineInterface
^^^^^^^^^^^^^^^

.. autoclass:: InlineInterface
   :members:
   :exclude-members: create

CaptureInterface
^^^^^^^^^^^^^^^^

.. autoclass:: CaptureInterface
	:members:
	:exclude-members: create

NodeInterface
^^^^^^^^^^^^^

.. autoclass:: NodeInterface
	:members:
	:exclude-members: create

SingleNodeInterface
^^^^^^^^^^^^^^^^^^^

.. autoclass:: SingleNodeInterface
	:members:
	:show-inheritance:
	:exclude-members: create, create_dhcp

Node
++++

.. automodule:: smc.core.node
   :members: Node
   :exclude-members: create
   :show-inheritance:

Appliance Info
**************

.. autoclass:: smc.core.node.ApplianceInfo
	:show-inheritance:

Appliance Status
****************

.. autoclass:: smc.core.node.ApplianceStatus
	:show-inheritance:

Hardware Status
***************

.. autoclass:: smc.core.node.HardwareStatus
	:members:

.. autoclass:: smc.core.node.HardwareCollection
	:members:
	
.. autoclass:: smc.core.node.Status
	:show-inheritance:
	
Interface Status
****************

.. autoclass:: smc.core.node.InterfaceStatus
	:members:

.. autoclass:: smc.core.node.ImmutableInterface
	:show-inheritance:

Debug
*****

.. autoclass:: smc.core.node.Debug
	:members:

Pending Changes
+++++++++++++++

.. automodule:: smc.core.resource
	:members: PendingChanges, ChangeRecord

Routing
+++++++

.. automodule:: smc.core.route

Routing
*******

.. autoclass:: Routing
	:members:
	:show-inheritance:

Route Table
***********

.. autoclass:: Routes
	:members:

Policy Routing
**************

.. autoclass:: PolicyRoute
	:members:
	
.. autoclass:: PolicyRouteEntry
	:members:

Antispoofing
************

.. autoclass:: Antispoofing
	:members:
	:show-inheritance:

Traffic Handlers (Netlinks)
***************************

.. automodule:: smc.elements.netlink
	:members:
	:show-inheritance:

Snapshot
++++++++

.. autoclass:: smc.core.resource.Snapshot
	:members:
	:show-inheritance:

VirtualResource
+++++++++++++++

.. autoclass:: smc.core.engine.VirtualResource
	:members:
	:show-inheritance:

Engine Types
------------

.. automodule:: smc.core.engines

IPS
+++

.. autoclass:: IPS
   :members:

Layer3Firewall
++++++++++++++

.. autoclass:: Layer3Firewall
   :members:

Layer2Firewall
++++++++++++++

.. autoclass:: Layer2Firewall
   :members:

Layer3VirtualEngine
+++++++++++++++++++

.. autoclass:: Layer3VirtualEngine
   :members:

FirewallCluster
+++++++++++++++

.. autoclass:: FirewallCluster
   :members:

MasterEngine
++++++++++++

.. autoclass:: MasterEngine
   :members:

MasterEngineCluster
+++++++++++++++++++

.. autoclass:: MasterEngineCluster
	:members:

Policy
------

.. automodule:: smc.policy.policy
   :members: Policy
   :show-inheritance:

FirewallPolicy
++++++++++++++

.. automodule:: smc.policy.layer3
   :members:
   :show-inheritance:


InterfacePolicy
+++++++++++++++

.. automodule:: smc.policy.interface
   :members:
   :show-inheritance:


IPSPolicy
+++++++++

.. automodule:: smc.policy.ips
   :members:
   :show-inheritance:
   
Layer2Policy
++++++++++++

.. automodule:: smc.policy.layer2
   :members:
   :show-inheritance:

InspectionPolicy
++++++++++++++++

.. autoclass:: smc.policy.policy.InspectionPolicy
   :members:
   :show-inheritance:

FileFilteringPolicy
+++++++++++++++++++

.. automodule:: smc.policy.file_filtering
   :members:
   :show-inheritance:


Sub Policy
----------

Sub Policies are referenced from within a normal policy as a parameter to
a 'jump' action. They provide rule encapsulation for similar rules and can
be delegated to an Admin User for more granular policy control.

FirewallSubPolicy
+++++++++++++++++

.. autoclass:: smc.policy.layer3.FirewallSubPolicy
   :members:
   :show-inheritance:

Policy Rules
------------
Represents classes responsible for configuring rule types.

.. automodule:: smc.policy.rule

Rule
++++

.. autoclass:: Rule
	:members:
	:show-inheritance:

IPv4Rule
********

.. autoclass:: IPv4Rule
   :members:
   :show-inheritance:

IPv4Layer2Rule
**************

.. autoclass:: IPv4Layer2Rule
   :members:
   :show-inheritance:

EthernetRule
************

.. autoclass:: EthernetRule
   :members:
   :show-inheritance:

IPv6Rule
********

.. autoclass:: IPv6Rule
   :members:
   :show-inheritance:

NATRule
+++++++

.. autoclass:: smc.policy.rule_nat.NATRule
	:members:
	:show-inheritance:

IPv4NATRule
***********

.. autoclass:: smc.policy.rule_nat.IPv4NATRule
   :members:
   :show-inheritance:

IPv6NATRule
***********

.. autoclass:: smc.policy.rule_nat.IPv6NATRule
   :members:
   :show-inheritance:

RuleElements
++++++++++++

.. automodule:: smc.policy.rule_elements
.. autoclass:: smc.policy.rule_elements.RuleElement
	:members:

Source
******

.. autoclass:: Source
	:members:
	:show-inheritance:

Destination
***********

.. autoclass:: Destination
	:members:
	:show-inheritance:

Service
*******

.. autoclass:: Service
	:members:
	:show-inheritance:

Action
******

.. autoclass:: Action
	:members:
	:show-inheritance:

ConnectionTracking
******************

.. autoclass:: ConnectionTracking
	:members:
	:show-inheritance:

LogOptions
**********

.. autoclass:: LogOptions
	:members:
	:show-inheritance:

AuthenticationOptions
*********************

.. autoclass:: AuthenticationOptions
	:members:
	:show-inheritance:

MatchExpression
***************

.. autoclass:: MatchExpression
	:members:
	:show-inheritance:

NATRuleElements
+++++++++++++++

.. automodule:: smc.policy.rule_nat
.. autoclass:: NAT
	:members:

DynamicSourceNAT
****************

.. autoclass:: DynamicSourceNAT
	:members:
	:show-inheritance:

StaticSourceNAT
***************

.. autoclass:: StaticSourceNAT
	:members:
	:show-inheritance:

DynamicSourceNAT
****************

.. autoclass:: DynamicSourceNAT
	:members:
	:show-inheritance:

VPN Configuration
-----------------
Represents classes responsible for configuring VPN settings such as PolicyVPN,
RouteVPN and all associated configurations.

.. note:: See API reference documentation on the Engine for instructions on how to enable the
  engine for VPN.

PolicyVPN
+++++++++

.. automodule:: smc.vpn.policy
   :members:
   :show-inheritance:

RouteVPN
++++++++

.. automodule:: smc.vpn.route
	:members:
	:show-inheritance:

ExternalGateway
+++++++++++++++

.. autoclass:: smc.vpn.elements.ExternalGateway
   :members:
   :show-inheritance:

ExternalEndpoint
++++++++++++++++

.. autoclass:: smc.vpn.elements.ExternalEndpoint
   :members:
   :show-inheritance:

VPNSite
+++++++

.. autoclass:: smc.vpn.elements.VPNSite
   :members:
   :show-inheritance:

GatewaySettings
+++++++++++++++

.. autoclass:: smc.vpn.elements.GatewaySettings
	:members:
	:show-inheritance:

GatewayNode
+++++++++++

.. autoclass:: smc.vpn.policy.GatewayNode
	:members:
	:show-inheritance:

GatewayProfile
++++++++++++++

.. autoclass:: smc.vpn.elements.GatewayProfile
	:members:
	:show-inheritance:

GatewayTreeNode
+++++++++++++++

.. autoclass:: smc.vpn.policy.GatewayTreeNode
	:members:
	:show-inheritance:

GatewayTunnel
+++++++++++++

.. autoclass:: smc.vpn.policy.GatewayTunnel
	:members:
	:show-inheritance:


Searching
---------

Collection
++++++++++

.. automodule:: smc.base.collection
	:members:
	:show-inheritance:


Search
++++++

Low level searching helper functions.

Search provides many front end search functions that enable you to retrieve abbreviated versions of the
data you requested. All GET requests to the SMC API will return an :class:`SMCResult` with attributes set, however
there may be cases where you only want a subset of this information. The search module provides these helper
functions to return the data you need.

Below are some common examples of retrieving data from the SMC:

.. code-block:: python

   #Only return the href of a particular SMC Element:
   smc.actions.search.element_href(name)

   #To obtain full json for an SMC Element:
   smc.actions.search.element_as_json(name)

   #To obtain full json data and etag information for SMC Element (etag used for modifying an element):
   smc.actions.search.element_as_json_with_etag(name)

   #To find all elements by type:
   smc.actions.search.elements_by_type('host')

   #To find all available log servers:
   smc.actions.search.log_servers()

   #To find all L3 FW policies:
   smc.actions.search.fw_policies()


.. automodule:: smc.actions.search
   :members:

Advanced Usage
--------------

SMCRequest
++++++++++

.. automodule:: smc.api.common
	:members: SMCRequest

SMCResult
+++++++++
Operations being performed that involve REST calls to SMC will return an
SMCResult object. This object will hold attributes that are useful to determine
if the operation was successful and if not, the reason. An SMCResult is handled
automatically and uses exceptions to provide statuses between modules and user
interaction.
The simplest way to get access to an SMCResult directly is to make an SMCRequest
using :func:`smc.base.model.prepared_request` and observe the attributes in the
return message.
All response data is serialized into the SMCResult.json attribute when it is
received by the SMC.

.. automodule:: smc.api.web
	:members: SMCResult
	
Example of using SMCRequest to fetch an element by href, returning an SMCResult:

	>>> vars(SMCRequest(href='http://1.1.1.1:8082/6.2/elements/host/978').read())
	{'code': 200, 'content': None, 'json': {u'comment': u'this is a searchable comment', u'read_only': False, u'ipv6_address': u'2001:db8:85a3::8a2e:370:7334', u'name': u'kali', u'third_party_monitoring': {u'netflow': False, u'snmp_trap': False}, u'system': False, u'link': [{u'href': u'http://1.1.1.1:8082/6.2/elements/host/978', u'type': u'host', u'rel': u'self'}, {u'href': u'http://1.1.1.1:8082/6.2/elements/host/978/export', u'rel': u'export'}, {u'href': u'http://1.1.1.1:8082/6.2/elements/host/978/search_category_tags_from_element', u'rel': u'search_category_tags_from_element'}], u'key': 978, u'address': u'1.1.11.1', u'secondary': [u'7.7.7.7']}, 'href': None, 'etag': '"OTc4MzExMzkxNDk2MzI1MTMyMDI4"', 'msg': None}


Waiters
-------

.. automodule:: smc.core.waiters
	:members:
	:show-inheritance:

Exceptions
----------
Exceptions thrown throughout smc-python. Be sure to check functions or class methods
that have raises documentation. All exception classes subclass SMCException

.. automodule:: smc.api.exceptions
   :members:
   :show-inheritance:
   	