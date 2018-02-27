from smc.core.interfaces import extract_sub_interface, InterfaceBuilder
from smc.core.sub_interfaces import LoopbackInterface
from smc.core.engine import Engine
from smc.api.exceptions import CreateEngineFailed, CreateElementFailed,\
    ElementNotFound
from smc.base.model import ElementCreator

    
class Layer3Firewall(Engine):
    """
    Represents a Layer 3 Firewall configuration.
    To instantiate and create, call 'create' classmethod as follows::

        engine = Layer3Firewall.create(name='mylayer3', 
                                       mgmt_ip='1.1.1.1', 
                                       mgmt_network='1.1.1.0/24')

    Set additional constructor values as necessary.       
    """
    typeof = 'single_fw'

    @classmethod
    def create(cls, name, mgmt_ip, mgmt_network,
               mgmt_interface=0,
               log_server_ref=None,
               default_nat=False,
               reverse_connection=False,
               domain_server_address=None, zone_ref=None,
               enable_antivirus=False, enable_gti=False,
               location_ref=None, enable_ospf=False,
               sidewinder_proxy_enabled=False,
               ospf_profile=None, comment=None, **kw):
        """ 
        Create a single layer 3 firewall with management interface and DNS. 
        Provide the `interfaces` keyword argument if adding multiple additional interfaces.
        Interfaces can be one of any valid interface for a layer 3 firewall. Unless the
        interface type is specified, physical_interface is assumed.
        
        Valid interface types:
            - physical_interface (default if not specified)
            - tunnel_interface
    
        Example interfaces format::
        
            {'interface_id': 1},
            {'interface_id': 2, 'address': '1.1.1.1', 'network_value': '1.1.1.0/24', 'zone_ref': 'myzone'},
            {'interface_id': 1000, 'address': '10.10.10.1', 'network_value': '10.10.10.0/24', 'type': 'tunnel_interface'}
        
         It is also possible to add VLAN interfaces in the following format::
         
            {'interface_id': 2, 'address': '1.1.1.1', 'network_value': '1.1.1.0/24', 'vlan_id': 10},
            {'interface_id': 2, 'address':'3.3.3.3', 'network_value': '3.3.3.0/24', 'vlan_id': 11, 'zone_ref': 'myzone'},
            {'interface_id': 3, 'vlan_id': 12, 'zone_ref': 'myzone'}
                  
        :param str name: name of firewall engine
        :param str mgmt_ip: ip address of management interface
        :param str mgmt_network: management network in cidr format
        :param str log_server_ref: (optional) href to log_server instance for fw
        :param int mgmt_interface: (optional) interface for management from SMC to fw
        :param list domain_server_address: (optional) DNS server addresses
        :param str zone_ref: zone name, str href or zone name for management interface
            (created if not found)
        :param bool reverse_connection: should the NGFW be the mgmt initiator (used when behind NAT)
        :param bool default_nat: (optional) Whether to enable default NAT for outbound
        :param bool enable_antivirus: (optional) Enable antivirus (required DNS)
        :param bool enable_gti: (optional) Enable GTI
        :param bool sidewinder_proxy_enabled: Enable Sidewinder proxy functionality
        :param str location_ref: location href or not for engine if needed to contact SMC
            behind NAT (created if not found)
        :param bool enable_ospf: whether to turn OSPF on within engine
        :param str ospf_profile: optional OSPF profile to use on engine, by ref
        :param kw: optional keyword arguments specifying additional interfaces  
        :raises CreateEngineFailed: Failure to create with reason
        :return: :py:class:`smc.core.engine.Engine`
        """
        builder = InterfaceBuilder()
        builder.interface_id = mgmt_interface
        builder.add_sni_only(
            mgmt_ip,
            mgmt_network,
            is_mgmt=True,
            reverse_connection=reverse_connection)
        builder.zone = zone_ref

        physical_interfaces = [{'physical_interface': builder.data}]
            
        if 'interfaces' in kw:
            vlans = {} # Store VLAN interface builders in case multiple VLANs are added
            for interface in kw['interfaces']:
                interface_id = interface.get('interface_id')

                if interface_id is None:
                    raise CreateEngineFailed('Interface_id is a required field when '
                        'defining interfaces.')
                
                # Build interface
                if interface.get('type', None) == 'tunnel_interface':
                    if 'address' not in interface or 'network_value' not in interface:
                        raise CreateEngineFailed('Tunnel interfaces require an address '
                            'and network_value')

                    builder = InterfaceBuilder(None) # TunnelInterface
                else:
                    builder = InterfaceBuilder()
            
                builder.interface_id = interface_id
                if 'vlan_id' in interface:
                    # Grab the stored VLAN builder if any
                    if interface_id in vlans:
                        builder = vlans.get(interface_id)
                    
                    if 'address' in interface and 'network_value' in interface:
                        builder.add_sni_to_vlan(
                            address=interface.get('address'),
                            network_value=interface.get('network_value'),
                            vlan_id=interface.get('vlan_id'),
                            nodeid=1,
                            zone_ref=interface.get('zone_ref'))
                    else:  # VLAN only
                        builder.add_vlan_only(
                            vlan_id=interface.get('vlan_id'),
                            zone_ref=interface.get('zone_ref'))
                    # Save builder
                    vlans[interface_id] = builder
                else:
                    builder.zone = interface.get('zone_ref', None)
                    if 'address' in interface and 'network_value' in interface:
                        builder.add_sni_only(
                            address=interface['address'],
                            network_value=interface['network_value'])
                    # else Blank interface, no IP addresses
                       
                    if interface.get('type', None) == 'tunnel_interface':
                        physical_interfaces.append({'tunnel_interface': builder.data})
                    else:
                        physical_interfaces.append({'physical_interface': builder.data})
            
            if vlans:
                for _, builder in vlans.items():
                    physical_interfaces.append({'physical_interface': builder.data})        

        engine = super(Layer3Firewall, cls)._create(
            name=name,
            node_type='firewall_node',
            physical_interfaces=physical_interfaces,
            domain_server_address=domain_server_address,
            log_server_ref=log_server_ref,
            nodes=1, enable_gti=enable_gti,
            enable_antivirus=enable_antivirus,
            sidewinder_proxy_enabled=sidewinder_proxy_enabled,
            default_nat=default_nat,
            location_ref=location_ref,
            enable_ospf=enable_ospf,
            ospf_profile=ospf_profile,
            comment=comment)
    
        try:
            return ElementCreator(cls, json=engine)
        
        except CreateElementFailed as e:
            raise CreateEngineFailed(e)
    
    @classmethod
    def create_dynamic(cls, name, interface_id,
                       dynamic_index=1,
                       primary_mgt=True,
                       reverse_connection=True,
                       automatic_default_route=True,
                       domain_server_address=None,
                       loopback_ndi='127.0.0.1',
                       loopback_ndi_network='127.0.0.1/32',
                       location_ref=None,
                       log_server_ref=None,
                       zone_ref=None,
                       enable_gti=False,
                       enable_antivirus=False,
                       sidewinder_proxy_enabled=False,
                       default_nat=False, comment=None):
        """
        Create a single layer 3 firewall with only a single DHCP interface. Useful
        when creating virtualized FW's such as in Microsoft Azure.
        """
        builder = InterfaceBuilder()
        builder.interface_id = interface_id
        builder.add_dhcp(dynamic_index, is_mgmt=primary_mgt)
        builder.zone = zone_ref
        
        loopback = LoopbackInterface.create(
            address=loopback_ndi, 
            nodeid=1, 
            auth_request=True, 
            rank=1)
        
        engine = super(Layer3Firewall, cls)._create(
            name=name,
            node_type='firewall_node',
            loopback_ndi=[loopback.data],
            physical_interfaces=[{'physical_interface': builder.data}],
            domain_server_address=domain_server_address,
            log_server_ref=log_server_ref,
            nodes=1, enable_gti=enable_gti,
            enable_antivirus=enable_antivirus,
            sidewinder_proxy_enabled=sidewinder_proxy_enabled,
            default_nat=default_nat,
            location_ref=location_ref,
            comment=comment)
    
        try:
            return ElementCreator(cls, json=engine)
        
        except CreateElementFailed as e:
            raise CreateEngineFailed(e)

        
