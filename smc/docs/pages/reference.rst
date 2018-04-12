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
	:members:

.. autoclass:: ElementBase
	:members:
	:exclude-members: get_relation, from_meta, from_href

.. autoclass:: Element
	:members:
	:show-inheritance:
	:exclude-members: from_meta, from_href

	.. automethod:: objects(self)

.. autoclass:: SubElement
	:members:
	:show-inheritance:

.. autoclass:: smc.core.resource.History
	:members:

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
	:exclude-members: load_cert_chain, pem_as_string

TLSServerCredential
*******************
.. automodule:: smc.administration.certificates.tls

.. autoclass:: TLSServerCredential
	:members:
	:show-inheritance:

ClientProtectionCA
******************

.. autoclass:: ClientProtectionCA
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

Reports
+++++++

.. automodule:: smc.administration.reports
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
    :exclude-members: download, execute
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
	:members:

Blacklist
*********

.. autoclass:: Blacklist
	:members:

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

Profiles are generic container settings that are used in other areas of the SMC configuration.
Each profile should document it's usage and how it is referenced.

DNSRelayProfile
***************

.. automodule:: smc.elements.profiles
	:members: DNSRelayProfile, FixedDomainAnswer, HostnameMapping, DomainSpecificDNSServer, DNSAnswerTranslation, DNSRule
	:show-inheritance:

SNMPAgent
*********

	.. autoclass:: SNMPAgent
		:members:
		:show-inheritance:

Engine
------

.. automodule:: smc.core.engine
   :members:
   :exclude-members: create, VirtualResource, InternalEndpoint, InternalGateway
   :show-inheritance:

AddOn
+++++

.. automodule:: smc.core.addon

AntiVirus
*********

.. autoclass:: smc.core.addon.AntiVirus
	:members:
	
FileReputation
**************

.. autoclass:: smc.core.addon.FileReputation
	:members:

SidewinderProxy
***************

.. autoclass:: smc.core.addon.SidewinderProxy
	:members:

UrlFiltering
************

.. autoclass:: smc.core.addon.UrlFiltering
	:members:

Sandbox
*******

.. autoclass:: smc.core.addon.Sandbox
	:members:

TLSInspection
*************

.. autoclass:: smc.core.addon.TLSInspection
	:members:

ContactAddress
++++++++++++++

.. automodule:: smc.core.contact_address
	:members:
	:show-inheritance:

Dynamic Routing
+++++++++++++++
Represents classes responsible for configuring dynamic routing protocols

OSPF
****

For more information on creating OSPF elements and enabling on a layer 3
engine:

.. seealso:: :py:mod:`smc.routing.ospf`

BGP
***

For more information on creating BGP elements and enabling on a layer 3
engine:

.. seealso:: :py:mod:`smc.routing.bgp`


General
+++++++

DefaultNAT
**********

.. autoclass:: smc.core.general.DefaultNAT
	:members:

DNSAddress
**********

.. autoclass:: smc.core.general.DNSAddress
	:members:

.. autoclass:: smc.core.general.DNSEntry
	:members:

DNS Relay
*********

.. autoclass:: smc.core.general.DNSRelay
	:members:

SNMP
****

.. autoclass:: smc.core.general.SNMP
	:members:

Layer2Settings
**************

.. autoclass:: smc.core.general.Layer2Settings
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

InterfaceCollections
********************

.. automodule:: smc.core.collection
	:members:
	:exclude-members: get_all_loopbacks
	:show-inheritance:

.. automodule:: smc.core.interfaces
	:members: Interface

InterfaceOptions
****************

.. autoclass:: InterfaceOptions
    :members:

LoopbackInterface
*****************

.. autoclass:: smc.core.sub_interfaces.LoopbackInterface
    :members:
    :exclude-members: create
    :show-inheritance:

LoopbackClusterInterface
************************

.. autoclass:: smc.core.sub_interfaces.LoopbackClusterInterface
    :members:
    :exclude-members: create
    :show-inheritance:
    
PhysicalInterface
*****************

.. autoclass:: PhysicalInterface
    :members:
    :show-inheritance:

