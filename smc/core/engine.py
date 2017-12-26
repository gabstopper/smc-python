from smc.compat import min_smc_version
from smc.elements.helpers import domain_helper, location_helper
from smc.base.model import Element, \
    SubElement, lookup_class, SubElementCreator
from smc.api.exceptions import UnsupportedEngineFeature,\
    UnsupportedInterfaceType, TaskRunFailed, EngineCommandFailed,\
    SMCConnectionError, CertificateError
from smc.core.node import Node
from smc.core.resource import Snapshot, PendingChanges
from smc.core.interfaces import InterfaceCollection, InterfaceOptions,\
    LoopbackCollection
from smc.administration.tasks import TaskOperationPoller
from smc.elements.other import prepare_blacklist
from smc.elements.network import Alias
from smc.vpn.elements import VPNSite
from smc.routing.bgp import BGP
from smc.routing.ospf import OSPF, OSPFProfile
from smc.core.route import Antispoofing, Routing, Routes, PolicyRoute
from smc.core.contact_address import ContactAddressCollection
from smc.core.properties import AddOn, AntiVirus, Layer2Settings, FileReputation,\
    SidewinderProxy, UrlFiltering, Sandbox, TLSInspection, DNSAddress,\
    DefaultNAT
from smc.elements.servers import LogServer
from smc.base.collection import create_collection, sub_collection
from smc.base.util import element_resolver
from smc.administration.access_rights import AccessControlList
from smc.base.decorators import cached_property, cacheable_resource
from smc.administration.certificates.vpn import GatewayCertificate


