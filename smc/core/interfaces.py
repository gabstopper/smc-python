"""
Interface module encapsulates interface types for security engines.
All interface have a 'top level' such as Physical or Tunnel Interface.
These top level interfaces have certain common settings that can be
modified such as assigning a zone.

IP addresses, netmask, management settings, VLANs, etc are part of an
interfaces 'sub' interface. Sub interfaces can be retrieved from an engine
reference and call to :func:`~smc.core.interfaces.Interface.sub_interfaces`

The interface hierarchy resembles:

::

    Physical/Tunnel Interface
            |
        Sub Interface (SingleNodeInterface, NodeInterface, InlineInterface, etc)
            |
        Attributes (address, network_value, vlan_id, etc)

Sub interfaces are documented in :py:mod:`smc.core.sub_interfaces`.

VLANs are properties of specific interfaces and can also be retrieved by
first getting the top level interface, and calling :func:`~smc.core.interfaces.Interface.vlan_interfaces`
to view or modify specific aspects of a VLAN, such as addresses, etc.
"""
import re
from smc.base.model import prepared_request, SubElement, lookup_class
from smc.api.exceptions import EngineCommandFailed, FetchElementFailed
from smc.core.sub_interfaces import (NodeInterface, SingleNodeInterface,
                                     ClusterVirtualInterface, InlineInterface,
                                     CaptureInterface, _add_vlan_to_inline,
                                     SubInterface)


def dispatch(instance, builder, interface=None):
    """
    Dispatch to SMC. Once successfully, reset the
    engine level cache or instances will not have
    visibility to newly added interfaces without
    re-retrieving.
    """
    if interface:  # Modify
        prepared_request(
            EngineCommandFailed,
            href=interface.href,
            json=builder.data,
            etag=interface.etag
        ).update()
    else:
        # Create
        prepared_request(
            EngineCommandFailed,
            href=instance.href,
            json=builder.data
        ).create()
    # Clear cache, next call for attributes will refresh it
    try:
        del instance._engine.cache
    except AttributeError:
        pass


class InterfaceCommon(object):
    """
    Interface settings common to Tunnel and Physical Interface
    types.
    """
    @property
    def addresses(self):
        """
        Return 3-tuple with (address, network, nicid)

        :return: address related information of interface as 3-tuple list
        :rtype: list
        """
        return [(i.address, i.network_value, i.nicid)
                for i in self.sub_interfaces()]

    def contact_addresses(self):
        """
        View the contact address/es for this physical interface.
        Use :meth:`~add_contact_address` to add a new contact
        address to the interface.

        :return: list :py:class:`smc.core.contact_address.ContactInterface`

        .. seealso:: :py:mod:`smc.core.contact_address`
        """
        return self._engine.contact_addresses(self.interface_id)

    @property
    def has_vlan(self):
        """
        Does the interface have VLANs

        :return: True, False if the interface has VLANs defined
        :rtype: bool
        """
        if 'vlanInterfaces' in self.data:
            return bool(self.data['vlanInterfaces'])
        return False

    @property
    def has_interfaces(self):
        """
        Does the interface have interface IP's assigned

        :return boolean value
        """
        if 'interfaces' in self.data:
            return bool(self.data['interfaces'])
        return False

    @property
    def interfaces(self):
        if self.has_interfaces:
            return [subif for subif in SubInterface(
                self.data.get('interfaces'))]
        return []

    def vlan_interfaces(self):
        """
        Access VLAN interfaces for this interface.

        Retrieve interface and view vlan interfaces::

            engine = Engine('testfw')
            for intf in engine.interface.all():
                if intf.has_vlan:
                    print(intf.vlan_interfaces()) #Show VLANs

        :return: list :py:class:`smc.core.interfaces.PhysicalVlanInterface`
        """
        if self.has_vlan:
            return [PhysicalVlanInterface(vlan)
                    for vlan in self.data['vlanInterfaces']]
        return []

    def sub_interfaces(self):
        """
        Access sub interfaces with sub-interface information. Single
        engines will typically only have 1 sub-interface, however interfaces
        with VLANs, clusters, or multiple IP's assigned will have multiple.
        It is not required to use this method to access interface attributes.
        However, it is required to make modifications to the right interface.

        Retrieve interface and type, with address and network::

            engine = Engine('testfw')
            for intf in engine.interface.all():
                for x in intf.sub_interfaces():
                    print(x) #Show sub interfaces by type
                    if x.address == '1.1.1.1':
                        x.address = '1.1.1.5'    #Change the IP address
                intf.save() #Save to top level interface

        :return: list :py:mod:`smc.core.sub_interfaces` by type
        """
        results = []

        data = self.data

        def inner(data):
            if data.get('interfaces'):
                # It's an interface definition
                for intf in data['interfaces']:
                    for if_type, values in intf.items():
                        results.append(
                            SubInterface.get_subinterface(if_type)(values))
            elif data.get('vlanInterfaces'):
                for vlan in data.get('vlanInterfaces'):
                    inner(vlan)
            else:
                if self.typeof == TunnelInterface.typeof:
                    pass
                else:  # PhysicalVlanInterface
                    if '.' in data.get('interface_id'):
                        results.append(PhysicalVlanInterface(data))
        inner(data)
        return results

    @property
    def comment(self):
        """
        Optional comment

        :param str value: comment
        :rtype: str
        """
        return self.data.get('comment')

    @comment.setter
    def comment(self, value):
        self.data['comment'] = value

    @property
    def interface_id(self):
        """
        The Interface ID automatically maps to a physical network port
        of the same number during the initial configuration of the engine,
        but the mapping can be changed as necessary.
        Change the interface ID for an existing interface::

            for x in engine.interface.all():
                if x.name == 'Interface 1':
                    x.interface_id = 13
                    x.save()

        :param str value: interface_id
        :rtype: str
        """
        return self.data.get('interface_id')

    @interface_id.setter
    def interface_id(self, value):
        self.data['interface_id'] = value

    @property
    def zone_ref(self):
        """
        Zone for this physical interface.

        :param str value: href of zone, set to None to remove existing zone
        :rtype: str
        """
        return self.data.get('zone_ref')

    @zone_ref.setter
    def zone_ref(self, value):
        if value is None:
            self.data.pop('zone_ref', None)
        else:
            self.data['zone_ref'] = value


