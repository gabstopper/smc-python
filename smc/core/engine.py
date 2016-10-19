import smc.actions.search as search
from smc.elements.helpers import domain_helper
from smc.elements.element import Meta
from smc.elements.util import find_link_by_name, bytes_to_unicode
from smc.api.exceptions import LoadEngineFailed, UnsupportedEngineFeature,\
    UnsupportedInterfaceType, TaskRunFailed, EngineCommandFailed,\
    SMCConnectionError
from smc.core.node import Node
from smc.core.interfaces import PhysicalInterface, Interface,\
    VirtualPhysicalInterface, TunnelInterface
from smc.actions.tasks import task_handler, Task
from smc.elements.vpn import InternalGateway
from smc.elements.other import Blacklist
from smc.api.common import SMCRequest
from smc.elements.mixins import ModifiableMixin, ExportableMixin, UnicodeMixin

class Engine(UnicodeMixin, ExportableMixin, ModifiableMixin):
    """
    Instance attributes:
    
    :ivar name: name of engine
    :ivar meta: meta information about the engine
    :ivar dict json: raw engine json
    :ivar node_type: type of node in engine
    :ivar href: href of the engine
    :ivar etag: current etag
    :ivar link: list link to engine resources
    
    Instance resources:
    
    :ivar list nodes: :py:class:`smc.core.node.Node` nodes associated with 
          this engine
    :ivar interface: :py:class:`smc.core.interfaces.Interface` interfaces 
          for this engine
    :ivar internal_gateway: :py:class:`smc.elements.vpn.InternalGateway` engine 
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
               default_nat=False, location_ref=None):
        """
        Create will return the engine configuration as a dict that is a 
        representation of the engine. The creating class will also add 
        engine specific requirements before constructing an SMCRequest
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
                result = search.element_info_as_json(self.name)
                if result and len(result) == 1:
                    self.meta = Meta(**result[0])
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
            result = search.element_by_href_as_json(self.meta.href)
            if result.get('nodes'):
                self.json = result
                self._name = self.json.get('name')
                return self
            else:
                raise LoadEngineFailed('Cannot load engine name: {}, please ensure the name ' 
                                       'is correct. An element was returned but was of type: '
                                       '{}'.format(self._name, self.meta.type))
        except LoadEngineFailed:
            raise

    @property
    def etag(self):
        #Need if making interface changes. ETag comes from engine level
        return search.element_by_href_as_smcresult(self.meta.href).etag

    @property
    def name(self):
        return bytes_to_unicode(self._name)
    
    @property
    def href(self):
        return self.meta.href
    
    @property
    def link(self):
        return self.json.get('link')

    @property
    def node_type(self):
        """
        Return the node types for this engine. Each engine will have
        only one node type so just return on the first one
        
        :return: str node type
        """
        for node in self.nodes:
            return node.node_type

    def reload(self):
        """ 
        Reload json into context, same as :func:`load`. This retrieves the
        new setting json from the SMC.
        
        :return: None
        """
        return self.load()
    
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
    
    @property
    def nodes(self):
        """
        Return a list of child nodes of this engine. This can be
        used to iterate to obtain access to node level operations
        
        :return: list :py:class:`smc.core.node.Node`
        """
        nodes = search.element_by_href_as_json(
                            find_link_by_name('nodes', self.link))
        node_list=[]
        for node in nodes:
            node_list.append(Node(meta=Meta(**node)))
        return node_list

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
        result = search.element_by_href_as_json(
                        find_link_by_name('alias_resolving', self.link))
        aliases=[]
        for alias in result:
            aliases.append(Alias(**alias))
        return aliases

    def blacklist(self, src, dst, duration=3600):
        """ 
        Add blacklist entry to engine node by name
    
        :method: POST
        :param str src: source to blacklist, can be /32 or network cidr
        :param str dst: dest to deny to, 0.0.0.0/32 indicates all destinations
        :param int duration: how long to blacklist in seconds
        :return: None
        :raises: :py:class:`smc.api.exceptions.EngineCommandFailed`
        """
        result = SMCRequest(href=find_link_by_name('blacklist', self.link),
                            json=vars(Blacklist(src, dst, duration))).create()
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
        result = SMCRequest(href=href).delete()
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
        return SMCRequest(
                    href=find_link_by_name('add_route', self.link),
                    params={'gateway': gateway, 
                            'network': network}).create()
                                  
    def routing(self):
        """ Retrieve routing json from engine node
        
        :method: GET
        :return: json representing routing configuration
        """
        return search.element_by_href_as_json(
                        find_link_by_name('routing', self.link))
       
    def routing_monitoring(self):
        """ Return route information for the engine, including gateway, networks
        and type of route (dynamic, static)
        
        :method: GET
        :return: list of routes
        """
        from collections import namedtuple
        routes=[]
        try:
            result = search.element_by_href_as_json(
                        find_link_by_name('routing_monitoring', self.link))
            for route in result.get('routing_monitoring_entry'):
                r = namedtuple('Route', route.keys())(**route)
                routes.append(r)
        except SMCConnectionError: #timeout if engine is not initialized
            pass    
        return routes
                              
    def antispoofing(self):
        """ Antispoofing interface information. By default is based on routing
        but can be modified in special cases
        
        :method: GET
        :return: dict of antispoofing settings per interface
        """
        return search.element_by_href_as_json(
                        find_link_by_name('antispoofing', self.link))
    
    @property
    def internal_gateway(self):
        """ Engine level VPN gateway information. This is a link from
        the engine to VPN level settings like VPN Client, Enabling/disabling
        an interface, adding VPN sites, etc. 
    
        :method: GET
        :return: :py:class:`smc.elements.vpn.InternalGateway`
        :raises: :py:class:`smc.api.exceptions.UnsupportedEngineFeature`
        """
        result = search.element_by_href_as_json(
                    find_link_by_name('internal_gateway', self.link))
        if not result:
            raise UnsupportedEngineFeature('This engine does not support an internal '
                                           'gateway for VPN, engine type: {}'\
                                           .format(self.node_type))
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
                                           .format(self.node_type))
        return VirtualResource(meta=Meta(href=href))
            
    @property    
    def interface(self):
        """ Get all interfaces, including non-physical interfaces such
        as tunnel or capture interfaces. These are returned as Interface 
        objects and can be used to load specific interfaces to modify, etc.

        :method: GET
        :return: :py:class:`smc.core.interfaces.Interface`
        
        See :py:class:`smc.core.interfaces.Interface` for more info
        """
        href = find_link_by_name('interfaces', self.link)
        return Interface(meta=Meta(href=href))

    @property
    def physical_interface(self):
        """ Returns a PhysicalInterface. This property can be used to
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
                                           .format(self.node_type))
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
                                           .format(self.node_type))
        return VirtualPhysicalInterface(meta=Meta(href=href))

    @property
    def tunnel_interface(self):
        """ Get only tunnel interfaces for this engine node.
        
        :method: GET
        :return: :py:class:`smc.core.interfaces.TunnelInterface`
        :raises: :py:class:`smc.api.exceptions.UnsupportedInterfaceType`
        """
        href = find_link_by_name('tunnel_interface', self.link)
        if not href:
            raise UnsupportedInterfaceType('Tunnel interfaces are only supported on '
                                           'layer 3 single engines or clusters; '
                                           'Engine type is: {}'
                                           .format(self.node_type))
        return TunnelInterface(meta=Meta(href=href))

    def modem_interface(self):
        """ Get only modem interfaces for this engine node.
        
        :method: GET
        :return: list of dict entries with href,name,type, or None
        """
        return search.element_by_href_as_json(
                        find_link_by_name('modem_interface', self.link))
    
    def adsl_interface(self):
        """ Get only adsl interfaces for this engine node.
        
        :method: GET
        :return: list of dict entries with href,name,type, or None
        """
        return search.element_by_href_as_json(
                        find_link_by_name('adsl_interface', self.link))
    
    def wireless_interface(self):
        """ Get only wireless interfaces for this engine node.
        
        :method: GET
        :return: list of dict entries with href,name,type, or None
        """
        return search.element_by_href_as_json(
                        find_link_by_name('wireless_interface', self.link))
    
    def switch_physical_interface(self):
        """ Get only switch physical interfaces for this engine node.
        
        :method: GET
        :return: list of dict entries with href,name,type, or None
        """
        return search.element_by_href_as_json(
                        find_link_by_name('switch_physical_interface', self.link))
    
    def refresh(self, wait_for_finish=True, sleep=3):
        """ Refresh existing policy on specified device. This is an asynchronous 
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
        element = SMCRequest(
                    href=find_link_by_name('refresh', self.link)).create()
        if not element.json:
            raise TaskRunFailed(element.msg)
        return task_handler(Task(**element.json), 
                            wait_for_finish=wait_for_finish,
                            sleep=sleep)

    def upload(self, policy, wait_for_finish=False, sleep=3):
        """ Upload policy to engine. This is used when a new policy is required
        for an engine, or this is the first time a policy is pushed to an engine.
        If an engine already has a policy and the intent is to re-push, then use
        :py:func:`refresh` instead.
        The policy argument can use a wildcard * to specify in the event a full 
        name is not known::
        
            engine = Engine('myfw').load()
            task = engine.upload('Amazon*', wait_for_finish=True)
            for message in task:
                print message
        
        :param str policy: name of policy to upload to engine
        :param boolean wait_for_finish: whether to wait for async responses
        :param int sleep: number of seconds to sleep if wait_for_finish=True
        :return: generator yielding updates on progress
        :raises: :py:class:`smc.api.exceptions.TaskRunFailed`
        """
        element = SMCRequest(
                    href=find_link_by_name('upload', self.link),
                    params={'filter': policy}).create()
        if not element.json: #policy not found
            raise TaskRunFailed(element.msg)
        return task_handler(Task(**element.json), 
                            wait_for_finish=wait_for_finish,
                            sleep=sleep)

    def generate_snapshot(self, filename='snapshot.zip'):
        """ Generate and retrieve a policy snapshot from the engine
        This is blocking as file is downloaded
        
        :method: GET
        :param str filename: name of file to save file to, including directory path
        :return: None
        """
        href = find_link_by_name('generate_snapshot', self.link)
        return SMCRequest(href=href, filename=filename).read()
    
    def snapshots(self):
        """ References to policy based snapshots for this engine, including
        the date the snapshot was made
        
        :method: GET
        :return: list :py:class:`smc.core.engine.Snapshot`
        :raises: :py:class:`smc.api.exceptions.EngineCommandFailed`
        """
        href = find_link_by_name('snapshots', self.link)
        snapshots=[]
        for snapshot in search.element_by_href_as_json(href):
            snapshots.append(Snapshot(**snapshot))
        return snapshots

    def __getattr__(self, value):
        raise AttributeError("You must first load the engine to access resources!")

    def __unicode__(self):
        return u'{0}(name={1})'.format(self.__class__.__name__, self.name)
  
    def __repr__(self):
        return repr(unicode(self))

