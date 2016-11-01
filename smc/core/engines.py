import smc.actions.search as search
from smc.core.interfaces import PhysicalInterface, VirtualPhysicalInterface
from smc.core.engine import Engine
from smc.api.exceptions import CreateEngineFailed
from smc.api.common import SMCRequest

class Layer3Firewall(object):
    """
    Represents a Layer 3 Firewall configuration.
    To instantiate and create, call 'create' classmethod as follows::
    
        engine = Layer3Firewall.create(name='mylayer3', 
                                       mgmt_ip='1.1.1.1', 
                                       mgmt_network='1.1.1.0/24')
                                       
    Set additional constructor values as necessary.       
    """ 
    node_type = 'firewall_node'
    
    def __init__(self, name):
        pass

    @classmethod
    def create(cls, name, mgmt_ip, mgmt_network, 
               log_server_ref=None,
               mgmt_interface=0, 
               default_nat=False,
               reverse_connection=False,
               domain_server_address=None, zone_ref=None,
               enable_antivirus=False, enable_gti=False,
               location_ref=None, enable_ospf=False, 
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
        :param boolean reverse_connection: should the NGFW be the mgmt initiator (used when behind NAT)
        :param boolean default_nat: (optional) Whether to enable default NAT for outbound
        :param boolean enable_antivirus: (optional) Enable antivirus (required DNS)
        :param boolean enable_gti: (optional) Enable GTI
        :param str location_ref: location href for engine if needed to contact SMC behind NAT
        :param boolean enable_ospf: whether to turn OSPF on within engine
        :param str ospf_profile: optional OSPF profile to use on engine, by ref   
        :return: :py:class:`smc.core.engine.Engine`
        :raises: :py:class:`smc.api.exceptions.CreateEngineFailed`: Failure to create with reason
        """
        physical = PhysicalInterface()
        physical.add_single_node_interface(mgmt_interface,
                                           mgmt_ip, 
                                           mgmt_network,
                                           is_mgmt=True,
                                           reverse_connection=reverse_connection,
                                           zone_ref=zone_ref)

        engine = Engine.create(name=name,
                               node_type=cls.node_type,
                               physical_interfaces=[
                                    {PhysicalInterface.typeof: physical.data}], 
                               domain_server_address=domain_server_address,
                               log_server_ref=log_server_ref,
                               nodes=1, enable_gti=enable_gti,
                               enable_antivirus=enable_antivirus,
                               default_nat=default_nat,
                               location_ref=location_ref,
                               enable_ospf=enable_ospf,
                               ospf_profile=ospf_profile)

        href = search.element_entry_point('single_fw')
        result = SMCRequest(href=href, json=engine).create()
        if result.href:
            return Engine(name).load()
        else:
            raise CreateEngineFailed('Could not create the engine, '
                                     'reason: {}'
                                     .format(result.msg))

class Layer2Firewall(object):
    """
    Creates a Layer 2 Firewall with a default inline interface pair
    """
    node_type = 'fwlayer2_node'
    
    def __init__(self, name):
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
        :param boolean enable_antivirus: (optional) Enable antivirus (required DNS)
        :param boolean enable_gti: (optional) Enable GTI
        :return: :py:class:`smc.core.engine.Engine`
        :raises: :py:class:`smc.api.exceptions.CreateEngineFailed`: Failure to create with reason
        """
        interfaces = [] 
        physical = PhysicalInterface()
        physical.add_node_interface(mgmt_interface,
                                    mgmt_ip, mgmt_network, 
                                    is_mgmt=True,
                                    zone_ref=zone_ref)
        
        intf_href = search.element_href_use_filter(logical_interface, 'logical_interface')
        
        inline = PhysicalInterface()
        inline.add_inline_interface(inline_interface, intf_href)
        interfaces.append({PhysicalInterface.typeof: physical.data})
        interfaces.append({PhysicalInterface.typeof: inline.data})    
        
        engine = Engine.create(name=name,
                               node_type=cls.node_type,
                               physical_interfaces=interfaces, 
                               domain_server_address=domain_server_address,
                               log_server_ref=log_server_ref,
                               nodes=1, enable_gti=enable_gti,
                               enable_antivirus=enable_antivirus)
       
        href = search.element_entry_point('single_layer2')
        result = SMCRequest(href=href, 
                            json=engine).create()
        if result.href:
            return Engine(name).load()
        else:
            raise CreateEngineFailed('Could not create the engine, '
                                     'reason: {}'
                                     .format(result.msg))   

class IPS(object):
    """
    Creates an IPS engine with a default inline interface pair
    """
    node_type = 'ips_node'
    
    def __init__(self, name):
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
        :param boolean enable_antivirus: (optional) Enable antivirus (required DNS)
        :param boolean enable_gti: (optional) Enable GTI
        :return: :py:class:`smc.core.engine.Engine`
        :raises: :py:class:`smc.api.exceptions.CreateEngineFailed`: Failure to create with reason
        """
        interfaces = []
        physical = PhysicalInterface()
        physical.add_node_interface(mgmt_interface,
                                    mgmt_ip, mgmt_network, 
                                    is_mgmt=True,
                                    zone_ref=zone_ref)
              
        intf_href = search.element_href_use_filter(logical_interface, 'logical_interface')
      
        inline = PhysicalInterface()
        inline.add_inline_interface(inline_interface, intf_href)
        interfaces.append({PhysicalInterface.typeof: physical.data})
        interfaces.append({PhysicalInterface.typeof: inline.data}) 
        
        engine = Engine.create(name=name,
                               node_type=cls.node_type,
                               physical_interfaces=interfaces, 
                               domain_server_address=domain_server_address,
                               log_server_ref=log_server_ref,
                               nodes=1, enable_gti=enable_gti,
                               enable_antivirus=enable_antivirus)
        
        href = search.element_entry_point('single_ips')
        result = SMCRequest(href=href, 
                            json=engine).create()
        if result.href:
            return Engine(name).load()
        else:
            raise CreateEngineFailed('Could not create the engine, '
                                     'reason: {}'
                                     .format(result.msg))
        
class Layer3VirtualEngine(object):
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
    node_type = 'virtual_fw_node'
    
    def __init__(self, name):
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
        :param boolean default_nat: Whether to enable default NAT for outbound
        :param int outgoing_intf: outgoing interface for VE. Specifies interface number
        :param list interfaces: interfaces mappings passed in
        :param boolean enable_ospf: whether to turn OSPF on within engine
        :param str ospf_profile: optional OSPF profile to use on engine, by ref   
        :return: :py:class:`smc.core.engine.Engine`
        :raises: :py:class:`smc.api.exceptions.CreateEngineFailed`: Failure to create with reason
        """
        virt_resource_href = None #need virtual resource reference
        master_engine = Engine(master_engine).load()
        for virt_resource in master_engine.virtual_resource.all():
            if virt_resource.name == virtual_resource:
                virt_resource_href = virt_resource.href
                break
        if not virt_resource_href:
            raise CreateEngineFailed('Cannot find associated virtual resource for '
                                      'VE named: {}. You must first create a virtual '
                                      'resource for the master engine before you can associate '
                                      'a virtual engine. Cannot add VE'.format(name))
        new_interfaces=[]   
        for interface in interfaces:       
            physical = VirtualPhysicalInterface()
            physical.add_single_node_interface(interface.get('interface_id'),
                                               interface.get('address'),
                                               interface.get('network_value'),
                                               zone_ref=interface.get('zone_ref'))

            #set auth request and outgoing on one of the interfaces
            if interface.get('interface_id') == outgoing_intf:
                physical.modify_attribute(outgoing=True,
                                          auth_request=True)
            new_interfaces.append({VirtualPhysicalInterface.typeof: physical.data})
           
            engine = Engine.create(name=name,
                               node_type=cls.node_type,
                               physical_interfaces=new_interfaces, 
                               domain_server_address=domain_server_address,
                               log_server_ref=None, #Isn't used in VE
                               nodes=1, default_nat=default_nat,
                               enable_ospf=enable_ospf,
                               ospf_profile=ospf_profile)

            engine.update(virtual_resource=virt_resource_href)
            engine.pop('log_server_ref', None) #Master Engine provides this service
        
        
        href = search.element_entry_point('virtual_fw')
        result = SMCRequest(href=href, json=engine).create()
        if result.href:
            return Engine(name).load()
        else:
            raise CreateEngineFailed('Could not create the virtual engine, '
                                     'reason: {}'
                                     .format(result.msg))
            
class FirewallCluster(object):
    """ 
    Firewall Cluster
    Creates a layer 3 firewall cluster engine with CVI and NDI's. Once engine is 
    created, and in context, add additional interfaces using engine.physical_interface
    
    Reference: 
    :func:`smc.core.interfaces.PhysicalInterface.add_cluster_virtual_interface`
    """
    node_type = 'firewall_node'  

    def __init__(self, name):
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
        :param nodes: address/network_value/nodeid combination for cluster nodes  
        :param str log_server_ref: (optional) href to log_server instance 
        :param list domain_server_address: (optional) DNS server addresses
        :param str zone_ref: (optional) zone name for management interface (created if not found)
        :param boolean enable_antivirus: (optional) Enable antivirus (required DNS)
        :param boolean enable_gti: (optional) Enable GTI
        :return: :py:class:`smc.core.engine.Engine`
        :raises: :py:class:`smc.api.exceptions.CreateEngineFailed`: Failure to create with reason
        
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
        physical = PhysicalInterface()
        physical.add_cluster_virtual_interface(cluster_nic,
                                               cluster_virtual, 
                                               cluster_mask,
                                               macaddress, 
                                               nodes, 
                                               is_mgmt=True,
                                               zone_ref=zone_ref)
        
        engine = Engine.create(name=name,
                               node_type=cls.node_type,
                               physical_interfaces=[
                                        {PhysicalInterface.typeof: physical.data}], 
                               domain_server_address=domain_server_address,
                               log_server_ref=log_server_ref,
                               nodes=len(nodes), enable_gti=enable_gti,
                               enable_antivirus=enable_antivirus,
                               default_nat=default_nat)

        href = search.element_entry_point('fw_cluster')
        result = SMCRequest(href=href,
                            json=engine).create()
        if result.href:
            return Engine(name).load()
        else:
            raise CreateEngineFailed('Could not create the firewall, '
                                     'reason: {}'
                                     .format(result.msg))
        
class MasterEngine(object):
    """
    Creates a master engine in a firewall role. Layer3VirtualEngine should be used
    to add each individual instance to the Master Engine.
    """
    node_type = 'master_node'
    
    def __init__(self, name):
        pass
    
    @classmethod
    def create(cls, name, master_type, mgmt_ip, mgmt_netmask,
               mgmt_interface=0, 
               log_server_ref=None, 
               domain_server_address=None, enable_gti=False,
               enable_antivirus=False):
        """
         Create a Master Engine with management interface
        
        :param str name: name of master engine engine
        :param str master_type: firewall|
        :param str log_server_ref: (optional) href to log_server instance 
        :param list domain_server_address: (optional) DNS server addresses
        :param boolean enable_antivirus: (optional) Enable antivirus (required DNS)
        :param boolean enable_gti: (optional) Enable GTI
        :return: :py:class:`smc.core.engine.Engine`
        :raises: :py:class:`smc.api.exceptions.CreateEngineFailed`: Failure to create with reason
        """             
        physical = PhysicalInterface()
        physical.add_node_interface(mgmt_interface, 
                                    mgmt_ip, mgmt_netmask)
        physical.modify_attribute(primary_mgt=True,
                                  primary_heartbeat=True,
                                  outgoing=True)
        
        engine = Engine.create(name=name,
                               node_type=cls.node_type,
                               physical_interfaces=[
                                        {PhysicalInterface.typeof: physical.data}], 
                               domain_server_address=domain_server_address,
                               log_server_ref=log_server_ref,
                               nodes=1, enable_gti=enable_gti,
                               enable_antivirus=enable_antivirus)      
        engine.setdefault('master_type', master_type)
        engine.setdefault('cluster_mode', 'balancing')

        href = search.element_entry_point('master_engine')
        result = SMCRequest(href=href, 
                            json=engine).create()
        if result.href:
            return Engine(name).load()
        else:
            raise CreateEngineFailed('Could not create the engine, '
                                     'reason: {}'
                                     .format(result.msg))

'''
class AWSLayer3Firewall(object):
    """
    Create AWSLayer3Firewall in SMC. This is a Layer3Firewall instance that uses
    a DHCP address for the management interface. Management is expected to be
    on interface 0 and interface eth0 on the AWS AMI. 
    When a Layer3Firewall uses a DHCP interface for management, a second interface
    is required to be the interface for Auth Requests. This second interface information
    is obtained by creating the network interface through the AWS SDK, and feeding that
    to the constructor. This can be statically assigned as well.
    """
    node_type = 'firewall_node'
    
    def __init__(self, name):
        pass
        
    @classmethod
    def create(cls, name, interfaces,
               dynamic_interface=0,
               dynamic_index=1, 
               log_server_ref=None, 
               domain_server_address=None,
               default_nat = True, 
               zone_ref=None,
               is_mgmt=False):
        """ 
        Create AWS Layer 3 Firewall. This will implement a DHCP
        interface for dynamic connection back to SMC. The initial_contact
        information will be used as user-data to initialize the EC2 instance. 
        
        :param str name: name of fw in SMC
        :param list interfaces: dict items specifying interfaces to create
        :param int dynamic_index: dhcp interface index (First DHCP Interface, etc)
        :param int dynamic_interface: interface ID to use for dhcp
        :return Engine
        :raises: :py:class:`smc.api.exceptions.CreateEngineFailed`: Failure to create with reason
        Example interfaces::
            
            [{ 'address': '1.1.1.1', 
               'network_value': '1.1.1.0/24', 
               'interface_id': 1
             },
             { 'address': '2.2.2.2',
               'network_value': '2.2.2.0/24',
               'interface_id': 2
            }]   
        """
        new_interfaces = []

        dhcp_physical = PhysicalInterface()
        dhcp_physical.add_dhcp_interface(dynamic_interface,
                                         dynamic_index, primary_mgt=True)
        new_interfaces.append({PhysicalInterface.typeof: dhcp_physical.data})
        
        auth_request = 0
        for interface in interfaces:
            if interface.get('interface_id') == dynamic_interface:
                continue #In case this is defined, skip dhcp_interface id
            physical = PhysicalInterface()
            physical.add_single_node_interface(interface.get('interface_id'),
                                               interface.get('address'), 
                                               interface.get('network_value'))
            if not auth_request: #set this on first interface that is not the dhcp_interface
                physical.modify_attribute(auth_request=True)
                auth_request = 1
            new_interfaces.append({PhysicalInterface.typeof: physical.data})
        
        engine = Engine.create(name=name,
                               node_type=cls.node_type,
                               physical_interfaces=new_interfaces, 
                               domain_server_address=domain_server_address,
                               log_server_ref=log_server_ref,
                               nodes=1)    
        if default_nat:
            engine.setdefault('default_nat', True)
       
        href = search.element_entry_point('single_fw')
        result = SMCRequest(href=href, 
                            json=engine).create()
        if result.href:
            return Engine(name).load()
        else:
            raise CreateEngineFailed('Could not create the engine, '
                                     'reason: {}'.format(result.msg))
'''