class Interface(SubElement):
    """
    Top level representation of all base interface types. Base interface types
    are: Physical, VirtualPhysical and Tunnel Interface. All other interface
    types are considered sub-interfaces and will be used depending on the type
    of engine. For example, an Inline Interface is a Physical Interface, but can
    only be used on Layer 2 Firewall or IPS Engines.

    Note that when modifying existing interface information changes can only be
    made to a single interface at once. Some changes like switching management
    interfaces is currently not supported.
    """

    def __init__(self, **meta):
        self._engine = meta.pop('engine', None)  # Engine reference
        if 'parent' in meta:
            self._parent = meta.pop('parent')
            meta.update(href=self._parent)
        super(Interface, self).__init__(**meta)

    def get(self, interface_id):
        """
        Get the interface by id, if known. The interface is
        retrieved from the top level Physical or Tunnel Interface.
        If interface type is unknown, use engine.interface
        for retrieving::

            >>> engine = Engine('sg_vm')
            >>> intf = engine.interface.get(0)
            >>> print(intf, intf.addresses)
            (PhysicalInterface(name=Interface 0), [('172.18.1.254', '172.18.1.0/24', '0')])

        :param str,int interface_id: interface ID to retrieve
        :raises EngineCommandFailed: interface not found
        :return: interface object by type (Physical, Tunnel, PhysicalVlanInterface)
        """
        interface = str(interface_id)
        _interface_re = '(Interface|Tunnel Interface)'

        found = None
        for intf in prepared_request(
                FetchElementFailed, href=self.meta.href).read().json:
            name = intf.get('name')
            if 'Inline' in name or 'Capture' in name:
                if re.search('{}\s{}\s'.format(
                        _interface_re, interface), name):
                    found = intf
                    break
            else:
                if re.match('{}\s{}$'.format(_interface_re, interface), name):
                    found = intf
                    break
        if found:
            found.update(engine=self._engine)  # Update meta
            return lookup_class(found.get('type'), Interface)(**found)

        raise EngineCommandFailed(
            'Interface id {} not found'.format(interface_id))

    def save(self):
        """
        Save this interface information back to SMC. When saving
        the interface, call save on the topmost level of the interface.

        Example of changing the IP address of an interface::

            >>> engine = Engine('sg_vm')
            >>> interface = engine.physical_interface.get(1)
            >>> interface.zone_ref = zone_helper('mynewzone')
            >>> interface.save()

        :raises UpdateElementFailed: failure to save changes
        :return: None
        """
        self.update()
        try:
            del self._engine.cache
        except AttributeError:
            pass

    def delete(self):
        """
        Override delete in parent class, delete routing configuration
        after interface deletion.
        ::

            engine = Engine('vm')
            interface = engine.interface.get(2)
            interface.delete()
        """
        super(Interface, self).delete()
        for routes in self._engine.routing:
            if routes.name == self.name or \
                    routes.name.startswith('VLAN {}.'.format(self.interface_id)):
                routes.delete()
                break

    def all(self):
        """
        Return all interfaces for this engine. This is a common entry
        point to viewing interface information.

        Retrieve specific information about an interface::

            >>> for interface in engine.interface.all():
            ...   print(interface.name, interface.addresses)
            ('Tunnel Interface 2001', [('169.254.9.22', '169.254.9.20/30', '2001')])
            ('Tunnel Interface 2000', [('169.254.11.6', '169.254.11.4/30', '2000')])
            ('Interface 2', [('192.168.1.252', '192.168.1.0/24', '2')])
            ('Interface 1', [('10.0.0.254', '10.0.0.0/24', '1')])
            ('Interface 0', [('172.18.1.254', '172.18.1.0/24', '0')])

        :return: list :py:class:`smc.elements.interfaces.Interface`
        """
        interfaces = []
        try:
            for interface in prepared_request(
                    FetchElementFailed, href=self._parent).read().json:
                intf_type = lookup_class(interface.get('type'), Interface)
                interface.update(engine=self._engine)
                interfaces.append(intf_type(**interface))
        except AttributeError:
            pass
        return interfaces