class VirtualResource(UnicodeMixin):
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
    
    :param meta: meta is provided from the engine.virtual_resource method
    """
    def __init__(self, meta=None, **kwargs):
        self.meta = meta    

    @property
    def href(self):
        return self.meta.href
    
    @property
    def name(self):
        return self.meta.name
   
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
      
    def describe(self):
        """
        Retrieve full json for this virtual resource and return pretty printed
        
        :return: json text
        """
        return search.element_by_href_as_json(self.href)
    
    def all(self):
        """
        Return metadata for all virtual resources
        
            for resource in engine.virtual_resource.all():
                if resource.name == 've-6':
                    print resource.describe()
        
        :return: list VirtualResource
        """
        resources=[]
        for resource in search.element_by_href_as_json(self.meta.href):
            resources.append(VirtualResource(meta=Meta(**resource)))
        return resources
    
    def __unicode__(self):
        return u'{0}(name={1})'.format(self.__class__.__name__, self.name)
  
    def __repr__(self):
        return repr(unicode(self))

class Snapshot(object):
    """
    Policy snapshots currently held on the SMC. You can retrieve all
    snapshots at the engine level and view details of each::
    
        for snapshot in engine.snapshots:
            print snapshot.describe()
    
    Snapshots can also be downloaded::
    
        for snapshot in engine.snapshots:
            if snapshot.name == 'blah snapshot':
                snapshot.download()
                
    Snapshot filename will be snapshot.name.zip if not specified.
    
    :ivar name: name of snapshot
    """
    def __init__(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)

    def download(self, filename=None):
        """
        Download snapshot to filename
        
        :param str filename: fully qualified path including filename .zip
        :return: :py:class:`smc.api.web.SMCResult`
        :raises: :py:class:`smc.api.exceptions.EngineCommandFailed`
        """
        if not filename:
            filename = '{}{}'.format(self.name, '.zip')
        snapshot = self.describe()
        href = find_link_by_name('content', snapshot.get('link'))
        try:
            return SMCRequest(href=href, filename=filename).read()
        except IOError as e:
            raise EngineCommandFailed("Snapshot download failed: {}"
                                      .format(e))
    def describe(self):
        """
        Retrieve full json for this snapshot
        
        :return: json text
        """
        return search.element_by_href_as_json(self.href)  
    
    def __repr__(self):
        return '{0}(name={1})'.format(self.__class__.__name__, 
                                      self.name)
        
class Alias(object):
    """
    Aliases are specific to an engine instance and are typically 
    used as rule elements. They are intended to have a different value
    based on the engine that the alias is applied to. 
    
    :ivar name: name of alias
    """
    def __init__(self, **kwargs):
        self.name = None
        self.resolved_value = None
        self.alias_ref = None
        self.cluster_ref = None
        for k, v in kwargs.iteritems():
            setattr(self, k, v)
            
    def describe(self):
        return search.element_by_href_as_json(self.alias_ref)
        
    def __repr__(self):
        self.name = self.describe().get('name')
        return '{0}(name={1})'.format(self.__class__.__name__, 
                                      self.name)
