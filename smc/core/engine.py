import smc.actions.search as search
from smc.compat import min_smc_version
from smc.elements.helpers import domain_helper
from smc.base.model import Meta, Element, prepared_request
from smc.base.util import find_link_by_name
from smc.api.exceptions import LoadEngineFailed, UnsupportedEngineFeature,\
    UnsupportedInterfaceType, TaskRunFailed, EngineCommandFailed,\
    SMCConnectionError, CertificateError
from smc.core.node import Node
from smc.core.resource import Alias, Snapshot, Routing, RouteTable
from smc.core.interfaces import PhysicalInterface, Interface,\
    VirtualPhysicalInterface, TunnelInterface, InterfaceEnum
from smc.administration.tasks import task_handler, Task
from smc.elements.other import prepare_blacklist
from smc.vpn.elements import VPNSite
from smc.api.common import SMCRequest

class Engine(Element):
    """
    Instance attributes:
    
    :ivar name: name of engine
    :ivar type: type of engine
    :ivar dict json: raw engine json
    :ivar href: href of the engine
    :ivar etag: current etag
    :ivar link: list link to engine resources
    
    Instance resources:
    
    :ivar list nodes: :py:class:`smc.core.node.Node` nodes associated with 
          this engine
    :ivar interface: :py:class:`smc.core.interfaces.Interface` interfaces 
          for this engine
    :ivar internal_gateway: :py:class:`~InternalGateway` engine 
          level VPN settings
    :ivar virtual_resource: :py:class:`smc.core.engine.VirtualResource` for engine, 
          only relavant to Master Engine
    :ivar physical_interface: :py:class:`smc.core.interfaces.PhysicalInterface` 
          access to physical interface settings
    :ivar tunnel_interface: :py:class:`smc.core.interfaces.TunnelInterface` 
          retrieve or create tunnel interfaces
    :ivar snapshots: :py:class:`smc.core.engine.Snapshot` engine level policy snapshots

    """
    def __init__(self, name, meta=None, **kwargs):
        self._name = name
        self.meta = meta
        
    @classmethod
    def create(cls, name, node_type, 
               physical_interfaces,
               nodes=1, log_server_ref=None, 
               domain_server_address=None,
               enable_antivirus=False, enable_gti=False,
               default_nat=False, location_ref=None,
               enable_ospf=None, ospf_profile=None):
        """
        Create will return the engine configuration as a dict that is a 
        representation of the engine. The creating class will also add 
        engine specific requirements before constructing the request
        and sending to SMC (which will serialize the dict to json).
        
        :param name: name of engine
        :param str node_type: comes from class attribute of engine type
        :param dict physical_interfaces: physical interface list of dict
        :param int nodes: number of nodes for engine
        :param str log_server_ref: href of log server
        :param list domain_server_address: dns addresses
        """
        node_list = []
        for nodeid in range(1, nodes+1): #start at nodeid=1
            node_list.append(Node.create(name, node_type, nodeid))
            
        domain_server_list = []
        if domain_server_address:
            rank_i = 0
            for entry in domain_server_address:
                domain_server_list.append(
                                    {"rank": rank_i, "value": entry})
        
        if not log_server_ref: #Set log server reference, if not explicitly set
            log_server_ref = search.get_first_log_server()
        
        base_cfg = {'name': name,
                    'nodes': node_list,
                    'domain_server_address': domain_server_list,
                    'log_server_ref': log_server_ref,
                    'physicalInterfaces': physical_interfaces}
        if enable_antivirus:
            antivirus = {'antivirus': {
                            'antivirus_enabled': True,
                            'antivirus_update': 'daily',
                            'virus_log_level': 'stored',
                            'virus_mirror': 'update.nai.com/Products/CommonUpdater'}}
            base_cfg.update(antivirus)
        if enable_gti:
            gti = {'gti_settings': {
                        'file_reputation_context': 'gti_cloud_only'}}
            base_cfg.update(gti)
        if default_nat:
            nat = {'default_nat': True}
            base_cfg.update(nat)
        if location_ref:
            location = {'location_ref': location_ref}
            base_cfg.update(location)
        if enable_ospf:
            if not ospf_profile: #get default profile
                ospf_profile = search.get_ospf_default_profile()
            ospf = {'dynamic_routing': {
                        'ospfv2': {
                            'enabled': True,
                            'ospfv2_profile_ref': ospf_profile}}}
            base_cfg.update(ospf)
        
        return base_cfg
          
    def load(self):
        """ 
        When engine is loaded, save the attributes that are needed. 
        Engine load can be called directly::
        
            engine = Engine('myengine').load()
            
        or load by calling collection.describe_xxx methods::
        
            for fw in describe_single_fws():
                if fw.name == 'myfw':
                    engine = fw.load()
                    
        Call this to reload settings, useful if changes are made and new 
        configuration references or updated attributes are needed.
        """
        try:
            if not self.meta:
                if not min_smc_version(6.1):
                    result = search.element_info_as_json(self.name)
                    if result and len(result) == 1:
                        self.meta = Meta(**result[0])
                        result = search.element_by_href_as_json(self.href)
                        if not result.get('nodes'):
                            raise LoadEngineFailed('Cannot load engine name: {}, please ensure the name ' 
                                                   'is correct. An element was returned but was of type: '
                                                   '{}'.format(self._name, self.meta.type))
                    else: #error
                        if result:
                            names = [name.get('name') for name in result 
                                     if name.get('name')]
                        else:
                            names = []
                        raise LoadEngineFailed('Cannot load engine name: {}, ensure the '
                                               'name is correct and that the engine exists. '
                                               'Search returned: {}'
                                               .format(self._name, names))
            self.cache
            return self    

        except LoadEngineFailed:
            raise

    @property
    def version(self):
        """
        Version of this engine
        """
        return self.cache[1].get('engine_version')
        
    @property
    def type(self):
        """
        Engine type
        """
        if not self.meta:
            self.load()    
        return self.meta.type
    
    def rename(self, name):
        """
        Rename the firewall engine, nodes, and internal gateway (vpn)

        :return: None
        """
        self.modify_attribute(name='{}'.format(name))
        self.internal_gateway.modify_attribute(name='{} Primary'\
                                               .format(name))
        for node in self.nodes:
            node.modify_attribute(name='{} node {}'.format(name, node.nodeid))
        self._name = self.cache[1].get('name')
        
    @property
    def nodes(self):
        """
        Return a list of child nodes of this engine. This can be
        used to iterate to obtain access to node level operations
        
        :return: list :py:class:`smc.core.node.Node`
        """
        href = find_link_by_name('nodes', self.link)
        return [Node(meta=Meta(**node))
                for node in search.element_by_href_as_json(href)]
        #TODO: Throws error when machine is deleted and monotirong is looping
        
    def permissions(self):
        """
        Retrieve the permissions for this engine instance.
        """
        result = search.element_by_href_as_json(
                        find_link_by_name('permissions', self.link))
        if not result:
            raise UnsupportedEngineFeature('Engine permissions are only supported '
                                           'when using SMC API version 6.1 and newer.')
        return result
    
    def alias_resolving(self):
        """ 
        Alias definitions defined for this engine 
        Aliases can be used in rules to simplify multiple object creation
        
        :method: GET
        :return: list :py:class:`smc.core.engine.Alias`
        """
        href = find_link_by_name('alias_resolving', self.link)
        return [Alias(**alias)
                for alias in search.element_by_href_as_json(href)]

    def blacklist(self, src, dst, duration=3600):
        """ 
        Add blacklist entry to engine node by name. For blacklist to work,
        you must also create a rule with action "Apply Blacklist".
    
        :method: POST
        :param str src: source to blacklist, can be /32 or network cidr
        :param str dst: dest to deny to, 0.0.0.0/32 indicates all destinations
        :param int duration: how long to blacklist in seconds
        :return: None
        :raises: :py:class:`smc.api.exceptions.EngineCommandFailed`
        """
        result = prepared_request(href=find_link_by_name('blacklist', self.link),
                                  json=prepare_blacklist(src, dst, duration)).create()
        if result.msg:
            raise EngineCommandFailed(result.msg)

    def blacklist_flush(self):
        """ 
        Flush entire blacklist for node name
    
        :method: DELETE
        :return: None
        :raises: :py:class:`smc.api.exceptions.EngineCommandFailed`
        """
        href = find_link_by_name('flush_blacklist', self.link)
        result = prepared_request(href=href).delete()
        if result.msg:
            raise EngineCommandFailed(result.msg)
    
    def add_route(self, gateway, network):
        """ 
        Add a route to engine. Specify gateway and network. 
        If this is the default gateway, use a network address of
        0.0.0.0/0.
        
        .. note: This will fail if the gateway provided does not have a 
                 corresponding interface on the network.
        
        :method: POST
        :param str gateway: gateway of an existing interface
        :param str network: network address in cidr format
        :return: :py:class:`smc.api.web.SMCResult`
        """
        return prepared_request(
                    href=find_link_by_name('add_route', self.link),
                    params={'gateway': gateway, 
                            'network': network}).create()
    @property                            
    def routing(self):
        """
        Find all routing nodes within engine::
    
            for routing_node in engine.routing.all():
                print routing_node.name, routing_node.network

        :method: GET
        :return: :py:class:`smc.core.resource.RoutingNode`
        """
        href=find_link_by_name('routing', self.link)
        return Routing(meta=Meta(href=href))

    @property
    def routing_monitoring(self):
        """ 
        Return route table for the engine, including 
        gateway, networks and type of route (dynamic, static). 
        Calling this can take a few seconds to retrieve routes
        from the engine.
        
        Find all routes for engine resource::
            
            engine = Engine('myengine').load()
            for route in engine.routing_monitoring.all():
                print route
        
        :method: GET
        :return: list :py:class:`smc.core.resource.Route`
        """
        try:
            result = search.element_by_href_as_json(
                        find_link_by_name('routing_monitoring', self.link))
            return RouteTable(result)
        except SMCConnectionError: #timeout if engine is not initialized
            return []
                         
    def antispoofing(self):
        """ 
        Antispoofing interface information. By default is based on routing
        but can be modified in special cases
        
        :method: GET
        :return: dict of antispoofing settings per interface
        """
        return search.element_by_href_as_json(
                        find_link_by_name('antispoofing', self.link))
    
    @property
    def internal_gateway(self):
        """ 
        Engine level VPN gateway information. This is a link from
        the engine to VPN level settings like VPN Client, Enabling/disabling
        an interface, adding VPN sites, etc. 
    
        :method: GET
        :return: :py:class:`~InternalGateway`
        :raises: :py:class:`smc.api.exceptions.UnsupportedEngineFeature`
        """
        result = search.element_by_href_as_json(
                    find_link_by_name('internal_gateway', self.link))
        if not result:
            raise UnsupportedEngineFeature('This engine does not support an internal '
                                           'gateway for VPN, engine type: {}'\
                                           .format(self.type))
        for gw in result:
            igw = InternalGateway(meta=Meta(**gw))
        return igw

    @property
    def virtual_resource(self):
        """ Master Engine only 
        
        To get all virtual resources call::
            
            engine.virtual_resource.all()
            
        :return: :py:class:`smc.elements.engine.VirtualResource`
        :raises: :py:class:`smc.api.exceptions.UnsupportedInterfaceType`
        """
        href = find_link_by_name('virtual_resources', self.link)
        if not href:
            raise UnsupportedEngineFeature('This engine does not support virtual '
                                           'resources; engine type: {}'\
                                           .format(self.type))
        return VirtualResource(meta=Meta(href=href))
            
    @property    
    def interface(self):
        """ 
        Get all interfaces, including non-physical interfaces such
        as tunnel or capture interfaces. These are returned as Interface 
        objects and can be used to load specific interfaces to modify, etc.

        :method: GET
        :return: :py:class:`smc.core.interfaces.Interface`
        
        See :py:class:`smc.core.interfaces.Interface` for more info
        """
        href = find_link_by_name('interfaces', self.link)
        return InterfaceEnum(meta=Meta(href=href))

    @property
    def physical_interface(self):
        """ 
        Returns a PhysicalInterface. This property can be used to
        add physical interfaces to the engine. For example::
        
            engine.physical_interface.add_single_node_interface(....)
            engine.physical_interface.add_node_interface(....)
       
        :method: GET
        :return: :py:class:`smc.core.interfaces.PhysicalInterface`
        :raises: :py:class:`smc.api.exceptions.UnsupportedInterfaceType`
        """
        href = find_link_by_name('physical_interface', self.link)
        if not href: #not supported by virtual engines
            raise UnsupportedInterfaceType('Engine type: {} does not support the '
                                           'physical interface type'\
                                           .format(self.type))
        return PhysicalInterface(meta=Meta(href=href))

    @property    
    def virtual_physical_interface(self):
        """ Master Engine virtual instance only
        
        A virtual physical interface is for a master engine virtual instance. This
        interface type is just a subset of a normal physical interface but for virtual
        engines. This interface only sets Auth_Request and Outgoing on the interface.
        
        To view all interfaces for a virtual engine::
        
            for intf in engine.virtual_physical_interface.all():
                print intf.describe()
        
        :method: GET
        :return: :py:class:`smc.core.interfaces.VirtualPhysicalInterface`
        :raises: :py:class:`smc.api.exceptions.UnsupportedInterfaceType`
        """
        href = find_link_by_name('virtual_physical_interface', self.link)
        if not href:
            raise UnsupportedInterfaceType('Only virtual engines support the '
                                           'virtual physical interface type. Engine '
                                           'type is: {}'
                                           .format(self.type))
        return VirtualPhysicalInterface(meta=Meta(href=href))

    @property
    def tunnel_interface(self):
        """ 
        Get only tunnel interfaces for this engine node.
        
        :method: GET
        :return: :py:class:`smc.core.interfaces.TunnelInterface`
        :raises: :py:class:`smc.api.exceptions.UnsupportedInterfaceType`
        """
        href = find_link_by_name('tunnel_interface', self.link)
        if not href:
            raise UnsupportedInterfaceType('Tunnel interfaces are only supported on '
                                           'layer 3 single engines or clusters; '
                                           'Engine type is: {}'
                                           .format(self.type))
        return TunnelInterface(meta=Meta(href=href))

    def modem_interface(self):
        """ 
        Get only modem interfaces for this engine node.
        
        :method: GET
        :return: list of dict entries with href,name,type, or None
        """
        return search.element_by_href_as_json(
                        find_link_by_name('modem_interface', self.link))
    
    def adsl_interface(self):
        """ 
        Get only adsl interfaces for this engine node.
        
        :method: GET
        :return: list of dict entries with href,name,type, or None
        """
        return search.element_by_href_as_json(
                        find_link_by_name('adsl_interface', self.link))
    
    def wireless_interface(self):
        """ 
        Get only wireless interfaces for this engine node.
        
        :method: GET
        :return: list of dict entries with href,name,type, or None
        """
        return search.element_by_href_as_json(
                        find_link_by_name('wireless_interface', self.link))
    
    def switch_physical_interface(self):
        """ 
        Get only switch physical interfaces for this engine node.
        
        :method: GET
        :return: list of dict entries with href,name,type, or None
        """
        return search.element_by_href_as_json(
                        find_link_by_name('switch_physical_interface', self.link))
    
    def refresh(self, wait_for_finish=True, sleep=3):
        """ 
        Refresh existing policy on specified device. This is an asynchronous 
        call that will return a 'follower' link that can be queried to determine 
        the status of the task. 
        
        Last yield is result href; if wait_for_finish=False, the only yield is 
        the follower href::
        
            task = engine.refresh()
            for message in task:
                print message
        
        :method: POST
        :param boolean wait_for_finish: whether to wait in a loop until the upload completes
        :param int sleep: number of seconds to sleep if wait_for_finish=True
        :return: generator yielding updates on progress
        :raises: :py:class:`smc.api.exceptions.TaskRunFailed`
        """
        element = prepared_request(
                    href=find_link_by_name('refresh', self.link)).create()
        if not element.json:
            raise TaskRunFailed(element.msg)
        return task_handler(Task(**element.json), 
                            wait_for_finish=wait_for_finish,
                            sleep=sleep)

    def upload(self, policy=None, wait_for_finish=False, sleep=3):
        """ 
        Upload policy to engine. This is used when a new policy is required
        for an engine, or this is the first time a policy is pushed to an engine.
        If an engine already has a policy and the intent is to re-push, then use
        :py:func:`refresh` instead.
        The policy argument can use a wildcard * to specify in the event a full 
        name is not known::
        
            engine = Engine('myfw').load()
            task = engine.upload('Amazon*', wait_for_finish=True)
            for message in task:
                print message
        
        :param str policy: name of policy to upload to engine; if None, current policy
        :param boolean wait_for_finish: whether to wait for async responses
        :param int sleep: number of seconds to sleep if wait_for_finish=True
        :return: generator yielding updates on progress
        :raises: :py:class:`smc.api.exceptions.TaskRunFailed`
        """
        element = prepared_request(
                    href=find_link_by_name('upload', self.link),
                    params={'filter': policy}).create()
        if not element.json: #policy not found
            raise TaskRunFailed(element.msg)
        return task_handler(Task(**element.json), 
                            wait_for_finish=wait_for_finish,
                            sleep=sleep)

    def generate_snapshot(self, filename='snapshot.zip'):
        """ 
        Generate and retrieve a policy snapshot from the engine
        This is blocking as file is downloaded
        
        :method: GET
        :param str filename: name of file to save file to, including directory path
        :return: None
        """
        href = find_link_by_name('generate_snapshot', self.link)
        return prepared_request(href=href, filename=filename).read()
    
    def snapshots(self):
        """ 
        References to policy based snapshots for this engine, including
        the date the snapshot was made
        
        :method: GET
        :return: list :py:class:`smc.core.engine.Snapshot`
        :raises: :py:class:`smc.api.exceptions.EngineCommandFailed`
        """
        href = find_link_by_name('snapshots', self.link)
        return [Snapshot(meta=Meta(**snapshot))
                for snapshot in search.element_by_href_as_json(href)]

