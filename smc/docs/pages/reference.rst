Reference
=========

Element
-------

.. automodule:: smc.elements.element
    :undoc-members:
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

AdminUser
+++++++++

.. autoclass:: AdminUser
   :members:

Engines
-------

.. automodule:: smc.elements.engines
    :undoc-members:
    :show-inheritance:

Engine
++++++

.. autoclass:: Engine
   :members:
   :show-inheritance:
   
Node
++++

.. autoclass:: Node
   :members: 
   :show-inheritance:

Layer3Firewall
++++++++++++++

.. autoclass:: Layer3Firewall
   :members:
   :show-inheritance:

Layer2Firewall
++++++++++++++

.. autoclass:: Layer2Firewall
   :members:
   :show-inheritance:

Layer3VirtualEngine
+++++++++++++++++++

.. autoclass:: Layer3VirtualEngine
   :members:
   :show-inheritance:

FirewallCluster
+++++++++++++++

.. autoclass:: FirewallCluster
   :members:
   :show-inheritance:

IPS
+++

.. autoclass:: IPS
   :members:
   :show-inheritance:

Interfaces
----------

.. automodule:: smc.elements.interfaces
    :members:
    :undoc-members:
    :show-inheritance:

Physical Interface
++++++++++++++++++

.. autoclass:: PhysicalInterface
   :members:
   :show-inheritance:

SingleNodeInterface
+++++++++++++++++++

.. autoclass:: SingleNodeInterface
   :members:
   :show-inheritance:

NodeInterface
+++++++++++++

.. autoclass:: NodeInterface
   :members:
   :show-inheritance:

InlineInterface
+++++++++++++++

.. autoclass:: InlineInterface
   :members:
   :show-inheritance:

CaptureInterface
++++++++++++++++

.. autoclass:: CaptureInterface
   :members:
   :show-inheritance:

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

Policy
------

.. automodule:: smc.elements.policy
    :members: Policy
    :undoc-members:
    :show-inheritance:

FirewallPolicy
++++++++++++++

.. autoclass:: FirewallPolicy
   :members:
   :show-inheritance:

InspectionPolicy
++++++++++++++++

.. autoclass:: InspectionPolicy
   :members:
   :show-inheritance:

FileFilteringPolicy
+++++++++++++++++++

.. autoclass:: FileFilteringPolicy
   :members:
   :show-inheritance:

Rule
----

.. automodule:: smc.elements.rule
   :members: Rule
   :show-inheritance:

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

VPNPolicy
---------

.. automodule:: smc.elements.vpn
   :members: VPNPolicy

InternalGateway
+++++++++++++++

.. autoclass:: InternalGateway
   :members:

InternalEndpoint
++++++++++++++++

.. autoclass:: InternalEndpoint
   :members:
   
ExternalGateway
+++++++++++++++

.. autoclass:: ExternalGateway
   :members:
   
ExternalEndpoint
++++++++++++++++

.. autoclass:: ExternalEndpoint
   :members:
   
VPNSite
+++++++

.. autoclass:: VPNSite
   :members:

Collection
----------

.. automodule:: smc.elements.collection
 
Search
------

.. automodule:: smc.actions.search
   :members:

Session
-------

.. automodule:: smc.api.web
    :members: SMCConnectionError, SMCException, SMCResult
    :undoc-members:
    :show-inheritance:

.. autoclass:: SMCAPIConnection
   :members: login, logout

System
------

.. automodule:: smc.elements.system
   :members:
   :undoc-members:
   :show-inheritance:

