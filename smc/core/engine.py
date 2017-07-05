import smc.actions.search as search
from smc.compat import min_smc_version
from smc.elements.helpers import domain_helper
from smc.base.model import Element, prepared_request, ResourceNotFound,\
    SubElement, lookup_class, load_element
from smc.api.exceptions import UnsupportedEngineFeature,\
    UnsupportedInterfaceType, TaskRunFailed, EngineCommandFailed,\
    SMCConnectionError, CertificateError, CreateElementFailed
from smc.core.node import Node
from smc.core.resource import Snapshot, PendingChanges
from smc.core.interfaces import PhysicalInterface, \
    VirtualPhysicalInterface, TunnelInterface, Interface
from smc.administration.tasks import TaskOperationPoller
from smc.elements.other import prepare_blacklist
from smc.elements.network import Alias
from smc.vpn.elements import VPNSite
from smc.core.route import Antispoofing, Routing, Routes
from smc.core.contact_address import ContactResource
from smc.core.properties import EngineProperty
from smc.elements.servers import LogServer
from smc.base.collection import create_collection, sub_collection
from smc.base.util import element_resolver


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
                nodes=1, loopback_ndi=None,
                log_server_ref=None,
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
            node_list.append(Node._create(
                name,
                node_type,
                nodeid,
                loopback_ndi))

        domain_server_list = []
        if domain_server_address:
            for num, server in enumerate(domain_server_address):
                domain_server_list.append({
                    'rank': num, 'value': server})

        # Set log server reference, if not explicitly provided
        if not log_server_ref and node_type is not 'virtual_fw_node':
            log_server_ref = LogServer.objects.first().href

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
        if not self._meta:
            load_element(self.href)
        return self._meta.type

    @property
    def version(self):
        """
        Version of this engine. Can be none if the engine has not been
        initialized yet.

        :rtype: str or None
        """
        return self.data.get('engine_version')

    def rename(self, name):
        """
        Rename the firewall engine, nodes, and internal gateway (VPN gw)

        :return: None
        """
        for node in self.nodes:
            node.rename(name)
        try:
            del self.data
        except AttributeError:
            pass
        self.update(name=name)
        self.internal_gateway.rename(name)

    @property
    def nodes(self):
        """
        Return a list of child nodes of this engine. This can be
        used to iterate to obtain access to node level operations

        :return: nodes for this engine
        :rtype: list(Node)
        """
        return list(sub_collection(
            self.data.get_link('nodes'), Node))

    @property
    def permissions(self):
        """
        Retrieve the permissions for this engine instance.
        ::

            for acl in engine.permissions:
                print(acl, acl.granted_element)

        :return: access control list permissions
        :rtype: list(AccessControlList)
        """
        try:
            acls = self.data.get_json('permissions')
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
            if self.data.get_link('pending_changes'):
                return PendingChanges(self)
        except ResourceNotFound:
            raise UnsupportedEngineFeature(
                'Pending changes is an unsupported feature on this engine: {}'
                .format(self.type))

    def alias_resolving(self):
        """
        Alias definitions with resolved values as defined on this engine.
        Aliases can be used in rules to simplify multiple object creation
        ::

            print(list(engine.alias_resolving()))

        :return: generator :py:class:`smc.elements.network.Alias`
        """
        for alias in self.data.get_json('alias_resolving'):
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
            href=self.data.get_link('blacklist'),
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
            href=self.data.get_link('flush_blacklist')
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
            href=self.data.get_link('add_route'),
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
        return Routing(href=self.data.get_link('routing'))

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
                href=self.data.get_link('routing_monitoring')
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
        return Antispoofing(href=self.data.get_link('antispoofing'))

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
            result = self.data.get_json('internal_gateway')
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
                self.data.get_link('virtual_resources'),
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
                    ipv4.add_contact_address('10.10.10.10')

            print(list(engine.contact_addresses))    # list all

            for interfaces in engine.contact_addresses.all(): #iterate all
                print(interfaces) #ContactInterface

        .. seealso:: :py:class:`smc.core.contact_address.ContactAddress`

        :return: list :py:class:`smc.core.contact_address.ContactInterface`
        """
        return ContactResource(
            self.data.get_json('contact_addresses'))

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
            parent=self.data.get_link('interfaces'),
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
                parent=self.data.get_link('physical_interface'),
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
                parent=self.data.get_link('virtual_physical_interface'),
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
                parent=self.data.get_link('tunnel_interface'),
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
            return self.data.get_json('modem_interface')
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
            return self.data.get_json('adsl_interface')
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
            return self.data.get_json('wireless_interface')
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
            return self.data.get_json('switch_physical_interface')
        except ResourceNotFound:
            raise UnsupportedInterfaceType(
                'Switch interfaces are not supported on this engine type: {}'
                .format(self.type))

    def refresh(self, timeout=3, wait_for_finish=False, **kw):
        """
        Refresh existing policy on specified device. This is an asynchronous
        call that will return a 'follower' link that can be queried to
        determine the status of the task.
        ::

            task = engine.refresh()
            for message in task.wait():
                print('Percentage complete {}%'.format(message))

        :param int timeout: timeout between queries
        :raises TaskRunFailed: refresh failed, possibly locked policy
        :return: TaskOperationPoller
        """
        task = prepared_request(
            TaskRunFailed,
            href=self.data.get_link('refresh'),
            ).create().json

        return TaskOperationPoller(
            task=task,
            wait_for_finish=wait_for_finish,
            **kw)

    def upload(self, policy=None, timeout=5, wait_for_finish=False, **kw):
        """
        Upload policy to engine. This is used when a new policy is required
        for an engine, or this is the first time a policy is pushed to an
        engine.
        If an engine already has a policy and the intent is to re-push, then
        use :py:func:`refresh` instead.
        The policy argument can use a wildcard * to specify in the event a full
        name is not known::

            engine = Engine('myfw')
            task = engine.upload('Amazon*')
            for message in task.wait():
                print(message)

        :param str policy: name of policy to upload to engine; if None, current
            policy
        :param int timeout: timeout between queries
        :raises TaskRunFailed: upload failed with reason
        :return: TaskOperationPoller
        """
        task = prepared_request(
            TaskRunFailed,
            href=self.data.get_link('upload'),
            params={'filter': policy}
            ).create().json

        return TaskOperationPoller(
            task=task, timeout=timeout,
            wait_for_finish=wait_for_finish,
            **kw)

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
                href=self.data.get_link('generate_snapshot'),
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
            self.data.get_link('snapshots'), Snapshot)

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

        >>> list(engine.internal_gateway.internal_endpoint.all())
        [InternalEndpoint(name=10.0.0.254), InternalEndpoint(name=172.18.1.254)]

    """
    typeof = 'internal_gateway'

    def __init__(self, **meta):
        super(InternalGateway, self).__init__(**meta)

    def rename(self, name):
        self.update(name='{} Primary'.format(name))

    @property
    def vpn_site(self):
        """
        Retrieve VPN Site information for this internal gateway

        Find all configured sites for engine::

            >>> for sites in engine.internal_gateway.vpn_site:
            ...   sites
            ...
            VPNSite(name=Automatic Site for sg_vm_vpn)

        :return: collection of :class:`smc.vpn.elements.VPNSite`
        :rtype: SubElementCollection
        """
        return create_collection(
            self.data.get_link('vpn_site'), VPNSite)

    @property
    def internal_endpoint(self):
        """
        Internal Endpoints define and enable VPN settings on a
        specific interface.

        Find all internal endpoints for an engine::

            >>> for gw in engine.internal_gateway.internal_endpoint:
            ...   gw
            ...
            InternalEndpoint(name=10.0.0.254)
            InternalEndpoint(name=172.18.1.254)

        :return: collection of :class:`.InternalEndpoint`
        :rtype: SubElementCollection
        """
        return sub_collection(
            self.data.get_link('internal_endpoint'),
            InternalEndpoint)

    def gateway_certificate(self):
        """
        :return: list
        """
        return self.data.get_json('gateway_certificate')

    def gateway_certificate_request(self):
        """
        :return: list
        """
        return self.data.get_json('gateway_certificate_request')

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
            href=self.data.get_link('generate_certificate'),
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
        >>> for e in engine.internal_gateway.internal_endpoint:
        ...   print(e)
        ...
        InternalEndpoint(name=10.0.0.254)
        InternalEndpoint(name=172.18.1.254)

    Available attributes:

    :ivar bool enabled: enable this interface as a VPN endpoint
        (default: False)
    :ivar bool nat_t: enable NAT-T (default: False)
    :ivar bool force_nat_t: force NAT-T (default: False)
    :ivar bool ssl_vpn_portal: enable SSL VPN portal on the interface
        (default: False)
    :ivar bool ssl_vpn_tunnel: enable SSL VPN tunnel on the interface
        (default: False)
    :ivar bool ipsec_vpn: enable IPSEC VPN on the interface (default: False)
    :ivar bool udp_encapsulation: Allow UDP encapsulation (default: False)
    :ivar str balancing_mode: VPN load balancing mode. Valid options are:
        'standby', 'aggregate', 'active' (default: 'active')
    """

    def __init__(self, **meta):
        super(InternalEndpoint, self).__init__(**meta)

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

    Available attributes:

    :ivar int connection_limit: Maximum number of connections for this virtual
        engine. 0 means unlimited (default: 0)
    :ivar bool show_master_nic: Show the master engine NIC id's in the virtual
        engine.

    When updating this element, make modifications and call update()
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

    def set_admin_domain(self, admin_domain):
        """
        Virtual Resources can be members of an Admin Domain to provide
        delegated administration features. Assign an admin domain to
        this resource. Admin Domains must already exist.

        :param str,AdminDomain admin_domain: Admin Domain to add
        :return: None
        """
        admin_domain = element_resolver(admin_domain)
        self.data['allocated_domain_ref'] = admin_domain

    @property
    def vfw_id(self):
        """
        Read-Only virtual engine identifier. This is unique per virtual engine
        and is set when the virtual resource is created.

        :return: vfw id
        :rtype: int
        """
        return self.data.get('vfw_id')