class Layer2Firewall(Engine):
    """
    Creates a Layer 2 Firewall with a default inline interface pair
    To instantiate and create, call 'create' classmethod as follows::

        engine = Layer2Firewall.create(name='myinline', 
                                       mgmt_ip='1.1.1.1', 
                                       mgmt_network='1.1.1.0/24')
    """
    typeof = 'single_layer2'

    @classmethod
    def create(cls, name, mgmt_ip, mgmt_network,
               mgmt_interface=0,
               inline_interface='1-2',
               logical_interface='default_eth',
               log_server_ref=None,
               domain_server_address=None, zone_ref=None,
               enable_antivirus=False, enable_gti=False, comment=None):
        """ 
        Create a single layer 2 firewall with management interface and inline pair

        :param str name: name of firewall engine
        :param str mgmt_ip: ip address of management interface
        :param str mgmt_network: management network in cidr format
        :param int mgmt_interface: (optional) interface for management from SMC to fw
        :param str inline_interface: interfaces to use for first inline pair
        :param str logical_interface: name, str href or LogicalInterface (created if it
            doesn't exist)
        :param str log_server_ref: (optional) href to log_server instance 
        :param list domain_server_address: (optional) DNS server addresses
        :param str zone_ref: zone name, str href or Zone for management interface
            (created if not found)
        :param bool enable_antivirus: (optional) Enable antivirus (required DNS)
        :param bool enable_gti: (optional) Enable GTI
        :raises CreateEngineFailed: Failure to create with reason
        :return: :py:class:`smc.core.engine.Engine`
        """
        interfaces = []

        mgmt = InterfaceBuilder()
        mgmt.interface_id = mgmt_interface
        mgmt.add_ndi_only(mgmt_ip, mgmt_network, is_mgmt=True)
        mgmt.zone = zone_ref

        inline = InterfaceBuilder()
        inline.interface_id = inline_interface.split('-')[0]
        inline.add_inline(inline_interface, logical_interface_ref=logical_interface)

        interfaces.append({'physical_interface': mgmt.data})
        interfaces.append({'physical_interface': inline.data})

        engine = super(Layer2Firewall, cls)._create(
            name=name,
            node_type='fwlayer2_node',
            physical_interfaces=interfaces,
            domain_server_address=domain_server_address,
            log_server_ref=log_server_ref,
            nodes=1, enable_gti=enable_gti,
            enable_antivirus=enable_antivirus,
            comment=comment)

        try:
            return ElementCreator(cls, json=engine)
        
        except CreateElementFailed as e:
            raise CreateEngineFailed(e)


