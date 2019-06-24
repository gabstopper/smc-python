from smc.core.interfaces import ClusterPhysicalInterface, TunnelInterface,\
    Layer3PhysicalInterface, Layer2PhysicalInterface, SwitchPhysicalInterface
from smc.core.sub_interfaces import LoopbackInterface
from smc.core.engine import Engine
from smc.api.exceptions import CreateEngineFailed, CreateElementFailed,\
    ElementNotFound
from smc.base.model import ElementCreator

    
class Layer3Firewall(Engine):
    """
    .. versionchanged:: 0.7.0
        extra_opts can be passed to the top level engine dict to customize
        input
    
    Represents a Layer 3 Firewall configuration.
    A layer 3 single FW is a standalone FW instance (not a cluster). You can
    use the `create` constructor and add interfaces after the engine exists,
    or use `create_bulk` to fully create the engine and interfaces in a single
    operation.
    
    You can also pass arbitrary kwargs passed in to the engine dict by providing
    the `extra_opts` value as a dict. Therefore it can support any custom
    configurations as long as the format is valid.
    For example, enabling file reputation on a SMC >= 6.6::
    
        extra_opts= {'file_reputation_settings':{'file_reputation_context': 'gti_cloud_only'}}
    
    """
    typeof = 'single_fw'

    @classmethod
    def create_bulk(cls, name, interfaces=None,
                   primary_mgt=None, backup_mgt=None,
                   auth_request=None, log_server_ref=None,
                   domain_server_address=None, nodes=1,
                   node_type='firewall_node',
                   location_ref=None, default_nat=False,
                   enable_antivirus=False,  sidewinder_proxy_enabled=False,
                   enable_ospf=False, ospf_profile=None, comment=None, snmp=None,
                   extra_opts=None, **kw):
        """
        Create a Layer 3 Firewall providing all of the interface configuration.
        This method provides a way to fully create the engine and all interfaces
        at once versus using :py:meth:`~create` and creating each individual
        interface after the engine exists.
        
        Example interfaces format::
        
            interfaces=[
                {'interface_id': 1},
                {'interface_id': 2, 
                 'interfaces':[{'nodes': [{'address': '2.2.2.2', 'network_value': '2.2.2.0/24'}]}],
                 'zone_ref': 'myzone'},
                {'interface_id': 3,
                 'interfaces': [{'nodes': [{'address': '3.3.3.3', 'network_value': '3.3.3.0/24'}],
                                 'vlan_id': 3,
                                 'zone_ref': 'myzone'},
                                 {'nodes': [{'address': '4.4.4.4', 'network_value': '4.4.4.0/24'}],
                                  'vlan_id': 4}]},
                {'interface_id': 4,
                 'interfaces': [{'vlan_id': 4,
                                 'zone_ref': 'myzone'}]},
                {'interface_id': 5,
                 'interfaces': [{'vlan_id': 5}]},
                {'interface_id': 1000,
                 'interfaces': [{'nodes': [{'address': '10.10.10.1', 'network_value': '10.10.10.0/24'}]}],
                 'type': 'tunnel_interface'}]
        
        Sample of creating a simple two interface firewall::
        
            firewall_def = {
                'name': 'firewall',
                'domain_server_address': ['192.168.122.1'],
                'primary_mgt': 0,
                'interfaces': [
                    {'interface_id': 0,
                     'interfaces': [{'nodes': [{'address': '192.168.122.100', 'network_value': '192.168.122.0/24', 'auth_request': False}]}
                                    ]
                     },
                    {'interface_id': 1,
                     'interfaces': [{'nodes': [{'address': '10.0.0.254', 'network_value': '10.0.0.0/24', 'auth_request': True}]}
                                    ]
                     }
                ]
            }
            fw = Layer3Firewall.create_bulk(**firewall_def)
        
        .. note:: You can set primary_mgt, backup_mgt, outgoing, and auth_request within the
            interface definition itself to specify interface options. If provided in the constructor,
            this will be passed to the interface creation factory. You should use one or the other
            method, not both.
        
        See :class:`smc.core.interfaces.Layer3PhysicalInterface` for more advanced examples
        """
        physical_interfaces = []
        for interface in interfaces:
            if 'interface_id' not in interface:
                raise CreateEngineFailed('Interface definitions must contain the interface_id '
                    'field. Failed to create engine: %s' % name)
            if interface.get('type', None) == 'tunnel_interface':
                tunnel_interface = TunnelInterface(**interface)
                physical_interfaces.append(
                    {'tunnel_interface': tunnel_interface})
            elif interface.get('type', None) == 'switch_physical_interface':
                physical_interfaces.append(
                    {'switch_physical_interface': SwitchPhysicalInterface(
                        primary_mgt=primary_mgt, backup_mgt=backup_mgt,
                        auth_request=auth_request, **interface)})
            else:
                interface.update(interface='single_node_interface')
                interface = Layer3PhysicalInterface(primary_mgt=primary_mgt,
                      backup_mgt=backup_mgt, auth_request=auth_request, **interface)
                physical_interfaces.append(
                    {'physical_interface': interface})

        if snmp:
            snmp_agent = dict(
                snmp_agent_ref=snmp.get('snmp_agent', ''),
                snmp_location=snmp.get('snmp_location', ''))
            
            snmp_agent.update(
                snmp_interface=add_snmp(
                    interfaces,
                    snmp.get('snmp_interface', [])))
        
        try:
            engine = super(Layer3Firewall, cls)._create(
                name=name,
                node_type=node_type,
                physical_interfaces=physical_interfaces,
                loopback_ndi=kw.pop('loopback_ndi', []),
                domain_server_address=domain_server_address,
                log_server_ref=log_server_ref,
                nodes=nodes, enable_antivirus=enable_antivirus,
                sidewinder_proxy_enabled=sidewinder_proxy_enabled,
                default_nat=default_nat,
                location_ref=location_ref,
                enable_ospf=enable_ospf,
                ospf_profile=ospf_profile,
                snmp_agent=snmp_agent if snmp else None,
                comment=comment, **extra_opts if extra_opts else {})

            return ElementCreator(cls, json=engine)
        
        except (ElementNotFound, CreateElementFailed) as e:
            raise CreateEngineFailed(e)

    @classmethod
    def create(cls, name, mgmt_ip, mgmt_network,
               mgmt_interface=0,
               log_server_ref=None,
               default_nat=False,
               reverse_connection=False,
               domain_server_address=None, zone_ref=None,
               enable_antivirus=False,
               location_ref=None, enable_ospf=False,
               sidewinder_proxy_enabled=False,
               ospf_profile=None, snmp=None, comment=None, 
               extra_opts=None, **kw):
        """ 
        Create a single layer 3 firewall with management interface and DNS. 
        Provide the `interfaces` keyword argument if adding multiple additional interfaces.
        Interfaces can be one of any valid interface for a layer 3 firewall. Unless the
        interface type is specified, physical_interface is assumed.
        
        Valid interface types:
            - physical_interface (default if not specified)
            - tunnel_interface
    
        If providing all engine interfaces in a single operation, see :py:meth:`~create_bulk`
        for the proper format.
                  
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
        :param dict extra_opts: extra options as a dict to be passed to the top level engine
        :param kw: optional keyword arguments specifying additional interfaces  
        :raises CreateEngineFailed: Failure to create with reason
        :return: :py:class:`smc.core.engine.Engine`
        """
        interfaces = kw.pop('interfaces', [])
        # Add the primary interface to the interface list
        interface = {'interface_id': mgmt_interface,
                     'interface': 'single_node_interface',
                     'zone_ref': zone_ref,
                     'interfaces': [{
                         'nodes': [{'address': mgmt_ip, 'network_value': mgmt_network, 'nodeid': 1,
                                    'reverse_connection': reverse_connection}]
                         }]
                     }
        interfaces.append(interface)
        
        return Layer3Firewall.create_bulk(
            name=name,
            node_type='firewall_node',
            interfaces=interfaces,
            primary_mgt=mgmt_interface,
            domain_server_address=domain_server_address,
            log_server_ref=log_server_ref,
            nodes=1, enable_antivirus=enable_antivirus,
            sidewinder_proxy_enabled=sidewinder_proxy_enabled,
            default_nat=default_nat,
            location_ref=location_ref,
            enable_ospf=enable_ospf,
            ospf_profile=ospf_profile, snmp=snmp,
            comment=comment, extra_opts=extra_opts)  
      
    @classmethod
    def create_dynamic(cls, name, interface_id,
                       dynamic_index=1,
                       reverse_connection=True,
                       automatic_default_route=True,
                       domain_server_address=None,
                       loopback_ndi='127.0.0.1',
                       location_ref=None,
                       log_server_ref=None,
                       zone_ref=None,
                       enable_antivirus=False,
                       sidewinder_proxy_enabled=False,
                       default_nat=False, comment=None, 
                       extra_opts=None, **kw):
        """
        Create a single layer 3 firewall with only a single DHCP interface. Useful
        when creating virtualized FW's such as in Microsoft Azure.
        
        :param str name: name of engine
        :param str,int interface_id: interface ID used for dynamic interface and management
        :param bool reverse_connection: specifies the dynamic interface should initiate connections
            to management (default: True)
        :param bool automatic_default_route: allow SMC to create a dynamic netlink for the default
            route (default: True)
        :param list domain_server_address: list of IP addresses for engine DNS
        :param str loopback_ndi: IP address for a loopback NDI. When creating a dynamic engine, the
            `auth_request` must be set to a different interface, so loopback is created
        :param str location_ref: location by name for the engine
        :param str log_server_ref: log server reference, will use the default or first retrieved if
            not specified
        :param dict extra_opts: extra options as a dict to be passed to the top level engine
        :raises CreateElementFailed: failed to create engine
        :return: :py:class:`smc.core.engine.Engine`
        """
        interfaces = kw.pop('interfaces', [])
        # Add the primary interface to the interface list
        interface = {'interface_id': interface_id,
                     'interface': 'single_node_interface',
                     'zone_ref': zone_ref,
                     'interfaces': [{
                         'nodes': [{'dynamic': True, 'dynamic_index': dynamic_index, 'nodeid': 1,
                                    'reverse_connection': reverse_connection,
                                    'automatic_default_route': automatic_default_route}]
                         }]
                     }
        interfaces.append(interface)
        
        loopback = LoopbackInterface.create(
            address=loopback_ndi, 
            nodeid=1, 
            auth_request=True, 
            rank=1)
        
        return Layer3Firewall.create_bulk(
            name=name,
            node_type='firewall_node',
            primary_mgt=interface_id,
            interfaces=interfaces,
            loopback_ndi=[loopback.data],
            domain_server_address=domain_server_address,
            log_server_ref=log_server_ref,
            nodes=1, enable_antivirus=enable_antivirus,
            sidewinder_proxy_enabled=sidewinder_proxy_enabled,
            default_nat=default_nat,
            location_ref=location_ref,
            comment=comment, extra_opts=extra_opts)

        
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
               enable_antivirus=False, comment=None, extra_opts=None, **kw):
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
        :param dict extra_opts: extra options as a dict to be passed to the top level engine
        :raises CreateEngineFailed: Failure to create with reason
        :return: :py:class:`smc.core.engine.Engine`
        """
        interfaces = []
        interface_id, second_interface_id = inline_interface.split('-')
        l2 = {'interface_id': interface_id,
              'interface': 'inline_interface',
              'second_interface_id': second_interface_id,
              'logical_interface_ref': logical_interface}
        
        interfaces.append(
            {'physical_interface': Layer2PhysicalInterface(**l2)})
        
        layer3 = {'interface_id': mgmt_interface,
                  'zone_ref': zone_ref,
                  'interfaces': [{'nodes': [
                      {'address': mgmt_ip, 'network_value': mgmt_network, 'nodeid': 1}]}]
             }
        
        interfaces.append(
            {'physical_interface': Layer3PhysicalInterface(primary_mgt=mgmt_interface, **layer3)})
            
        engine = super(Layer2Firewall, cls)._create(
            name=name,
            node_type='fwlayer2_node',
            physical_interfaces=interfaces,
            domain_server_address=domain_server_address,
            log_server_ref=log_server_ref,
            nodes=1, enable_antivirus=enable_antivirus,
            comment=comment, **extra_opts if extra_opts else {})
        
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
    def create(cls, name, mgmt_ip, mgmt_network, mgmt_interface=0,
               inline_interface='1-2', logical_interface='default_eth',
               log_server_ref=None, domain_server_address=None, zone_ref=None,
               enable_antivirus=False, comment=None, extra_opts=None, **kw):
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
        :param dict extra_opts: extra options as a dict to be passed to the top level engine
        :raises CreateEngineFailed: Failure to create with reason
        :return: :py:class:`smc.core.engine.Engine`
        """
        interfaces = []
        interface_id, second_interface_id = inline_interface.split('-')
        l2 = {'interface_id': interface_id,
              'interface': 'inline_interface',
              'second_interface_id': second_interface_id,
              'logical_interface_ref': logical_interface}
        
        interfaces.append(
            {'physical_interface': Layer2PhysicalInterface(**l2)})
        
        layer3 = {'interface_id': mgmt_interface,
                  'zone_ref': zone_ref,
             'interfaces': [{'nodes': [
                 {'address': mgmt_ip, 'network_value': mgmt_network, 'nodeid': 1}]}]
             }
        
        interfaces.append(
            {'physical_interface': Layer3PhysicalInterface(primary_mgt=mgmt_interface, **layer3)})

        engine = super(IPS, cls)._create(
            name=name,
            node_type='ips_node',
            physical_interfaces=interfaces,
            domain_server_address=domain_server_address,
            log_server_ref=log_server_ref,
            nodes=1, enable_antivirus=enable_antivirus,
            comment=comment, **extra_opts if extra_opts else {})

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
               ospf_profile=None, comment=None, extra_opts=None, **kw):
        """
        Create a Layer3Virtual engine for a Master Engine. Provide interfaces
        as a list of dict items specifying the interface details in format::
        
            {'interface_id': 1, 'address': '1.1.1.1', 'network_value': '1.1.1.0/24',
             'zone_ref': zone_by_name,href, 'comment': 'my interface comment'}
        
        :param str name: Name of this layer 3 virtual engine
        :param str master_engine: Name of existing master engine
        :param str virtual_resource: name of pre-created virtual resource
        :param list interfaces: dict of interface details
        :param bool default_nat: Whether to enable default NAT for outbound
        :param int outgoing_intf: outgoing interface for VE. Specifies interface number
        :param list interfaces: interfaces mappings passed in
        :param bool enable_ospf: whether to turn OSPF on within engine
        :param str ospf_profile: optional OSPF profile to use on engine, by ref
        :param dict extra_opts: extra options as a dict to be passed to the top level engine
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
                'VE named: {}. You must first create a virtual resource for the '
                'master engine before you can associate a virtual engine. Cannot '
                'add VE'.format(name))
        
        virtual_interfaces = []
        for interface in interfaces:
            nodes = {'address': interface.get('address'),
                     'network_value': interface.get('network_value')}
            
            layer3 = {'interface_id': interface.get('interface_id'),
                      'interface': 'single_node_interface',
                      'comment': interface.get('comment', None),
                      'zone_ref': interface.get('zone_ref')}
            
            if interface.get('interface_id') == outgoing_intf:
                nodes.update(outgoing=True, auth_request=True)
            
            layer3['interfaces'] = [{'nodes': [nodes]}]
            
            virtual_interfaces.append(
                {'virtual_physical_interface': Layer3PhysicalInterface(**layer3).data.data})
            
            engine = super(Layer3VirtualEngine, cls)._create(
                name=name,
                node_type='virtual_fw_node',
                physical_interfaces=virtual_interfaces,
                domain_server_address=domain_server_address,
                log_server_ref=None,  # Isn't used in VE
                nodes=1, default_nat=default_nat,
                enable_ospf=enable_ospf,
                ospf_profile=ospf_profile,
                comment=comment, **extra_opts if extra_opts else {})

            engine.update(virtual_resource=virt_resource_href)
            engine.pop('log_server_ref', None) # Master Engine provides this service
        
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
    
    .. seealso::  :func:`smc.core.physical_interface.add_layer3_cluster_interface`
    """
    typeof = 'fw_cluster'
    
    @classmethod
    def create_bulk(cls, name, interfaces=None, nodes=2, cluster_mode='balancing',
            primary_mgt=None, backup_mgt=None, primary_heartbeat=None,
            log_server_ref=None, domain_server_address=None, location_ref=None,
            default_nat=False, enable_antivirus=False, comment=None,
            snmp=None, extra_opts=None, **kw):
        """
        Create bulk is called by the `create` constructor when creating a cluster FW.
        This allows for multiple interfaces to be defined and passed in during element
        creation.
        
        :param dict snmp: SNMP dict should have keys `snmp_agent` str defining name of SNMPAgent,
            `snmp_interface` which is a list of interface IDs, and optionally `snmp_location` which
            is a string with the SNMP location name.
        """
        primary_heartbeat = primary_mgt if not primary_heartbeat else primary_heartbeat
        
        physical_interfaces = []
        for interface in interfaces:
            if 'interface_id' not in interface:
                raise CreateEngineFailed('Interface definitions must contain the interface_id '
                    'field. Failed to create engine: %s' % name)
            if interface.get('type', None) == 'tunnel_interface':
                tunnel_interface = TunnelInterface(**interface)
                physical_interfaces.append(
                    {'tunnel_interface': tunnel_interface})
            else:
                cluster_interface = ClusterPhysicalInterface(
                    primary_mgt=primary_mgt, backup_mgt=backup_mgt,
                    primary_heartbeat=primary_heartbeat, **interface)
                physical_interfaces.append(
                    {'physical_interface': cluster_interface})

        if snmp:
            snmp_agent = dict(
                snmp_agent_ref=snmp.get('snmp_agent', ''),
                snmp_location=snmp.get('snmp_location', ''))
            
            snmp_agent.update(
                snmp_interface=add_snmp(
                    interfaces,
                    snmp.get('snmp_interface', [])))
    
        try:
            engine = super(FirewallCluster, cls)._create(
                name=name,
                node_type='firewall_node',
                physical_interfaces=physical_interfaces,
                domain_server_address=domain_server_address,
                log_server_ref=log_server_ref,
                location_ref=location_ref,
                nodes=nodes, enable_antivirus=enable_antivirus,
                default_nat=default_nat,
                snmp_agent=snmp_agent if snmp else None,
                comment=comment, **extra_opts if extra_opts else {})
            engine.update(cluster_mode=cluster_mode)
            
            return ElementCreator(cls, json=engine)
    
        except (ElementNotFound, CreateElementFailed) as e:
            raise CreateEngineFailed(e)
   
    @classmethod
    def create(cls, name, cluster_virtual, network_value, macaddress,
               interface_id, nodes, vlan_id=None, cluster_mode='balancing',
               backup_mgt=None, primary_heartbeat=None, log_server_ref=None,
               domain_server_address=None, location_ref=None, zone_ref=None,
               default_nat=False, enable_antivirus=False,
               comment=None, snmp=None, extra_opts=None, **kw):
        """
        Create a layer 3 firewall cluster with management interface and any number
        of nodes. If providing keyword arguments to create additional interfaces,
        use the same constructor arguments and pass an `interfaces` keyword argument.
        The constructor defined interface will be assigned as the primary
        management interface by default. Otherwise the engine will be created with a
        single interface and interfaces can be added after.
        
        .. versionchanged:: 0.6.1
            Chgnged `cluster_nic` to `interface_id`, and `cluster_mask` to `network_value`
        
        :param str name: name of firewall engine
        :param str cluster_virtual: ip of cluster CVI
        :param str network_value: ip netmask of cluster CVI
        :param str macaddress: macaddress for packet dispatch clustering
        :param str interface_id: nic id to use for primary interface
        :param list nodes: address/network_value/nodeid combination for cluster nodes
        :param str vlan_id: optional VLAN id for the management interface, i.e. '15'.
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
        :param list interfaces: optional keyword to supply additional interfaces
        :param dict snmp: SNMP dict should have keys `snmp_agent` str defining name of SNMPAgent,
            `snmp_interface` which is a list of interface IDs, and optionally `snmp_location` which
            is a string with the SNMP location name.
        :param dict extra_opts: extra options as a dict to be passed to the top level engine
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
               {'interface_id': 1,
                'macaddress': '02:02:02:02:02:03',
                'interfaces': [{'cluster_virtual': '2.2.2.1',
                                'network_value': '2.2.2.0/24',
                                'nodes':[{'address': '2.2.2.2', 'network_value': '2.2.2.0/24', 'nodeid': 1},
                                         {'address': '2.2.2.3', 'network_value': '2.2.2.0/24', 'nodeid': 2}]
                              }]
                },
               {'interface_id': 2,
                'interfaces': [{'nodes':[{'address': '3.3.3.2', 'network_value': '3.3.3.0/24', 'nodeid': 1},
                                         {'address': '3.3.3.3', 'network_value': '3.3.3.0/24', 'nodeid': 2}]
                              }]
                }]
        
        It is also possible to define VLAN interfaces by providing the `vlan_id` keyword.
        Example VLAN with NDI only interfaces. If nesting the zone_ref within the interfaces
        list, the zone will be applied to the VLAN versus the top level interface::
        
            interfaces=[
               {'interface_id': 2,
                'interfaces': [{'nodes':[{'address': '3.3.3.2', 'network_value': '3.3.3.0/24', 'nodeid': 1},
                                         {'address': '3.3.3.3', 'network_value': '3.3.3.0/24', 'nodeid': 2}],
                                'vlan_id': 22,
                                'zone_ref': 'private-network'
                              },
                              {'nodes': [{'address': '4.4.4.1', 'network_value': '4.4.4.0/24', 'nodeid': 1},
                                         {'address': '4.4.4.2', 'network_value': '4.4.4.0/24', 'nodeid': 2}],
                               'vlan_id': 23,
                               'zone_ref': 'other_vlan'
                            }]
            }]
        
        Tunnel interfaces can also be created. As all interfaces defined are assumed to be
        a physical interface type, you must specify the `type` parameter to indicate the
        interface is a tunnel interface. Tunnel interfaces do not have a macaddress or VLANs.
        They be configured with NDI interfaces by omitting the `cluster_virtual` and
        `network_value` top level attributes::
        
            interfaces=[
                {'interface_id': 1000,
                 'interfaces': [{'cluster_virtual': '100.100.100.1',
                                 'network_value': '100.100.100.0/24',
                                 'nodes':[{'address': '100.100.100.2', 'network_value': '100.100.100.0/24', 'nodeid': 1},
                                          {'address': '100.100.100.3', 'network_value': '100.100.100.0/24', 'nodeid': 2}]
                               }],
                 'zone_ref': 'AWStunnel',
                 'type': 'tunnel_interface'
                }]
        
        If setting primary_heartbeat or backup_mgt to a specific interface (the primary
        interface configured in the constructor will have these roles by default), you
        must define the interfaces in the `interfaces` keyword argument list.
           
        .. note:: If creating additional interfaces, you must at minimum provide the
            `interface_id` and `nodes` to create an NDI only interface.
                                
        """
        interfaces = kw.pop('interfaces', [])
        # Add the primary interface to the interface list
        interface = {'cluster_virtual': cluster_virtual,
                     'network_value': network_value,
                     'nodes': nodes}
        if vlan_id:
            interface.update(vlan_id=vlan_id)
        
        interfaces.append(dict(
            interface_id=interface_id,
            macaddress=macaddress,
            zone_ref=zone_ref,
            interfaces=[interface]))
        
        primary_mgt = interface_id if not vlan_id else '{}.{}'.format(interface_id, vlan_id)
        
        return FirewallCluster.create_bulk(
            name, interfaces=interfaces, nodes=len(nodes),
            cluster_mode=cluster_mode, primary_mgt=primary_mgt,
            backup_mgt=backup_mgt, primary_heartbeat=primary_heartbeat, 
            log_server_ref=log_server_ref,
            domain_server_address=domain_server_address,
            location_ref=location_ref, default_nat=default_nat,
            enable_antivirus=enable_antivirus,
            comment=comment, snmp=snmp, **extra_opts if extra_opts else {})
 
       
