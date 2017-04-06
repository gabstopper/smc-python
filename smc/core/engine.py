import smc.actions.search as search
from smc.compat import min_smc_version
from smc.elements.helpers import domain_helper
from smc.base.model import Element, prepared_request, ResourceNotFound,\
    SubElement, lookup_class, fetch_collection
from smc.api.exceptions import UnsupportedEngineFeature,\
    UnsupportedInterfaceType, TaskRunFailed, EngineCommandFailed,\
    SMCConnectionError, CertificateError, CreateElementFailed
from smc.core.node import Node
from smc.core.resource import Snapshot, PendingChanges
from smc.core.interfaces import PhysicalInterface, \
    VirtualPhysicalInterface, TunnelInterface, Interface
from smc.administration.tasks import task_handler, Task
from smc.elements.other import prepare_blacklist
from smc.elements.network import Alias
from smc.vpn.elements import VPNSite
from smc.core.route import Antispoofing, Routing, Routes
from smc.core.contact_address import ContactResource

class EngineFeature:
    def enable_dns_relay(self, dns_relay_profile, interface):
        """
        DNS Relay allows the engine to provide DNS caching or specific
        host, IP and domain replies to clients. It can also be used 
        to sinkhole specific DNS requests.
        
        :param str,Element dns_relay_profile: href of profile or DNSRelayProfile
        :param int interface: interface id to enable relay
        :raises EngineCommandFailed: interface not found
        :raises ElementNotFound: profile not found
        :raises ModificationFailed: failure modifying setting
        :return: None
        """
        if isinstance(dns_relay_profile, Element):
            dns_relay_profile = dns_relay_profile.href
        
        data = self.physical_interface.get(interface)
        
        d = dict(dns_relay_profile_ref=dns_relay_profile)
        d.update(dns_relay_interface=([{'address':ip,'nicid':nicid} 
                                       for ip,ntwk,nicid in data.addresses]))  # @UnusedVariable
        self.modify_attribute(**d)
    
          