class IPS(Engine):
    """
    Creates an IPS engine with a default inline interface pair
    """
    typeof = 'single_ips'

    @classmethod
    def create(cls, name, mgmt_ip, mgmt_network,
               mgmt_interface=0,
               inline_interface='1-2',
               logical_interface='default_eth',
               log_server_ref=None,
               domain_server_address=None, zone_ref=None,
               enable_antivirus=False, enable_gti=False,
               comment=None):
        """ 
        Create a single IPS engine with management interface and inline pair

        :param str name: name of ips engine
        :param str mgmt_ip: ip address of management interface
        :param str mgmt_network: management network in cidr format
        :param int mgmt_interface: (optional) interface for management from SMC to fw
        :param str inline_interface: interfaces to use for first inline pair
        :param str logical_interface: name, str href or LogicalInterface (created if it
            doesn't exist)
        :param str log_server_ref: (optional) href to log_server instance 
        :param list domain_server_address: (optional) DNS server addresses
        :param str zone_ref: zone name, str href or Zone for management interface
            (created if not found)
        :param bool enable_antivirus: (optional) Enable antivirus (required DNS)
        :param bool enable_gti: (optional) Enable GTI
        :raises CreateEngineFailed: Failure to create with reason
        :return: :py:class:`smc.core.engine.Engine`
        """
        interfaces = []

        mgmt = InterfaceBuilder()
        mgmt.interface_id = mgmt_interface
        mgmt.add_ndi_only(mgmt_ip, mgmt_network, is_mgmt=True)
        mgmt.zone = zone_ref

        inline = InterfaceBuilder()
        inline.interface_id = inline_interface.split('-')[0]
        inline.add_inline(inline_interface, logical_interface_ref=logical_interface)

        interfaces.append({'physical_interface': mgmt.data})
        interfaces.append({'physical_interface': inline.data})

        engine = super(IPS, cls)._create(
            name=name,
            node_type='ips_node',
            physical_interfaces=interfaces,
            domain_server_address=domain_server_address,
            log_server_ref=log_server_ref,
            nodes=1, enable_gti=enable_gti,
            enable_antivirus=enable_antivirus,
            comment=comment)

        try:
            return ElementCreator(cls, json=engine)
    
        except CreateElementFailed as e:
            raise CreateEngineFailed(e)


class Layer3VirtualEngine(Engine):
    """ 
    Create a layer3 virtual engine and map to specified Master Engine
    Each layer 3 virtual firewall will use the same virtual resource that 
    should be pre-created.

    To instantiate and create, call 'create' as follows::

        engine = Layer3VirtualEngine.create(
                                name='myips', 
                                master_engine='mymaster_engine', 
                                virtual_engine='ve-3',
                                interfaces=[{'interface_id': 0,
                                             'address': '5.5.5.5', 
                                             'network_value': '5.5.5.5/30',  
                                             'zone_ref': ''}]
    """
    typeof = 'virtual_fw'

    @classmethod
    def create(cls, name, master_engine, virtual_resource,
               interfaces, default_nat=False, outgoing_intf=0,
               domain_server_address=None, enable_ospf=False,
               ospf_profile=None, comment=None, **kwargs):
        """
        :param str name: Name of this layer 3 virtual engine
        :param str master_engine: Name of existing master engine
        :param str virtual_resource: name of pre-created virtual resource
        :param list interfaces: dict of interface details
        :param bool default_nat: Whether to enable default NAT for outbound
        :param int outgoing_intf: outgoing interface for VE. Specifies interface number
        :param list interfaces: interfaces mappings passed in
        :param bool enable_ospf: whether to turn OSPF on within engine
        :param str ospf_profile: optional OSPF profile to use on engine, by ref   
        :raises CreateEngineFailed: Failure to create with reason
        :raises LoadEngineFailed: master engine not found
        :return: :py:class:`smc.core.engine.Engine`
        """
        virt_resource_href = None  # need virtual resource reference
        master_engine = Engine(master_engine)

        for virt_resource in master_engine.virtual_resource.all():
            if virt_resource.name == virtual_resource:
                virt_resource_href = virt_resource.href
                break
        if not virt_resource_href:
            raise CreateEngineFailed('Cannot find associated virtual resource for '
                                     'VE named: {}. You must first create a virtual '
                                     'resource for the master engine before you can associate '
                                     'a virtual engine. Cannot add VE'.format(name))
        new_interfaces = []
        for interface in interfaces:
            builder = InterfaceBuilder()
            builder.interface_id = interface.get('interface_id')
            builder.add_sni_only(interface.get('address'),
                                 interface.get('network_value'))
            builder.zone_ref = interface.get('zone_ref')

            # set auth request and outgoing on one of the interfaces
            if interface.get('interface_id') == outgoing_intf:
                intf = extract_sub_interface(builder.data)
                intf.update(outgoing=True, auth_request=True)
                
            new_interfaces.append({'virtual_physical_interface': builder.data})

            engine = super(Layer3VirtualEngine, cls)._create(
                name=name,
                node_type='virtual_fw_node',
                physical_interfaces=new_interfaces,
                domain_server_address=domain_server_address,
                log_server_ref=None,  # Isn't used in VE
                nodes=1, default_nat=default_nat,
                enable_ospf=enable_ospf,
                ospf_profile=ospf_profile,
                comment=comment)

            engine.update(virtual_resource=virt_resource_href)
            # Master Engine provides this service
            engine.pop('log_server_ref', None)
            
        try:
            return ElementCreator(cls, json=engine)
    
        except CreateElementFailed as e:
            raise CreateEngineFailed(e)
    