class MasterEngine(Engine):
    """
    Creates a master engine in a firewall role. Layer3VirtualEngine should be used
    to add each individual instance to the Master Engine.
    """
    typeof = 'master_engine'

    @classmethod
    def create(cls, name, master_type, mgmt_ip, mgmt_network,
               mgmt_interface=0,
               log_server_ref=None, zone_ref=None,
               domain_server_address=None,
               enable_antivirus=False, comment=None, extra_opts=None, **kw):
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
        :param dict extra_opts: extra options as a dict to be passed to the top level engine
        :raises CreateEngineFailed: Failure to create with reason
        :return: :py:class:`smc.core.engine.Engine`
        """
        interface = {'interface_id': mgmt_interface,
                     'interfaces': [{'nodes': [{'address': mgmt_ip, 'network_value': mgmt_network}]}],
                     'zone_ref': zone_ref, 'comment': comment}
        
        interface = Layer3PhysicalInterface(primary_mgt=mgmt_interface,
            primary_heartbeat=mgmt_interface, **interface)
        
        engine = super(MasterEngine, cls)._create(
            name=name,
            node_type='master_node',
            physical_interfaces=[{'physical_interface':interface}],
            domain_server_address=domain_server_address,
            log_server_ref=log_server_ref,
            nodes=1, enable_antivirus=enable_antivirus,
            comment=comment, **extra_opts if extra_opts else {})

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
    def create(cls, name, master_type, macaddress, nodes, mgmt_interface=0,
        log_server_ref=None, domain_server_address=None,
        enable_antivirus=False, comment=None, extra_opts=None, **kw):
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
        :param dict extra_opts: extra options as a dict to be passed to the top level engine
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
        primary_mgt = primary_heartbeat = mgmt_interface
        
        interface = {'interface_id': mgmt_interface,
                     'interfaces': [{
                         'nodes': nodes
                         }],
                     'macaddress': macaddress,
                     }
        
        interface = Layer3PhysicalInterface(primary_mgt=primary_mgt,
            primary_heartbeat=primary_heartbeat, **interface)

        engine = super(MasterEngineCluster, cls)._create(
            name=name,
            node_type='master_node',
            physical_interfaces=[{'physical_interface': interface}],
            domain_server_address=domain_server_address,
            log_server_ref=log_server_ref,
            nodes=len(nodes), enable_antivirus=enable_antivirus,
            comment=comment, **extra_opts if extra_opts else {})

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
            for if_def in interface.get('interfaces', []):
                _interface_id = None
                if 'vlan_id' in if_def:
                    _interface_id = '{}.{}'.format(
                        interface_id, if_def['vlan_id'])
                else:
                    _interface_id = interface_id
                if _interface_id in interfaces and 'type' not in interface:
                    for node in if_def.get('nodes', []):
                        snmp_interface.append(
                            {'address': node.get('address'),
                             'nicid': _interface_id})
    return snmp_interface