class TunnelInterface(InterfaceCommon, Interface):
    """
    This interface type represents a tunnel interface that is typically used for
    route based VPN traffic.
    Nested interface nodes can be SingleNodeInterface (for L3 NGFW), a NodeInterface
    (for cluster's with only NDI's) or ClusterVirtualInterface (CVI) for cluster VIP.
    Tunnel Interfaces are only available under layer 3 routed interfaces and do not
    support VLANs.
    """
    typeof = 'tunnel_interface'

    def __init__(self, **meta):
        super(TunnelInterface, self).__init__(**meta)
        pass

    def add_single_node_interface(self, tunnel_id, address, network_value,
                                  nodeid=1, zone_ref=None):
        """
        Creates a tunnel interface with sub-type single_node_interface. This is
        to be used for single layer 3 firewall instances.

        :param str,int tunnel_id: the tunnel id for the interface, used as nicid also
        :param str address: ip address of interface
        :param str network_value: network cidr for interface; format: 1.1.1.0/24
        :param int nodeid: nodeid, used only for clusters
        :param str zone_ref: zone reference for interface
        :raises EngineCommandFailed: failure during creation
        :return: None
        """
        builder, interface = InterfaceBuilder.getBuilder(self, tunnel_id)
        builder.add_sni_only(address, network_value)
        if zone_ref:
            builder.zone_ref = zone_ref

        dispatch(self, builder, interface)

    def add_cluster_virtual_interface(self, tunnel_id, cluster_virtual=None,
                                      cluster_mask=None, nodes=None,
                                      zone_ref=None):
        """
        Add a tunnel interface on a clustered engine. For tunnel interfaces
        on a cluster, you can specify a CVI only, NDI interfaces, or both.
        This interface type is only supported on layer 3 firewall engines.
        ::

            Add a tunnel CVI and NDI:

            engine.tunnel_interface.add_cluster_virtual_interface(
                tunnel_id=3000,
                cluster_virtual='4.4.4.1',
                cluster_mask='4.4.4.0/24',
                nodes=nodes)

            Add tunnel NDI's only:

            engine.tunnel_interface.add_cluster_virtual_interface(
                tunnel_id=3000,
                nodes=nodes)

            Add tunnel CVI only:

            engine.tunnel_interface.add_cluster_virtual_interface(
                tunnel_id=3000,
                cluster_virtual='31.31.31.31',
                cluster_mask='31.31.31.0/24',
                zone_ref=zone_helper('myzone'))

        :param str,int tunnel_id: tunnel identifier (akin to interface_id)
        :param str cluster_virtual: CVI ipaddress (optional)
        :param str cluster_mask: CVI network; required if ``cluster_virtual`` set
        :param list nodes: nodes for clustered engine with address,network_value,nodeid
        :param str zone_ref: zone reference (optional)
        """
        builder, interface = InterfaceBuilder.getBuilder(self, tunnel_id)
        if cluster_virtual and cluster_mask:
            builder.add_cvi_only(cluster_virtual, cluster_mask)
        if zone_ref:
            builder.zone_ref = zone_ref
        if nodes:
            for node in nodes:
                builder.add_ndi_only(**node)

        dispatch(self, builder, interface)