class FirewallCluster(Engine):
    """ 
    Firewall Cluster
    Creates a layer 3 firewall cluster engine with CVI and NDI's. Once engine is 
    created, you can later add additional interfaces using the `engine.physical_interface`
    reference.
    
    .. seealso::  :func:`smc.core.interfaces.PhysicalInterface.add_layer3_cluster_interface`
    """
    typeof = 'fw_cluster'

    @classmethod
    def create(cls, name, cluster_virtual, network_value,
               macaddress, interface_id, nodes,
               cluster_mode='balancing',
               backup_mgt=None, primary_heartbeat=None, 
               log_server_ref=None,
               domain_server_address=None,
               location_ref=None,
               zone_ref=None, default_nat=False,
               enable_antivirus=False, enable_gti=False,
               comment=None, snmp_agent=None, **kw):
        """
        Create a layer 3 firewall cluster with management interface and any number
        of nodes. If providing keyword arguments to create additional interfaces,
        use the same constructor arguments and pass an `interfaces` keyword argument.
        The constructor defined interface will be assigned as the primary
        management interface by default.
        
        .. versionchanged:: 0.6.1
            Chgnged `cluster_nic` to `interface_id`, and `cluster_mask` to `network_value`
        
        :param str name: name of firewall engine
        :param str cluster_virtual: ip of cluster CVI
        :param str network_value: ip netmask of cluster CVI
        :param str macaddress: macaddress for packet dispatch clustering
        :param str interface_id: nic id to use for primary interface
        :param list nodes: address/network_value/nodeid combination for cluster nodes
        :param str cluster_mode: 'balancing' or 'standby' mode (default: balancing)
        :param str,int primary_heartbeat: optionally set the primary_heartbeat. This is
            automatically set to the management interface but can be overridden to use
            another interface if defining additional interfaces using `interfaces`.
        :param str,int backup_mgt: optionally set the backup management interface. This
            is unset unless you define additional interfaces using `interfaces`.
        :param str log_server_ref: (optional) href to log_server instance 
        :param list domain_server_address: (optional) DNS server addresses
        :param str location_ref: location href or not for engine if needed to contact SMC
            behind NAT (created if not found)
        :param str zone_ref: zone name, str href or Zone for management interface
            (created if not found)
        :param bool enable_antivirus: (optional) Enable antivirus (required DNS)
        :param bool enable_gti: (optional) Enable GTI
        :param list interfaces: optional keyword to supply additional interfaces
        :param str snmp_agent: the name of the SNMPAgent element to enable for this engine
        :param str snmp_location: provide as kw, defines optional snmp location string
        :param list snmp_interface: provide as kw, defines a list of interface id's to
            enable SNMP (i.e. [1, '2.3', etc]. Otherwise SNMP is enabled on all NDI
            interfaces with exception of tunnel interfaces
        :raises CreateEngineFailed: Failure to create with reason
        :return: :py:class:`smc.core.engine.Engine`

        Example nodes parameter input::

            [{'address':'5.5.5.2', 'network_value':'5.5.5.0/24', 'nodeid':1},
             {'address':'5.5.5.3', 'network_value':'5.5.5.0/24', 'nodeid':2},
             {'address':'5.5.5.4', 'network_value':'5.5.5.0/24', 'nodeid':3}]
        
        You can also create additional CVI+NDI, or NDI only interfaces by providing
        the keyword argument interfaces using the same keyword values from the
        constructor::
        
            interfaces=[
               {'cluster_virtual': '2.2.2.1',
                'network_value': '2.2.2.0/24',
                'macaddress': '02:02:02:02:02:03',
                'interface_id': 1,
                'nodes':[{'address': '2.2.2.2', 'network_value': '2.2.2.0/24', 'nodeid': 1},
                         {'address': '2.2.2.3', 'network_value': '2.2.2.0/24', 'nodeid': 2}]
                },
               {'interface_id': 2,
                'nodes':[{'address': '3.3.3.2', 'network_value': '3.3.3.0/24', 'nodeid': 1},
                         {'address': '3.3.3.3', 'network_value': '3.3.3.0/24', 'nodeid': 2}]
                }]
        
        It is also possible to define VLAN interfaces by providing the `vlan_id` keyword.
        Example VLAN with NDI only interfaces::
        
            interfaces=[
               {'interface_id': 2,
                'nodes':[{'address': '3.3.3.2', 'network_value': '3.3.3.0/24', 'nodeid': 1},
                         {'address': '3.3.3.3', 'network_value': '3.3.3.0/24', 'nodeid': 2}],
                'vlan_id': 22,
                'zone_ref': 'private-network'
                }]
        
        Tunnel interfaces can also be created. As all interfaces defined are assumed to be
        a physical interface type, you must specify the `type` parameter to indicate the
        interface is a tunnel interface. Tunnel interfaces do not have a macaddress or VLANs.
        They be configured with NDI interfaces by omitting the `cluster_virtual` and
        `network_value` top level attributes::
        
            interfaces=[
                {'interface_id': 1000,
                 'cluster_virtual': '100.100.100.1',
                 'network_value': '100.100.100.0/24',
                 'nodes':[{'address': '100.100.100.2', 'network_value': '100.100.100.0/24', 'nodeid': 1},
                          {'address': '100.100.100.3', 'network_value': '100.100.100.0/24', 'nodeid': 2}],
                 'zone_ref': 'AWStunnel',
                 'type': 'tunnel_interface'
                }]
        
        If setting primary_heartbeat or backup_mgt to a specific interface (the primary
        interface configured in the constructor will have these roles by default), you
        must define the interfaces in the `interfaces` keyword argument list.
           
        .. note:: If creating additional interfaces, you must at minimum provide the
            `interface_id` and `nodes` to create an NDI only interface.
                                
        """
        builder = InterfaceBuilder()
        builder.interface_id = interface_id
        builder.macaddress = macaddress
        builder.cvi_mode = 'packetdispatch'
        builder.zone = zone_ref
        builder.add_cvi_only(cluster_virtual, network_value, is_mgmt=True)
        for node in nodes:
            if primary_heartbeat is not None:
                node.update(primary_mgt=True, outgoing=True)
            else:
                node.update(is_mgmt=True)
            builder.add_ndi_only(**node)
        
        physical_interfaces = [{'physical_interface': builder.data}]
        
        # Optional additional interfaces
        if 'interfaces' in kw:
            vlans = {} # Store VLAN interface builders in case multiple VLANs are added
            
            # Custom backup management
            if backup_mgt is not None:
                if '.' in str(backup_mgt):
                    bkup_interface, bkup_vlan = backup_mgt.split('.')
                else:
                    bkup_interface, bkup_vlan = str(backup_mgt), None
            
            # Custom primary heartbeat
            if primary_heartbeat is not None:
                if '.' in str(primary_heartbeat):
                    hb_interface, hb_vlan = primary_heartbeat.split('.')
                else:
                    hb_interface, hb_vlan = str(primary_heartbeat), None
            
            for interface in kw['interfaces']:
                _interface_id = interface.get('interface_id')
                interface_type = interface.get('type', 'physical_interface')
                
                if _interface_id is None:
                    raise CreateEngineFailed('Interface_id is a required field when '
                        'defining interfaces.')
                
                if interface_type == 'tunnel_interface':
                    builder = InterfaceBuilder(None) # TunnelInterface
                    builder.interface_id = _interface_id
                elif 'vlan_id' in interface and _interface_id in vlans:
                    builder = vlans.get(_interface_id)
                else:
                    builder = InterfaceBuilder()
                    builder.interface_id = _interface_id

                # Check for CVI configuration
                if all(cvi in interface and interface[cvi] is not None \
                       for cvi in ('cluster_virtual', 'network_value', 'macaddress')):
                
                    # Tunnel interfaces do not have macaddress or cvi mode
                    if interface_type != 'tunnel_interface':
                        builder.macaddress = interface.get('macaddress')
                        builder.cvi_mode = 'packetdispatch'

                    if 'vlan_id' in interface:
                        builder.add_cvi_to_vlan(
                            address=interface['cluster_virtual'],
                            network_value=interface['network_value'],
                            vlan_id=interface['vlan_id'],
                            zone_ref=interface.get('zone_ref'))
                    else:
                        builder.zone = interface.get('zone_ref')
                        builder.add_cvi_only(
                            address=interface.get('cluster_virtual'),
                            network_value=interface.get('network_value'))
                
                # If nodes are specified
                if interface.get('nodes', []):
                    for node in interface.get('nodes', []):
                        if 'vlan_id' in interface:
                            node.update(vlan_id=interface['vlan_id'])
                            # If backup management is set, identify the correct
                            # VLAN nodes to assign
                            if backup_mgt is not None:
                                if str(_interface_id) == bkup_interface and \
                                    str(interface['vlan_id']) == bkup_vlan:
                                    node.update(backup_mgt=True)
                            
                            if primary_heartbeat is not None:
                                if str(_interface_id) == hb_interface and \
                                    str(interface['vlan_id']) == hb_vlan:
                                    node.update(primary_heartbeat=True)
                            
                            node.update(zone_ref=interface.get('zone_ref'))        
                            builder.add_ndi_to_vlan(**node)
                            
                        else:
                            # Assign primary backup and heartbeat if specified
                            if backup_mgt is not None and str(_interface_id) == bkup_interface:
                                node.update(backup_mgt=True)
                            if primary_heartbeat is not None and str(_interface_id) == hb_interface:
                                node.update(primary_heartbeat=True)
                            builder.add_ndi_only(**node)
                
                elif 'cluster_virtual' not in interface or \
                    interface['cluster_virtual'] is None:
                    # No nodes were specified and this is not a cluster virtual which
                    # means it's an empty interface but may still have a VLAN id or
                    # zone.
                    zone = interface.get('zone_ref')
                    if 'vlan_id' in interface:
                        builder.add_vlan_only(
                            vlan_id=interface['vlan_id'],
                            zone_ref=zone)
                    else:
                        builder.zone = zone
                
                if 'vlan_id' in interface:
                    vlans[_interface_id] = builder
                else:
                    physical_interfaces.append({interface_type: builder.data})
            
            if vlans:
                for _, builder in vlans.items(): 
                    physical_interfaces.append({'physical_interface': builder.data})

        if snmp_agent:
            snmp_agent = dict(
                snmp_agent_ref=snmp_agent,
                snmp_location=kw.get('snmp_location', ''))
            
            kw.setdefault('interfaces', []).append(
                {'interface_id': interface_id, 'nodes': nodes})
            
            snmp_agent.update(
                snmp_interface=add_snmp(
                    kw.get('interfaces'),
                    kw.get('snmp_interface', [])))

        try:
            engine = super(FirewallCluster, cls)._create(
                name=name,
                node_type='firewall_node',
                physical_interfaces=physical_interfaces,
                domain_server_address=domain_server_address,
                log_server_ref=log_server_ref,
                location_ref=location_ref,
                nodes=len(nodes), enable_gti=enable_gti,
                enable_antivirus=enable_antivirus,
                default_nat=default_nat,
                snmp_agent=snmp_agent if snmp_agent else None,
                comment=comment)
            engine.update(cluster_mode=cluster_mode)
        
            return ElementCreator(cls, json=engine)
    
        except (ElementNotFound, CreateElementFailed) as e:
            raise CreateEngineFailed(e)
        

