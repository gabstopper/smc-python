from smc.compat import min_smc_version
from smc.elements.helpers import domain_helper
from smc.base.model import Element, ResourceNotFound,\
    SubElement, lookup_class
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
from smc.routing.bgp import BGP
from smc.routing.ospf import OSPF, OSPFProfile
from smc.core.route import Antispoofing, Routing, Routes
from smc.core.contact_address import ContactResource
from smc.core.properties import AddOn, AntiVirus, Layer2Settings, FileReputation,\
    SidewinderProxy, UrlFiltering, Sandbox
from smc.elements.servers import LogServer
from smc.base.collection import create_collection, sub_collection
from smc.base.util import element_resolver
from smc.administration.access_rights import AccessControlList


class Engine(AddOn, Element):
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

        >>> list(Search.objects.context_filter('engine_clusters'))
        [Layer3Firewall(name=i-06145fc6c59a04335 (us-east-2a)), FirewallCluster(name=sg_vm),
        Layer3VirtualEngine(name=ve-5), MasterEngine(name=master-eng)]

    Instance resources:

    :ivar list nodes: :class:`smc.core.node.Node` nodes associated with
          this engine
    :ivar permissions: :class:`smc.administration.access_rights.AccessControlList`
    :ivar routing: :class:`smc.core.route.Routing` routing configuration hierarchy
    :ivar routing_monitoring: :class:`smc.core.route.Routes` current route table
    :ivar antispoofing: :class:`smc.core.route.Antispoofing` antispoofing interface
          configuration
    :ivar internal_gateway: :class:`~InternalGateway` engine
          level VPN settings
    :ivar virtual_resource: :class:`smc.core.engine.VirtualResource` for engine,
          only relevant to Master Engine
    :ivar interface: :class:`smc.core.interfaces.Interface` interfaces
          for this engine
    :ivar physical_interface: :class:`smc.core.interfaces.PhysicalInterface`
          access to physical interface settings
    :ivar tunnel_interface: :class:`smc.core.interfaces.TunnelInterface`
          retrieve or create tunnel interfaces
    :ivar snapshots: :class:`smc.core.engine.Snapshot` engine level policy
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
                if hasattr(server, 'href'):
                    domain_server = {'rank': num, 'ne_ref' : server.href}
                else:
                    domain_server = {'rank': num, 'value': server}
                
                domain_server_list.append(domain_server)

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
                ospf_profile = OSPFProfile('Default OSPFv2 Profile').href
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
            self.href
        return self._meta.type

    @property
    def version(self):
        """
        Version of this engine. Can be none if the engine has not been
        initialized yet.

        :rtype: str or None
        """
        return self.data.get('engine_version')

    @property
    def installed_policy(self):
        """
        Return the name of the policy installed on this engine. If
        no policy, None will be returned.
        
        :rtype: str or None
        """
        for node in self.nodes:
            return node.status().installed_policy
    
    def rename(self, name):
        """
        Rename the firewall engine, nodes, and internal gateway (VPN gw)

        :return: None
        """
        for node in self.nodes:
            node.rename(name)
        # Flush cache to force refresh
        self._del_cache()
        self.update(name=name)
        self.internal_gateway.rename(name)

    @property
    def antivirus(self):
        """
        AntiVirus engine settings. Note that for virtual engines
        the AV settings are configured on the Master Engine.
        Get current status::
        
            engine.antivirus.status
        
        :raises UnsupportedEngineFeature: Invalid engine type for AV
        :rtype: AntiVirus
        """
        if not self.type.startswith('virtual'):
            return AntiVirus(self)
        raise UnsupportedEngineFeature(
            'Antivirus is not supported directly on this engine type. If this '
            'is a virtual engine, AV is configured on the master engine.')
    
    @property
    def file_reputation(self):
        """
        File reputation status on engine. Note that for virtual engines
        the AV settings are configured on the Master Engine.
        Get current status::
        
            engine.file_reputation.status
            
        :raises UnsupportedEngineFeature: Invalid engine type for file rep
        :rtype: FileReputation
        """
        if not self.type.startswith('virtual'):
            return FileReputation(self)
        raise UnsupportedEngineFeature(
            'GTI should be enabled on the Master Engine not directly on the '
            'virtual engine.')
    
    @property
    def sidewinder_proxy(self):
        """
        Configure Sidewinder Proxy settings on this engine. Sidewinder
        proxy is supported on layer 3 engines and require SMC and engine
        version >= 6.1.
        Get current status::
        
            engine.sidewinder_proxy.status
            
        :rtype: SidewinderProxy
        """
        if 'sidewinder_proxy_enabled' in self.data:
            return SidewinderProxy(self)
        raise UnsupportedEngineFeature(
            'Sidewinder Proxy requires a layer 3 engine and version >= v6.1.')
    
    @property
    def url_filtering(self):
        """
        Configure URL Filtering settings on the engine.
        Get current status::
        
            engine.url_filtering.status
        
        :rtype: UrlFiltering
        """
        if not self.type.startswith('virtual'):
            return UrlFiltering(self)
        raise UnsupportedEngineFeature(
            'Enabling URL Filtering should be done on the Master Engine, not '
            'directly on the virtual engine.')
    
    @property
    def sandbox(self):
        """
        Configure sandbox settings on the engine.
        Get current status::
        
            engine.sandbox.status
        """    
        if not self.type.startswith('virtual'):
            return Sandbox(self)
        raise UnsupportedEngineFeature(
            'Enabling sandbox should be done on the Master Engine, not '
            'directly on the virtual engine.')
        
    @property
    def ospf(self):
        """
        Obtain an instance of the OSPF configuration for this engine.
        Dynamic routing is only supported on layer 3 engines and clusters.
        
        :raises UnsupportedEngineFeature: For engines that do not support
            dynamic routing capabilities
        :rtype: OSPF
        """
        if 'dynamic_routing' in self.data:
            return OSPF(self)
        raise UnsupportedEngineFeature(
            'Dynamic routing is only supported on layer 3 engine types')
        
    @property
    def bgp(self):
        """
        Obtain an instance of the BGP configuration for this engine.
        Dynamic routing is only supported on layer 3 engines and clusters.
        
        :raises UnsupportedEngineFeature: For engines that do not support
            dynamic routing capabilities
        :rtype: BGP
        """
        if 'dynamic_routing' in self.data:
            return BGP(self)
        raise UnsupportedEngineFeature( 
            'Dynamic routing is only supported on layer 3 engine types')
    
    @property
    def l2fw_settings(self):
        """
        Layer 2 Firewall Settings make it possible for a layer 3 firewall
        to run specified interfaces in layer 2 mode. This requires that
        a layer 2 interface policy is assigned to the engine and that
        inline_l2fw interfaces are created. 
        
        :rtype: Layer2Settings
        """
        if 'l2fw_settings' in self.data:
            return Layer2Settings(self)
    
    @property
    def nodes(self):
        """
        Return a list of child nodes of this engine. This can be
        used to iterate to obtain access to node level operations

        :return: nodes for this engine
        :rtype: list(Node)
        """
        return Node._load(self.data.get('nodes'))

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
            acl_list = list(AccessControlList.objects.all())
            def acl_map(elem_href):
                for elem in acl_list:
                    if elem.href == elem_href:
                        return elem
            
            acls = self.read_cmd(resource='permissions')
            for acl in acls['granted_access_control_list']:
                yield(acl_map(acl))

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
        :rtype: PendingChanges
        """
        if 'pending_changes' in self.data.links:
            return PendingChanges(self)
        
        raise UnsupportedEngineFeature(
            'Pending changes is an unsupported feature on this engine: {}'
            .format(self.type))
    
    def alias_resolving(self):
        """
        Alias definitions with resolved values as defined on this engine.
        Aliases can be used in rules to simplify multiple object creation
        ::

            fw = Engine('myfirewall')
            for alias in fw.alias_resolving():
                print(alias, alias.resolved_value)
            ...
            (Alias(name=$$ Interface ID 0.ip), [u'10.10.0.1'])
            (Alias(name=$$ Interface ID 0.net), [u'10.10.0.0/24'])
            (Alias(name=$$ Interface ID 1.ip), [u'10.10.10.1'])

        :return: generator of aliases
        :rtype: Alias
        """
        alias_list = list(Alias.objects.all())
        for alias in self.read_cmd(resource='alias_resolving'):
            yield Alias.from_engine(alias, alias_list)

    def blacklist(self, src, dst, duration=3600, **kw):
        """
        Add blacklist entry to engine node by name. For blacklist to work,
        you must also create a rule with action "Apply Blacklist".

        :param src: source address, with cidr, i.e. 10.10.10.10/32 or 'any'
        :param dst: destination address with cidr, i.e. 1.1.1.1/32 or 'any'
        :param int duration: how long to blacklist in seconds
        :raises EngineCommandFailed: blacklist failed during apply
        :return: None
        
        .. note:: If more advanced blacklist is required using source/destination
            ports and protocols (udp/tcp), use kw to provide these arguments. See
            :py:func:`smc.elements.other.prepare_blacklist` for more details.
        """
        self.send_cmd(
            EngineCommandFailed,
            resource='blacklist',
            json=prepare_blacklist(src, dst, duration, **kw))

    def blacklist_flush(self):
        """
        Flush entire blacklist for engine

        :raises EngineCommandFailed: flushing blacklist failed with reason
        :return: None
        """
        self.del_cmd(
            EngineCommandFailed,
            resource='flush_blacklist')
    
    def blacklist_show(self, **kw):
        """
        .. versionadded:: 0.5.6
            Requires pip install smc-python-monitoring
        
        Blacklist show requires that you install the smc-python-monitoring
        package. To obtain blacklist entries from the engine you need to
        use this extension to plumb the websocket to the session. If you
        need more granular controls over the blacklist such as filtering by
        source and destination address, use the smc-python-monitoring 
        package directly.
        Blacklist entries that are returned from this generator have a
        delete() method that can be called to simplify removing entries.
        
        :param kw: keyword arguments passed to blacklist query. Common setting
            is to pass max_recv=20, which specifies how many "receive" batches
            will be retrieved from the SMC for the query. At most, 200 results
            can be returned in a single query. If max_recv=5, then 1000 results
            can be returned if they exist. If less than 1000 events are available,
            the call will be blocking until 5 receives has been reached.
        :return: generator of results
        :rtype: :class:`smc_monitoring.monitors.blacklist.BlacklistEntry`
        """
        try:
            from smc_monitoring.monitors.blacklist import BlacklistQuery
        except ImportError:
            pass
        else:
            query = BlacklistQuery(self.name)
            for record in query.fetch_as_element(**kw):
                yield record
    
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
        self.send_cmd(
            EngineCommandFailed,
            resource='add_route',
            params={'gateway': gateway,
                    'network': network})

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

        :return: top level routing node
        :rtype: Routing
        """
        return Routing(href=self.data.links['routing'])

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
        :return: list of route elements
        :rtype: Routes
        """
        try:
            result = self.read_cmd(
                EngineCommandFailed,
                resource='routing_monitoring')
            
            return Routes(result)
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

        :return: top level antispoofing node
        :rtype: Antispoofing
        """
        return Antispoofing(href=self.data.links['antispoofing'])

    @property
    def internal_gateway(self):
        """
        Engine level VPN gateway information. This is a link from
        the engine to VPN level settings like VPN Client, Enabling/disabling
        an interface, adding VPN sites, etc.

        :raises UnsupportedEngineFeature: engine type does not have an internal
            gateway
        :return: this engines internal gateway
        :rtype: InternalGateway
        """
        try:
            result = self.read_cmd(resource='internal_gateway')
            if result:
                return InternalGateway(**result[0])

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
        :rtype: create_collection
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
    def vpn_endpoint(self):
        """
        A VPN endpoint is an address assigned to a layer 3 interface
        that can be enabled to turn on VPN capabilities. As an interface
        may have multiple IP addresses assigned, the endpoints are
        returned based on the address. Endpoints are properties of the
        engines Internal Gateway.
        
        :return: collection of :class:`.InternalEndpoint`
        :rtype: SubElementCollection
        """
        return self.internal_gateway.internal_endpoint
    
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

        .. seealso:: :class:`smc.core.contact_address.ContactAddress`

        :return: list of interfaces with contact addresses
        :rtype: InterfaceContactAddress
        """
        return ContactResource(
            self.read_cmd(resource='contact_addresses'))

    @property
    def interface(self):
        """
        Get all interfaces, including non-physical interfaces such
        as tunnel or capture interfaces. These are returned as Interface
        objects and can be used to load specific interfaces to modify, etc.
        ::

            for interfaces in engine.interface.all():
                ......

        :rtype: Interface

        See :class:`smc.core.interfaces.Interface` for more info
        """
        return Interface(
            parent=self.data.get_link('interfaces'),
            engine=self)

    @property
    def physical_interface(self):
        """
        Returns a PhysicalInterface. This property can be used to
        add physical interfaces to the engine. For example::

            engine.physical_interface.add_inline_interface(....)
            engine.physical_interface.add_layer3_interface(....)

        :raises UnsupportedInterfaceType: engine doesn't support this type
        :rtype: PhysicalInterface
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
        :rtype: VirtualPhysicalInterface
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
        :rtype: TunnelInterface
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
            return self.read_cmd(resource='modem_interface')
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
            return self.read_cmd(resource='adsl_interface')
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
            return self.read_cmd(resource='wireless_interface')
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
            return self.read_cmd(resource='switch_physical_interface')
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

            poller = engine.refresh()
            while not poller.done():
                poller.wait(5)
                print('Percentage complete {}%'.format(poller.task.progress))

        :param int timeout: timeout between queries
        :raises TaskRunFailed: refresh failed, possibly locked policy
        :rtype: TaskOperationPoller
        """
        task = self.send_cmd(
            TaskRunFailed,
            resource='refresh')

        return TaskOperationPoller(
            task=task, timeout=timeout,
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
        :rtype: TaskOperationPoller
        """
        task = self.send_cmd(
            TaskRunFailed,
            resource='upload',
            params={'filter': policy})

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
            self.read_cmd(
                EngineCommandFailed,
                resource='generate_snapshot',
                filename=filename)

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
    InternalGateway represents the engine side VPN configuration.
    An internal gateway is synonymous with an interface where VPN
    can be anbled.
    This will also define settings such as setting VPN sites on
    protected networks and engine level certificates.

    Since each engine has only one internal gateway, this resource
    is loaded immediately when called through engine.internal_gateway

    List endpoints where VPN can be enabled::

        >>> list(engine.vpn_endpoint)
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
        :rtype: create_collection
        """
        return create_collection(
            self.data.get_link('vpn_site'),
            VPNSite)

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
        return self.read_cmd(resource='gateway_certificate')

    def gateway_certificate_request(self):
        """
        :return: list
        """
        return self.read_cmd(resource='gateway_certificate_request')

    def generate_certificate(self, certificate_request):
        """
        Generate an internal gateway certificate used for VPN on this engine.
        Certificate request should be an instance of VPNCertificate.

        :param: VPNCertificate certificate_request: CSR generated to provide
            a valid certificate
        :raises CertificateError: error generating certificate
        :return: None
        """
        self.send_cmd(
            CertificateError,
            resource='generate_certificate',
            json=vars(certificate_request))
    

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

    def enable_by_interface_id(self, interface_id, ipaddress=None):
        pass
    
    @property
    def interface_id(self):
        """
        Interface ID for this VPN endpoint
        
        :return: str interface id
        """
        return self.physical_interface.interface_id
        
    @property
    def physical_interface(self):
        """
        Read-only referenced physical interface for this endpoint.
        
        :rtype: PhysicalInterface
        """
        return Element.from_href(self.data.get('physical_interface'))
    
    
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

        location = self._request(
            CreateElementFailed,
            href=self.href,
            json=json
        ).create().href
        
        return VirtualResource(
            name=name,
            href=location,
            type='virtual_resource')

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