class InternalGateway(Element):
    """ 
    InternalGateway represents the engine side VPN configuration
    This defines settings such as setting VPN sites on protected
    networks and generating certificates.
    This is defined under Engine->VPN within SMC.
    Since each engine has only one internal gateway, this resource
    is loaded immediately when called through engine.internal_gateway
    
    This is a resource of an Engine as it defines engine specific VPN 
    gateway settings::
    
        engine.internal_gateway.describe()
    
    :ivar href: location of this internal gateway
    :ivar etag: etag of internal gateway
    :ivar vpn_site: vpn site object
    :ivar internal_endpoint: interface endpoint mappings (where to enable VPN) 
    """
    def __init__(self, meta=None, **kwargs):
        self.meta = meta

    @property
    def name(self):
        return self.meta.name

    @property
    def vpn_site(self):
        """
        Retrieve VPN Site information for this internal gateway
        
        Find all configured sites for engine::
        
            for site in engine.internal_gateway.vpn_site.all():
                print site
        
        :method: GET
        :return: :py:class:`smc.vpn.elements.VPNSite`
        """
        href = find_link_by_name('vpn_site', self.link)
        return VPNSite(meta=Meta(href=href))
    
    @property
    def internal_endpoint(self):
        """
        Internal Endpoint setting VPN settings to the interface
        
        Find all internal endpoints for an engine::
        
            for x in engine.internal_gateway.internal_endpoint.all():
                print x
                
        :method: GET
        :return: list :py:class:`smc.vpn.elements.InternalEndpoint`
        """
        href = find_link_by_name('internal_endpoint', self.link)
        return InternalEndpoint(meta=Meta(href=href))
    
    def gateway_certificate(self):
        """
        :method: GET
        :return: list
        """
        return search.element_by_href_as_json(
                find_link_by_name('gateway_certificate', self.link))
    
    def gateway_certificate_request(self):
        """
        :method: GET
        :return: list
        """
        return search.element_by_href_as_json(
                find_link_by_name('gateway_certificate_request', self.link))    
    
    def generate_certificate(self, certificate_request):
        """
        Generate an internal gateway certificate used for VPN on this engine.
        Certificate request should be an instance of VPNCertificate.
    
        :method: POST
        :param: :py:class:`~smc.vpn.elements.VPNCertificate` certificate_request: 
                certificate request created
        :return: None
        :raises: :py:class:`smc.api.exceptions.CertificateError`
        """
        result = prepared_request(
                    href=find_link_by_name('generate_certificate', self.link),
                    json=vars(certificate_request)).create()
        if result.msg:
            raise CertificateError(result.msg)

