Reference
=========

Elements
--------

.. automodule:: smc.elements.element
    :exclude-members: SMCElement
    :show-inheritance:

SMCElement
++++++++++

.. autoclass:: SMCElement
	:members:
	:show-inheritance:

Host
++++

.. autoclass:: Host
   :members:
   :show-inheritance:

Network
+++++++

.. autoclass:: Network
   :members:
   :show-inheritance:

AddressRange
++++++++++++

.. autoclass:: AddressRange
   :members:
   :show-inheritance:

Router
++++++

.. autoclass:: Router
   :members:
   :show-inheritance:

Group
+++++

.. autoclass:: Group
   :members:
   :show-inheritance:

DomainName
++++++++++

.. autoclass:: DomainName 
   :members:
   :show-inheritance:

TCPService
++++++++++

.. autoclass:: TCPService 
   :members:
   :show-inheritance:

UDPService
++++++++++

.. autoclass:: UDPService 
   :members:
   :show-inheritance:
   
IPService
+++++++++

.. autoclass:: IPService 
   :members:
   :show-inheritance:
   
EthernetService
+++++++++++++++

.. autoclass:: EthernetService 
   :members:
   :show-inheritance:
   
Protocol
++++++++

.. autoclass:: Protocol 
   :members:
   :show-inheritance:
   
ICMPService
+++++++++++

.. autoclass:: ICMPService 
   :members:
   :show-inheritance:
   
ICMPIPv6Service
+++++++++++++++

.. autoclass:: ICMPIPv6Service 
   :members:
   :show-inheritance:
   
ServiceGroup
++++++++++++

.. autoclass:: ServiceGroup 
   :members:
   :show-inheritance:
   
TCPServiceGroup
+++++++++++++++

.. autoclass:: TCPServiceGroup 
   :members:
   :show-inheritance:

UDPServiceGroup
+++++++++++++++

.. autoclass:: UDPServiceGroup 
   :members:
   :show-inheritance:

IPServiceGroup
++++++++++++++

.. autoclass:: IPServiceGroup 
   :members:
   :show-inheritance:

IPList
++++++

.. autoclass:: IPList
   :members:
   :exclude-members: create
   :show-inheritance:

Expression
++++++++++

.. autoclass:: Expression
	:members:
	:show-inheritance:

Zone
++++

.. autoclass:: Zone 
   :members:
   :show-inheritance:

LogicalInterface
++++++++++++++++

.. autoclass:: LogicalInterface 
   :members:
   :show-inheritance:

Engine
------

.. automodule:: smc.core.engine
   :members:
   :show-inheritance:

InternalGateway
+++++++++++++++

.. autoclass:: InternalGateway
   :members:
   :show-inheritance:

InternalEndpoint
++++++++++++++++

.. autoclass:: InternalEndpoint
   :members:
   
Resources
+++++++++

.. automodule:: smc.core.resources
	:members:

Node
----

.. automodule:: smc.core.node
   :members: Node
   :exclude-members: create
      
Engines
-------

.. automodule:: smc.core.engines
   :members:
   :undoc-members:

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

Interfaces
----------
Represents classes responsible for configuring interfaces on engines

.. automodule:: smc.core.interfaces
    :members:

Physical Interface
++++++++++++++++++

.. autoclass:: PhysicalInterface
   :members:

SingleNodeInterface
+++++++++++++++++++

.. autoclass:: SingleNodeInterface
   :members:

NodeInterface
+++++++++++++

.. autoclass:: NodeInterface
   :members:
  
InlineInterface
+++++++++++++++

.. autoclass:: InlineInterface
   :members:
  
CaptureInterface
++++++++++++++++

.. autoclass:: CaptureInterface
   :members:
  
VlanInterface
+++++++++++++

.. autoclass:: VlanInterface
   :members:

ClusterVirtualInterface
+++++++++++++++++++++++

.. autoclass:: ClusterVirtualInterface
   :members:

TunnelInterface
+++++++++++++++

.. autoclass:: TunnelInterface
   :members:

VirtualPhysicalInterface
++++++++++++++++++++++++

.. autoclass:: VirtualPhysicalInterface
   :members:
   :show-inheritance:

Dynamic Routing
---------------
Represents classes responsible for configuring dynamic routing protocols

.. automodule:: smc.routing
    :members:

OSPF
++++

.. automodule:: smc.routing.ospf
	:members:

IPAccessList
++++++++++++

.. automodule:: smc.routing.access_list
	:members: IPAccessList
	:show-inheritance:

IPv6AccessList
++++++++++++++

.. automodule:: smc.routing.access_list
	:members: IPv6AccessList
	:show-inheritance:

AccessList
++++++++++

.. automodule:: smc.routing.access_list
	:members: AccessList

IPPrefixList
++++++++++++

.. automodule:: smc.routing.prefix_list
	:members: IPPrefixList
	:show-inheritance:

IPv6PrefixList
++++++++++++++

.. automodule:: smc.routing.prefix_list
	:members: IPv6PrefixList
	:show-inheritance:
	
PrefixList
++++++++++

.. automodule:: smc.routing.prefix_list
	:members: PrefixList

Policy
------

.. automodule:: smc.policy.policy
   :members:
   :show-inheritance:

FirewallPolicy
++++++++++++++

.. automodule:: smc.policy.layer3
   :members:
   :show-inheritance:

Layer2Policy
++++++++++++

.. automodule:: smc.policy.layer2
   :members:
   :show-inheritance:

InspectionPolicy
++++++++++++++++

.. automodule:: smc.policy.inspection
   :members:
   :show-inheritance:

FileFilteringPolicy
+++++++++++++++++++

.. automodule:: smc.policy.file_filtering
   :members:
   :show-inheritance:

Rules
-----
Represents classes responsible for configuring rule types

.. automodule:: smc.policy.rule

IPv4Rule
++++++++

.. autoclass:: IPv4Rule
   :members:
   :show-inheritance:

IPv4NATRule
+++++++++++

.. autoclass:: IPv4NATRule
   :members:
   :show-inheritance:

IPv4Layer2Rule
++++++++++++++

.. autoclass:: IPv4Layer2Rule
   :members:
   :show-inheritance:
  
EthernetRule
++++++++++++

.. autoclass:: EthernetRule
   :members:
   :show-inheritance:
   
Rule
++++

.. autoclass:: Rule
   :members:
   :exclude-members: rule_common, rule_l2_common

VPN
---
Represents classes responsible for configuring VPN settings such as VPN external
gateways, VPN sites, VPN Certificate and VPN Policy

.. automodule:: smc.policy.vpn
   :members: 
 
VPNPolicy
+++++++++

.. autoclass:: VPNPolicy
   :members:
   :show-inheritance:

ExternalGateway
+++++++++++++++

.. autoclass:: ExternalGateway
   :members:
   :show-inheritance:
   
ExternalEndpoint
++++++++++++++++

.. autoclass:: ExternalEndpoint
   :members:
   
VPNSite
+++++++

.. autoclass:: VPNSite
   :members:

VPNCertificate
++++++++++++++

.. autoclass:: VPNCertificate
   :members:
 
Users
-----

.. automodule:: smc.elements.user
   :members: 
   :show-inheritance:

Mixins
------

.. automodule:: smc.elements.mixins
   :members: ModifiableMixin, ExportableMixin

Collection
----------

.. automodule:: smc.elements.collection
   :members:

Search
------

.. automodule:: smc.actions.search
   :members:

Tasks
-----

.. automodule:: smc.actions.tasks
   :members: TaskMonitor, TaskDownload
   
Session
-------

.. automodule:: smc.api.session
.. autoclass:: Session
   :members: login, logout, api_version, url, api_key, session, session_id

System
------

.. automodule:: smc.administration.system
	:members:

SMCResult
---------
Most operations being performed that involve REST operations will return an
SMCResult object. This object will hold attributes that are useful to determine
if the operation was successful and if not, the reason.

.. automodule:: smc.api.web
	:members: SMCResult

Exceptions
----------
Exceptions thrown throughout smc-python. Be sure to check functions or class methods
that have raises documentation. All exception classes subclass SMCException

.. automodule:: smc.api.exceptions
   :members:
   :show-inheritance:
