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

        Interface
            |
    Physical/Tunnel Interface
            |
            | - VlanInterface (is a PhysicalInterface)
            |      /
        Sub Interfaces (SingleNodeInterface, NodeInterface, InlineInterface, etc)
            |
        Attributes (address, network_value, vlan_id, etc)

Sub interfaces are documented in :py:mod:`smc.core.sub_interfaces`.

VLANs are properties of specific interfaces and can also be retrieved by
first getting the top level interface, and calling :func:`~smc.core.interfaces.Interface.vlan_interface`
to view or modify specific aspects of a VLAN, such as addresses, etc.
"""
import copy
from smc.base.model import SubElement, lookup_class, ElementCache
from smc.api.exceptions import InterfaceNotFound
from smc.core.route import del_invalid_routes
from smc.core.sub_interfaces import (
    NodeInterface, SingleNodeInterface, ClusterVirtualInterface,
    InlineInterface, CaptureInterface, get_sub_interface, SubInterfaceCollection)
from smc.compat import string_types
from smc.elements.helpers import zone_helper, logical_intf_helper
from smc.elements.network import Zone
from smc.base.structs import BaseIterable
from smc.policy.qos import QoSPolicy
from smc.core.hardware import ApplianceSwitchModule


class InterfaceOptions(object):
    """
    Interface Options allow you to define settings related to the roles of
    the firewall interfaces:
    
    * Which IP addresses are used as the primary and backup Control IP address
    * Which interfaces are used as the primary and backup heartbeat interface
    * The default IP address for outgoing traffic

    You can optionally change which interface is used for each of these purposes,
    and define a backup Control IP address and backup Heartbeat Interface. If
    calling the `set` methods, using a value of None will unset the option.
    
    .. note:: Setting an interface option will commit the change immediately.
    """
    def __init__(self, engine):
        self._engine = engine
        self.interface = InterfaceEditor(engine)
    
    @property
    def primary_mgt(self):
        """
        Obtain the interface specified as the primary management interface.
        This will always return a value as you must have at least one
        physical interface specified for management.
        
        :return: interface id 
        :rtype: str
        """
        return self.interface.find_mgmt_interface('primary_mgt')
        
    @property
    def backup_mgt(self):
        """
        Obtain the interface specified as the backup management
        interface. This can return None if no backup has been
        defined
        
        :return: interface id 
        :rtype: str
        """
        return self.interface.find_mgmt_interface('backup_mgt')

    @property
    def primary_heartbeat(self):
        """
        Obtain the interface specified as the primary heartbeat
        interface. This will return None if this is not
        a clustered engine.
        
        :return: interface id 
        :rtype: str
        """
        return self.interface.find_mgmt_interface('primary_heartbeat')

    @property
    def backup_heartbeat(self):
        """
        Obtain the interface specified as the backup heartbeat
        interface. This may return None if a backup has not been
        specified or this is not a cluster.
        
        :return: interface id 
        :rtype: str
        """
        return self.interface.find_mgmt_interface('backup_heartbeat')
    
    @property
    def outgoing(self):
        """
        Obtain the interface specified as the "Default IP address for
        outgoing traffic". This will always return a value.
        
        :return: interface id 
        :rtype: str
        """
        return self.interface.find_mgmt_interface('outgoing')
    
    @property
    def auth_request(self):
        """
        Return the interface for authentication requests. Can be either
        a PhysicalInterface or LoopbackInterface
        
        :return: interface id
        :rtype: str
        """
        return self.interface.find_mgmt_interface('auth_request')
    
    def set_auth_request(self, interface_id, address=None):
        """
        Set the authentication request field for the specified
        engine.
        
        """
        self.interface.set_auth_request(interface_id, address)
        self._engine.update()
        
    def set_primary_heartbeat(self, interface_id):
        """
        Set this interface as the primary heartbeat for this engine. 
        This will 'unset' the current primary heartbeat and move to
        specified interface_id.
        Clusters and Master NGFW Engines only.
        
        :param str,int interface_id: interface specified for primary mgmt
        :raises InterfaceNotFound: specified interface is not found
        :raises UpdateElementFailed: failed modifying interfaces
        :return: None
        """
        self.interface.set_unset(interface_id, 'primary_heartbeat')
        self._engine.update()
        
    def set_backup_heartbeat(self, interface_id):
        """
        Set this interface as the backup heartbeat interface.
        Clusters and Master NGFW Engines only.
        
        :param str,int interface_id: interface as backup
        :raises InterfaceNotFound: specified interface is not found
        :raises UpdateElementFailed: failure to update interface
        :return: None
        """
        self.interface.set_unset(interface_id, 'backup_heartbeat')
        self._engine.update()
            
    def set_primary_mgt(self, interface_id, auth_request=None,
                        address=None):
        """
        Specifies the Primary Control IP address for Management Server
        contact. For single FW and cluster FW's, this will enable 'Outgoing',
        'Auth Request' and the 'Primary Control' interface. For clusters, the
        primary heartbeat will NOT follow this change and should be set
        separately using :meth:`.set_primary_heartbeat`.
        For virtual FW engines, only auth_request and outgoing will be set.
        For master engines, only primary control and outgoing will be set.
        
        Primary management can be set on an interface with single IP's,
        multiple IP's or VLANs.
        ::
        
            engine.interface_options.set_primary_mgt(1)
        
        Set primary management on a VLAN interface::
        
            engine.interface_options.set_primary_mgt('1.100')
            
        Set primary management and different interface for auth_request::
        
            engine.interface_options.set_primary_mgt(
                interface_id='1.100', auth_request=0)
            
        Set on specific IP address of interface VLAN with multiple addresses::
        
             engine.interface_options.set_primary_mgt(
                 interface_id='3.100', address='50.50.50.1')
        
        :param str,int interface_id: interface id to make management
        :param str address: if the interface for management has more than
            one ip address, this specifies which IP to bind to.
        :param str,int auth_request: if setting primary mgt on a cluster
            interface with no CVI, you must pick another interface to set
            the auth_request field to (default: None)
        :raises InterfaceNotFound: specified interface is not found
        :raises UpdateElementFailed: updating management fails
        :return: None
        
        .. note:: Setting primary management on a cluster interface with no
            CVI requires you to set the interface for auth_request.
        """
        intfattr = ['primary_mgt', 'outgoing']
        if self.interface.engine.type in ('virtual_fw',):
            intfattr.remove('primary_mgt')
        
        for attribute in intfattr:
            self.interface.set_unset(interface_id, attribute, address)
        
        if auth_request is not None:
            self.interface.set_auth_request(auth_request)
        else:
            self.interface.set_auth_request(interface_id, address)

        self._engine.update()
        
    def set_backup_mgt(self, interface_id):
        """
        Set this interface as a backup management interface.
        
        Backup management interfaces cannot be placed on an interface with
        only a CVI (requires node interface/s). To 'unset' the specified
        interface address, set interface id to None
        ::
        
            engine.interface_options.set_backup_mgt(2)
            
        Set backup on interface 1, VLAN 201::
    
            engine.interface_options.set_backup_mgt('1.201')
        
        Remove management backup from engine::
        
            engine.interface_options.set_backup_mgt(None)
     
        :param str,int interface_id: interface identifier to make the backup
            management server.
        :raises InterfaceNotFound: specified interface is not found
        :raises UpdateElementFailed: failure to make modification
        :return: None
        """
        self.interface.set_unset(interface_id, 'backup_mgt')
        self._engine.update()
    
    def set_outgoing(self, interface_id):
        """
        Specifies the IP address that the engine uses to initiate connections
        (such as for system communications and ping) through an interface
        that has no Node Dedicated IP Address. In clusters, you must select
        an interface that has an IP address defined for all nodes.
        Setting primary_mgt also sets the default outgoing address to the same
        interface.
        
        :param str,int interface_id: interface to set outgoing
        :raises InterfaceNotFound: specified interface is not found
        :raises UpdateElementFailed: failure to make modification
        :return: None
        """
        self.interface.set_unset(interface_id, 'outgoing')
        self._engine.update()
            

class QoS(object):
    """
    QoS can be placed on physical interfaces, physical VLAN interfaces
    and tunnel interfaces. It is possible to have multiple QoS policies
    defined if using VLANs on a physical interface as QoS can be attached
    directly at the interface level or VLAN level. You obtain the QoS
    reference after retrieving the interface::
    
        itf = engine.interface.get(0)
        itf.qos.full_qos(100000, QoSPolicy('testqos'))
        itf.update()
        
    Disable QoS::
    
        itf = engine.interface.get(0)
        itf.qos.disable()
        itf.update()
        
    On a tunnel interface::
    
        itf = engine.interface.get(1000)
        itf.qos.full_qos(100000, QoSPolicy('testqos'))
        itf.update()
        
    Or a VLAN::
    
        itf = engine.interface.get('1.100')
        itf.qos.full_qos(100000, QoSPolicy('testqos'))
        itf.update()
        
    .. note:: You must call `update` on the interface to commit the change
    """
    def __init__(self, interface):
        self._interface = interface
         
    def disable(self):
        """
        Disable QoS on this interface
        """
        self._interface.data.update(qos_limit=-1, qos_mode='no_qos',
            qos_policy_ref=None)
    
    @property
    def qos_policy(self):
        """
        QoS Policy for this interface/vlan. A QoS policy will only
        be present if DSCP throttling or Full QoS is specified.
        
        :rtype: QoSPolicy
        """
        return QoSPolicy.from_href(self._interface.data.get(
            'qos_policy_ref', None))
    
    @property
    def qos_mode(self):
        """
        QoS mode in string format
        
        :rtype: str
        """
        return self._interface.data.get('qos_mode', 'no_qos')
    
    @property
    def qos_limit(self):
        """
        QoS Limit for this interface. The limit represents the number in
        bps. For example, 100000 represents 100Mbps.
        
        :rtype: int
        """
        return self._interface.data.get('qos_limit', -1)
     
    def statistics_only(self):
        """
        Set interface to collect QoS statistics only. No enforcement is being
        done but visiblity will be provided in dashboards against applications
        tagged by QoS.
        """
        self._interface.data.update(qos_limit=-1, qos_mode='statistics_only',
            qos_policy_ref=None)
         
    def full_qos(self, qos_limit, qos_policy):
        """
        Enable full QoS on the interface. Full QoS requires that you set a 
        bandwidth limit (in Mbps) for the interface. You must also provide a
        QoS policy to which identifies the parameters for prioritizing traffic.
        
        :param int qos_limit: max bandwidth in Mbps
        :param QoSPolicy qos_policy: the qos policy to apply to the interface
        """
        self._interface.data.update(qos_limit=qos_limit,
            qos_mode='full_qos',
            qos_policy_ref=qos_policy.href)
 
    def dscp_marking_and_throttling(self, qos_policy):
        """
        Enable DSCP marking and throttling on the interface. This requires that
        you provide a QoS policy to which identifies DSCP tags and how to prioritize
        that traffic.
        
        :param QoSPolicy qos_policy: the qos policy to apply to the interface
        """
        self._interface.data.update(qos_limit=-1,
            qos_mode='dscp',
            qos_policy_ref=qos_policy.href)
            

class Interface(SubElement):
    """
    Interface settings common to all interface types.
    """
    def __init__(self, **meta):
        self._engine = meta.pop('engine', None)  # Engine reference
        if self._engine and not meta.get('href'):
            meta.update(href=self._engine.get_relation(self.typeof))
        super(Interface, self).__init__(**meta)
                                
    def delete(self):
        """
        Override delete in parent class, this will also delete
        the routing configuration referencing this interface.
        ::

            engine = Engine('vm')
            interface = engine.interface.get(2)
            interface.delete()
        """
        super(Interface, self).delete()
        for route in self._engine.routing:
            if route.to_delete:
                route.delete()
        self._engine._del_cache()
    
    def update(self, *args, **kw):
        """
        Update/save this interface information back to SMC. When interface
        changes are made, especially to sub interfaces, call `update` on
        the top level interface.

        Example of changing the IP address of an interface::

            >>> engine = Engine('sg_vm')
            >>> interface = engine.physical_interface.get(1)
            >>> interface.zone_ref = zone_helper('mynewzone')
            >>> interface.update()

        :raises UpdateElementFailed: failure to save changes
        :return: Interface
        """
        super(Interface, self).update(*args, **kw)
        self._engine._del_cache()
        return self
    
    def save(self):
        self.update()
        self._engine._del_cache()
    
    @property
    def all_interfaces(self):
        """
        Access to all assigned sub-interfaces on this interface. A sub
        interface is the node level where IP addresses are assigned, or
        a inline interface is defined, VLANs, etc.
        Example usage::
        
            >>> engine = Engine('dingo')
            >>> itf = engine.interface.get(0)
            >>> assigned = itf.all_interfaces
            >>> list(assigned)
            [SingleNodeInterface(address=1.1.1.1)]
            >>> assigned.get(address='1.1.1.1')
            SingleNodeInterface(address=1.1.1.1)
            >>> itf = engine.interface.get(52)
            >>> assigned = itf.all_interfaces
            >>> list(assigned)
            [Layer3PhysicalInterfaceVlan(name=VLAN 52.52), Layer3PhysicalInterfaceVlan(name=VLAN 52.53)]
            >>> vlan = assigned.get(vlan_id='52')
            >>> vlan.addresses
            [(u'52.52.52.52', u'52.52.52.0/24', u'52.52')]
        
        :rtype: BaseIterable(AllInterfaces)
        """
        return AllInterfaces([
            self.vlan_interface, self.interfaces, self.port_group_interface])
    
    @property
    def interfaces(self):
        """
        Access to assigned `sub-interfaces` on this interface. A sub
        interface is the node level where IP addresses are assigned, or
        a layer 2 interface is defined.
            
            >>> itf = engine.interface.get(20)
            >>> assigned = itf.interfaces
            >>> list(assigned)
            [SingleNodeInterface(address=20.20.20.20), SingleNodeInterface(address=21.21.21.21)]
            >>> assigned.get(address='20.20.20.20')
            SingleNodeInterface(address=20.20.20.20)
            
        :rtype: BaseIterable(SubInterfaceCollection)
        """
        return SubInterfaceCollection(self)

    @property
    def vlan_interface(self):
        """
        Access VLAN interfaces for this interface, if any.
        Example usage::
        
            >>> itf = engine.interface.get(52)
            >>> assigned = itf.vlan_interface
            >>> list(assigned)
            [Layer3PhysicalInterfaceVlan(name=VLAN 52.52), Layer3PhysicalInterfaceVlan(name=VLAN 52.53)]
            >>> vlan = assigned.get(vlan_id='52')
            >>> vlan.addresses
            [(u'52.52.52.52', u'52.52.52.0/24', u'52.52')]
            >>> assigned.get(address='12.12.12.13')
            SingleNodeInterface(address=12.12.12.13, vlan_id=1)
            >>> assigned.get(vlan_id='1')
            SingleNodeInterface(address=12.12.12.12, vlan_id=1)
            >>> assigned.get(vlan_id='2')
            SingleNodeInterface(address=36.35.35.37, vlan_id=2)

        :rtype: BaseIterable(VlanInterface)
        """
        return VlanCollection(self)
    
    @property
    def port_group_interface(self):
        """
        The associated port group interfaces for this switch physical
        interface.
        
        :rtype: PortGroupInterfaceCollection(PortGroupInterface)
        """
        return PortGroupInterfaceCollection(self)
    
    @property
    def addresses(self):
        """
        Return 3-tuple with (address, network, nicid)

        :return: address related information of interface as 3-tuple list
        :rtype: list
        """
        addresses = []
        for i in self.all_interfaces:
            if isinstance(i, VlanInterface):
                for v in i.interfaces:
                    addresses.append((v.address, v.network_value, v.nicid))
            else:
                addresses.append((i.address, i.network_value, i.nicid))
        return addresses
    
    @property
    def contact_addresses(self):
        """
        Configure an interface contact address for this interface.
        Note that an interface may have multiple IP addresses assigned
        so you may need to iterate through contact addresses.
        Example usage::
        
            >>> itf = engine.interface.get(0)
            >>> itf.contact_addresses
            [ContactAddressNode(interface_id=0, interface_ip=1.1.1.10),
             ContactAddressNode(interface_id=0, interface_ip=1.1.1.25)]
            >>> for ca in itf.contact_addresses:
            ...   print("IP: %s, addresses: %s" % (ca.interface_ip, list(ca)))
            ... 
            IP: 1.1.1.10, addresses: []
            IP: 1.1.1.25, addresses: [InterfaceContactAddress(address=172.18.1.20, location=Default)]

            >>> for ca in itf.contact_addresses:
            ...   if ca.interface_ip == '1.1.1.10':
            ...     ca.add_contact_address('10.5.5.5', location='remote')
            
        :return: list of interface contact addresses
        :rtype: ContactAddressNode

        .. seealso:: :py:mod:`smc.core.contact_address`
        """
        return self._engine.contact_addresses.get(self.interface_id)
    
    @property
    def has_multiple_addresses(self):
        if len(self.cluster_virtual_interface) > 1:
            return True
        nodeid = [ndi.nodeid for ndi in self.interfaces
                  if isinstance(ndi, (SingleNodeInterface, NodeInterface))]
        return (any(nodeid.count(n) > 1 for n in nodeid))
    
    @property
    def cluster_virtual_interface(self):
        return [interface for interface in self.interfaces
                if getattr(interface, 'typeof', None) == \
                'cluster_virtual_interface']
         
    @property
    def has_vlan(self):
        """
        Does the interface have VLANs

        :return: Whether VLANs are configured
        :rtype: bool
        """
        return bool(self.data.get('vlanInterfaces', []))

    @property
    def has_interfaces(self):
        """
        Does the interface have interface have any sub interface
        types assigned. For example, a physical interface with no
        IP addresses would return False.

        :return: Does this interface have actual types assigned
        :rtype: bool
        """
        return bool(self.data.get('interfaces', []))

    def sub_interfaces(self):
        """
        Flatten out all top level interfaces and only return sub interfaces.
        It is recommended to use :meth:`~all_interfaces`, :meth:`~interfaces`
        or :meth:`~vlan_interfaces` which return collections with helper
        methods to get sub interfaces based on index or attribute value pairs.

        :rtype: list(SubInterface)
        """
        interfaces = self.all_interfaces
        sub_interfaces = []
        for interface in interfaces:
            if isinstance(interface, (VlanInterface, PortGroupInterface)):
                if interface.has_interfaces:
                    for subaddr in interface.interfaces:
                        sub_interfaces.append(subaddr)
                else:
                    sub_interfaces.append(interface)
            else:
                sub_interfaces.append(interface)
        
        return sub_interfaces
        
    def get_boolean(self, name):
        """
        Get the boolean value for attribute specified from the
        sub interface/s.
        """
        for interface in self.all_interfaces:
            if isinstance(interface, VlanInterface):
                if any(vlan for vlan in interface.interfaces
                       if getattr(vlan, name)):
                    return True
            else:
                if getattr(interface, name):
                    return True
        return False
    
    def delete_invalid_route(self):
        """
        Delete any invalid routes for this interface. An invalid route is
        a left over when an interface is changed to a different network.
        
        :return: None
        """
        try:
            routing = self._engine.routing.get(self.interface_id)
            for route in routing:
                if route.invalid or route.to_delete:
                    route.delete()
        except InterfaceNotFound: # Only VLAN identifiers, so no routing
            pass

    def reset_interface(self):
        """
        Reset the interface by removing all assigned addresses and VLANs.
        This will not delete the interface itself, only the sub interfaces that
        may have addresses assigned. This will not affect inline or capture
        interfaces.
        Note that if this interface is used as a primary control, auth request
        or outgoing interface, the update will fail. You should move that
        functionality to another interface before calling this. See also::
        :class:`smc.core.engine.interface_options`.
        
        :raises UpdateElementFailed: failed to update the interfaces. This is
            usually caused when the interface is assigned as a control, outgoing,
            or auth_request interface.
        :return: None
        """
        self.data['interfaces'] = []
        if self.typeof != 'tunnel_interface':
            self.data['vlanInterfaces'] = []
        self.update()
        self.delete_invalid_route()
    
    @property
    def interface_id(self):
        """
        The Interface ID automatically maps to a physical network port
        of the same number during the initial configuration of the engine,
        but the mapping can be changed as necessary. Call 
        :meth:`.change_interface_id` to change inline, VLAN, cluster and
        single interface ID's.
        
        .. note:: It is not possible to change an interface ID from a 
            VlanInterface. You must call on the parent PhysicalInterface.
        
        :param str value: interface_id
        :rtype: str
        """
        return self.data.get('interface_id')

    @interface_id.setter
    def interface_id(self, newid):
        self.data['interface_id'] = newid
    
    def change_interface_id(self, interface_id):
        """
        Change the interface ID for this interface. This can be used on any
        interface type. If the interface is an Inline interface, you must
        provide the ``interface_id`` in format '1-2' to define both
        interfaces in the pair. The change is committed after calling this
        method.
        ::
        
            itf = engine.interface.get(0)
            itf.change_interface_id(10)
            
        Or inline interface pair 10-11::
        
            itf = engine.interface.get(10)
            itf.change_interface_id('20-21')
        
        :param str,int interface_id: new interface ID. Format can be single
            value for non-inline interfaces or '1-2' format for inline.
        :raises UpdateElementFailed: changing the interface failed with reason
        :return: None
        """
        splitted = str(interface_id).split('-')
        if1 = splitted[0]
        
        for interface in self.all_interfaces:
            # Set top level interface, this only uses a single value which
            # will be the leftmost interface
            if isinstance(interface, VlanInterface):
                interface.interface_id = '{}.{}'.format(if1,
                    interface.interface_id.split('.')[-1])
                
                if interface.has_interfaces:
                    for sub_interface in interface.interfaces:
                        if isinstance(sub_interface, InlineInterface):
                            sub_interface.change_interface_id(interface_id)
                        else:
                            # VLAN interface only (i.e. CVI, NDI, etc)
                            sub_interface.change_interface_id(if1)  
            else:
                if isinstance(interface, InlineInterface):
                    interface.change_interface_id(interface_id)
                else:
                    interface.update(nicid=if1)
        
        self.interface_id = if1
        self.update()
    
    def _update_interface(self, other_interface):
        """
        Update the physical interface base settings with another interface.
        Only set updated if a value has changed. You must also call `update`
        on the interface if modifications are made. This is called from other
        interfaces (i.e. PhysicalInterface, ClusterPhysicalInterface, etc) to
        update the top layer.
        
        :param other_interface PhysicalInterface: an instance of an
            interface where values in this interface will overwrite values
            that are different.
        :raises UpdateElementFailed: Failed to update the element
        :rtype: bool
        """
        updated = False
        for name, value in other_interface.data.items():
            if isinstance(value, string_types) and getattr(self, name, None) != value:
                self.data[name] = value
                updated = True
            elif value is None and getattr(self, name, None):
                self.data[name] = None
                updated = True
        return updated
    
    def update_interface(self, other_interface, ignore_mgmt=True):
        """
        Update an existing interface by comparing values between two
        interfaces. If a VLAN interface is defined in the other interface
        and it doesn't exist on the existing interface, it will be created.
        
        :param other_interface Interface: an instance of an
            interface where values in this interface will be used to as the
            template to determine changes. This only has to provide attributes
            that need to change (or not).
        :param bool ignore_mgmt: ignore resetting management fields. These are
            generally better set after creation using `engine.interface_options`
        :raises UpdateElementFailed: Failed to update the element
        :return: (Interface, modified, created)
        :rtype: tuple
        
        .. note:: Interfaces with multiple IP addresses are ignored
        """
        base_updated = self._update_interface(other_interface)
        
        mgmt = ('auth_request', 'backup_heartbeat', 'backup_mgt',
            'primary_mgt', 'primary_heartbeat', 'outgoing')
        
        updated = False
        invalid_routes = []
            
        def process_interfaces(current, interface):
            updated = False
            invalid_routes = []
            
            # Ignore interfaces with multiple addresses
            if current.has_multiple_addresses:
                return updated, invalid_routes
            
            local_interfaces = current.interfaces # Existing interface
            for interface in interface.interfaces: # New values
                local_interface = None
                if not getattr(interface, 'nodeid', None): # CVI
                    cvi = [itf for itf in local_interfaces if not getattr(itf, 'nodeid', None)]
                    local_interface = cvi[0] if cvi else None
                else:
                    local_interface = local_interfaces.get(nodeid=interface.nodeid)
                
                if local_interface: # CVI or NDI sub interfaces
                    for name, value in interface.data.items():
                        if getattr(local_interface, name) != value:
                            if ignore_mgmt and name in mgmt:
                                pass
                            else:
                                local_interface[name] = value
                                updated = True
                            if 'network_value' in name: # Only reset routes if network changed
                                invalid_routes.append(interface.nicid)
                else:
                    current.data.setdefault('interfaces', []).append(
                        {interface.typeof: interface.data})
                    updated = True

            return updated, invalid_routes

        # Handle VLANs
        is_vlan = other_interface.has_vlan
        if is_vlan:
            vlan_interfaces = self.vlan_interface
            for pvlan in other_interface.vlan_interface:
                current = vlan_interfaces.get(pvlan.vlan_id)
                if current:
                    # PhysicalVlanInterface, set any parent interface values
                    if current._update_interface(pvlan):
                        updated = True
                else:
                    # Create new interface
                    self.data.setdefault('vlanInterfaces', []).append(pvlan.data)
                    updated = True
                    continue # Skip sub interface check
                
                _updated, routes = process_interfaces(current, pvlan)
                if _updated: updated = True
                invalid_routes.extend(routes)

        else:
            _updated, routes = process_interfaces(self, other_interface)
            if _updated: updated = True
            invalid_routes.extend(routes)
        
        interface = self
        if updated or base_updated:
            interface = self.update()
            if invalid_routes: # Interface updated, check the routes
                del_invalid_routes(self._engine, invalid_routes)
           
        return interface, base_updated or updated

    @property
    def name(self):
        """
        Read only name tag
        """
        name = super(Interface, self).name
        return name if name else self.data.get('name')
    
    @property
    def comment(self):
        """
        Optional interface comment
        
        :return: str or None
        """
        return self.data.get('comment', None)
    
    @comment.setter
    def comment(self, value):
        self.data['comment'] = value if value is not None else ''
    
    @property
    def zone(self):
        """
        Return the Zone for this interface, otherwise None
        
        :return: Zone or None
        """
        return Zone.from_href(self.zone_ref)
    
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
            self.data['zone_ref'] = zone_helper(value)


class TunnelInterface(Interface):
    """
    This interface type represents a tunnel interface that is typically
    used for route based VPN traffic.
    Nested interface nodes can be SingleNodeInterface (for L3 NGFW), a
    NodeInterface (for cluster's with only NDI's) or ClusterVirtualInterface
    (CVI) for cluster VIP. Tunnel Interfaces are only available under layer
    3 routed interfaces and do not support VLANs.
    
    Example tunnel interface format on cluster FW::
    
        cluster_tunnel_interface = {
            'comment': u'My Tunnel on cluster',
            'interface_id': u'1000',
            'interfaces': [{'cluster_virtual': u'77.77.77.70',
                            'network_value': u'77.77.77.0/24',
                            'nodes': [{'address': u'5.5.5.2',
                                       'network_value': u'5.5.5.0/24',
                                        'nodeid': 1},
                                      {'address': u'5.5.5.3',
                                       'network_value': u'5.5.5.0/24',
                                       'nodeid': 2}]}],
             'zone_ref': 'foozone'}
    
    Tunnel interface on single FW with multiple tunnel IPs::
    
        single_fw_interface = {
            'comment': u'Tunnel with two addresses on single FW',
            'interface_id': u'1000',
            'interfaces': [{'nodes': [{'address': u'5.5.5.2',
                                       'network_value': u'5.5.5.0/24',
                                       'nodeid': 1},
                                      {'address': u'5.5.5.3',
                                       'network_value': u'5.5.5.0/24',
                                       'nodeid': 1}]
                                    }],
             'zone_ref': 'foozone'}
    """
    typeof = 'tunnel_interface'
    
    def __init__(self, engine=None, meta=None, **interface):
        if not meta:
            meta = {key: interface.pop(key)
                    for key in ('href', 'type', 'name')
                    if key in interface}
        super(TunnelInterface, self).__init__(engine=engine, meta=meta)
        if interface:
            self._add_interface(**interface)
    
    def _add_interface(self, interface_id, **kw):
        """
        Create a tunnel interface. Kw argument list is as follows
        """
        base_interface = ElementCache()

        base_interface.update(
            interface_id=str(interface_id),
            interfaces=[])
        
        if 'zone_ref' in kw:
            zone_ref = kw.pop('zone_ref')
            base_interface.update(zone_ref=zone_helper(zone_ref) if zone_ref else None)
                
        if 'comment' in kw:
            base_interface.update(comment=kw.pop('comment'))
            
        self.data = base_interface
                          
        interfaces = kw.pop('interfaces', [])
        if interfaces:
            for interface in interfaces:
                if interface.get('cluster_virtual', None) or \
                    len(interface.get('nodes', [])) > 1:    # Cluster
                    
                    kw.update(interface_id=interface_id, interfaces=interfaces)
                    cvi = ClusterPhysicalInterface(**kw)
                    cvi.data.pop('vlanInterfaces', None)
                    self.data.update(cvi.data)
                else:
                    # Single interface FW
                    for node in interface.get('nodes', []):
                        node.update(nodeid=1)
                        sni = SingleNodeInterface.create(interface_id, **node)
                        base_interface.setdefault('interfaces', []).append(
                            {sni.typeof: sni.data})
    
    @property
    def qos(self):
        """
        The QoS settings for this tunnel interface
        
        :rtype: QoS
        """
        return QoS(self)
    
    @property
    def ndi_interfaces(self):
        return []


class SwitchPhysicalInterface(Interface):
    """
    A switch physical interface is a new dedicated physical module supported
    on N110 appliances at the time of this document. Check the latest updated
    spec sheets to determine if your physical appliance currently supports
    this module
    
    Represents a routed layer 3 interface on an any engine type.
    
    Example interface::
    
        {'interface_id': u'SWP_0.1',
         'interfaces': [{'nodes': [{'dynamic': True,
                                    'dynamic_index': 2}]}],
         'switch_physical_interface_port': [{u'switch_physical_interface_port_comment': u'',
                                             u'switch_physical_interface_port_number': 0}],
         'zone_ref': u'External'},
        {'interface_id': u'SWP_0.2',
         'interfaces': [{'nodes': [{'dynamic': True,
                                    'dynamic_index': 3}]}],
         'switch_physical_interface_port': [{u'switch_physical_interface_port_comment': u'',
                                             u'switch_physical_interface_port_number': 1}],
         'zone_ref': u'External'},
        {'interface_id': u'SWP_0.3',
         'interfaces': [{'nodes': [{'dynamic': True,
                                    'dynamic_index': 4}]}],
         'switch_physical_interface_port': [{u'switch_physical_interface_port_comment': u'',
                                             u'switch_physical_interface_port_number': 3}],
         'zone_ref': u'External'},
        {'interface_id': u'SWP_0.4',
         'switch_physical_interface_port': [{u'switch_physical_interface_port_comment': u'port 2',
                                             u'switch_physical_interface_port_number': 2},
                                            {u'switch_physical_interface_port_comment': u'',
                                             u'switch_physical_interface_port_number': 4},
                                            {u'switch_physical_interface_port_comment': u'',
                                             u'switch_physical_interface_port_number': 5},
                                            {u'switch_physical_interface_port_comment': u'',
                                             u'switch_physical_interface_port_number': 6}]}
                                                                       
    :ivar ApplianceSwitchModule switch_physical_module: appliance module type
    """
    typeof = 'switch_physical_interface'
    
    def __init__(self, engine=None, meta=None, **interface):
        if not meta:
            meta = {key: interface.pop(key)
                for key in ('href', 'type', 'name')
                if key in interface}
        super(SwitchPhysicalInterface, self).__init__(engine=engine, meta=meta)
        if interface:
            self._add_interface(**interface)
        
    def _add_interface(self, interface_id, **kw):
        """
        Create a tunnel interface. Kw argument list is as follows
        """
        port_group_interfaces = kw.pop('port_group_interface', [])
        # Clustering not supported on switch interfaces therefore no
        # need for primary/secondary heartbeat
        mgt = dict( 
            primary_mgt = kw.pop('primary_mgt', None),
            backup_mgt = kw.pop('backup_mgt', None),
            auth_request = kw.pop('auth_request', None))
        
        # Everything else is top level
        base_interface = ElementCache()
        
        base_interface.update(switch_physical_interface_switch_module_ref=
            getattr(ApplianceSwitchModule.objects.filter(
                kw.pop('appliance_switch_module', None), exact_match=False).first(), 'href', None),
            interface_id=interface_id, **kw)

        self.data = base_interface
        
        for interface in port_group_interfaces:
            interfaces = interface.pop('interfaces', [])
            
            sub_interface = {}
            zone_ref = interface.pop('zone_ref', None)
            if zone_ref:
                sub_interface.update(zone_ref=zone_helper(zone_ref))
            # Rest goes to next layer interface
            sub_interface.update(interface)
            
            for _interface in interfaces:
                interface_id = interface.get('interface_id')
                if_mgt = {k: str(v) == str(interface_id) for k, v in mgt.items()}

                for node in _interface.get('nodes', []):
                    _node = if_mgt.copy()
                    _node.update(node) # Override management if set within interface
                    sni = SingleNodeInterface.create(interface_id, **_node)
                    sub_interface.setdefault('interfaces', []).append(
                            {sni.typeof: sni.data})

            base_interface.setdefault('port_group_interface', []).append(sub_interface)
    
    def update_interface(self, other_interface, ignore_mgmt=True):
        """
        Update a switch physical interface with another interface. You can provide
        only partial interface data, for example, if you have an existing port group
        and you want to add additional ports. Or if you want to change the zone
        assigned to a single port group. There is nothing that can be modified on
        the top level switch interface itself, only the nested port groups.
        
        If the intent is to delete a port_group, retrieve the port group interface
        and call delete().
        
        :param SwitchPhysicalInterface other_interface: interface to use for
            modifications
        :param bool ignore_mgmt: ignore management settings
        """
        updated = False
        invalid_routes = []
        
        mgmt = ('auth_request', 'backup_mgt', 'primary_mgt', 'outgoing')
        
        for other in other_interface.port_group_interface:
            try:
                this = self.port_group_interface.get(other.interface_id, raise_exc=True)
                if len(this.switch_physical_interface_port) != len(
                    other.switch_physical_interface_port):
                    this.data.update(switch_physical_interface_port=other.switch_physical_interface_port)
                    updated = True
                
                if this.zone_ref != other.zone_ref: # Zone compare
                    this.zone_ref = other.zone_ref
                    updated = True
                
                # Are port groups and comments alike. Switch port count matches, but value/s
                # within the existing changed so take new setting
                val = ('switch_physical_interface_port_number', 
                       'switch_physical_interface_port_comment')
                
                if set(
                        [(d.get(val[0]),d.get(val[1])) for d in this.switch_physical_interface_port]) ^ \
                    set(
                        [(d.get(val[0]),d.get(val[1])) for d in other.switch_physical_interface_port]):
                    
                    this.data.update(switch_physical_interface_port=other.switch_physical_interface_port)
                    updated = True
                
                # If there is more than 1 interfaces (IP's assigned) on any given
                # interface, update. Or update if interface counts differ.
                if len(this.interfaces) != len(other.interfaces) or \
                    len(this.interfaces) > 1 or len(other.interfaces) > 1:
                    this.data.update(interfaces=[{sni.typeof: sni} for sni in other.interfaces])
                    invalid_routes.append(this)
                    updated = True
                else:
                    for interface in this.interfaces:
                        for _other in other.interfaces:
                            # SMC-20479; cannot change from dynamic to static
                            # Dynamic to address or address to dynamic
                            #if getattr(_other, 'dynamic', None) and getattr(interface, 'address', None):
                            #    interface.pop('address')
                            #    interface.pop('network_value') 
                            #if getattr(_other, 'address', None) and getattr(interface, 'dynamic', None):
                            #    interface.pop('dynamic_index')
                            for name, value in _other.data.items():
                                if getattr(interface, name) != value:
                                    if ignore_mgmt and name in mgmt:
                                        pass
                                    else:
                                        interface[name] = value
                                        updated = True
                                        invalid_routes.append(this)
                
            except InterfaceNotFound:
                self.data.setdefault('port_group_interface', []).append(other)
                updated = True
                
        if updated:
            self.update()
        
        for interface in invalid_routes:
            del_invalid_routes(self._engine, interface.interface_id)
            
        return self, updated  
      
    @property
    def appliance_switch_module(self):
        """
        Return the appliance module used for this switch physical interface.
        
        :rtype: ApplianceSwitchModule
        """
        return ApplianceSwitchModule.from_href(self.data.get(
            'switch_physical_interface_switch_module_ref'))

    
class PhysicalInterface(Interface):
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
        engine.physical_interface.add_layer3_interface(.....)
        engine.physical_interface.add(5) #single unconfigured physical interface
        engine.physical_interface.add_inline_ips_interface('5-6', ....)
        ....

    When making changes, the etag used should be the top level engine etag.
    """
    typeof = 'physical_interface'
    
    def __init__(self, engine=None, meta=None, **interface):
        if not meta:
            meta = {key: interface.pop(key)
                for key in ('href', 'type', 'name')
                if key in interface}
        super(PhysicalInterface, self).__init__(engine=engine, meta=meta)
        if interface:
            # Optional management dict to specify mgt by interface id
            mgt = dict( 
                primary_mgt=interface.pop('primary_mgt', None),
                backup_mgt=interface.pop('backup_mgt', None),
                primary_heartbeat=interface.pop('primary_heartbeat', None),
                backup_heartbeat=interface.pop('backup_heartbeat', None))
            
            auth_request = interface.pop('auth_request', None)
            if auth_request is not None:
                mgt.update(auth_request=auth_request)
            else:
                mgt.update(auth_request=mgt.get('primary_mgt'))
            
            self.data = ElementCache()
            self.data.update(
                interface_id=interface.get('interface_id'),
                interfaces=[],
                vlanInterfaces=[])
            self._add_interface(mgt=mgt, **interface) 
    
    @property
    def qos(self):
        """
        The QoS settings for this physical interface
        
        :rtype: QoS
        """
        return QoS(self)
    
    @property
    def is_primary_mgt(self):
        """
        Is this physical interface tagged as the backup management
        interface for this cluster.
        
        :return: is backup heartbeat
        :rtype: bool
        """
        return self.get_boolean('primary_mgt')

    @property
    def is_backup_mgt(self):
        """
        Is this physical interface tagged as the backup management
        interface for this cluster.
        
        :return: is backup heartbeat
        :rtype: bool
        """
        return self.get_boolean('backup_mgt')

    @property
    def is_primary_heartbeat(self):
        """
        Is this physical interface tagged as the primary heartbeat
        interface for this cluster.
        
        :return: is backup heartbeat
        :rtype: bool
        """
        return self.get_boolean('primary_heartbeat')
    
    @property
    def is_auth_request(self):
        """
        Is this physical interface tagged as the interface for 
        authentication requests
        
        :rtype: bool
        """
        return self.get_boolean('auth_request')

    @property
    def is_backup_heartbeat(self):
        """
        Is this physical interface tagged as the backup heartbeat
        interface for this cluster.
        
        :return: is backup heartbeat
        :rtype: bool
        """
        return self.get_boolean('backup_heartbeat')
    
    @property
    def is_outgoing(self):
        """
        Is this the default interface IP used for outgoing for system
        communications.
        
        :return: is dedicated outgoing IP interface
        :rtype: bool
        """
        return self.get_boolean('outgoing')
    
    @property
    def ndi_interfaces(self):
        """
        Return a formatted dict list of NDI interfaces on this engine.
        This will ignore CVI or any inline or layer 2 interface types.
        This can be used to identify  to indicate available IP addresses
        for a given interface which can be used to run services such as
        SNMP or DNS Relay.
        
        :return: list of dict items [{'address':x, 'nicid':y}]
        :rtype: list(dict)
        """
        return [{'address': interface.address, 'nicid': interface.nicid}
                for interface in self.interfaces
                if isinstance(interface, (NodeInterface, SingleNodeInterface))]
                    
    def change_vlan_id(self, original, new):
        """
        Change VLAN ID for a single VLAN, cluster VLAN or inline
        interface. When changing a single or cluster FW vlan, you
        can specify the original VLAN and new VLAN as either single
        int or str value. If modifying an inline interface VLAN when
        the interface pair has two different VLAN identifiers per
        interface, use a str value in form: '10-11' (original), and
        '20-21' (new).
        
        Single VLAN id::
        
            >>> engine = Engine('singlefw')
            >>> itf = engine.interface.get(1)
            >>> itf.vlan_interfaces()
            [PhysicalVlanInterface(vlan_id=11), PhysicalVlanInterface(vlan_id=10)]
            >>> itf.change_vlan_id(11, 100)
            >>> itf.vlan_interfaces()
            [PhysicalVlanInterface(vlan_id=100), PhysicalVlanInterface(vlan_id=10)]
        
        Inline interface with unique VLAN on each interface pair::
        
            >>> itf = engine.interface.get(2)
            >>> itf.vlan_interfaces()
            [PhysicalVlanInterface(vlan_id=2-3)]
            >>> itf.change_vlan_id('2-3', '20-30')
            >>> itf.vlan_interfaces()
            [PhysicalVlanInterface(vlan_id=20-30)]
        
        :param str,int original: original VLAN to change.
        :param str,int new: new VLAN identifier/s.
        :raises InterfaceNotFound: VLAN not found
        :raises UpdateElementFailed: failed updating the VLAN id
        :return: None
        """
        vlan = self.vlan_interface.get_vlan(original)
        newvlan = str(new).split('-')
        splitted = vlan.interface_id.split('.')
        vlan.interface_id = '{}.{}'.format(splitted[0], newvlan[0])
        for interface in vlan.interfaces:
            if isinstance(interface, InlineInterface):
                interface.change_vlan_id(new)
            else:
                interface.change_vlan_id(newvlan[0])
        self.update()

    def enable_aggregate_mode(self, mode, interfaces):
        """    
        Enable Aggregate (LAGG) mode on this interface. Possible LAGG
        types are 'ha' and 'lb' (load balancing). For HA, only one
        secondary interface ID is required. For load balancing mode, up
        to 7 additional are supported (8 max interfaces).
        
        :param str mode: 'lb' or 'ha'
        :param list interfaces: secondary interfaces for this LAGG
        :type interfaces: list(str,int)
        :raises UpdateElementFailed: failed adding aggregate
        :return: None
        """
        if mode in ['lb', 'ha']:
            self.data['aggregate_mode'] = mode
            self.data['second_interface_id'] = ','.join(map(str, interfaces))   
            self.save() 
    
    @property
    def aggregate_mode(self):
        """
        LAGG configuration mode for this interface. Values are 'ha' or
        'lb' (load balancing). This can return None if LAGG is not
        configured.

        :return: aggregate mode set, if any
        :rtype: str, None
        """
        return self.data.get('aggregate_mode')

    def static_arp_entry(self, ipaddress, macaddress, arp_type='static', netmask=32):
        """
        Add an arp entry to this physical interface.
        ::

            interface = engine.physical_interface.get(0)
            interface.static_arp_entry(
                ipaddress='23.23.23.23',
                arp_type='static',
                macaddress='02:02:02:02:04:04')
            interface.save()

        :param str ipaddress: ip address for entry
        :param str macaddress: macaddress for ip address
        :param str arp_type: type of entry, 'static' or 'proxy' (default: static)
        :param str,int netmask: netmask for entry (default: 32)
        :return: None
        """
        self.data['arp_entry'].append({
            'ipaddress': ipaddress,
            'macaddress': macaddress,
            'netmask': netmask,
            'type': arp_type})

    @property
    def arp_entry(self):
        """
        Return any manually configured ARP entries for this physical
        interface

        :return: arp entries as dict
        :rtype: list
        """
        return self.data.get('arp_entry')

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
        Peer interfaces used in LAGG configuration.

        :param str value: comma seperated nic id's for LAGG peers
        :rtype: str
        """
        return self.data.get('second_interface_id')

    @property
    def virtual_mapping(self):
        """
        The virtual mapping id. Required if Virtual Resource chosen.
        See :py:class:`smc.core.engine.VirtualResource.vfw_id`

        :param int value: vfw_id
        :rtype: int
        """
        if 'virtual_mapping' in self.data:
            return int(self.data['virtual_mapping'])

    @property
    def virtual_resource_name(self):
        """
        Virtual Resource name used on Master Engine to map a virtual engine.
        See :py:class:`smc.core.engine.VirtualResource.name`

        :param str value: virtual resource name
        :rtype: str
        """
        return self.data.get('virtual_resource_name')

    @property
    def virtual_engine_vlan_ok(self):
        """
        Whether to allow VLAN creation on the Virtual Engine.
        Only valid for master engine.

        :param bool value: enable/disable
        :rtype: bool
        """
        return self.data.get('virtual_engine_vlan_ok')


class Layer2PhysicalInterface(PhysicalInterface):
    """
    Represents a Layer 2 Physical Interface. This interface type can be
    either a Capture, Inline or InlineL2FW interface. VLANs are not supported
    on Capture interfaces and `failure_mode` is not supported on Layer 2
    Firewall interfaces.
    
    Inline IPS example::
    
        inline_ips = {
            'interface_id': '10',
            'second_interface_id': '11',
            'interface': 'inline_ips_interface',
            'logical_interface_ref': 'interfaceref',
            'inspect_unspecified_vlans': True,
            'failure_mode': 'bypass',
            'interfaces': [{'logical_interface_ref': 'logical',
                            'vlan_id': 15,
                            'zone_ref': 'vlan15 side a',
                            'second_zone_ref': 'vlan15 side b',
                            'comment': 'vlan15_comment'},
                            {'logical_interface_ref': 'logical2',
                             'vlan_id': 16}],
            'zone_ref': 'foozone',
            'second_zone_ref': 'foozone',
            'comment': 'mycomment'}
    
    Capture example::
    
        capture = {
            'interface_id': '10',
            'interface': 'capture_interface',
            'logical_interface_ref': 'myinterface',
            'inspect_unspecified_vlans': True,
            'failure_mode': True,
            'reset_interface_id': 6,
            'zone_ref': 'foozone',
            'comment': 'my span port'}
    
    .. note:: An interface type `inline_l2fw_interface` uses the same structure
        as `inline_ips_interface`.
    
    :param str interface_id: interface ID for first interface
    :param str second_interface_id: second interface ID in pair
    :param str interface: interface type, values: `inline_ips_interface` or
        `inline_l2fw_interface`
    :param str,href logical_interface_ref: required logical interface. Used
        for top level interface
    :param str,href zone_ref: zone reference for top level interface pair
    :param str,href second_zone_ref: zone reference for second interface pair
    :param str comment: comment
    :param list interfaces: a list of vlan interfaces. Same top level settings
        are used for this list, `vlan_id` is required here.
    """
    @property
    def failure_mode(self):
        return self.interfaces.get(0, {}).get('failure_mode')
    
    @property
    def inspect_unspecified_vlans(self):
        return self.interfaces.get(0, {}).get('inspect_unspecified_vlans')
    
    def _add_interface(self, interface_id, **kw):
        # Top level physical interface reference
        clz = get_sub_interface(kw.pop('interface', 'capture_interface'))
        
        # Only change top level interface if it doesn't already exist    
        if not bool(self.interfaces):
            zone_ref = kw.pop('zone_ref', None)
            comment = kw.pop('comment', None)
            if zone_ref:
                self.data.update(zone_ref=zone_helper(zone_ref) if zone_ref else None)
            
            if comment:
                self.data.update(comment=comment)
            
            inline_intf = clz.create(
                interface_id=interface_id,
                second_interface_id=kw.get('second_interface_id'),
                logical_interface_ref=logical_intf_helper(
                    kw.get('logical_interface_ref', 'default_eth')),
                failure_mode=kw.get('failure_mode', 'normal'),
                zone_ref=zone_helper(kw.get('second_zone_ref', None)))
            
            self.data['interfaces'] = [{inline_intf.typeof: inline_intf.data}]
    
        interfaces = kw.pop('interfaces', [])
        for interface in interfaces:
            # Interfaces are for VLANs
            if interface.get('vlan_id') and clz is not CaptureInterface:
                vlan_id = interface['vlan_id']
                second_vlan_id = interface.get('second_vlan_id') # Only used for L2/IPS engines
                vlan_interface = {
                    'interface_id': '{}.{}'.format(interface_id, vlan_id),
                    'zone_ref': zone_helper(interface.get('zone_ref', None)),
                    'comment': interface.get('comment', None)}
                
                # Use top logical interface if VLAN level was not specified
                _inline_intf = clz.create(
                    interface_id = '{}.{}'.format(interface_id, vlan_id),
                    second_interface_id = '{}.{}'.format(kw.get('second_interface_id'),
                        second_vlan_id if second_vlan_id else vlan_id),
                    logical_interface_ref=logical_intf_helper(
                        interface.get('logical_interface_ref', kw.get('logical_interface_ref'))),
                    failure_mode=self.failure_mode,
                    zone_ref=zone_helper(interface.get('second_zone_ref')))
                       
                vlan_interface.update(interfaces=[{_inline_intf.typeof: _inline_intf.data}])
                self.data.setdefault('vlanInterfaces', []).append(
                    vlan_interface)    
    
    def update_interface(self, other_interface, ignore_mgmt=True):
        #TODO: Not Yet Implemented
        pass
    

class Layer3PhysicalInterface(PhysicalInterface):
    """
    Represents a routed layer 3 interface on an any engine type.
    
    Example interface::
    
        interface = {
            'comment': u'Regular interface',
            'interface_id': u'67',
            'interfaces': [{'nodes': [{'address': u'5.5.5.2',
                                       'network_value': u'5.5.5.0/24',
                                       'nodeid': 1},
                                      {'address': u'5.5.5.3',
                                       'network_value': u'5.5.5.0/24',
                                       'nodeid': 1}]}],
             'zone_ref': 'foozone'}
        
    Layer3 VLAN interface::
    
        interface = {
            'comment': u'Interface with VLAN',
            'interface_id': u'67',
            'interfaces': [{'nodes': [{'address': u'5.5.5.2',
                                       'network_value': u'5.5.5.0/24',
                                       'nodeid': 1},
                                      {'address': u'5.5.5.3',
                                       'network_value': u'5.5.5.0/24',
                                       'nodeid': 1}],
                            'vlan_id': 10}],
             'zone_ref': 'foozone'}
    
    DHCP interface on a VLAN (use `dynamic` and specify `dynamic_index`)::
    
        interface = {
            'comment': u'Interface with VLAN',
            'interface_id': u'67',
            'interfaces': [{'nodes': [{'dynamic': True,
                                       'dynamic_index': 2,
                                       'nodeid': 1}],
                            'vlan_id': 10}],
             'zone_ref': 'foozone'}
             
    When an interface is created, the first key level is applied to the "top" level physical
    interface. The `interfaces` list specifies the node and addressing information using the
    `nodes` parameter. If `vlan_id` is specified as a key/value in the interfaces dict, the
    list dict keys are applied to the nested physical interface VLAN.
    
    :param str interface_id: id for interface
    :param str interface: specifies the type of interface to create. The interface
        type defaults to 'node_interface' and applies to all engine types except a
        single FW. For single FW, specify `single_node_interface`
    :param list interfaces: interface attributes, `cluster_virtual`, `network_value`,
        `nodes`, etc
    :param dict nodes: nodes dict should contain keys `address`, `network_value` and
        `nodeid`. Overridden sub interface settings can also be set here
    :param str zone_ref: zone reference, name or zone
    :param str comment: comment for interface
    """
    def _add_interface(self, interface_id, interface='node_interface', **kw):
        _kw = copy.deepcopy(kw) # Preserve original kw, especially lists
        mgt = _kw.pop('mgt', {})
        
        # Only update zone or comment if there are no interfaces defined.
        # Use update_or_create to update existing
        zone_ref = _kw.pop('zone_ref', None)
        comment = _kw.pop('comment', None)
        if not bool(self.interfaces):
            if zone_ref:
                self.data.update(zone_ref=zone_helper(zone_ref) if zone_ref else None)
            
            if comment:
                self.data.update(comment=comment)
        
        clz = NodeInterface if interface == 'node_interface'\
            else SingleNodeInterface
        
        interfaces = _kw.pop('interfaces', [])
        for interface in interfaces:
            vlan_id = interface.pop('vlan_id', None)
            if vlan_id:
                _interface_id = '{}.{}'.format(interface_id, vlan_id)
            else:
                _interface_id = interface_id
    
            _interface = []
            if_mgt = {k: str(v) == str(_interface_id) for k, v in mgt.items()}
            
            for node in interface.pop('nodes', []):
                _node = if_mgt.copy() # Each node should be treated independently
                _node.update(
                    outgoing=True if if_mgt.get('primary_mgt') else False,
                    auth_request=if_mgt.get('auth_request', False))
                # Add node specific key/value pairs set on the node. This can
                # also be used to override management settings
                _node.update(node)
                ndi = clz.create(
                    interface_id=_interface_id, **_node)
                _interface.append({ndi.typeof: ndi.data})
            
            if vlan_id:
                vlan_interface = {
                    'interface_id': _interface_id,
                    'zone_ref': zone_helper(interface.pop('zone_ref', None)),
                    'comment': interface.pop('comment', None),
                    'interfaces': _interface}
                if interface.get('virtual_mapping', None) is not None:
                    vlan_interface.update(
                        virtual_mapping=interface.pop('virtual_mapping'),
                        virtual_resource_name=interface.pop('virtual_resource_name', None))
                # Add any remaining kwargs into the VLAN interface
                for name, value in interface.items():
                    vlan_interface[name] = value
                self.data.setdefault('vlanInterfaces', []).append(
                    vlan_interface)
            else:
                # Check for virtual mappings embedded on the interface level. If additional
                # kwargs are specified on a non-VLAN interface they are ignored
                if interface.get('virtual_mapping', None) is not None:
                    self.data.update(
                        virtual_mapping=interface.get('virtual_mapping'),
                        virtual_resource_name=interface.get('virtual_resource_name', None))
                self.data.setdefault('interfaces', []).extend(
                    _interface)
        
        # Remaining kw go to base level interface
        for name, value in _kw.items():
            self.data[name] = value


class ClusterPhysicalInterface(PhysicalInterface):
    """
    A ClusterPhysicalInterface represents an interface on a cluster that
    is a physical interface type. A cluster interface can have a CVI, NDI's,
    or CVI's and NDI's.
    
    Example interface format, with CVI and 2 nodes::
        
        interface = {
            'interface_id': '23',
            'comment': 'my comment',
            'zone_ref': 'zone1',
            'cvi_mode': 'packetdispatch',
            'macaddress': '02:08:08:02:02:06',
            'interfaces': [{'cluster_virtual': '241.241.241.250',
                            'network_value': '241.241.241.0/24',
                            'nodes': [{'address': '241.241.241.2', 'network_value': '241.241.241.0/24', 'nodeid': 1},
                                      {'address': '241.241.241.3', 'network_value': '241.241.241.0/24', 'nodeid': 2}]
                            }]}
            
       Example interface with VLAN and CVI / NDI::
       
       interface = {
           'interface_id': '24',
           'cvi_mode': 'packetdispatch',
           'macaddress': '02:02:08:08:08:06',
           'interfaces': [{'cluster_virtual': '242.242.242.250',
                           'network_value': '242.242.242.0/24',
                           'nodes': [{'address': '242.242.242.2', 'network_value': '242.242.242.0/24', 'nodeid': 1},
                                     {'address': '242.242.242.3', 'network_value': '242.242.242.0/24', 'nodeid': 2}],
                           'vlan_id': 24,
                           'zone_ref': 'vlanzone',
                           'comment': 'comment on vlan'}],
           'zone_ref': zone_helper('myzone'),
           'comment': 'top level interface'}
    
    When an interface is created, the first key level is applied to the "top" level physical
    interface. The `interfaces` list specifies the node and addressing information using the
    `nodes` parameter. If `vlan_id` is specified as a key/value in the interfaces dict, the
    list dict keys are applied to the nested physical interface VLAN.
    
    :param str interface_id: id for interface
    :param cvi_mode: cvi mode type (i.e. packetdispatch), required when using CVI
    :param str macaddress: mac address for top level physical interface. Required if CVI set
    :param list interfaces: interface attributes, `cluster_virtual`, `network_value`,
        `nodes`, etc
    :param dict nodes: nodes dict should contain keys `address`, `network_value` and
        `nodeid`. Overridden sub interface settings can also be set here
    :param str,href zone_ref: zone reference, name or zone. If zone does not exist it will be created
    :param str comment: comment for interface
    
    .. note:: Values for dict match the FirewallCluster.create constructor
    """
    def _add_interface(self, interface_id, mgt=None, **kw):
        """
        Add the Cluster interface. If adding a cluster interface to
        an existing node, retrieve the existing interface and call
        this method. Use the supported format for defining an interface.
        """
        _kw = copy.deepcopy(kw) # Preserve original kw, especially lists
        mgt = mgt if mgt else {}
        
        if 'cvi_mode' in _kw:
            self.data.update(cvi_mode=_kw.pop('cvi_mode'))
        
        if 'macaddress' in _kw:
            self.data.update(
                macaddress=_kw.pop('macaddress'))
            if 'cvi_mode' not in self.data:
                self.data.update(cvi_mode='packetdispatch')
        
        if 'zone_ref' in _kw:
            zone_ref = _kw.pop('zone_ref')
            self.data.update(zone_ref=zone_helper(zone_ref) if zone_ref else None)
        
        if 'comment' in _kw:
            self.data.update(comment=_kw.pop('comment'))

        interfaces = _kw.pop('interfaces', [])
        for interface in interfaces:
            vlan_id = interface.pop('vlan_id', None)
            if vlan_id:
                _interface_id = '{}.{}'.format(interface_id, vlan_id)
            else:
                _interface_id = interface_id
    
            _interface = []
            if_mgt = {k: str(v) == str(_interface_id) for k, v in mgt.items()}
            
            # Auth_request sits on CVI unless there is no CVI
            if 'cluster_virtual' in interface and 'network_value' in interface:
                cluster_virtual = interface.pop('cluster_virtual')
                network_value = interface.pop('network_value')
                if cluster_virtual and network_value:
                    cvi = ClusterVirtualInterface.create(
                        _interface_id, cluster_virtual, network_value,
                        auth_request=if_mgt.pop('auth_request', False))
                      
                    _interface.append({cvi.typeof: cvi.data})
    
            for node in interface.pop('nodes', []):
                _node = if_mgt.copy()
                _node.update(outgoing=True if if_mgt.get('primary_mgt') else False)
                # Add node specific key/value pairs set on the node. This can
                # also be used to override management settings
                _node.update(node)
                ndi = NodeInterface.create(
                    interface_id=_interface_id, **_node)
                _interface.append({ndi.typeof: ndi.data})

            if vlan_id:
                vlan_interface = {
                    'interface_id': _interface_id,
                    'zone_ref': zone_helper(interface.pop('zone_ref', None)),
                    'comment': interface.pop('comment', None),
                    'interfaces': _interface}
                # Add remaining kwargs on vlan level to VLAN physical interface
                for name, value in interface.items():
                    vlan_interface[name] = value
                self.data.setdefault('vlanInterfaces', []).append(
                    vlan_interface)
            else:
                self.data.setdefault('interfaces', []).extend(
                    _interface)

        # Remaining kw go to base level interface
        for name, value in _kw.items():
            self.data[name] = value
        
    @property
    def cvi_mode(self):
        """
        HA Cluster mode.

        :return: possible values: packetdispatch, unicast, multicast,
            multicastgmp
        :rtype: str
        """
        return self.data.get('cvi_mode')

    @cvi_mode.setter
    def cvi_mode(self, value):
        if value in ('packetdispatch', 'none'):
            self.data['cvi_mode'] = value
    
    @property
    def macaddress(self):
        """
        MAC Address for cluster virtual interface. Not required for NDI
        only interfaces.
        
        :param str value: macaddress
        :rtype: str
        """
        return self.data.get('macaddress')

    @macaddress.setter
    def macaddress(self, value):
        self.data['macaddress'] = value
  
    def __str__(self):
        return '{}(name={})'.format(self.__class__.__name__, self.name
            if self.name else 'Interface %s' % self.interface_id)
    

class VirtualPhysicalInterface(Layer3PhysicalInterface):
    """
    VirtualPhysicalInterface
    This interface type is used by virtual engines and has subtle differences
    to a normal interface. For a VE in layer 3 firewall, it also specifies a
    Single Node Interface as the physical interface sub-type.
    When creating the VE, one of the interfaces must be designated as the source
    for Auth Requests and Outgoing.
    """
    typeof = 'virtual_physical_interface'
    

class PortGroupInterface(object):
    """
    A PortGroupInterface is a group of ports associated with a switch physical
    interface. Port group interfaces can have IP addresses assigned and treated
    like normal interfaces or can be grouped as normal switch ports.
    
    This class inherits from Interface and is generated dynamically by the
    collection.
    Retrieve a port group interface by reference to the switch::
    
        engine = Engine('azure')
        switch = engine.interface.get('SWP_0')
        for port_group in switch.port_group_interface:
            ...
    """
    @property
    def switch_physical_interface_port(self):
        """
        Return a raw dict of the switch port configuration which is a list of
        dict with a comment field and interface port number, i.e::
            
            [{'switch_physical_interface_port_comment': 'some comment',
              'switch_physical_interface_port_number': 0}]
        
        :rtype: dict
        """
        return self.data.get('switch_physical_interface_port', [])
    
    
class VlanInterface(object):
    """
    VlanInterface is a dynamic class generated by collections referencing
    interfaces with vlan interfaces. The inheriting class for a VlanInterface
    is dependent on the parent interface.
    """
    def __eq__(self, other):
        return bool(other.name == self.name)
    
    def __ne__(self, other):
        return not self.__eq__(other)
    
    @property
    def qos(self):
        """
        QoS on VLANs is only supported for Layer3PhysicalInterface
        types.
        
        :rtype: QoS
        """
        if isinstance(self._parent, (Layer3PhysicalInterface, ClusterPhysicalInterface)):
            return QoS(self)
    
    def delete(self):
        """
        Delete this Vlan interface from the parent interface.
        This will also remove stale routes if the interface has
        networks associated with it.
        
        :return: None
        """
        if self in self._parent.vlan_interface:
            self._parent.data['vlanInterfaces'] = [
                v for v in self._parent.vlan_interface
                if v != self]
            self.update()
            for route in self._parent._engine.routing:
                if route.to_delete:
                    route.delete()
    
    def update(self, **kw):
        if kw:
            self.data.update(**kw)
        self._parent.update()
    
    @property
    def vlan_id(self):
        """
        Vlan id for this vlan
        
        :rtype: str
        """
        return self.data.get('interface_id').split('.')[-1]
    
    def change_vlan_id(self, vlan_id):
        """
        Change the VLAN id for this VLAN interface. If this is an
        inline interface, you can specify two interface values to
        create unique VLANs on both sides of the inline pair. Or
        provide a single to use the same VLAN id.
        
        :param str vlan_id: string value for new VLAN id.
        :raises UpdateElementFailed: failed to update the VLAN id
        :return: None
        """
        intf_id, _ = self.interface_id.split('.')
        self.interface_id = '{}.{}'.format(intf_id, vlan_id)
        for interface in self.interfaces:
            interface.change_vlan_id(vlan_id)
        self.update()


#### Collections ####

class AllInterfaces(BaseIterable):
    """
    Iterable for obtaining all Sub Interfaces for PhysicalInterface
    types. This is a iterable over a VPNCollection and SubInterfaceCollection.
    Using `get` will check each collection for the interface result based
    on kwarg arguments or return None.
    
    :param list interfaces: list of iterable classes (VlanCollection,
        SubInterfaceCollection)
    :rtype: SubInterface or VlanInterface
    """
    def __init__(self, interfaces):
        super(AllInterfaces, self).__init__(interfaces)
    
    def __iter__(self):
        for it in self.items:
            for element in it:
                yield element   
    
    def __len__(self):
        return sum(len(x) for x in self.items)
    
    def get(self, *args, **kwargs):
        """
        Get from the interface collection. It is more accurate to use
        kwargs to specify an attribute of the sub interface to retrieve
        rather than using an index value. If retrieving using an index,
        the collection will first check vlan interfaces and standard
        interfaces second. In most cases, if VLANs exist, standard
        interface definitions will be nested below the VLAN with exception
        of Inline Interfaces which may have both.
        
        :param int args: index to retrieve
        :param kwargs: key value for sub interface
        :rtype: SubInterface or None
        """
        for collection in self.items:
            if args:
                index = args[0]
                if len(collection) and (index <= len(collection)-1):
                    return collection[index]
            else:
                # Collection with get
                result = collection.get(**kwargs)
                if result is not None:
                    return result
        return None


class VlanCollection(BaseIterable):
    """
    A collection of VLAN interfaces based on the parent interface type.
    A VLAN is an instance of the parent class but is generated dynamically
    to provide a consistent interface for modifying the VLAN interface data.
    
    :param Interface interface: interface by reference
    :rtype: BaseIterable
    """
    def __init__(self, interface):
        name = '{}Vlan'.format(type(interface).__name__)
        data = [type(name, (VlanInterface, interface.__class__), {
                'data': ElementCache(vlan), '_parent': interface})()
                for vlan in interface.data.get('vlanInterfaces', [])]
        super(VlanCollection, self).__init__(data)
    
    @property
    def vlan_ids(self):
        """
        Return all VLAN ids in use by the interface
        
        :return: list of VLANs by ID
        :rtype: list
        """
        return [vlan.vlan_id for vlan in self]
    
    def get_vlan(self, *args, **kwargs):
        """
        Get the VLAN from this PhysicalInterface.
        Use args if you want to specify only the VLAN id. Otherwise
        you can specify a valid attribute for the VLAN sub interface
        such as `address` for example::
        
            >>> vlan = itf.vlan_interface.get_vlan(4)
            >>> vlan
            Layer3PhysicalInterfaceVlan(name=VLAN 3.4)
            >>> vlan.addresses
            [(u'32.32.32.36', u'32.32.32.0/24', u'3.4'), (u'32.32.32.33', u'32.32.32.0/24', u'3.4')]
        
        :param int args: args are translated to vlan_id=args[0]
        :param kwargs: key value for sub interface
        :raises InterfaceNotFound: VLAN interface could not be found
        :rtype: VlanInterface
        """
        if args:
            kwargs = {'vlan_id': str(args[0])}
        key, value = kwargs.popitem()
        for vlan in self:
            if getattr(vlan, key, None) == value:
                return vlan
        raise InterfaceNotFound('VLAN ID {} was not found on this engine.'
            .format(value))
        
    def get(self, *args, **kwargs):
        """
        Get the sub interfaces for this VlanInterface
        
            >>> itf = engine.interface.get(3)
            >>> list(itf.vlan_interface)
            [Layer3PhysicalInterfaceVlan(name=VLAN 3.3), Layer3PhysicalInterfaceVlan(name=VLAN 3.5),
            Layer3PhysicalInterfaceVlan(name=VLAN 3.4)]
        
        :param int args: args are translated to vlan_id=args[0]
        :param kwargs: key value for sub interface
        :rtype: VlanInterface or None
        """
        if args:
            kwargs = {'vlan_id': str(args[0])}
        key, value = kwargs.popitem()
        for item in self:
            if 'vlan_id' in key and getattr(item, key, None) == value:
                return item
            for vlan in item.interfaces:
                if getattr(vlan, key, None) == value:
                    return item
                

class PortGroupInterfaceCollection(BaseIterable):
    """
    A port group interface collection tracks all port groups defined under a
    switch physical interface.
    This collection returns a list of PortGroupInterface definitions which
    have an MRO of Interface -> PortGroupInterface
    
    :rtype: PortGroupInterface(Interface)
    """
    def __init__(self, interface):
        data = [type('PortGroupInterface', (PortGroupInterface, Interface,), {
            'data': ElementCache(port_interface), '_parent': interface})()
            for port_interface in interface.data.get('port_group_interface', [])]
        super(PortGroupInterfaceCollection, self).__init__(data)
    
    def get(self, *args, **kwargs):
        """
        Get a specific port group interface from the collection. Port group names
        will be in the format::
         
            SWP_0.1
             
        Where 0 indicates the switch physical interface number (i.e. the hardware
        switch module) and 1 is the port group number.
        Optionally provide kwargs to find an interface by a specific sub interface
        attribute, i.e. address='13.13.13.13'.
        
        :param str args: name of the portgroup to retrieve, i.e. 'SWP_0.1'
        :param kwargs: key value for fetch, i.e. address='1.1.1.1'
        :rtype: PortGroupInterface or None
        """
        intf = args[0] if args else None
        raise_exc = kwargs.pop('raise_exc', False)
        key = next(iter(kwargs)) if kwargs else None
        for item in self:
            if intf and item.interface_id == intf:
                return item
            elif key:
                for sub_interface in item.sub_interfaces():
                    if getattr(sub_interface, key, None) == kwargs.get(key):
                        return item
        if raise_exc:
            raise InterfaceNotFound('Port Group %s was not found on this engine.' % intf if intf else \
                    'Port group does not exist on this engine')
        
        
class InterfaceEditor(object):
    def __init__(self, engine):
        self.engine = engine
    
    def extract_self(self, link_list):
        for keys in link_list:
            if keys.get('rel') =='self':
                return keys.get('href')
    
    def serialize(self):
        for interface in self.engine.data.get('physicalInterfaces', []):
            for typeof, data in interface.items():
                subif_type = extract_sub_interface(data)
                if isinstance(subif_type, (InlineInterface, CaptureInterface)):
                    clz = Layer2PhysicalInterface
                else:
                    if typeof == 'physical_interface':
                        if 'cluster' in self.engine.type:
                            clz = ClusterPhysicalInterface
                        else:
                            clz = Layer3PhysicalInterface
                    else:
                        clz = lookup_class(typeof, Interface)

                clazz = clz(meta=dict(
                    name=data.get('name', 'Interface %s' % data.get('interface_id')),
                    type=typeof,
                    href=self.extract_self(data.get('link'))))
    
                clazz.data = ElementCache(data)
                clazz._engine = self.engine
                yield clazz

    def __iter__(self):
        return self.serialize()
    
    def __len__(self):
        return len(self.engine.data.get('physicalInterfaces'))

    def find_mgmt_interface(self, mgmt):
        """
        Find the management interface specified and return
        either the string representation of the interface_id.
        
        Valid options: primary_mgt, backup_mgt, primary_heartbeat,
            backup_heartbeat, outgoing, auth_request
        
        :return: str interface_id
        """
        for intf in self:
            for allitf in intf.all_interfaces:
                if isinstance(allitf, (VlanInterface, PortGroupInterface)):
                    for vlan in allitf.interfaces:
                        if getattr(vlan, mgmt, None):
                            return allitf.interface_id
                else:
                    if getattr(allitf, mgmt, None):
                        return intf.interface_id
    
    def get(self, interface_id):
        """
        Get the interface from engine json
        
        :param str interface_id: interface ID to find
        :raises InterfaceNotFound: Cannot find interface
        """
        # From within engine, skips nested iterators for this find
        # Make sure were dealing with a string
        interface_id = str(interface_id)
        for intf in self:
            if intf.interface_id == interface_id:
                intf._engine = self.engine
                return intf
            else: # Check for switch interfaces
                if 'SWP_' in interface_id and 'SWP_' in intf.interface_id:
                    if '.' in interface_id:
                        return intf.port_group_interface.get(interface_id, raise_exc=True)

                elif '.' in interface_id: # Check for inline interfaces
                    # It's a VLAN interface
                    vlan = interface_id.split('.')
                    # Check that we're on the right interface
                    if intf.interface_id == vlan[0]:
                        if intf.has_vlan:
                            return intf.vlan_interface.get_vlan(vlan[-1])

                elif intf.has_interfaces:
                    for interface in intf.interfaces:
                        if isinstance(interface, InlineInterface):
                            split_intf = interface.nicid.split('-')
                            if interface_id == interface.nicid or \
                                str(interface_id) in split_intf:
                                intf._engine = self.engine
                                return intf

        raise InterfaceNotFound(
            'Interface id {} was not found on this engine.'.format(interface_id))
    
    def set_unset(self, interface_id, attribute, address=None):
        """
        Set attribute to True and unset the same attribute for all other
        interfaces. This is used for interface options that can only be
        set on one engine interface. 
        
        :raises InterfaceNotFound: raise if specified address does not exist or
            if the interface is not supported for this management role (i.e. you
            cannot set primary mgt to a CVI interface with no nodes).
        """
        interface = self.get(interface_id) if interface_id is not None else None
        if address is not None:
            target_network = None
            sub_interface = interface.all_interfaces.get(address=address)
            if sub_interface:
                target_network = sub_interface.network_value

            if not target_network:
                raise InterfaceNotFound('Address specified: %s was not found on interface '
                    '%s' % (address, interface_id))
        
        for interface in self:
            all_subs = interface.sub_interfaces()
            for sub_interface in all_subs:
                # Skip top level VLAN and inline interfaces (they have no addresses)
                if not isinstance(sub_interface, (VlanInterface, InlineInterface, PortGroupInterface)):
                    if getattr(sub_interface, attribute) is not None:
                        if sub_interface.nicid == str(interface_id):
                            if address is not None:
                                if sub_interface.network_value == target_network:
                                    sub_interface[attribute] = True
                                else:
                                    sub_interface[attribute] = False
                            else:
                                sub_interface[attribute] = True
                        else: #unset
                            sub_interface[attribute] = False

    def set_auth_request(self, interface_id, address=None):
        """
        Set auth request, there can only be one per engine so unset all
        other interfaces. If this is a cluster, auth request can only be
        set on an interface with a CVI (not valid on NDI only cluster
        interfaces).
        If this is a cluster interface, address should be CVI IP.
        """
        for engine_type in ['master', 'layer2', 'ips']:
            if engine_type in self.engine.type:
                return
        
        interface = self.get(interface_id)
        if 'cluster' in self.engine.type:
            # Auth request on a cluster interface must have at least a CVI.
            # It cannot bind to NDI only interfaces
            if not any(isinstance(itf, ClusterVirtualInterface)
                       for itf in interface.all_interfaces):
                raise InterfaceNotFound('The interface specified: %s does not have '
                    'a CVI interface defined and therefore cannot be used as an '
                    'interface for auth_requests. If setting the primary_mgt interface '
                    'provide an interface id for auth_request.' % interface_id)
        
        current_interface = self.get(
            self.engine.interface_options.auth_request)
        for itf in current_interface.all_interfaces:
            if getattr(itf, 'auth_request', False):
                itf['auth_request'] = False
        # Set
        sub_if = interface.all_interfaces
        if any(isinstance(itf, ClusterVirtualInterface) for itf in sub_if):
            for itf in sub_if:
                if isinstance(itf, ClusterVirtualInterface):
                    if address:
                        if getattr(itf, 'address', None) == address:
                            itf['auth_request'] = True
                    else:
                        itf['auth_request'] = True
        else:
            for itf in sub_if:
                if getattr(itf, 'auth_request', None) is not None:
                    if address:
                        if getattr(itf, 'address', None) == address:
                            itf['auth_request'] = True
                    else:
                        itf['auth_request'] = True


def extract_sub_interface(data):
    for intf in data.get('interfaces', []):
        for if_type, values in intf.items():
            return get_sub_interface(if_type)(values)