class Engine(EngineFeature, Element):
    """
    An engine is the top level representation of a firewall, IPS
    or virtualized software. 
    
    Engine load can be called directly::
        
        >>> from smc.core.engine import Engine
        >>> engine = Engine('testfw')
        >>> print(engine.href)
        http://1.1.1.1:8082/6.1/elements/single_fw/39550
            
        or load by calling collections::
        
        >>> from smc.elements.resources import Search
        >>> list(Search('single_fw').objects.filter('testfw'))
        [Layer3Firewall(name=testfw)]
            
    Instance attributes:
    
    :ivar name: name of engine
    :ivar type: type of engine
    :ivar href: href of the engine
    :ivar etag: current etag
    
    Instance resources:
    
    :ivar list nodes: :py:class:`smc.core.node.Node` nodes associated with 
          this engine
    :ivar permissions: :py:class:`smc.administration.access_rights.AccessControlList`
    :ivar routing: :py:class:`smc.core.route.Routing` routing configuration hierarchy
    :ivar routing_monitoring: :py:class:`smc.core.route.Routes` current route table
    :ivar antispoofing: :py:class:`smc.core.route.Antispoofing` antispoofing interface
          configuration
    :ivar internal_gateway: :py:class:`~InternalGateway` engine 
          level VPN settings
    :ivar virtual_resource: :py:class:`smc.core.engine.VirtualResource` for engine, 
          only relevant to Master Engine
    :ivar interface: :py:class:`smc.core.interfaces.Interface` interfaces 
          for this engine
    :ivar physical_interface: :py:class:`smc.core.interfaces.PhysicalInterface` 
          access to physical interface settings
    :ivar tunnel_interface: :py:class:`smc.core.interfaces.TunnelInterface` 
          retrieve or create tunnel interfaces
    :ivar snapshots: :py:class:`smc.core.engine.Snapshot` engine level policy snapshots
    """
    typeof = 'engine_clusters'
    
    def __init__(self, name, **meta):
        super(Engine, self).__init__(name, **meta)
        pass
        
    @classmethod
    def _create(cls, name, node_type, 
                physical_interfaces,
                nodes=1, log_server_ref=None, 
                domain_server_address=None,
                enable_antivirus=False, enable_gti=False,
                sidewinder_proxy_enabled=False,
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
            node_list.append(Node._create(name, node_type, nodeid))
            
        domain_server_list = []
        if domain_server_address:
            rank_i = 0
            for entry in domain_server_address:
                domain_server_list.append(
                                    {"rank": rank_i, "value": entry})
        
        #Set log server reference, if not explicitly provided
        if not log_server_ref and node_type is not 'virtual_fw_node': 
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
        if min_smc_version(6.1):
            if sidewinder_proxy_enabled:
                base_cfg.update(sidewinder_proxy_enabled=True)
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
    
    @property
    def type(self):
        if not self.meta:
            self.cache()
        return self.meta.type

    @property
    def version(self):
        """
        Version of this engine
        """
        return self.attr_by_name('engine_version')
    
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
        self._name = self.data.get('name')
        
    @property
    def nodes(self):
        """
        Return a list of child nodes of this engine. This can be
        used to iterate to obtain access to node level operations
        
        :return: list :py:class:`smc.core.node.Node`
        """
        return [Node(**node)
                for node in self.resource.get('nodes')]
    
    @property
    def permissions(self):
        """
        Retrieve the permissions for this engine instance.
        ::
        
            for acl in engine.permissions:
                print(acl, acl.granted_element)
        
        :return: list :py:class:`smc.administration.access_rights.AccessControlList`
        """
        try:
            acls = self.resource.get('permissions')
            return [Element.from_href(acl) 
                    for acl in acls['granted_access_control_list']]
    
        except ResourceNotFound:
            raise UnsupportedEngineFeature('Engine permissions are only supported '
                                           'when using SMC API version 6.1 and newer.')
    
    @property
    def pending_changes(self):
        """
        Pending changes provides insight into changes on an engine that are
        pending approval or disapproval. Feature requires SMC >= v6.2.
        
        :raises UnsupportedEngineFeature: if SMC is not
            version >= 6.2 or the engine type doesn't support pending changes
        :return: :py:class:`smc.core.resources.PendingChanges`
        """
        try:
            if self.resource.pending_changes:
                return PendingChanges(self.resource)
        except ResourceNotFound:
            raise UnsupportedEngineFeature('Pending changes is an unsupported feature '
                                           'on this engine: {}'.format(self.type))
               
    def alias_resolving(self):
        """ 
        Alias definitions with resolved values as defined on this engine. 
        Aliases can be used in rules to simplify multiple object creation
        ::
        
            print(list(engine.alias_resolving()))
        
        :return: generator :py:class:`smc.elements.network.Alias`
        """
        for alias in self.resource.get('alias_resolving'):
            yield Alias.load(alias)
  
    def blacklist(self, src, dst, duration=3600):
        """ 
        Add blacklist entry to engine node by name. For blacklist to work,
        you must also create a rule with action "Apply Blacklist".
    
        :param str src: source to blacklist, can be /32 or network cidr
        :param str dst: dest to deny to, 0.0.0.0/32 indicates all destinations
        :param int duration: how long to blacklist in seconds
        :raises EngineCommandFailed: blacklist failed during apply
        :return: None
        """
        prepared_request(EngineCommandFailed,
                         href=self.resource.blacklist,
                         json=prepare_blacklist(src, dst, duration)
                         ).create()

    def blacklist_flush(self):
        """ 
        Flush entire blacklist for engine
        
        :raises EngineCommandFailed: flushing blacklist failed with reason
        :return: None
        """
        prepared_request(EngineCommandFailed,
                         href=self.resource.flush_blacklist
                         ).delete()
    
    def add_route(self, gateway, network):
        """ 
        Add a route to engine. Specify gateway and network. 
        If this is the default gateway, use a network address of
        0.0.0.0/0.
        
        .. note: This will fail if the gateway provided does not have a 
                 corresponding interface on the network.
        
        :param str gateway: gateway of an existing interface
        :param str network: network address in cidr format
        :raises EngineCommandFailed: invalid route, possibly no network
        :return: None
        """
        prepared_request(EngineCommandFailed,
                         href=self.resource.add_route,
                         params={'gateway': gateway, 
                                 'network': network}
                         ).create()

    @property                            
    def routing(self):
        """
        Find all routing nodes within engine::
    
            for routing_node in engine.routing.all():
                for routes in routing_node:
                    print(routes)

        :return: :py:class:`smc.core.route.Routing`
        """
        href = self.resource.routing
        return Routing(href=href,
                       data=self.resource.get(href))
    
    @property
    def routing_monitoring(self):
        """ 
        Return route table for the engine, including 
        gateway, networks and type of route (dynamic, static). 
        Calling this can take a few seconds to retrieve routes
        from the engine.
        
        Find all routes for engine resource::
            
            engine = Engine('myengine')
            for route in engine.routing_monitoring.all():
                print route
      
        :raises EngineCommandFailed: routes cannot be retrieved
        :return: list :py:class:`smc.core.route.Routes`
        """
        try:
            result = prepared_request(EngineCommandFailed,
                                      href=self.resource.routing_monitoring
                                      ).read()
            return Routes(result.json)
        except SMCConnectionError:
            raise EngineCommandFailed('Timed out waiting for routes')
    
    @property                     
    def antispoofing(self):
        """ 
        Antispoofing interface information. By default is based on routing
        but can be modified.
        ::
            
            for entry in engine.antispoofing.all():
                print(entry)
        
        :return: :py:class:`smc.core.route.Antispoofing`
        """
        href = self.resource.antispoofing
        return Antispoofing(href=href,
                            data=self.resource.get(href))
    
    @property
    def internal_gateway(self):
        """ 
        Engine level VPN gateway information. This is a link from
        the engine to VPN level settings like VPN Client, Enabling/disabling
        an interface, adding VPN sites, etc. 

        :raises UnsupportedEngineFeature: engine type does not have an internal
            gateway
        :return: :py:class:`~InternalGateway`
        """
        try:
            result = self.resource.get('internal_gateway')
            if result:
                return InternalGateway(**result.pop())
        except ResourceNotFound:
            raise UnsupportedEngineFeature('This engine does not support an internal '
                                           'gateway for VPN, engine type: {}'\
                                           .format(self.type))
   
    @property
    def virtual_resource(self):
        """ Master Engine only 
        
        To get all virtual resources call::
            
            engine.virtual_resource.all()
            
        :raises UnsupportedInterfaceType: master engine only
        :return: :py:class:`smc.elements.engine.VirtualResource`
        """
        try:
            return VirtualResource(href=self.resource.virtual_resources)
        except ResourceNotFound:
            raise UnsupportedEngineFeature('This engine does not support virtual '
                                           'resources; engine type: {}'\
                                          .format(self.type))
    
    @property
    def contact_addresses(self):
        """
        All available interfaces that can have contact adresses assigned.
        Only supported with SMC >= 6.2.
        ::
            
            interface1 = engine.contact_addresses(1) # For interface 1
            for ipv4 in interface1:
                if ipv4.address == '2.2.2.2':
                    contact = ContactAddress.create('10.10.10.10', location='Default')
                    ipv4.add_contact_address(contact)

            print(list(engine.contact_addresses))    # list all
            
            for interfaces in engine.contact_addresses.all(): #iterate all
                print(interfaces) #ContactInterface
                
        .. seealso:: :py:class:`smc.core.contact_address.ContactAddress`
        
        :return: list :py:class:`smc.core.contact_address.ContactInterface`
        """
        return ContactResource(self.resource.get(self.resource.contact_addresses))
    
    @property    
    def interface(self):
        """ 
        Get all interfaces, including non-physical interfaces such
        as tunnel or capture interfaces. These are returned as Interface 
        objects and can be used to load specific interfaces to modify, etc.
        ::
        
            for interfaces in engine.interface.all():
                ......
        
        :return: :py:class:`smc.core.interfaces.Interface`
        
        See :py:class:`smc.core.interfaces.Interface` for more info
        """
        return Interface(href=self.resource.interfaces, 
                         engine=self)
        
    @property
    def physical_interface(self):
        """ 
        Returns a PhysicalInterface. This property can be used to
        add physical interfaces to the engine. For example::
        
            engine.physical_interface.add_single_node_interface(....)
            engine.physical_interface.add_node_interface(....)

        :raises UnsupportedInterfaceType: engine doesn't support this type
        :return: :py:class:`smc.core.interfaces.PhysicalInterface`
        """
        try:
            return PhysicalInterface(href=self.resource.physical_interface, 
                                     engine=self)
        except ResourceNotFound:
            raise UnsupportedInterfaceType('Engine type: {} does not support the '
                                           'physical interface type'\
                                           .format(self.type))

    @property    
    def virtual_physical_interface(self):
        """ Master Engine virtual instance only
        
        A virtual physical interface is for a master engine virtual instance. This
        interface type is just a subset of a normal physical interface but for virtual
        engines. This interface only sets Auth_Request and Outgoing on the interface.
        
        To view all interfaces for a virtual engine::
        
            for intf in engine.virtual_physical_interface.all():
                print(intf)
        
        :raises UnsupportedInterfaceType: virtual engines only
        :return: :py:class:`smc.core.interfaces.VirtualPhysicalInterface`
        """
        try:
            return VirtualPhysicalInterface(href=self.resource.virtual_physical_interface, 
                                            engine=self)
        except ResourceNotFound:
            raise UnsupportedInterfaceType('Only virtual engines support the '
                                           'virtual physical interface type. Engine '
                                           'type is: {}'
                                           .format(self.type))

    @property
    def tunnel_interface(self):
        """ 
        Get only tunnel interfaces for this engine node.
        
        :raises UnsupportedInterfaceType: layer 3 engine's only
        :return: :py:class:`smc.core.interfaces.TunnelInterface`
        """
        try:
            return TunnelInterface(href=self.resource.tunnel_interface, 
                                   engine=self)
        except ResourceNotFound:
            raise UnsupportedInterfaceType('Tunnel interfaces are only supported on '
                                           'layer 3 single engines or clusters; '
                                           'Engine type is: {}'
                                           .format(self.type))

    @property
    def modem_interface(self):
        """ 
        Get only modem interfaces for this engine node.
        
        :return: list of dict entries with href,name,type, or None
        """
        try:
            return self.resource.get('modem_interface')
        except ResourceNotFound:
            raise UnsupportedInterfaceType('Modem interfaces are not supported '
                                           'on this engine type: {}'
                                           .format(self.type))
    
    @property
    def adsl_interface(self):
        """ 
        Get only adsl interfaces for this engine node.
        
        :return: list of dict entries with href,name,type, or None
        """
        try:
            return self.resource.get('adsl_interface')
        except ResourceNotFound:
            raise UnsupportedInterfaceType('ADSL interfaces are not supported '
                                           'on this engine type: {}'
                                           .format(self.type))
    
    @property
    def wireless_interface(self):
        """ 
        Get only wireless interfaces for this engine node.

        :return: list of dict entries with href,name,type, or None
        """
        try:
            return self.resource.get('wireless_interface')
        except ResourceNotFound:
            raise UnsupportedInterfaceType('Wireless interfaces are not supported '
                                           'on this engine type: {}'
                                           .format(self.type))
    
    @property
    def switch_physical_interface(self):
        """ 
        Get only switch physical interfaces for this engine node.

        :return: list of dict entries with href,name,type, or None
        """
        try:
            return self.resource.get('switch_physical_interface')
        except ResourceNotFound:
            raise UnsupportedInterfaceType('Switch interfaces are not supported '
                                           'on this engine type: {}'
                                           .format(self.type))
    
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

        :param boolean wait_for_finish: whether to wait in a loop until the upload completes
        :param int sleep: number of seconds to sleep if wait_for_finish=True
        :raises TaskRunFailed: refresh failed, possibly locked policy
        :return: generator yielding updates on progress
        """
        element = prepared_request(TaskRunFailed,
                                   href=self.resource.refresh
                                   ).create()
       
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
        
            engine = Engine('myfw')
            task = engine.upload('Amazon*', wait_for_finish=True)
            for message in task:
                print message
        
        :param str policy: name of policy to upload to engine; if None, current policy
        :param boolean wait_for_finish: whether to wait for async responses
        :param int sleep: number of seconds to sleep if wait_for_finish=True
        :raises TaskRunFailed: upload failed with reason
        :return: generator yielding updates on progress
        """
        element = prepared_request(TaskRunFailed,
                                   href=self.resource.upload,
                                   params={'filter': policy}
                                   ).create()
        
        return task_handler(Task(**element.json), 
                            wait_for_finish=wait_for_finish,
                            sleep=sleep)

    def generate_snapshot(self, filename='snapshot.zip'):
        """ 
        Generate and retrieve a policy snapshot from the engine
        This is blocking as file is downloaded

        :param str filename: name of file to save file to, including directory path
        :raises EngineCommandFailed: snapshot failed, possibly invalid filename specified
        :return: None
        """
        try:
            prepared_request(EngineCommandFailed,
                             href=self.resource.generate_snapshot, 
                             filename=filename
                             ).read()
        except IOError as e:
            raise EngineCommandFailed("Generate snapshot failed: {}"
                                      .format(e))
           
    def snapshots(self):
        """ 
        References to policy based snapshots for this engine, including
        the date the snapshot was made

        :return: list :py:class:`smc.core.engine.Snapshot`
        :raises EngineCommandFailed: failure downloading, or IOError
        """
        return [Snapshot(**snapshot)
                for snapshot in self.resource.get('snapshots')]

    def __unicode__(self):
        return u'{0}(name={1})'.format(lookup_class(self.type).__name__, self.name)
  
class InternalGateway(SubElement):
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
    def __init__(self, **meta):
        super(InternalGateway, self).__init__(**meta)
        pass

    @property
    def vpn_site(self):
        """
        Retrieve VPN Site information for this internal gateway
        
        Find all configured sites for engine::
        
            for site in engine.internal_gateway.vpn_site.all():
                print site

        :return: :py:class:`smc.vpn.elements.VPNSite`
        """
        return VPNSite(href=self.resource.vpn_site)
    
    @property
    def internal_endpoint(self):
        """
        Internal Endpoint setting VPN settings to the interface
        
        Find all internal endpoints for an engine::
        
            for x in engine.internal_gateway.internal_endpoint.all():
                print x

        :return: list :py:class:`smc.vpn.elements.InternalEndpoint`
        """
        return InternalEndpoint(href=self.resource.internal_endpoint)
    
    def gateway_certificate(self):
        """
        :return: list
        """
        return self.resource.get('gateway_certificate')
    
    def gateway_certificate_request(self):
        """
        :return: list
        """
        return self.resource.get('gateway_certificate_request')   
    
    def generate_certificate(self, certificate_request):
        """
        Generate an internal gateway certificate used for VPN on this engine.
        Certificate request should be an instance of VPNCertificate.

        :param: :py:class:`~smc.vpn.elements.VPNCertificate` certificate_request: 
                certificate request created
        :return: None
        :raises CertificateError: error generating certificate
        """
        prepared_request(CertificateError,
                         href=self.resource.generate_certificate,
                         json=vars(certificate_request)
                         ).create()

class InternalEndpoint(SubElement):
    """
    InternalEndpoint lists the VPN endpoints either enabled or disabled for
    VPN. You should enable the endpoint for the interface that will be the
    VPN endpoint. You may also need to enable NAT-T and ensure IPSEC is enabled.
    This is defined under Engine->VPN->EndPoints in SMC. This class is a property
    of the engines internal gateway and not accessed directly.
    
    To see all available internal endpoint (VPN gateways) on a particular
    engine, get the engine context first::
        
        engine = Engine('myengine')
        for endpt in engine.internal_gateway.internal_endpoint.all():
            print endpt
    
    :ivar deducted_name: name of the endpoint is based on the interface
    :ivar dynamic: True|False
    :ivar enabled: True|False
    :ivar ipsec_vpn: True|False
    :ivar nat_t: True|False
    
    :param href: pass in href to init which will have engine insert location  
    """
    def __init__(self, **meta):
        super(InternalEndpoint, self).__init__(**meta)
        pass
    
    def all(self):
        """
        Return all internal endpoints
        
        :return: list :py:class:`smc.core.engine.InternalEndpoint`
        """
        return [InternalEndpoint(**ep)
                for ep in fetch_collection(self.href)]
        
class VirtualResource(SubElement):
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
    def __init__(self, **meta):
        super(VirtualResource, self).__init__(**meta)
        pass 
   
    @property
    def vfw_id(self):
        return self.data.get('vfw_id')

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
        :return: str href: href location of new virtual resource
        """
        allocated_domain = domain_helper(domain)
        json = {'name': name,
                'connection_limit': connection_limit,
                'show_master_nic': show_master_nic,
                'vfw_id': vfw_id,
                'allocated_domain_ref': allocated_domain}
        
        return prepared_request(CreateElementFailed,
                                href=self.href,
                                json=json
                                ).create().href
    
    def all(self):
        """
        Return metadata for all virtual resources
        
            for resource in engine.virtual_resource.all():
                if resource.name == 've-6':
                    print resource.describe()
        
        :return: list VirtualResource
        """
        return [VirtualResource(**resource)
                for resource in fetch_collection(self.href)]