Layer3PhysicalInterface
***********************

.. autoclass:: Layer3PhysicalInterface
	:members:
	:show-inheritance:

Layer2PhysicalInterface
***********************

.. autoclass:: Layer3PhysicalInterface
	:members:
	:show-inheritance:

ClusterPhysicalInterface
************************

.. autoclass:: ClusterPhysicalInterface
	:members:
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

Sub-Interfaces
**************

.. automodule:: smc.core.sub_interfaces
	:members:
	:exclude-members: create

Node
++++

.. automodule:: smc.core.node
   :members: Node, NodeCollection
   :exclude-members: create, update
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
	:show-inheritance:

.. autoclass:: smc.core.node.Status
	:show-inheritance:
	
Interface Status
****************

.. autoclass:: smc.core.node.InterfaceStatus
	:members:
	:show-inheritance:

Debug
*****

.. autoclass:: smc.core.node.Debug
	:members:

Pending Changes
+++++++++++++++

.. automodule:: smc.core.resource
	:members: PendingChanges, ChangeRecord
	:show-inheritance:

Routing
+++++++

.. automodule:: smc.core.route
	:members: RoutingTree

Routing
*******

.. autoclass:: Routing
	:members:
	:show-inheritance:

Antispoofing
************

.. autoclass:: Antispoofing
	:members:
	:show-inheritance:

Route Table
***********

.. autoclass:: Route
	:members:

Policy Routing
**************

.. autoclass:: PolicyRoute
	:members:


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

Dynamic Routing Elements
------------------------

RouteMap
++++++++

.. automodule:: smc.routing.route_map
	:members:
	:exclude-members: Metric, Condition
	:show-inheritance:

.. autoclass:: smc.routing.route_map.Metric
	:show-inheritance:
	
.. autoclass:: smc.routing.route_map.Condition
	:show-inheritance:

IPAccessList
++++++++++++

.. automodule:: smc.routing.access_list
	:members:
	:exclude-members: AccessListEntry
	:show-inheritance:

.. autoclass:: smc.routing.access_list.AccessListEntry
	:show-inheritance:

IPPrefixList
++++++++++++

.. automodule:: smc.routing.prefix_list
	:members:
	:exclude-members: PrefixListEntry
	:show-inheritance:

.. autoclass:: smc.routing.prefix_list.PrefixListEntry
	:show-inheritance:

BGP Elements
++++++++++++

.. automodule:: smc.routing.bgp
	:members: BGP

AutonomousSystem
****************

.. autoclass:: AutonomousSystem
	:members:
	:show-inheritance:
	
ExternalBGPPeer
***************

.. autoclass:: ExternalBGPPeer
	:members:
	:show-inheritance:

BGPPeering
**********

.. autoclass:: BGPPeering
	:members:
	:show-inheritance:

BGPProfile
**********

.. autoclass:: BGPProfile
	:members:
	:show-inheritance:

BGPConnectionProfile
********************

.. autoclass:: BGPConnectionProfile
	:members:
	:show-inheritance:

ASPathAccessList
****************

.. autoclass:: smc.routing.bgp_access_list.ASPathAccessList
	:members:
	:show-inheritance:
	
.. autoclass:: smc.routing.bgp_access_list.ASPathListEntry
	:show-inheritance:

CommunityAccessList
*******************

.. autoclass:: smc.routing.bgp_access_list.CommunityAccessList
	:members:
	:show-inheritance:
	
.. autoclass:: smc.routing.bgp_access_list.CommunityListEntry
	:show-inheritance:
	
ExtendedCommunityAccessList
***************************

.. autoclass:: smc.routing.bgp_access_list.ExtendedCommunityAccessList
	:members:
	:show-inheritance:
	
.. autoclass:: smc.routing.bgp_access_list.ExtCommunityListEntry
	:show-inheritance:


OSPF Elements
+++++++++++++

.. automodule:: smc.routing.ospf
	:members: OSPF

OSPFArea
********

.. autoclass:: OSPFArea
	:members:
	:show-inheritance:

OSPFKeyChain
************

.. autoclass:: OSPFKeyChain
	:members:
	:show-inheritance:

OSPFProfile
***********

.. autoclass:: OSPFProfile
	:members:
	:show-inheritance:
	
OSPFDomainSetting
*****************

.. autoclass:: OSPFDomainSetting
	:members:
	:show-inheritance:

OSPFInterfaceSetting
********************

.. autoclass:: OSPFInterfaceSetting
	:members:
	:show-inheritance:




Policies
--------

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


Sub Policies
------------

Sub Policies are referenced from within a normal policy as a parameter to
a 'jump' action. They provide rule encapsulation for similar rules and can
be delegated to an Admin User for more granular policy control.

FirewallSubPolicy
+++++++++++++++++

.. autoclass:: smc.policy.layer3.FirewallSubPolicy
   :members:
   :show-inheritance:

Rules
-----
Represents classes responsible for configuring rule types.

Rule
++++

.. autoclass:: smc.policy.rule.Rule
	:members:
	:show-inheritance:

IPv4Rule
********

.. autoclass:: smc.policy.rule.IPv4Rule
   :members: create_rule_section, create
   :show-inheritance:

IPv4Layer2Rule
**************

.. autoclass:: smc.policy.rule.IPv4Layer2Rule
   :members: create_rule_section, create
   :show-inheritance:

EthernetRule
************

.. autoclass:: smc.policy.rule.EthernetRule
   :members: create_rule_section, create
   :show-inheritance:

IPv6Rule
********

.. autoclass:: smc.policy.rule.IPv6Rule
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
   :members: create_rule_section, create
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

NATElements
+++++++++++

.. automodule:: smc.policy.rule_nat
	:members: NATElement

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

VPN
---
Represents classes responsible for configuring VPN settings such as PolicyVPN,
RouteVPN and all associated configurations.

.. note:: See API reference documentation on the Engine for instructions on how to enable the
  engine for VPN.

PolicyVPN
+++++++++

.. autoclass:: smc.vpn.policy.PolicyVPN
   :members:
   :show-inheritance:

RouteVPN
++++++++

.. automodule:: smc.vpn.route
	:members:
	:show-inheritance:

Gateways
++++++++

ExternalGateway
***************

.. automodule:: smc.vpn.elements
	:exclude-members: VPNSite

.. autoclass:: ExternalGateway
	:members:
	:show-inheritance:
	

ExternalEndpoint
****************

.. autoclass:: ExternalEndpoint
   :members:
   :show-inheritance:

VPNSite
+++++++

.. autoclass:: smc.vpn.elements.VPNSite
   :members:
   :show-inheritance:

Other Elements
++++++++++++++
Other elements associated with VPN configurations

GatewaySettings
***************

.. autoclass:: smc.vpn.elements.GatewaySettings
	:members:
	:show-inheritance:

GatewayNode
***********

.. autoclass:: smc.vpn.policy.GatewayNode
	:members:
	:show-inheritance:

GatewayProfile
**************

.. autoclass:: smc.vpn.elements.GatewayProfile
	:members:
	:show-inheritance:

GatewayTreeNode
***************

.. autoclass:: smc.vpn.policy.GatewayTreeNode
	:members:
	:show-inheritance:

GatewayTunnel
*************

.. autoclass:: smc.vpn.policy.GatewayTunnel
	:members:
	:show-inheritance:


Collections Reference
---------------------

.. automodule:: smc.base.collection

ElementCollection
+++++++++++++++++

.. autoclass:: ElementCollection
	:members:

.. autoclass:: CollectionManager
	:members:

SubElementCollection
++++++++++++++++++++

.. autoclass:: SubElementCollection
	:members:

CreateCollection
****************

.. autoclass:: CreateCollection
	:members:
	:show-inheritance:
	
RuleCollection
**************
	
.. autofunction:: rule_collection


Search
++++++

.. autoclass:: Search
	:members:
	:show-inheritance:

BaseIterable
++++++++++++

.. automodule:: smc.base.structs

.. autoclass:: BaseIterable
	:members:
	
SerializedIterable
++++++++++++++++++

.. autoclass:: SerializedIterable
	:members:
	:show-inheritance:


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
   	