class Engine(AddOn, Element):
    """
    An engine is the top level representation of a firewall, IPS
    or virtualized software.

    Engine can be referenced directly and will be loaded when attributes
    are accessed::

        >>> from smc.core.engine import Engine
        >>> engine = Engine('testfw')
        >>> print(engine.href)
        http://1.1.1.1:8082/6.1/elements/single_fw/39550

    Generically search for engines of all types::

        >>> list(Engine.objects.all())
        [Layer3Firewall(name=i-06145fc6c59a04335 (us-east-2a)), FirewallCluster(name=sg_vm),
        Layer3VirtualEngine(name=ve-5), MasterEngine(name=master-eng)]
        
    Or only search for specific engine types::

        >>> from smc.core.engines import Layer3Firewall
        >>> list(Layer3Firewall.objects.all())
        [Layer3Firewall(name=i-06145fc6c59a04335 (us-east-2a))]

    Engine types are defined in :class:`smc.core.engines`.
    """
    typeof = 'engine_clusters'

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
                try:
                    domain_server = {'rank': num, 'ne_ref' : server.href}
                except AttributeError:
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
        self.update(name=name)
        self.vpn.internal_gateway.rename(name)
    
    @property
    def log_server(self):
        """
        Log server for this engine.

        :return: The specified log server
        :rtype: LogServer
        """
        return Element.from_href(self.log_server_ref)
    
    @property
    def location(self):
        """
        The location for this engine (may be Default).

        :param value: location to assign engine. Can be name, str href,
            or Location element. If name, it will be automatically created
            if a Location with the same name doesn't exist.
        :raises UpdateElementFailed: failure to update element
        :return: :class:`smc.elements.other.Location` or None
        """
        return Element.from_href(self.location_ref)
    
    @location.setter
    def location(self, value):
        self.data.update(location_ref=location_helper(value))
        
    @property
    def default_nat(self):
        """
        Configure default nat on the engine. Default NAT provides automatic
        NAT without the requirement to add specific NAT rules. This is a
        more common configuration for outbound traffic. Inbound traffic
        will still require specific NAT rules for redirection.
        
        :rtype: DefaultNAT
        """
        if 'default_nat' in self.data:
            return DefaultNAT(self)
        raise UnsupportedEngineFeature( 
            'This engine type does not support default NAT.')
    
    @property
    def dns(self):
        """
        Current DNS entries for the engine. Add and remove DNS entries.
        This resource is iterable and yields instances of
        :class:`smc.core.properties.DNSEntry`.
        Example of adding entries::
        
            >>> from smc.elements.servers import DNSServer
            >>> server = DNSServer.create(name='mydnsserver', address='10.0.0.1')
            >>> engine.dns.add(['8.8.8.8', server])
            >>> engine.update()
            'http://172.18.1.151:8082/6.4/elements/single_fw/948'
            >>> list(engine.dns)
            [DNSEntry(rank=0,value=8.8.8.8,ne_ref=None),
             DNSEntry(rank=1,value=None,ne_ref=DNSServer(name=mydnsserver))]
        
        :rtype: DNSAddress
        """
        return DNSAddress(self)

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
        
        :raises UnsupportedEngineFeature: requires layer 3 engine    
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
        
        :raises UnsupportedEngineFeature: not supported on virtual engines
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
        
        :raises UnsupportedEngineFeature: not supported on virtual engine
        :rtype: Sandbox
        """    
        if not self.type.startswith('virtual'):
            return Sandbox(self)
        raise UnsupportedEngineFeature(
            'Enabling sandbox should be done on the Master Engine, not '
            'directly on the virtual engine.')
    
    @property
    def tls_inspection(self):
        """    
        TLS Inspection settings manage certificates assigned to the
        engine for TLS server decryption (inbound) and TLS client
        decryption (outbound). In order to enable either, you must
        first assign certificates to the engine.
        Example of adding TLSServerCredentials to an engine::
        
            >>> engine = Engine('myfirewall')
            >>> tls = TLSServerCredential('server2.test.local')
            >>> engine.tls_inspection.add_tls_credential([tls])
            >>> engine.tls_inspection.server_credentials
            [TLSServerCredential(name=server2.test.local)]
        
        :rtype: TLSInspection
        """
        return TLSInspection(self)
    
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
        
        :raises UnsupportedEngineFeature: requires layer 3 engine
        :rtype: Layer2Settings
        """
        if 'l2fw_settings' in self.data:
            return Layer2Settings(self)
        raise UnsupportedEngineFeature( 
            'Layer2FW settings are only supported on layer 3 engines using '
            'engine and SMC version >= 6.3')
    
    @property
    def nodes(self):
        """
        Return a list of child nodes of this engine. This can be
        used to iterate to obtain access to node level operations
        ::
        
            >>> print(engine.nodes)
            [Node(name=myfirewall node 1)]
        
        :return: nodes for this engine
        :rtype: list(Node)
        """
        return Node._load(self)

    @property
    def permissions(self):
        """
        Retrieve the permissions for this engine instance.
        ::

            >>> from smc.core.engine import Engine
            >>> engine = Engine('myfirewall')
            >>> for x in engine.permissions:
            ...   print(x)
            ... 
            AccessControlList(name=ALL Elements)
            AccessControlList(name=ALL Firewalls)

        :raises UnsupportedEngineFeature: requires SMC version >= 6.1
        :return: access control list permissions
        :rtype: list(AccessControlList)
        """
        acl_list = list(AccessControlList.objects.all())
        def acl_map(elem_href):
            for elem in acl_list:
                if elem.href == elem_href:
                    return elem
        
        acls = self.make_request(
            UnsupportedEngineFeature,
            resource='permissions')
        for acl in acls['granted_access_control_list']:
            yield(acl_map(acl))

    @property
    def pending_changes(self):
        """
        Pending changes provides insight into changes on an engine that are
        pending approval or disapproval. Feature requires SMC >= v6.2.

        :raises UnsupportedEngineFeature: SMC version >= 6.2 is required to
            support pending changes
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
        for alias in self.make_request(resource='alias_resolving'):
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
        self.make_request(
            EngineCommandFailed,
            method='create',
            resource='blacklist',
            json=prepare_blacklist(src, dst, duration, **kw))

    def blacklist_flush(self):
        """
        Flush entire blacklist for engine

        :raises EngineCommandFailed: flushing blacklist failed with reason
        :return: None
        """
        self.make_request(
            EngineCommandFailed,
            method='delete',
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
        A simple query would look like::
        
            for bl_entry in engine.blacklist_show():
                print(bl_entry)
        
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
        self.make_request(
            EngineCommandFailed,
            method='create',
            resource='add_route',
            params={'gateway': gateway,
                    'network': network})

    @property
    def policy_routing(self):
        """
        Configure policy based routes on the engine. The
        policy_routing node is also iterable and yields
        instances of :class:`smc.core.route.PolicyRouteEntry`.
        ::
            
            engine.policy_routing.create(
                source='172.18.1.150/32', 
                destination='8.8.8.8/32',
                gateway_ip='10.0.0.1')
        
        :rtype: PolicyRoute  
        """
        if 'policy_route' in self.data:
            return PolicyRoute(self)
        raise UnsupportedEngineFeature( 
            'Policy routing is only supported on layer 3 engine types')
    
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
        return Routing(href=self.get_relation('routing'))

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
            result = self.make_request(
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
        return Antispoofing(href=self.get_relation('antispoofing'))

    @property
    def internal_gateway(self):
        """
        Engine level VPN gateway information. This is a link from
        the engine to VPN level settings like VPN Client, Enabling/disabling
        an interface, adding VPN sites, etc.
        Example of adding a new VPN site to the engine's site list with
        associated networks::
        
            >>> network = Network.get_or_create(name='mynetwork', ipv4_network='1.1.1.0/24')
            Network(name=mynetwork)
            >>> engine.internal_gateway.vpn_site.create(name='mynewsite', site_element=[network])
            VPNSite(name=mynewsite)

        :raises UnsupportedEngineFeature: internal gateway is only supported on layer 3
            engine types.
        :return: this engines internal gateway
        :rtype: InternalGateway
        """
        result = self.make_request(
            UnsupportedEngineFeature,
            resource='internal_gateway')
        if result:
            return InternalGateway(**result[0])

    @cacheable_resource
    def vpn(self):
        """
        VPN configuration for the engine.
        
        :raises: UnsupportedEngineFeature: VPN is only supported on layer 3
            engines.
        :rtype: VPN
        """
        return VPN(self)

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
        return self.vpn.internal_endpoint

    @property
    def virtual_resource(self):
        """
        Available on a Master Engine only.

        To get all virtual resources call::

            engine.virtual_resource.all()

        :raises UnsupportedEngineFeature: master engine only
        :return: collection of `.VirtualResource`
        :rtype: create_collection
        """
        return create_collection(
            self.get_relation(
                'virtual_resources',
                UnsupportedEngineFeature),
            VirtualResource)

    @property
    def contact_addresses(self):
        """
        Contact addresses are NAT addresses that are assigned to interfaces.
        These are used when a component needs to communicate with another
        component through a NAT'd connection. For example, if a firewall is
        known by a pubic address but the interface uses a private address,
        you would assign the public address as a contact address for that
        interface. 
        
        .. note:: Contact addresses are only supported with SMC >= 6.2.
        
        Obtain all eligible interfaces for contact addressess::
        
            >>> engine = Engine('dingo')
            >>> for ca in engine.contact_addresses:
            ...   ca
            ... 
            ContactAddressInterface(interface_id=11, interface_ip=10.10.10.20)
            ContactAddressInterface(interface_id=120, interface_ip=120.120.120.100)
            ContactAddressInterface(interface_id=0, interface_ip=1.1.1.1)
            ContactAddressInterface(interface_id=12, interface_ip=3.3.3.3)
            ContactAddressInterface(interface_id=12, interface_ip=17.17.17.17)
        
        .. seealso:: :py:mod:`smc.core.contact_address`

        :rtype: ContactAddressCollection
        """
        return ContactAddressCollection(self)

    @property
    def interface_options(self):
        """
        Interface options specify settings related to setting primary/
        backup management, outgoing, and primary/backup heartbeat
        interfaces. For example, set primary management interface
        (this unsets it from the currently assigned interface)::
        
            engine.interface_options.set_primary_mgt(10)
        
        Obtain the primary management interface::
        
            print(engine.interface_options.primary_mgt)
        
        :rtype: InterfaceOptions
        """
        return InterfaceOptions(self)
    
    @property
    def interface(self):
        """
        Get all interfaces, including non-physical interfaces such
        as tunnel or capture interfaces. These are returned as Interface
        objects and can be used to load specific interfaces to modify, etc.
        ::

            for interfaces in engine.interface:
                ......

        :rtype: InterfaceCollection

        See :class:`smc.core.interfaces.Interface` for more info
        """
        return InterfaceCollection(engine=self)

    @property
    def physical_interface(self):
        """
        Returns a PhysicalInterface. This property can be used to
        add physical interfaces to the engine. For example::

            engine.physical_interface.add_inline_interface(....)
            engine.physical_interface.add_layer3_interface(....)

        :raises UnsupportedInterfaceType: engine doesn't support this type
        :rtype: InterfaceCollection
        """
        return InterfaceCollection(
            engine=self, rel='physical_interface')

    @property
    def virtual_physical_interface(self):
        """ Master Engine virtual instance only

        A virtual physical interface is for a master engine virtual instance.
        This interface type is just a subset of a normal physical interface
        but for virtual engines. This interface only sets Auth_Request and
        Outgoing on the interface.

        To view all interfaces for a virtual engine::

            for intf in engine.virtual_physical_interface:
                print(intf)

        :raises UnsupportedInterfaceType: supported on virtual engines only
        :rtype: InterfaceCollection
        """
        return InterfaceCollection(
            engine=self, rel='virtual_physical_interface')

    @property
    def tunnel_interface(self):
        """
        Get only tunnel interfaces for this engine node.

        :raises UnsupportedInterfaceType: supported on layer 3 engine only
        :rtype: InterfaceCollection
        """
        return InterfaceCollection(
            engine=self, rel='tunnel_interface')

    @property
    def loopback_interface(self):
        """
        Retrieve any loopback interfaces for this engine.
        Loopback interfaces are only supported on layer 3 firewall types.
        
        Retrieve all loopback addresses::
        
            for loopback in engine.loopback_interface:
                print(loopback)
        
        :raises UnsupportedInterfaceType: supported on layer 3 engine only
        :rtype: LoopbackCollection
        """
        if self.type in ('single_fw', 'fw_cluster', 'virtual_fw'):
            return LoopbackCollection(self)
        raise UnsupportedInterfaceType(
            'Loopback addresses are only supported on layer 3 firewall types')
    
    @property
    def modem_interface(self):
        """
        Get only modem interfaces for this engine node.

        :raises: UnsupportedInterfaceType: modem interfaces are only supported
            on layer 3 engines
        :return: list of dict entries with href,name,type, or None
        """
        return self.make_request(
            UnsupportedInterfaceType,
            resource='modem_interface')

    @property
    def adsl_interface(self):
        """
        Get only adsl interfaces for this engine node.

        :raises UnsupportedInterfaceType: adsl interfaces are only supported
            on layer 3 engines
        :return: list of dict entries with href,name,type, or None
        """
        return self.make_request(
            UnsupportedInterfaceType,
            resource='adsl_interface')

    @property
    def wireless_interface(self):
        """
        Get only wireless interfaces for this engine node.

        :raises UnsupportedInterfaceType: wireless interfaces are only
            supported on layer 3 engines
        :return: list of dict entries with href,name,type, or None
        """
        return self.make_request(
            UnsupportedInterfaceType,
            resource='wireless_interface')

    @property
    def switch_physical_interface(self):
        """
        Get only switch physical interfaces for this engine node.

        :raises UnsupportedInterfaceType: wireless interfaces are only
            supported on layer 3 engines
        :return: list of dict entries with href,name,type, or None
        """
        return self.make_request(
            UnsupportedInterfaceType,
            resource='switch_physical_interface')

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
        task = self.make_request(
            TaskRunFailed,
            method='create',
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
        task = self.make_request(
            TaskRunFailed,
            method='create',
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
            self.make_request(
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
            self.get_relation('snapshots', EngineCommandFailed), Snapshot)

    def __unicode__(self):
        return u'{0}(name={1})'.format(
            lookup_class(self.type).__name__, self.name)


class VPN(object):
    """
    VPN is the top level interface to all engine based VPN settings.
    To enable IPSEC, SSL or SSL VPN on the engine, enable on the
    endpoint.
    """
    def __init__(self, engine):
        self.engine = engine
    
    @cached_property
    def internal_gateway(self):
        result = self.engine.make_request(
            UnsupportedEngineFeature,
            resource='internal_gateway') 
        if result: 
            return InternalGateway(**result[0]) 
    
    @property
    def vpn_client(self):
        """
        VPN Client settings for this engine.
        
        Alias for internal_gateway.
        
        :rtype: InternalGateway
        """
        return self.internal_gateway
    
    @property
    def sites(self):
        """
        VPN sites configured for this engine
        
        :rtype: VPNSite
        """
        return create_collection( 
            self.internal_gateway.get_relation('vpn_site'), 
            VPNSite) 
    
    def add_site(self, name, site_elements=None):
        """
        Add a VPN site with site elements to this engine.
        VPN sites identify the sites with protected networks
        to be included in the VPN.
        Add a network and new VPN site::
        
            >>> net = Network.get_or_create(name='wireless', ipv4_network='192.168.5.0/24')
            >>> engine.vpn.add_site(name='wireless', site_elements=[net])
            VPNSite(name=wireless)
            >>> list(engine.vpn.sites)
            [VPNSite(name=dingo - Primary Site), VPNSite(name=wireless)]
        
        :param str name: name for VPN site
        :param list site_elements: network elements for VPN site
        :type site_elements: list(str,Element)
        :raises ElementNotFound: if site element is not found
        :raises UpdateElementFailed: failed to add vpn site
        :rtype: VPNSite
        
        .. note:: Update is immediate for this operation.
        """
        site_elements = site_elements if site_elements else []
        return self.sites.create(
            name, site_elements)
        
    @property
    def internal_endpoint(self):
        """
        Internal endpoints to enable VPN for the engine.
        
        :rtype: InternalEndpoint
        """
        return sub_collection( 
            self.internal_gateway.get_relation('internal_endpoint'), 
            InternalEndpoint) 
    
    def loopback_endpoint(self):
        pass
    
    @property
    def gateway_profile(self):
        """
        Gateway Profile for this VPN. This is only a valid setting
        on layer 3 firewalls.
        
        :rtype: GatewayProfile
        """
        return Element.from_href(self.internal_gateway.gateway_profile)
    
    @property
    def gateway_settings(self):
        """   
        A gateway settings profile defines VPN specific settings related
        to timers such as negotiation retries (min, max) and mobike
        settings. Gateway settings are only present on layer 3 FW
        types.

        :rtype: GatewaySettings

        .. note::
            This can return None on layer 3 firewalls if VPN is not
            enabled.
        """
        return Element.from_href(
            self.engine.data.get('gateway_settings_ref'))
    
    @property
    def gateway_certificate(self):
        """
        A Gateway Certificate is used by the engine for securing
        communications such as VPN. You can also check the expiration,
        view the signing CA and renew the certificate from this element.
        
        :return: GatewayCertificate
        :rtype: list
        """
        return [GatewayCertificate(**cert)
                for cert in \
                self.internal_gateway.make_request(resource='gateway_certificate')]

    def generate_certificate(self, common_name, public_key_algorithm='rsa',
            signature_algorithm='rsa_sha_512', key_length=2048,
            signing_ca=None):
        """
        Generate an internal gateway certificate used for VPN on this engine.
        Certificate request should be an instance of VPNCertificate.

        :param: str common_name: common name for certificate
        :param str public_key_algorithm: public key type to use. Valid values
            rsa, dsa, ecdsa.
        :param str signature_algorithm: signature algorithm. Valid values
            dsa_sha_1, dsa_sha_224, dsa_sha_256, rsa_md5, rsa_sha_1, rsa_sha_256,
            rsa_sha_384, rsa_sha_512, ecdsa_sha_1, ecdsa_sha_256, ecdsa_sha_384,
            ecdsa_sha_512. (Default: rsa_sha_512)
        :param int key_length: length of key. Key length depends on the key
            type. For example, RSA keys can be 1024, 2048, 3072, 4096. See SMC
            documentation for more details.
        :param str,VPNCertificateCA signing_ca: by default will use the
            internal RSA CA
        :raises CertificateError: error generating certificate
        :return: GatewayCertificate
        """
        return GatewayCertificate._create(self, common_name, public_key_algorithm,
            signature_algorithm, key_length, signing_ca)


class InternalGateway(SubElement):
    """
    InternalGateway represents the engine side VPN configuration.
    An Internal Gateway correlates to the VPN Client area within
    the SMC.
    Each layer 3 engine has only one internal gateway.

    List endpoints where VPN can be enabled::

        >>> list(engine.vpn.internal_endpoint)
        [InternalEndpoint(name=10.0.0.254), InternalEndpoint(name=172.18.1.254)]

    """
    typeof = 'internal_gateway'

    def rename(self, name):
        self._del_cache() # Engine update changes this ETag
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
            self.get_relation('vpn_site'),
            VPNSite)

    def add_site(self, name, site_elements=None):
        """
        Add a VPN site with site elements to this engine.
        VPN sites identify the sites with protected networks
        to be included in the VPN.
        Add a network and new VPN site::
        
            >>> net = Network.get_or_create(name='wireless', ipv4_network='192.168.5.0/24')
            >>> engine.internal_gateway.add_site(name='wireless', site_elements=[net])
            VPNSite(name=wireless)
            >>> list(engine.internal_gateway.vpn_site)
            [VPNSite(name=dingo - Primary Site), VPNSite(name=wireless)]
        
        :param str name: name for VPN site
        :param list site_elements: network elements for VPN site
        :type site_elements: list(str,Element)
        :raises ElementNotFound: if site element is not found
        :raises UpdateElementFailed: failed to add vpn site
        :rtype: VPNSite
        
        .. note:: Update is immediate for this operation.
        """
        site_elements = site_elements if site_elements else []
        return self.vpn_site.create(
            name, site_elements)
    
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
            self.get_relation('internal_endpoint'),
            InternalEndpoint)

    def gateway_certificate(self):
        """
        :return: list
        """
        return self.make_request(resource='gateway_certificate')

    def generate_certificate(self, certificate_request):
        """
        Generate an internal gateway certificate used for VPN on this engine.
        Certificate request should be an instance of VPNCertificate.

        :param: VPNCertificate certificate_request: CSR generated to provide
            a valid certificate
        :raises CertificateError: error generating certificate
        :return: None
        """
        self.make_request(
            CertificateError,
            method='create',
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
        >>> for e in engine.vpn.internal_endpoint:
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
        Physical interface for this endpoint.
        
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
    typeof = 'virtual_resource'
    
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

        return SubElementCreator(
            self.__class__,
            href=self.href,
            json=json)
        
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
