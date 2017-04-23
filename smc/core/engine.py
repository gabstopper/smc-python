import smc.actions.search as search
from smc.compat import min_smc_version
from smc.elements.helpers import domain_helper
from smc.base.model import Element, prepared_request, ResourceNotFound,\
    SubElement, lookup_class
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
from smc.core.properties import EngineProperty
from smc.elements.servers import LogServer
from smc.base.collection import create_collection, sub_collection


class Engine(EngineProperty, Element):
    """
    An engine is the top level representation of a firewall, IPS
    or virtualized software.

    Engine load can be called directly::

        >>> from smc.core.engine import Engine
        >>> engine = Engine('testfw')
        >>> print(engine.href)
        http://1.1.1.1:8082/6.1/elements/single_fw/39550

    Or load by calling collections (by firewall type)::

        >>> from smc.core.engines import Layer3Firewall
        >>> list(Layer3Firewall.objects.all())
        [Layer3Firewall(name=i-06145fc6c59a04335 (us-east-2a))]

    Or generic search for all::

        >>> list(Search('engine_clusters').objects.all())
        [Layer3Firewall(name=i-06145fc6c59a04335 (us-east-2a)), FirewallCluster(name=sg_vm),
        Layer3VirtualEngine(name=ve-5), MasterEngine(name=master-eng)]

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
    :ivar snapshots: :py:class:`smc.core.engine.Snapshot` engine level policy
        snapshots
    """
    typeof = 'engine_clusters'

    def __init__(self, name, **meta):
        super(Engine, self).__init__(name, **meta)

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
        for nodeid in range(1, nodes + 1):  # start at nodeid=1
            node_list.append(Node._create(name, node_type, nodeid))

        domain_server_list = []
        if domain_server_address:
            for num, server in enumerate(domain_server_address):
                domain_server_list.append({
                    'rank': num, 'value': server})

        # Set log server reference, if not explicitly provided
        if not log_server_ref and node_type is not 'virtual_fw_node':
            for log_server in list(LogServer.objects.limit(1)):
                log_server_ref = log_server.href

        base_cfg = {
            'name': name,
            'nodes': node_list,
            'domain_server_address': domain_server_list,
            'log_server_ref': log_server_ref,
            'physicalInterfaces': physical_interfaces}

        if enable_antivirus:
            antivirus = {
                'antivirus': {
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
            base_cfg.update(default_nat=True)

        if location_ref:
            base_cfg.update(location_ref=location_ref)

        if enable_ospf:
            if not ospf_profile:  # get default profile
                ospf_profile = search.get_ospf_default_profile()
            ospf = {'dynamic_routing': {
                'ospfv2': {
                    'enabled': True,
                    'ospfv2_profile_ref': ospf_profile}
            }}
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
        Rename the firewall engine, nodes, and internal gateway (VPN gw)

        :return: None
        """
        for node in self.nodes:
            node.rename(name)
        try:
            del self.cache
        except AttributeError:
            pass
        self.data['name'] = '{}'.format(name)
        self._name = self.data.get('name')
        self.update()
        self.internal_gateway.rename(name)

    @property
    def nodes(self):
        """
        Return a list of child nodes of this engine. This can be
        used to iterate to obtain access to node level operations

        :return: list :py:class:`smc.core.node.Node`
        """
        return list(sub_collection(self.resource.nodes, Node))

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
            raise UnsupportedEngineFeature(
                'Engine permissions are only supported when using SMC API '
                'version 6.1 and newer.')

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
            raise UnsupportedEngineFeature(
                'Pending changes is an unsupported feature '
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
        prepared_request(
            EngineCommandFailed,
            href=self.resource.blacklist,
            json=prepare_blacklist(src, dst, duration)
        ).create()

    def blacklist_flush(self):
        """
        Flush entire blacklist for engine

        :raises EngineCommandFailed: flushing blacklist failed with reason
        :return: None
        """
        prepared_request(
            EngineCommandFailed,
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
        prepared_request(
            EngineCommandFailed,
            href=self.resource.add_route,
            params={'gateway': gateway,
                    'network': network}
        ).create()

    @property
    def routing(self):
        """
        Find all routing nodes within engine::

            for routing in engine.routing.all():
                for routes in routing:
                    ...

        Or just retrieve a routing configuration for a single
        interface::

            interface = engine.routing.get(0)

        :return: :py:class:`smc.core.route.Routing` element
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
            result = prepared_request(
                EngineCommandFailed,
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
            raise UnsupportedEngineFeature(
                'This engine does not support an internal gateway for VPN, '
                'engine type: {}'.format(self.type))

    @property
    def virtual_resource(self):
        """
        Available on a Master Engine only.

        To get all virtual resources call::

            engine.virtual_resource.all()

        :raises UnsupportedInterfaceType: master engine only
        :return: collection of `.VirtualResource`
        :rtype: SubElementCollection
        """
        try:
            return create_collection(
                self.resource.virtual_resources,
                VirtualResource)

        except ResourceNotFound:
            raise UnsupportedEngineFeature(
                'This engine does not support virtual resources; engine '
                'type: {}'.format(self.type))

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
        return ContactResource(
            self.resource.get(self.resource.contact_addresses))

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
        return Interface(
            parent=self.resource.interfaces,
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
            return PhysicalInterface(
                parent=self.resource.physical_interface,
                engine=self)
        except ResourceNotFound:
            raise UnsupportedInterfaceType(
                'Engine type: {} does not support the physical interface '
                'type'.format(self.type))

    @property
    def virtual_physical_interface(self):
        """ Master Engine virtual instance only

        A virtual physical interface is for a master engine virtual instance.
        This interface type is just a subset of a normal physical interface
        but for virtual engines. This interface only sets Auth_Request and
        Outgoing on the interface.

        To view all interfaces for a virtual engine::

            for intf in engine.virtual_physical_interface.all():
                print(intf)

        :raises UnsupportedInterfaceType: virtual engines only
        :return: :py:class:`smc.core.interfaces.VirtualPhysicalInterface`
        """
        try:
            return VirtualPhysicalInterface(
                parent=self.resource.virtual_physical_interface,
                engine=self)
        except ResourceNotFound:
            raise UnsupportedInterfaceType(
                'Only virtual engines support the virtual physical '
                'interface type. Engine type is: {}'.format(self.type))

    @property
    def tunnel_interface(self):
        """
        Get only tunnel interfaces for this engine node.

        :raises UnsupportedInterfaceType: layer 3 engine's only
        :return: :py:class:`smc.core.interfaces.TunnelInterface`
        """
        try:
            return TunnelInterface(
                parent=self.resource.tunnel_interface,
                engine=self)
        except ResourceNotFound:
            raise UnsupportedInterfaceType(
                'Tunnel interfaces are only supported on layer 3 single '
                'engines or clusters; Engine type is: {}'.format(self.type))

    @property
    def modem_interface(self):
        """
        Get only modem interfaces for this engine node.

        :return: list of dict entries with href,name,type, or None
        """
        try:
            return self.resource.get('modem_interface')
        except ResourceNotFound:
            raise UnsupportedInterfaceType(
                'Modem interfaces are not supported on this engine type: {}'
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
            raise UnsupportedInterfaceType(
                'ADSL interfaces are not supported on this engine type: {}'
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
            raise UnsupportedInterfaceType(
                'Wireless interfaces are not supported on this engine type: '
                '{}'.format(self.type))

    @property
    def switch_physical_interface(self):
        """
        Get only switch physical interfaces for this engine node.

        :return: list of dict entries with href,name,type, or None
        """
        try:
            return self.resource.get('switch_physical_interface')
        except ResourceNotFound:
            raise UnsupportedInterfaceType(
                'Switch interfaces are not supported on this engine type: {}'
                .format(self.type))

    def refresh(self, wait_for_finish=True, sleep=3):
        """
        Refresh existing policy on specified device. This is an asynchronous
        call that will return a 'follower' link that can be queried to
        determine the status of the task.

        Last yield is result href; if wait_for_finish=False, the only yield is
        the follower href::

            task = engine.refresh()
            for message in task:
                print message

        :param bool wait_for_finish: whether to wait in a loop until the upload
            completes
        :param int sleep: number of seconds to sleep if wait_for_finish=True
        :raises TaskRunFailed: refresh failed, possibly locked policy
        :return: generator yielding updates on progress
        """
        element = prepared_request(
            TaskRunFailed,
            href=self.resource.refresh
            ).create()

        return task_handler(
            Task(**element.json),
            wait_for_finish=wait_for_finish,
            sleep=sleep)

    def upload(self, policy=None, wait_for_finish=False, sleep=3):
        """
        Upload policy to engine. This is used when a new policy is required
        for an engine, or this is the first time a policy is pushed to an
        engine.
        If an engine already has a policy and the intent is to re-push, then
        use :py:func:`refresh` instead.
        The policy argument can use a wildcard * to specify in the event a full
        name is not known::

            engine = Engine('myfw')
            task = engine.upload('Amazon*', wait_for_finish=True)
            for message in task:
                print message

        :param str policy: name of policy to upload to engine; if None, current
            policy
        :param bool wait_for_finish: whether to wait for async responses
        :param int sleep: number of seconds to sleep if wait_for_finish=True
        :raises TaskRunFailed: upload failed with reason
        :return: generator yielding updates on progress
        """
        element = prepared_request(
            TaskRunFailed,
            href=self.resource.upload,
            params={'filter': policy}
            ).create()

        return task_handler(
            Task(**element.json),
            wait_for_finish=wait_for_finish,
            sleep=sleep)

    def generate_snapshot(self, filename='snapshot.zip'):
        """
        Generate and retrieve a policy snapshot from the engine
        This is blocking as file is downloaded

        :param str filename: name of file to save file to, including directory
            path
        :raises EngineCommandFailed: snapshot failed, possibly invalid filename
            specified
        :return: None
        """
        try:
            prepared_request(
                EngineCommandFailed,
                href=self.resource.generate_snapshot,
                filename=filename
            ).read()
        except IOError as e:
            raise EngineCommandFailed(
                'Generate snapshot failed: {}'.format(e))

    @property
    def snapshots(self):
        """
        References to policy based snapshots for this engine, including
        the date the snapshot was made

        :raises EngineCommandFailed: failure downloading, or IOError
        :return: collection of :class:`smc.core.resource.Snapshot`
        :rtype: SubElementCollection
        """
        return sub_collection(
            self.resource.snapshots, Snapshot)

    def __unicode__(self):
        return u'{0}(name={1})'.format(
            lookup_class(self.type).__name__, self.name)


class InternalGateway(SubElement):
    """
    InternalGateway represents the engine side VPN configuration
    This defines settings such as setting VPN sites on protected
    networks and engine level certificates.

    Since each engine has only one internal gateway, this resource
    is loaded immediately when called through engine.internal_gateway

    List endpoints where VPN can be enabled::

        list(engine.internal_gateway.internal_endpoint.all())

    """

    def __init__(self, **meta):
        super(InternalGateway, self).__init__(**meta)

    def rename(self, name):
        self.data['name'] = name = '{} Primary'.format(name)
        self.update()

    @property
    def vpn_site(self):
        """
        Retrieve VPN Site information for this internal gateway

        Find all configured sites for engine::

            for site in engine.internal_gateway.vpn_site.all():
                print site

        :return: collection of :class:`smc.vpn.elements.VPNSite`
        :rtype: SubElementCollection
        """
        return create_collection(
            self.resource.vpn_site, VPNSite)

    @property
    def internal_endpoint(self):
        """
        Internal Endpoints define and enable VPN settings on a
        specific interface.

        Find all internal endpoints for an engine::

            for x in engine.internal_gateway.internal_endpoint.all():
                print x

        :return: collection of :class:`.InternalEndpoint`
        :rtype: SubElementCollection
        """
        return sub_collection(
            self.resource.internal_endpoint,
            InternalEndpoint)

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

        :param: VPNCertificate certificate_request: CSR generated to provide
            a valid certificate
        :raises CertificateError: error generating certificate
        :return: None
        """
        prepared_request(
            CertificateError,
            href=self.resource.generate_certificate,
            json=vars(certificate_request)
        ).create()


class InternalEndpoint(SubElement):
    """
    An Internal Endpoint is an interface mapping that enables VPN on the
    associated interface.
    This also defines what type of VPN to enable such as IPSEC, SSL VPN,
    or SSL VPN Portal. 

    To see all available internal endpoint (VPN gateways) on a particular
    engine, use an engine reference::

        >>> engine = Engine('sg_vm')
        >>> for e in list(engine.internal_gateway.internal_endpoint):
        ...   print(e)
        ...
        InternalEndpoint(name=10.0.0.254)
        InternalEndpoint(name=172.18.1.254)
    
    Each property defines an attribute that can be modified. The property name
    maps to the attribute name and return value to the type. For example, to 
    specify custom endpoint settings::
    
        vpn.modify_attribute(
            enabled=True,
            nat_t=True,
            force_nat_t=True,
            ssl_vpn_portal=False,
            ssl_vpn_tunnel=True,
            ipsec_vpn=True)
    """

    def __init__(self, **meta):
        super(InternalEndpoint, self).__init__(**meta)

    @property
    def enabled(self):
        """
        Is this VPN endpoint enabled
        
        :return: True, False
        :rtype: boolean
        """
        return self.data.get('enabled')

    @property
    def force_nat_t(self):
        """
        Is force NAT-T enabled
        
        :return: True, False
        :rtype: boolean
        """
        return self.data.get('force_nat_t')
    
    @property
    def nat_t(self):
        """
        Is NAT-T enabled
        
        :return: True, False
        :rtype: boolean
        """
        return self.data.get('nat_t')

    @property
    def ssl_vpn_portal(self):
        """
        Whether SSL VPN portal is enabled
        
        :return: True, False
        :rtype: boolean
        """
        return self.data.get('ssl_vpn_portal')
    
    @property
    def ssl_vpn_tunnel(self):
        """
        Whether SSL VPN Tunnel is enabled
        
        :return: True, False
        :rtype: boolean
        """
        return self.data.get('ssl_vpn_tunnel')
    
    @property
    def ipsec_vpn(self):
        """
        Whether IPSEC vpn is enabled on this VPN interface
        
        :return: True, False
        :rtype: boolean
        """
        return self.data.get('ipsec_vpn')
        
    @property
    def physical_interface(self):
        """
        Read-only referenced physical interface for this endpoint.
        """
        pass


class VirtualResource(SubElement):
    """
    A Virtual Resource is a container placeholder for a virtual engine
    within a Master Engine. When creating a virtual engine, each virtual
    engine must have a unique virtual resource for mapping. The virtual
    resource has an identifier (vfw_id) that specifies the engine ID for
    that instance.

    This is called as a resource of an engine. To view all virtual
    resources::

        list(engine.virtual_resource.all())
    """

    def __init__(self, **meta):
        super(VirtualResource, self).__init__(**meta)

    def create(self, name, vfw_id, domain='Shared Domain',
               show_master_nic=False, connection_limit=0):
        """
        Create a new virtual resource. Called through engine
        reference::

            engine.virtual_resource.create(....)

        :param str name: name of virtual resource
        :param int vfw_id: virtual fw identifier
        :param str domain: name of domain to install, (default Shared)
        :param bool show_master_nic: whether to show the master engine NIC ID's
               in the virtual instance
        :param int connection_limit: whether to limit number of connections for
            this instance
        :return: href of new virtual resource
        :rtype: str
        """
        allocated_domain = domain_helper(domain)
        json = {'name': name,
                'connection_limit': connection_limit,
                'show_master_nic': show_master_nic,
                'vfw_id': vfw_id,
                'allocated_domain_ref': allocated_domain}

        return prepared_request(
            CreateElementFailed,
            href=self.href,
            json=json
        ).create().href

    @property
    def allocated_domain_ref(self):
        """
        Domain that this virtual engine is allocated in. 'Shared Domain' is
        is the default if no domain is specified.
        ::

            >>> for resource in engine.virtual_resource:
            ...   resource, resource.allocated_domain_ref
            ... 
            (VirtualResource(name=ve-1), AdminDomain(name=Shared Domain))
            (VirtualResource(name=ve-8), AdminDomain(name=Shared Domain))

        :return: AdminDomain element
        :rtype: AdminDomain
        """
        return Element.from_href(self.data.get('allocated_domain_ref'))

    @property
    def connection_limit(self):
        """
        Maximum connections allowed by this virtual engine

        :return: connection limit
        :rtype: int
        """
        return self.data.get('connection_limit')

    @property
    def vfw_id(self):
        """
        Virtual fw identifier. This is unique per virtual engine.

        :return: vfw id
        :rtype: int
        """
        return self.data.get('vfw_id')

    @property
    def show_master_nic(self):
        """
        Show the Physical Interface IDs of the Master NGFW Engine in the
        interface properties of the Virtual NGFW Engine.

        :return: True, False if engine can see master engine nic order
        :rtype: bool
        """
        return self.data.get('show_master_nic')