class PhysicalInterface(InterfaceCommon, Interface):
    """
    Physical Interfaces on NGFW. This represents the following base configuration for
    the following interface types:

        * Single Node Interface
        * Node Interface
        * Capture Interface
        * Inline Interface
        * Cluster Virtual Interface
        * Virtual Physical Interface (used on Virtual Engines)
        * DHCP Interface

    This should be used to add interfaces to an engine after it has been created.
    First get the engine context by loading the engine then get the engine property for
    physical interface::

        engine = Engine('myfw')
        engine.physical_interface.add_single_node_interface(.....)
        engine.physical_interface.add(5) #single unconfigured physical interface
        engine.physical_interface.add_node_interface(....)
        engine.physical_interface.add_inline_interface('5-6', ....)
        ....

    When making changes, the etag used should be the top level engine etag.
    """

    typeof = 'physical_interface'

    def __init__(self, **meta):
        super(PhysicalInterface, self).__init__(**meta)
        pass

    def add(self, interface_id, virtual_mapping=None,
            virtual_resource_name=None):
        """
        Add single physical interface with interface_id. Use other methods
        to fully add an interface configuration based on engine type.
        Virtual mapping and resource are only used in Virtual Engines.

        :param str,int interface_id: interface identifier
        :param int virtual_mapping: virtual firewall id mapping
               See :py:class:`smc.core.engine.VirtualResource.vfw_id`
        :param str virtual_resource_name: virtual resource name
               See :py:class:`smc.core.engine.VirtualResource.name`
        :raises EngineCommandFailed: failure creating interface
        :return: None
        """
        builder = InterfaceBuilder()
        builder.interface_id = interface_id
        builder.virtual_mapping = virtual_mapping
        builder.virtual_resource_name = virtual_resource_name

        dispatch(self, builder)

    def add_single_node_interface(self, interface_id, address, network_value,
                                  zone_ref=None, is_mgmt=False, **kw):
        """
        Adds an interface to a single fw instance.

        :param str,int interface_id: interface identifier
        :param str address: ip address
        :param str network_value: network/cidr (12.12.12.0/24)
        :param str zone_ref: zone reference
        :param bool is_mgmt: enable as management interface
        :raises EngineCommandFailed: failure creating interface
        :return: None

        .. note::
            If an existing ip address exists on the interface and zone_ref is
            provided, this value will overwrite any previous zone definition.

        See :py:class:`smc.core.sub_interfaces.SingleNodeInterface` for more information
        """
        builder, interface = InterfaceBuilder.getBuilder(self, interface_id)
        if zone_ref:
            builder.zone_ref = zone_ref
        builder.add_sni_only(address, network_value, is_mgmt, **kw)

        dispatch(self, builder, interface)

    def add_node_interface(self, interface_id, address, network_value,
                           zone_ref=None, is_mgmt=False):
        """
        Node interfaces are used on all engine types except single fw
        engines. For inline and IPS engines, this interface type represents
        a layer 3 routed (node dedicated) interface. For clusters, use the
        cluster related methods such as :func:`add_cluster_virtual_interface`

        :param str,int interface_id: interface identifier
        :param str address: ip address
        :param str network_value: network/cidr (12.12.12.0/24)
        :param str zone_ref: zone reference
        :param bool is_mgmt: enable management
        :raises EngineCommandFailed: failure creating interface
        :return: None

        .. note::
            If an existing ip address exists on the interface and zone_ref is
            provided, this value will overwrite any previous zone definition.

        See :py:class:`smc.core.sub_interfaces.NodeInterface` for more information
        """
        builder, interface = InterfaceBuilder.getBuilder(self, interface_id)
        if zone_ref:
            builder.zone_ref = zone_ref
        builder.add_ndi_only(address, network_value, is_mgmt=is_mgmt)

        dispatch(self, builder, interface)

    def add_capture_interface(self, interface_id, logical_interface_ref,
                              zone_ref=None):
        """
        Add a capture interface. Supported only on Layer 2 and IPS engines.

        :param str,int interface_id: interface identifier
        :param str logical_interface_ref: logical interface reference
        :param str zone_ref: zone reference
        :raises EngineCommandFailed: failure creating interface
        :return: None

        See :py:class:`smc.core.sub_interfaces.CaptureInterface` for more information
        """
        builder = InterfaceBuilder()
        builder.interface_id = interface_id
        builder.add_capture(logical_interface_ref)
        if zone_ref:
            builder.zone_ref = zone_ref

        dispatch(self, builder)

    def add_inline_interface(self, interface_id, logical_interface_ref,
                             zone_ref_intf1=None,
                             zone_ref_intf2=None):
        """
        Add an inline interface pair

        :param str interface_id: interface id; '1-2', '3-4', etc
        :param str logical_interface_ref: logical interface reference
        :param zone_ref_intf1: zone for inline interface 1
        :param zone_ref_intf2: zone for inline interface 2
        :raises EngineCommandFailed: failure creating interface
        :return: None

        See :py:class:`smc.core.sub_interfaces.InlineInterface` for more information
        """
        builder = InterfaceBuilder()
        builder.interface_id = interface_id.split('-')[0]
        builder.zone_ref = zone_ref_intf1
        builder.add_inline(interface_id, logical_interface_ref, zone_ref_intf2)

        dispatch(self, builder)

    def add_dhcp_interface(self, interface_id, dynamic_index,
                           is_mgmt=False, zone_ref=None):
        """
        Add a DHCP interface on a single FW

        :param int interface_id: interface id
        :param int dynamic_index: index number for dhcp interface
        :param bool primary_mgt: whether to make this primary mgt
        :param str zone_ref: zone reference for interface
        :param int nodeid: node identifier
        :raises EngineCommandFailed: failure creating interface
        :return: None

        See :py:class:`~DHCPInterface` for more information
        """
        builder = InterfaceBuilder()
        builder.interface_id = interface_id
        builder.add_dhcp(dynamic_index, is_mgmt)
        builder.zone_ref = zone_ref

        dispatch(self, builder)

    def add_cluster_virtual_interface(self, interface_id, cluster_virtual,
                                      cluster_mask, macaddress, nodes,
                                      cvi_mode='packetdispatch',
                                      zone_ref=None, is_mgmt=False):
        """
        Add cluster virtual interface. A "CVI" interface is used as a VIP
        address for clustered engines. Providing 'nodes' will create the
        node specific interfaces.
        ::

            physical_interface.add_cluster_virtual_interface(
                    cluster_virtual='5.5.5.1',
                    cluster_mask='5.5.5.0/24',
                    macaddress='02:03:03:03:03:03',
                    nodes=[{'address':'5.5.5.2', 'network_value':'5.5.5.0/24', 'nodeid':1},
                           {'address':'5.5.5.3', 'network_value':'5.5.5.0/24', 'nodeid':2},
                           {'address':'5.5.5.4', 'network_value':'5.5.5.0/24', 'nodeid':3}],
                    zone_ref=zone_helper('Heartbeat'))

        :param str,int interface_id: physical interface identifier
        :param str cluster_virtual: CVI address (VIP) for this interface
        :param str cluster_mask: network value for VIP; format: 10.10.10.0/24
        :param str macaddress: required mac address for this CVI
        :param list nodes: list of dictionary items identifying cluster nodes
        :param str cvi_mode: packetdispatch is recommended setting
        :param str zone_ref: if present, set on top level physical interface
        :param bool is_mgmt: enable management
        :raises EngineCommandFailed: failure creating interface
        :return: None
        """
        builder = InterfaceBuilder()
        builder.interface_id = interface_id
        builder.macaddress = macaddress
        builder.cvi_mode = cvi_mode
        builder.add_cvi_only(cluster_virtual, cluster_mask, is_mgmt=is_mgmt)

        for node in nodes:
            node.update(is_mgmt=is_mgmt)
            builder.add_ndi_only(**node)

        builder.zone_ref = zone_ref

        dispatch(self, builder)

    def add_cluster_interface_on_master_engine(self, interface_id,
                                               macaddress, nodes,
                                               is_mgmt=False,
                                               zone_ref=None):
        """
        Add a cluster address specific to a master engine. Master engine
        clusters will not use "CVI" interfaces like normal layer 3 FW clusters,
        instead each node has a unique address and share a common macaddress.

        :param str,int interface_id: interface id to use
        :param str macaddress: mac address to use on interface
        :param list nodes: interface node list
        :param bool is_mgmt: is this a management interface
        :param zone_ref: zone to use, if any
        :raises EngineCommandFailed: failure creating interface
        :return: None
        """
        builder = InterfaceBuilder()
        builder.interface_id = interface_id
        builder.macaddress = macaddress

        for node in nodes:
            node.update(is_mgmt=is_mgmt)
            builder.add_ndi_only(**node)

        builder.zone_ref = zone_ref

        dispatch(self, builder)

    def add_vlan_to_inline_interface(self, interface_id, vlan_id,
                                     vlan_id2=None,
                                     logical_interface_ref=None,
                                     zone_ref_intf1=None,
                                     zone_ref_intf2=None):
        """
        Add a VLAN to inline interface. VLANs and zones can both be
        unique per inline interface pair.

        :param str interface_id: interfaces for inline pair, '1-2', '5-6'
        :param int vlan_id: vlan identifier for interface 1
        :param int vlan_id2: vlan identifier for interface 2 (if none, vlan_id used)
        :param str logical_interface_ref: logical interface reference to use
        :param str zone_ref_intf1: zone for inline interface 1
        :param str zone_ref_intf2: zone for inline interface 2
        :raises EngineCommandFailed: failure creating interface
        :return: None

        .. note::
            If the inline interface does not exist, it will be created automatically.

        See :py:class:`smc.core.sub_interfaces.InlineInterface` for more information
        """
        builder = InterfaceBuilder()
        builder.interface_id = interface_id.split('-')[0]
        builder.add_inline(interface_id, logical_interface_ref,
                           zone_ref=zone_ref_intf2)

        builder.add_vlan_to_inline(interface_id, vlan_id, vlan_id2,
                                   logical_interface_ref,
                                   zone_ref_intf1, zone_ref_intf2)

        dispatch(self, builder)

    def add_vlan_to_node_interface(self, interface_id, vlan_id,
                                   virtual_mapping=None,
                                   virtual_resource_name=None,
                                   zone_ref=None):
        """
        Add vlan to a routed interface. Interface is created if
        it doesn't already exist. This can be used on any engine
        type, but is typically used to create an interface on a
        master engine with a virtual mapping and no IP address.

        :param str,int interface_id: interface identifier
        :param int vlan_id: vlan identifier
        :param int virtual_mapping: virtual engine mapping id
               See :py:class:`smc.core.engine.VirtualResource.vfw_id`
        :param str virtual_resource_name: name of virtual resource
               See :py:class:`smc.core.engine.VirtualResource.name`
        :raises EngineCommandFailed: failure creating interface
        :return: None

        .. note::
            If the interface does not exist, it will be create automatically.
        """
        builder, interface = InterfaceBuilder.getBuilder(self, interface_id)
        builder.interface_id = interface_id
        builder.add_vlan_only(vlan_id, virtual_mapping,
                              virtual_resource_name, zone_ref)

        dispatch(self, builder, interface)

    def add_ipaddress_to_vlan_interface(self, interface_id, address,
                                        network_value,
                                        vlan_id,
                                        zone_ref=None):
        """
        When an existing interface VLAN exists but has no IP address assigned,
        use this to add an ip address to the VLAN. Multiple addresses on the
        same interface can also be added using this method.
        This is supported on any non-clustered engine as long as the interface
        type supports IP address assignment.

        :param str,int interface_id: interface to modify
        :param str address: ip address for vlan
        :param str network_value: network for address; format: 10.10.10.0/24
        :param int vlan_id: id of vlan
        :raises EngineCommandFailed: invalid interface
        :return: None

        .. note::
            If the interface vlan does not exist, it will be create automatically.
        """
        builder, interface = InterfaceBuilder.getBuilder(self, interface_id)
        if self._engine.type in ['single_fw']:
            builder.add_ndi_to_vlan(address, network_value, vlan_id,
                                    zone_ref=zone_ref,
                                    cls=SingleNodeInterface)
        else:
            builder.add_ndi_to_vlan(address, network_value, vlan_id,
                                    zone_ref=zone_ref)

        dispatch(self, builder, interface)

    def add_ipaddress_and_vlan_to_cluster(self, interface_id, vlan_id,
                                          nodes=None, cluster_virtual=None,
                                          cluster_mask=None,
                                          macaddress=None,
                                          cvi_mode='packetdispatch',
                                          zone_ref=None):
        """
        Add IP addresses to VLANs on a firewall cluster. The minimum params
        required are ``interface_id`` and ``vlan_id``.
        To create a VLAN interface with a CVI, specify ``cluster_virtual``
        and ``cluster_mask`` (optionally ``macaddress``).
        If this interface should participate in load balancing, provide a
        value for ``macaddress`` and ``cvi_mode``.

        To create a VLAN with only NDI, specify ``nodes`` parameter.

        Nodes data structure is expected to be in this format::

            nodes=[{'address':'5.5.5.2', 'network_value':'5.5.5.0/24', 'nodeid':1},
                   {'address':'5.5.5.3', 'network_value':'5.5.5.0/24', 'nodeid':2}]

        :param str,int interface_id: interface id to assign VLAN.
        :param str,int vlan_id: vlan identifier
        :param list nodes: optional addresses for node interfaces (NDI's). For a cluster,
            each node will require an address specified using the nodes format.
        :param str cluster_virtual: cluster virtual ip address (optional). If specified, cluster_mask
            parameter is required
        :param str cluster_mask: Specifies the network address, i.e. if cluster virtual is 1.1.1.1,
            cluster mask could be 1.1.1.0/24.
        :param str macaddress: (optional) if used will provide the mapping from node interfaces
            to participate in load balancing.
        :param str cvi_mode: cvi mode for cluster interface (default: packetdispatch)
        :param zone_ref: optional zone reference for physical interface level
        :raises EngineCommandFailed: failure creating interface
        :return: None

        .. note::
            If the ``interface_id`` specified already exists, it is still possible
            to add additional VLANs and interface addresses.
        """
        builder, interface = InterfaceBuilder.getBuilder(self, interface_id)
        if interface is None:
            if cluster_virtual and cluster_mask:   # Add CVI
                builder.add_cvi_to_vlan(cluster_virtual, cluster_mask, vlan_id)
                if macaddress:
                    builder.macaddress = macaddress
                    builder.cvi_mode = cvi_mode
                else:
                    builder.cvi_mode = None
        if nodes:
            for node in nodes:
                node.update(vlan_id=vlan_id)
                builder.add_ndi_to_vlan(**node)

        dispatch(self, builder, interface)

    def remove_vlan(self, interface_id, vlan_id):
        """
        Remove a VLAN from any engine, given the interface_id and
        VLAN id.

        :param str,int interface_id: interface identifier
        :param int vlan_id: vlan identifier
        :return: None

        .. note::
            If a VLAN to be removed has IP addresses assigned, they
            will be removed along with any associated entries in the
            route table.
        """
        builder, interface = InterfaceBuilder.getBuilder(self, interface_id)
        if interface is None:
            raise EngineCommandFailed('Remove VLAN command failed. Interface {} '
                                      'was not found.'.format(interface_id))
        else:
            builder.remove_vlan(vlan_id)
            dispatch(self, builder, interface)

            for routes in self._engine.routing:
                if routes.name == 'VLAN {}.{}'.format(interface_id, vlan_id):
                    routes.delete()
                    break

    @property
    def aggregate_mode(self):
        """
        LAGG configuration for this physical interface.
        Options are HA (failover) or LB (load balancing). HA
        mode LAGG supports a single failover interface. LB
        supports up to 7 additional secondary NICs. Set the
        secondary NICs using :func:`second_interface_id`

        :param str value: 'lb' or 'ha'
        :rtype: str
        """
        return self.data.get('aggregate_mode')

    @aggregate_mode.setter
    def aggregate_mode(self, value):
        self.data['aggregate_mode'] = value

    def add_arp_entry(self, ipaddress, macaddress, netmask=32):
        """
        Add an arp entry to this physical interface.
        ::

            interface = engine.physical_interface.get(0)
            interface.add_arp_entry(
                ipaddress='23.23.23.23',
                macaddress='02:02:02:02:04:04')
            interface.save()

        :param str ipaddress: ip address for entry
        :param str macaddress: macaddress for ip address
        :param str,int netmask: netmask for entry
        :return: None
        """
        self.data['arp_entry'].append(
            {'ipaddress': ipaddress,
             'macaddress': macaddress,
             'netmask': netmask})

    @property
    def arp_entry(self):
        """
        Return any ARP entries for this physical interface

        :return: arp entries
        :rtype: list
        """
        return self.data.get('arp_entry')

    @property
    def cvi_mode(self):
        """
        HA Cluster mode. Not valid for non-cluster engines.

        :param str value: packetdispatch, unicast, multicast, multicastgmp
        :rtype: str
        """
        return self.data.get('cvi_mode')

    @cvi_mode.setter
    def cvi_mode(self, value):
        self.data['cvi_mode'] = value

    @property
    def macaddress(self):
        """
        MAC Address for cluster virtual interface.
        Only valid for cluster engines.

        :param str value: macaddress
        :rtype: str
        """
        return self.data.get('macaddress')

    @macaddress.setter
    def macaddress(self, value):
        self.data['macaddress'] = value

    @property
    def mtu(self):
        """
        Set MTU on interface. Enter a value between 400-65535.
        The same MTU is automatically applied to any VLANs
        created under this physical interface

        :param int value: MTU
        :rtype: int
        """
        return self.data.get('mtu')

    @mtu.setter
    def mtu(self, value):
        self.data['mtu'] = value

    @property
    def multicast_ip(self):
        """
        Enter a multicast address, that is, an IP address from the
        range 224.0.0.0-239.255.255.255.
        The address is used for automatically calculating a MAC address.
        Required only if multicastigmp cvi mode is selected as the cvi_mode.

        :param str value: address
        :rtype: str
        """
        return self.data.get('multicast_ip')

    @multicast_ip.setter
    def multicast_ip(self, value):
        self.data['multicast_ip'] = value

    @property
    def second_interface_id(self):
        """
        Peer interfaces used in LAGG configuration. Input should
        be a comma separated string.

        :param str value: comma seperated nic id's for LAGG peers
        :rtype: str
        """
        return self.data.get('second_interface_id')

    @second_interface_id.setter
    def second_interface_id(self, value):
        self.data['second_interface_id'] = value

    @property
    def virtual_mapping(self):
        """
        The virtual mapping id. Required if Virtual Resource chosen.
        See :py:class:`smc.core.engine.VirtualResource.vfw_id`

        :param int value: vfw_id
        :rtype: int
        """
        if self.data.get('virtual_mapping'):
            return int(self.data.get('virtual_mapping'))

    @virtual_mapping.setter
    def virtual_mapping(self, value):
        self.data['virtual_mapping'] = value

    @property
    def virtual_resource_name(self):
        """
        Virtual Resource name used on Master Engine to map a virtual engine.
        See :py:class:`smc.core.engine.VirtualResource.name`

        :param str value: virtual resource name
        :rtype: str
        """
        return self.data.get('virtual_resource_name')

    @virtual_resource_name.setter
    def virtual_resource_name(self, value):
        self.data['virtual_resource_name'] = value

    @property
    def virtual_engine_vlan_ok(self):
        """
        Whether to allow VLAN creation on the Virtual Engine.
        Only valid for master engine.

        :param bool value: enable/disable
        :rtype: bool
        """
        return self.data.get('virtual_engine_vlan_ok')

    @virtual_engine_vlan_ok.setter
    def virtual_engine_vlan_ok(self, value):
        self.data['virtual_engine_vlan_ok'] = value


class PhysicalVlanInterface(PhysicalInterface):
    """
    This is a container class used when enumerating vlan interfaces
    from it's top level parent physical interface. This handles being
    able to more cleanly identify the interface type as well as
    being able to modify the top level parent as well as nested nodes
    of this interface. This will always be created from a reference of
    the top level parent interface when attempting to enumerate VLANs.
    """
    typeof = 'physical_vlan_interface'

    def __init__(self, data, meta=None):
        super(PhysicalVlanInterface, self).__init__(href=None)
        self._add_cache(data)

    @staticmethod
    def create(interface_id, vlan_id,
               virtual_mapping=None,
               virtual_resource_name=None,
               zone_ref=None, **kwargs):
        """
        VLAN Interface
        These interfaces can be applied on all engine types but will be bound to
        being on a physical interface. VLAN's can be applied to layer 3 routed
        interfaces as well as inline interfaces.

        :param int interface_id: id of interface to assign VLAN to
        :param int vlan_id: ID of vlan
        :param int virtual_mapping: The interface ID for the virtual engine. Virtual engine
               interface mapping starts numbering at 0 by default, which means you must
               account for interfaces used by master engine
        :param str virtual_resource_name: Name of virtual resource for this VLAN if a VE
        :rtype: dict
        """
        interface_id = '{}.{}'.format(str(interface_id), str(vlan_id))
        intf = {'interface_id': interface_id,
                'virtual_mapping': virtual_mapping,
                'virtual_resource_name': virtual_resource_name,
                'interfaces': [],
                'zone_ref': zone_ref}
        # Address sent as kwarg?
        interface = kwargs.pop('interface', None)
        if interface:  # Should be sub-interface type
            intf.get('interfaces').append(interface.data)
        return intf

    @property
    def address(self):
        if self.has_interfaces:
            i = []
            for intf in self.sub_interfaces():
                i.append(getattr(intf, 'address'))
            return ','.join(i)
        return None

    @property
    def vlan_id(self):
        """
        VLAN iD's are set on a physical interface and may
        also contain IP addressing if on a FW engine (vs.
        Inline interface).

        Change a VLAN ID from id 12 to 20::

            engine = Engine('testfw')
            for intf in engine.interface.all():
                if intf.name == 'Interface 2':
                    if intf.has_vlan:
                        for vlan in x.vlan_interfaces():
                            if vlan.vlan_id == '12':
                                vlan.vlan_id = '20'
                intf.save() #Save full interface

        :param str|int value: new vlan id
        """
        v = self.interface_id.split('.')
        if len(v) > 1:
            return v[1]

    @vlan_id.setter
    def vlan_id(self, value):
        intf_id = self.interface_id.split('.')
        intf_id[1] = str(value)
        self.interface_id = ('.').join(intf_id)
        # Once interfaceID is formatted, change nicid on subinterfaces
        for subintf in self.interfaces:
            subintf.nicid = ('.').join(intf_id)

    def __str__(self):
        return '{0}(address={1},vlan_id={2})'.format(self.__class__.__name__,
                                                     self.address, self.vlan_id)

    def __repr__(self):
        return str(self)