class InternalEndpoint(Element):
    """
    InternalEndpoint lists the VPN endpoints either enabled or disabled for
    VPN. You should enable the endpoint for the interface that will be the
    VPN endpoint. You may also need to enable NAT-T and ensure IPSEC is enabled.
    This is defined under Engine->VPN->EndPoints in SMC. This class is a property
    of the engines internal gateway and not accessed directly.
    
    To see all available internal endpoint (VPN gateways) on a particular
    engine, get the engine context first::
        
        engine = Engine('myengine').load()
        for endpt in engine.internal_gateway.internal_endpoint.all():
            print endpt
    
    :ivar deducted_name: name of the endpoint is based on the interface
    :ivar dynamic: True|False
    :ivar enabled: True|False
    :ivar ipsec_vpn: True|False
    :ivar nat_t: True|False
    
    :param href: pass in href to init which will have engine insert location  
    """
    def __init__(self, meta=None):
        self.meta = meta
    
    @property
    def name(self):
        return self.meta.name

    def all(self):
        """
        Return all internal endpoints
        
        :return: list :py:class:`smc.core.engine.InternalEndpoint`
        """
        return [InternalEndpoint(meta=Meta(**ep))
                for ep in search.element_by_href_as_json(self.href)]
 
class VirtualResource(Element):
    """
    A Virtual Resource is a container placeholder for a virtual engine
    within a Master Engine. When creating a virtual engine, each virtual
    engine must have a unique virtual resource for mapping. The virtual 
    resource has an identifier (vfw_id) that specifies the engine ID for 
    that instance. There is currently no modify_attribute method available
    for this resource.
    
    This is called as a resource of an engine. To view all virtual
    resources::
        
        for resource in engine.virtual_resource.all():
            print resource
            
    To create a new virtual resource::
    
        engine.virtual_resource.create(......)
    
    When class is initialized, meta data is passed in from the engine method. 
    This is used to get the entry point for an empty resource and when loading
    existing resources, provides name and href of the virtual resource. 
    
    :ivar name: name of virtual resource
    :ivar vfw_id: virtual resource id

    :param meta: meta is provided from the engine.virtual_resource method
    """
    def __init__(self, meta=None):
        self.meta = meta    

    @property
    def name(self):
        return self.meta.name
   
    @property
    def vfw_id(self):
        return self.describe().get('vfw_id')

    def create(self, name, vfw_id, domain='Shared Domain',
               show_master_nic=False, connection_limit=0):
        """
        Create a new virtual resource
        
        :param str name: name of virtual resource
        :param int vfw_id: virtual fw identifier
        :param str domain: name of domain to install, (default Shared)
        :param boolean show_master_nic: whether to show the master engine NIC ID's
               in the virtual instance
        :param int connection_limit: whether to limit number of connections for this 
               instance
        :return: :py:class:`smc.api.web.SMCResult`
        """
        allocated_domain = domain_helper(domain)
        json = {'name': name,
                'connection_limit': connection_limit,
                'show_master_nic': show_master_nic,
                'vfw_id': vfw_id,
                'allocated_domain_ref': allocated_domain}
       
        return SMCRequest(href=self.href, json=json).create()

    def all(self):
        """
        Return metadata for all virtual resources
        
            for resource in engine.virtual_resource.all():
                if resource.name == 've-6':
                    print resource.describe()
        
        :return: list VirtualResource
        """
        return [VirtualResource(meta=Meta(**resource))
                for resource in search.element_by_href_as_json(self.href)]