class MasterEngine(Engine):
    """
    Creates a master engine in a firewall role. Layer3VirtualEngine should be used
    to add each individual instance to the Master Engine.
    """
    typeof = 'master_engine'

    @classmethod
    def create(cls, name, master_type, mgmt_ip, mgmt_network,
               mgmt_interface=0,
               log_server_ref=None,
               domain_server_address=None, enable_gti=False,
               enable_antivirus=False, comment=None):
        """
        Create a Master Engine with management interface

        :param str name: name of master engine engine
        :param str master_type: firewall|
        :param str mgmt_ip: ip address for management interface
        :param str mgmt_network: full netmask for management
        :param str mgmt_interface: interface to use for mgmt (default: 0)
        :param str log_server_ref: (optional) href to log_server instance 
        :param list domain_server_address: (optional) DNS server addresses
        :param bool enable_antivirus: (optional) Enable antivirus (required DNS)
        :param bool enable_gti: (optional) Enable GTI
        :raises CreateEngineFailed: Failure to create with reason
        :return: :py:class:`smc.core.engine.Engine`
        """
        builder = InterfaceBuilder()
        builder.interface_id = mgmt_interface
        builder.add_ndi_only(mgmt_ip, mgmt_network,
                             is_mgmt=True,
                             primary_heartbeat=True,
                             outgoing=True)

        engine = super(MasterEngine, cls)._create(
            name=name,
            node_type='master_node',
            physical_interfaces=[{'physical_interface': builder.data}],
            domain_server_address=domain_server_address,
            log_server_ref=log_server_ref,
            nodes=1, enable_gti=enable_gti,
            enable_antivirus=enable_antivirus,
            comment=comment)

        engine.update(master_type=master_type,
                      cluster_mode='standby')

        try:
            return ElementCreator(cls, json=engine)
    
        except CreateElementFailed as e:
            raise CreateEngineFailed(e)
    