class VirtualPhysicalInterface(PhysicalInterface):
    """
    VirtualPhysicalInterface
    This interface type is used by virtual engines and has subtle differences
    to a normal interface. For a VE in layer 3 firewall, it also specifies a
    Single Node Interface as the physical interface sub-type.
    When creating the VE, one of the interfaces must be designated as the source
    for Auth Requests and Outgoing.
    """
    typeof = 'virtual_physical_interface'

    def __init__(self, **meta):
        super(VirtualPhysicalInterface, self).__init__(**meta)
        pass


class InterfaceBuilder(object):
    """
    InterfaceBuilder is a configuration container to simplify
    access to interface creation and modification.
    """

    def __init__(self, cls=PhysicalInterface, **kw):
        if kw:  # existing interface
            for name, value in kw.items():
                setattr(self, name, value)
        else:
            setattr(self, 'interface_id', None)
            setattr(self, 'interfaces', [])

            if cls is PhysicalInterface:
                setattr(self, 'vlanInterfaces', [])
                setattr(self, 'zone_ref', None)

    def add_vlan_only(self, vlan_id, virtual_mapping=None,
                      virtual_resource_name=None, zone_ref=None):
        """
        Create a VLAN interface, no addresses, layer 3 interfaces only
        """
        vlan = PhysicalVlanInterface.create(
            self.interface_id,
            vlan_id,
            virtual_mapping,
            virtual_resource_name,
            zone_ref=zone_ref)

        self.vlanInterfaces.append(vlan)

    def add_vlan_to_inline(self, interface_id, vlan_id, vlan_id2,
                           logical_interface_ref, zone_ref_intf1=None,
                           zone_ref_intf2=None):
        """
        Add a VLAN to inline interface, layer 2 and IPS only
        """
        first_intf = interface_id.split('-')[0]
        vlan = PhysicalVlanInterface.create(
            first_intf,
            vlan_id,
            zone_ref=zone_ref_intf1)

        inline_intf = InlineInterface.create(
            interface_id,
            logical_interface_ref,
            zone_ref=zone_ref_intf2)

        vlan.get('interfaces').append(
            _add_vlan_to_inline(
                inline_intf.data,
                vlan_id,
                vlan_id2))

        self.vlanInterfaces.append(vlan)

    def add_cvi_only(self, address, network_value,
                     zone=None, is_mgmt=False):
        """
        Add a CVI and NDI
        """
        cvi = ClusterVirtualInterface.create(
            self.interface_id,
            address, network_value)

        if is_mgmt:
            cvi.auth_request = True

        self.interfaces.append(cvi.data)

    def add_sni_only(self, address, network_value, is_mgmt=False,
                     **kw):
        """
        Add Single Node Interface - Layer 3 single FW only
        """
        sni = SingleNodeInterface.create(
            self.interface_id,
            address,
            network_value,
            **kw)

        if is_mgmt:
            sni.auth_request = True
            sni.outgoing = True
            sni.primary_mgt = True

        if hasattr(self, 'interfaces'):  # BUG in SMC 6.1.2
            self.interfaces.append(sni.data)
        else:  # Interface assigned, with no IP's
            self.interfaces = [sni.data]

    def add_ndi_only(self, address, network_value, nodeid=1, is_mgmt=False,
                     **kw):
        """
        Add NDI, for all engine types except single fw
        """
        ndi = NodeInterface.create(
            interface_id=self.interface_id,
            address=address,
            network_value=network_value,
            nodeid=nodeid,
            **kw)

        if is_mgmt:
            ndi.primary_mgt = True
            ndi.outgoing = True
            ndi.primary_heartbeat = True

        self.interfaces.append(ndi.data)

    def add_capture(self, logical_interface_ref):
        """
        Add capture interface, only for layer 2, IPS
        """
        capture = CaptureInterface.create(
            self.interface_id,
            logical_interface_ref)

        self.interfaces.append(capture.data)

    def add_inline(self, interface_id, logical_interface_ref, zone_ref=None):
        """
        Add inline interface, only for layer 2, IPS
        """
        inline = InlineInterface.create(
            interface_id,
            logical_interface_ref=logical_interface_ref,
            zone_ref=zone_ref)  # Zone ref directly on the inline interface

        self.interfaces.append(inline.data)

    def add_dhcp(self, dynamic_index, is_mgmt=False):
        """
        Add a DHCP interface
        """
        intf = SingleNodeInterface.create_dhcp(
            self.interface_id,
            dynamic_index)

        if is_mgmt:
            intf.primary_mgt = True
            intf.reverse_connection = True
            intf.automatic_default_route = True

        self.interfaces.append(intf.data)

    def add_ndi_to_vlan(self, address, network_value, vlan_id,
                        nodeid=1, zone_ref=None, cls=NodeInterface):
        """
        Add IP address to an ndi/sni. If the VLAN doesn't exist,
        create it. Interface class is passed in to create the
        proper sub-interface (SingleNode or Node)
        """
        vlan_str = '{}.{}'.format(self.interface_id, vlan_id)
        found = False
        for vlan in self.vlanInterfaces:
            if vlan.get('interface_id') == vlan_str:
                intf = cls.create(
                    self.interface_id,
                    address,
                    network_value,
                    nodeid=nodeid,
                    nicid=vlan_str)
                if vlan.get('interfaces'):
                    vlan['interfaces'].append(intf.data)
                else:  # VLAN exists but no interfaces assigned
                    vlan['interfaces'] = [intf.data]
                found = True
                break
        if not found:  # create new
            intf = cls.create(
                self.interface_id,
                address,
                network_value,
                nicid=vlan_str)
            vlan = PhysicalVlanInterface.create(
                self.interface_id,
                vlan_id,
                zone_ref=zone_ref,
                interface=intf)

            self.vlanInterfaces.append(vlan)

    def add_cvi_to_vlan(self, address, network_value, vlan_id):
        """
        Add a CVI into a vlan
        """
        vlan_str = '{}.{}'.format(self.interface_id, vlan_id)
        cvi = ClusterVirtualInterface.create(
            self.interface_id,
            address,
            network_value,
            nicid=vlan_str)

        vlan = PhysicalVlanInterface.create(
            self.interface_id,
            vlan_id,
            interface=cvi)

        self.vlanInterfaces.append(vlan)

    def remove_vlan(self, vlan_id):
        """
        Remove vlan from existing interface
        """
        vlan_str = '{}.{}'.format(self.interface_id, vlan_id)
        vlans = []
        for vlan in self.vlanInterfaces:
            if not vlan.get('interface_id') == vlan_str:
                vlans.append(vlan)

        self.vlanInterfaces = vlans

    @property
    def data(self):
        return vars(self)

    @classmethod
    def getBuilder(cls, instance, interface_id):
        """
        Optional loader to get a builder and load an existing
        configuration based on interface id. This allows toggling
        between updating (PUT) on the interface, versus creating
        new (POST). If 'interface' attribute is None, an existing
        interface did not exist, otherwise return that reference.
        """
        try:
            interface = instance.get(interface_id)
        except EngineCommandFailed:
            if instance.__class__ is TunnelInterface:
                builder = InterfaceBuilder(TunnelInterface)
            else:
                builder = InterfaceBuilder()
            builder.interface_id = interface_id
            interface = None
        else:
            builder = InterfaceBuilder(**interface.data)

        return (builder, interface)  # Return builder, interface ref


def _interface_helper(data):
    """
    Return sub interface instance
    """
    for intf in data['interfaces']:
        for if_type, values in intf.items():
            return SubInterface.get_subinterface(if_type)(values)
