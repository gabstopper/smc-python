import smc.actions.search as search
from smc.core.interfaces import _interface_helper, InterfaceBuilder
from smc.core.engine import Engine
from smc.api.exceptions import CreateEngineFailed
from smc.base.model import prepared_request
from smc.elements.helpers import logical_intf_helper
from smc.core.sub_interfaces import LoopbackInterface


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

    def __init__(self, name, **meta):
        super(Layer3Firewall, self).__init__(name, **meta)
        pass

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
               ospf_profile=None):
        """ 
        Create a single layer 3 firewall with management interface and DNS

        :param str name: name of firewall engine
        :param str mgmt_ip: ip address of management interface
        :param str mgmt_network: management network in cidr format
        :param str log_server_ref: (optional) href to log_server instance for fw
        :param int mgmt_interface: (optional) interface for management from SMC to fw
        :param list domain_server_address: (optional) DNS server addresses
        :param str zone_ref: (optional) zone name for management interface (created if not found)
        :param bool reverse_connection: should the NGFW be the mgmt initiator (used when behind NAT)
        :param bool default_nat: (optional) Whether to enable default NAT for outbound
        :param bool enable_antivirus: (optional) Enable antivirus (required DNS)
        :param bool enable_gti: (optional) Enable GTI
        :param bool sidewinder_proxy_enabled: Enable Sidewinder proxy functionality
        :param str location_ref: location href for engine if needed to contact SMC behind NAT
        :param bool enable_ospf: whether to turn OSPF on within engine
        :param str ospf_profile: optional OSPF profile to use on engine, by ref   
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
        builder.zone_ref = zone_ref

        engine = super(Layer3Firewall, cls)._create(
            name=name,
            node_type='firewall_node',
            physical_interfaces=[{'physical_interface': builder.data}],
            domain_server_address=domain_server_address,
            log_server_ref=log_server_ref,
            nodes=1, enable_gti=enable_gti,
            enable_antivirus=enable_antivirus,
            sidewinder_proxy_enabled=sidewinder_proxy_enabled,
            default_nat=default_nat,
            location_ref=location_ref,
            enable_ospf=enable_ospf,
            ospf_profile=ospf_profile)

        href = search.element_entry_point('single_fw')
        result = prepared_request(href=href, json=engine).create()
        if result.href:
            return Engine(name=name,
                          href=result.href,
                          type='single_fw')
        else:
            raise CreateEngineFailed('Could not create the engine, '
                                     'reason: {}.'
                                     .format(result.msg, engine))

    @classmethod
    def create_dynamic(cls, name, interface_id,
                       dynamic_index=1,
                       primary_mgt=True,
                       reverse_connection=True,
                       automatic_default_route=True,
                       loopback_ndi='127.0.0.1',
                       loopback_ndi_network='127.0.0.1/32',
                       location_ref=None,
                       log_server_ref=None,
                       zone_ref=None,
                       enable_gti=False,
                       enable_antivirus=False,
                       sidewinder_proxy_enabled=False,
                       default_nat=False):
        """
        Create a single layer 3 firewall with only a DHCP interface. Useful
        when creating virtualized FW's such as in Microsoft Azure.
        """
        builder = InterfaceBuilder()
        builder.interface_id = interface_id
        builder.add_dhcp(dynamic_index, is_mgmt=primary_mgt)
        builder.zone_ref = zone_ref
        
        loopback = LoopbackInterface.create(
            address=loopback_ndi, 
            network_value=loopback_ndi_network, 
            nodeid=1, 
            auth_request=True, 
            rank=1)
        
        engine = super(Layer3Firewall, cls)._create(
            name=name,
            node_type='firewall_node',
            loopback_ndi=[loopback],
            physical_interfaces=[{'physical_interface': builder.data}],
            log_server_ref=log_server_ref,
            nodes=1, enable_gti=enable_gti,
            enable_antivirus=enable_antivirus,
            sidewinder_proxy_enabled=sidewinder_proxy_enabled,
            default_nat=default_nat,
            location_ref=location_ref)
    
        href = search.element_entry_point('single_fw')
        result = prepared_request(href=href, json=engine).create()
        if result.href:
            return Engine(name=name,
                          href=result.href,
                          type='single_fw')
        else:
            raise CreateEngineFailed('Could not create the engine, '
                                     'reason: {}.'
                                     .format(result.msg, engine))
        
class Layer2Firewall(Engine):
    """
    Creates a Layer 2 Firewall with a default inline interface pair
    To instantiate and create, call 'create' classmethod as follows::

        engine = Layer2Firewall.create(name='myinline', 
                                       mgmt_ip='1.1.1.1', 
                                       mgmt_network='1.1.1.0/24')
    """
    typeof = 'single_layer2'

    def __init__(self, name, **meta):
        super(Layer2Firewall, self).__init__(name, **meta)
        pass

    @classmethod
    def create(cls, name, mgmt_ip, mgmt_network,
               mgmt_interface=0,
               inline_interface='1-2',
               logical_interface='default_eth',
               log_server_ref=None,
               domain_server_address=None, zone_ref=None,
               enable_antivirus=False, enable_gti=False):
        """ 
        Create a single layer 2 firewall with management interface and inline pair

        :param str name: name of firewall engine
        :param str mgmt_ip: ip address of management interface
        :param str mgmt_network: management network in cidr format
        :param int mgmt_interface: (optional) interface for management from SMC to fw
        :param str inline_interface: interfaces to use for first inline pair
        :param str logical_interface: (optional) logical_interface reference
        :param str log_server_ref: (optional) href to log_server instance 
        :param list domain_server_address: (optional) DNS server addresses
        :param str zone_ref: (optional) zone name for management interface (created if not found)
        :param bool enable_antivirus: (optional) Enable antivirus (required DNS)
        :param bool enable_gti: (optional) Enable GTI
        :raises CreateEngineFailed: Failure to create with reason
        :return: :py:class:`smc.core.engine.Engine`
        """
        interfaces = []

        mgmt = InterfaceBuilder()
        mgmt.interface_id = mgmt_interface
        mgmt.add_ndi_only(mgmt_ip, mgmt_network, is_mgmt=True)
        mgmt.zone_ref = zone_ref

        intf_href = logical_intf_helper(logical_interface)

        inline = InterfaceBuilder()
        inline.interface_id = inline_interface.split('-')[0]
        inline.add_inline(inline_interface, logical_interface_ref=intf_href)

        interfaces.append({'physical_interface': mgmt.data})
        interfaces.append({'physical_interface': inline.data})

        engine = super(Layer2Firewall, cls)._create(
            name=name,
            node_type='fwlayer2_node',
            physical_interfaces=interfaces,
            domain_server_address=domain_server_address,
            log_server_ref=log_server_ref,
            nodes=1, enable_gti=enable_gti,
            enable_antivirus=enable_antivirus)

        href = search.element_entry_point('single_layer2')
        result = prepared_request(href=href,
                                  json=engine).create()
        if result.href:
            return Engine(name=name,
                          href=result.href,
                          type='single_layer2')
        else:
            raise CreateEngineFailed('Could not create the engine, reason: {}'
                                     .format(result.msg))


class IPS(Engine):
    """
    Creates an IPS engine with a default inline interface pair
    """
    typeof = 'single_ips'

    def __init__(self, name, **meta):
        super(IPS, self).__init__(name, **meta)
        pass

    @classmethod
    def create(cls, name, mgmt_ip, mgmt_network,
               mgmt_interface='0',
               inline_interface='1-2',
               logical_interface='default_eth',
               log_server_ref=None,
               domain_server_address=None, zone_ref=None,
               enable_antivirus=False, enable_gti=False):
        """ 
        Create a single IPS engine with management interface and inline pair

        :param str name: name of ips engine
        :param str mgmt_ip: ip address of management interface
        :param str mgmt_network: management network in cidr format
        :param int mgmt_interface: (optional) interface for management from SMC to fw
        :param str inline_interface: interfaces to use for first inline pair
        :param str logical_interface: (optional) logical_interface reference
        :param str log_server_ref: (optional) href to log_server instance 
        :param list domain_server_address: (optional) DNS server addresses
        :param str zone_ref: (optional) zone name for management interface (created if not found)
        :param bool enable_antivirus: (optional) Enable antivirus (required DNS)
        :param bool enable_gti: (optional) Enable GTI
        :raises CreateEngineFailed: Failure to create with reason
        :return: :py:class:`smc.core.engine.Engine`
        """
        interfaces = []

        mgmt = InterfaceBuilder()
        mgmt.interface_id = mgmt_interface
        mgmt.add_ndi_only(mgmt_ip, mgmt_network, is_mgmt=True)
        mgmt.zone_ref = zone_ref

        intf_href = logical_intf_helper(logical_interface)

        inline = InterfaceBuilder()
        inline.interface_id = inline_interface.split('-')[0]
        inline.add_inline(inline_interface, logical_interface_ref=intf_href)

        interfaces.append({'physical_interface': mgmt.data})
        interfaces.append({'physical_interface': inline.data})

        engine = super(IPS, cls)._create(
            name=name,
            node_type='ips_node',
            physical_interfaces=interfaces,
            domain_server_address=domain_server_address,
            log_server_ref=log_server_ref,
            nodes=1, enable_gti=enable_gti,
            enable_antivirus=enable_antivirus)

        href = search.element_entry_point('single_ips')
        result = prepared_request(href=href,
                                  json=engine).create()
        if result.href:
            return Engine(name=name,
                          href=result.href,
                          type='single_ips')
        else:
            raise CreateEngineFailed('Could not create the engine, reason: {}'
                                     .format(result.msg))


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

    def __init__(self, name, **meta):
        super(Layer3VirtualEngine, self).__init__(name, **meta)
        pass

    @classmethod
    def create(cls, name, master_engine, virtual_resource,
               interfaces, default_nat=False, outgoing_intf=0,
               domain_server_address=None, enable_ospf=False,
               ospf_profile=None, **kwargs):
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
                #intf = _interface_helper(physical.data)
                intf = _interface_helper(builder.data)
                intf.outgoing = True
                intf.auth_request = True

            # new_interfaces.append(physical())
            new_interfaces.append({'virtual_physical_interface': builder.data})

            engine = super(Layer3VirtualEngine, cls)._create(
                name=name,
                node_type='virtual_fw_node',
                physical_interfaces=new_interfaces,
                domain_server_address=domain_server_address,
                log_server_ref=None,  # Isn't used in VE
                nodes=1, default_nat=default_nat,
                enable_ospf=enable_ospf,
                ospf_profile=ospf_profile)

            engine.update(virtual_resource=virt_resource_href)
            # Master Engine provides this service
            engine.pop('log_server_ref', None)

        href = search.element_entry_point('virtual_fw')
        result = prepared_request(href=href, json=engine).create()
        if result.href:
            return Engine(name=name,
                          href=result.href,
                          type='virtual_fw')
        else:
            raise CreateEngineFailed('Could not create the virtual engine, '
                                     'reason: {}'
                                     .format(result.msg))


class FirewallCluster(Engine):
    """ 
    Firewall Cluster
    Creates a layer 3 firewall cluster engine with CVI and NDI's. Once engine is 
    created, and in context, add additional interfaces using engine.physical_interface

    Reference: 
    :func:`smc.core.interfaces.PhysicalInterface.add_cluster_virtual_interface`
    """
    typeof = 'fw_cluster'

    def __init__(self, name, **meta):
        super(FirewallCluster, self).__init__(name, **meta)
        pass

    @classmethod
    def create(cls, name, cluster_virtual, cluster_mask,
               macaddress, cluster_nic, nodes,
               log_server_ref=None,
               domain_server_address=None,
               zone_ref=None, default_nat=False,
               enable_antivirus=False, enable_gti=False):
        """
         Create a layer 3 firewall cluster with management interface and any number
         of nodes

        :param str name: name of firewall engine
        :param cluster_virtual: ip of cluster CVI
        :param cluster_mask: ip netmask of cluster CVI
        :param macaddress: macaddress for packet dispatch clustering
        :param cluster_nic: nic id to use for primary interface
        :param list nodes: address/network_value/nodeid combination for cluster nodes  
        :param str log_server_ref: (optional) href to log_server instance 
        :param list domain_server_address: (optional) DNS server addresses
        :param str zone_ref: (optional) zone name for management interface (created if not found)
        :param bool enable_antivirus: (optional) Enable antivirus (required DNS)
        :param bool enable_gti: (optional) Enable GTI
        :raises CreateEngineFailed: Failure to create with reason
        :return: :py:class:`smc.core.engine.Engine`

        Example nodes parameter input::

            [{'address':'5.5.5.2', 'network_value':'5.5.5.0/24', 'nodeid':1},
             {'address':'5.5.5.3', 'network_value':'5.5.5.0/24', 'nodeid':2},
             {'address':'5.5.5.4', 'network_value':'5.5.5.0/24', 'nodeid':3}]

        """
        builder = InterfaceBuilder()
        builder.interface_id = cluster_nic
        builder.macaddress = macaddress
        builder.cvi_mode = 'packetdispatch'
        builder.zone_ref = zone_ref
        builder.add_cvi_only(cluster_virtual, cluster_mask, is_mgmt=True)
        for node in nodes:
            node.update(is_mgmt=True)
            builder.add_ndi_only(**node)

        engine = super(FirewallCluster, cls)._create(
            name=name,
            node_type='firewall_node',
            physical_interfaces=[{'physical_interface': builder.data}],
            domain_server_address=domain_server_address,
            log_server_ref=log_server_ref,
            nodes=len(nodes), enable_gti=enable_gti,
            enable_antivirus=enable_antivirus,
            default_nat=default_nat)

        href = search.element_entry_point('fw_cluster')
        result = prepared_request(href=href,
                                  json=engine).create()
        if result.href:
            return Engine(name=name,
                          href=result.href,
                          type='fw_cluster')
        else:
            raise CreateEngineFailed('Could not create the firewall, '
                                     'reason: {}'
                                     .format(result.msg))


class MasterEngine(Engine):
    """
    Creates a master engine in a firewall role. Layer3VirtualEngine should be used
    to add each individual instance to the Master Engine.
    """
    typeof = 'master_engine'

    def __init__(self, name, **meta):
        super(MasterEngine, self).__init__(name, **meta)
        pass

    @classmethod
    def create(cls, name, master_type, mgmt_ip, mgmt_network,
               mgmt_interface=0,
               log_server_ref=None,
               domain_server_address=None, enable_gti=False,
               enable_antivirus=False):
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
            enable_antivirus=enable_antivirus)

        engine.update(master_type=master_type,
                      cluster_mode='standby')

        href = search.element_entry_point('master_engine')
        result = prepared_request(href=href,
                                  json=engine).create()
        if result.href:
            return Engine(name=name,
                          href=result.href,
                          type='master_engine')
        else:
            raise CreateEngineFailed('Could not create the engine, '
                                     'reason: {}'
                                     .format(result.msg))


class MasterEngineCluster(Engine):
    """
    Master Engine Cluster
    Clusters are currently supported in an active/standby configuration
    only. 
    """

    def __init__(self, name, **meta):
        super(MasterEngineCluster, self).__init__(name, **meta)
        pass

    @classmethod
    def create(cls, name, master_type, macaddress,
               nodes, mgmt_interface=0, log_server_ref=None,
               domain_server_address=None,
               enable_gti=False,
               enable_antivirus=False):
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
            enable_antivirus=enable_antivirus)

        engine.update(master_type=master_type,
                      cluster_mode='standby')

        href = search.element_entry_point('master_engine')
        result = prepared_request(href=href,
                                  json=engine).create()
        if result.href:
            return Engine(name=name,
                          href=result.href,
                          type='master_engine')
        else:
            raise CreateEngineFailed('Could not create the engine, '
                                     'reason: {}'
                                     .format(result.msg))