class MasterEngineCluster(Engine):
    """
    Master Engine Cluster
    Clusters are currently supported in an active/standby configuration
    only. 
    """
    typeof = 'master_engine'
    
    @classmethod
    def create(cls, name, master_type, macaddress,
               nodes, mgmt_interface=0, log_server_ref=None,
               domain_server_address=None,
               enable_gti=False,
               enable_antivirus=False, comment=None):
        """
        Create Master Engine Cluster

        :param str name: name of master engine engine
        :param str master_type: firewall|
        :param str mgmt_ip: ip address for management interface
        :param str mgmt_netmask: full netmask for management
        :param str mgmt_interface: interface to use for mgmt (default: 0)
        :param list nodes: address/network_value/nodeid combination for cluster nodes 
        :param str log_server_ref: (optional) href to log_server instance 
        :param list domain_server_address: (optional) DNS server addresses
        :param bool enable_antivirus: (optional) Enable antivirus (required DNS)
        :param bool enable_gti: (optional) Enable GTI
        :raises CreateEngineFailed: Failure to create with reason
        :return: :py:class:`smc.core.engine.Engine`

        Example nodes parameter input::

            [{'address':'5.5.5.2', 
              'network_value':'5.5.5.0/24', 
              'nodeid':1},
             {'address':'5.5.5.3', 
              'network_value':'5.5.5.0/24', 
              'nodeid':2},
             {'address':'5.5.5.4', 
              'network_value':'5.5.5.0/24', 
              'nodeid':3}]
        """
        builder = InterfaceBuilder()
        builder.interface_id = mgmt_interface
        builder.macaddress = macaddress
        for node in nodes:
            node.update(is_mgmt=True)
            builder.add_ndi_only(**node)

        engine = super(MasterEngineCluster, cls)._create(
            name=name,
            node_type='master_node',
            physical_interfaces=[{'physical_interface': builder.data}],
            domain_server_address=domain_server_address,
            log_server_ref=log_server_ref,
            nodes=len(nodes), enable_gti=enable_gti,
            enable_antivirus=enable_antivirus,
            comment=comment)

        engine.update(master_type=master_type,
                      cluster_mode='standby')

        try:
            return ElementCreator(cls, json=engine)
            
        except CreateElementFailed as e:
            raise CreateEngineFailed(e)
        

def add_snmp(data, interfaces):
    """
    Format data for adding SNMP to an engine.
    
    :param list data: list of interfaces as provided by kw
    :param list interfaces: interfaces to enable SNMP by id
    """
    snmp_interface = []
    if interfaces: # Not providing interfaces will enable SNMP on all NDIs
        interfaces = map(str, interfaces)
        for interface in data:
            interface_id = str(interface.get('interface_id'))
            if 'vlan_id' in interface:
                interface_id = '{}.{}'.format(
                    interface.get('interface_id'),
                    interface.get('vlan_id'))
            
            # If 'type' is specified, it is something other than a
            # physical interface (tunnel, inline, etc). Ignore.
            if interface_id in interfaces and 'type' not in interface:
                if 'nodes' in interface and interface['nodes'] is not None:
                    for node in interface.get('nodes', []):
                        snmp_interface.append(
                            {'address': node.get('address'),
                             'nicid': interface_id})
    return snmp_interface
