from smc.elements.element import SMCElement, Meta
from smc.elements.other import Blacklist
from smc.elements.interfaces import VirtualPhysicalInterface, PhysicalInterface, Interface,\
    TunnelInterface
import smc.actions.search as search
import smc.api.common as common_api
from smc.elements.util import find_link_by_name
from smc.api.exceptions import CreateEngineFailed, LoadEngineFailed,\
    UnsupportedEngineFeature, UnsupportedInterfaceType
from smc.elements.vpn import InternalGateway
from smc.elements.helpers import domain_helper


class Engine(object):
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
    
        :ivar list nodes: (Node) nodes associated with this engine
        :ivar interface: (Interface) interfaces for this engine
        :ivar internal_gateway: (InternalGateway) engine level VPN settings
        :ivar virtual_resource: (VirtualResource) for engine, only relavant to Master Engine
        :ivar physical_interface: (PhysicalInterface) access to physical interface settings
        :ivar tunnel_interface: (TunnelInterface) retrieve or create tunnel interfaces
    """
    def __init__(self, name, meta=None, **kwargs):
        self.name = name
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
        engine specific requirements before adding it to an SMCElement
        and sending to SMC (which will serialize the dict to json).
        
        :param name: name of engine
        :param str node_type: comes from class attribute of engine type
        :param dict physical_interfaces
        :param int nodes: number of nodes for engine
        :param str log_server_ref: href of log server
        :param list domain_server_address
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
        """ When engine is loaded, save the attributes that are needed. 
        Engine load can be called directly::
        
            engine = Engine('myengine').load()
            
        or by calling collection.describe_xxx methods::
        
            for fw in describe_single_fws():
                if fw.name == 'myfw':
                    engine = fw.load()
                    
        Call this to reload settings, useful if changes are made and new 
        configuration references or updated attributes are needed. Metadata
        is set upon load either via collection.describe_* function or directly.
        """
        if not self.meta:
            result = search.element_info_as_json(self.name)
            if result:
                self.meta = Meta(**result)
            else:
                raise LoadEngineFailed("Cannot load engine name: {}, please ensure the name is " 
                                        "correct and the engine exists.".format(self.name)) 
        result = search.element_by_href_as_json(self.meta.href)
        if result.get('nodes'):
            self.json = result
            self.nodes = []
            for node in self.json.get('nodes'):
                for node_type, data in node.iteritems():
                    new_node = Node(node_type, data)
                    self.nodes.append(new_node)
            return self
        else:
            raise LoadEngineFailed("Cannot load engine name: {}, please ensure the name is " 
                                    "correct. An element was returned but was of type: {}"
                                    .format(self.name, self.meta.type))
    @property
    def etag(self):
        if self.meta:
            return search.element_by_href_as_smcresult(self.meta.href).etag
    
    @property
    def href(self):
        if self.meta:
            return self.meta.href
    
    @property
    def link(self):
        if hasattr(self, 'json'):
            return self.json.get('link')
        else:
            raise AttributeError("You must first load the engine to access resources!")
    
    @property
    def node_type(self):
        for node in self.node():
            return node.get('type')

    def reload(self):
        """ 
        Reload json into context, same as :py:func:`load`
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
    
    def modify_attribute(self, **kwargs):
        """
        Modify a top level engine attribute. This is limited to key/value pairs
        that have single values, or where the value is a dict::
            
            engine.modify_attribute(passive_discard_mode=False)
            engine.modify_attribute(antivirus={'antivirus_enabled':True, 
                                               'virus_log_level':'stored'})
            engine.modify_attribute(gti_settings={'file_reputation_context': 
                                                  'gti_cloud_only'})
        :param kwargs: (key=value)
        """
        for k, v in kwargs.iteritems():
            if isinstance(self.json.get(k), dict):
                self.json[k].update(v)
            else: #single key/value
                self.json.update({k: v})
        return SMCElement(href=self.href, json=self.json,
                          etag=self.etag).update()

    def node(self):
        """ Return node/s references for this engine. For a cluster this will
        contain multiple entries. 
        
        :method: GET
        :return: list dict with metadata {href, name, type}
        """
        return search.element_by_href_as_json(
                        find_link_by_name('nodes', self.link))
  
    def alias_resolving(self):
        """ Alias definitions defined for this engine 
        Aliases can be used in rules to simplify multiple object creation
        
        :method: GET
        :return: dict list [{alias_ref: str, 'cluster_ref': str, 'resolved_value': []}]
        """
        return search.element_by_href_as_json(
                        find_link_by_name('alias_resolving', self.link))
       
    def blacklist(self, src, dst, duration=3600):
        """ Add blacklist entry to engine node by name
    
        :method: POST
        :param str src: source to blacklist, can be /32 or network cidr
        :param str dst: dest to deny to, 0.0.0.0/32 indicates all destinations
        :param int duration: how long to blacklist in seconds
        :return: SMCResult (href attr set with blacklist entry)
        """
        return SMCElement(href=find_link_by_name('blacklist', self.link),
                          json=vars(Blacklist(src, dst, duration))).create()
    
    def blacklist_flush(self):
        """ Flush entire blacklist for node name
    
        :method: DELETE
        :return: SMCResult (msg attribute set if failure)
        """
        return common_api.delete(find_link_by_name('flush_blacklist', self.link))
    
    def add_route(self, gateway, network):
        """ Add a route to engine. Specify gateway and network. 
        If this is the default gateway, use a network address of
        0.0.0.0/0.
        
        .. note: This will fail if the gateway provided does not have a 
                 corresponding interface on the network.
        
        :method: POST
        :param str gateway: gateway of an existing interface
        :param str network: network address in cidr format
        :return: SMCResult
        """
        return SMCElement(
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
        :return: dict of dict list entries representing routes
        """
        return search.element_by_href_as_json(
                        find_link_by_name('routing_monitoring', self.link))
                              
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
        :raises UnsupportedEngineFeature: this feature doesnt exist for engine type
        """
        result = search.element_by_href_as_json(
                    find_link_by_name('internal_gateway', self.link))
        if not result:
            raise UnsupportedEngineFeature('This engine does not support an internal '
                                           'gateway for VPN, engine type: {}'\
                                           .format(self.node_type))
        for gw in result:
            igw = InternalGateway(
                        **search.element_by_href_as_json(gw.get('href')))
        return igw
    
    @property
    def virtual_resource(self):
        """ Master Engine only 
        
        To get all virtual resources call::
            
            engine.virtual_resource.all()
            
        :return: :py:class:`smc.elements.engine.VirtualResource`
        :raises UnsupportedEngineFeature: this feature doesn't exist for engine type
        """
        href = find_link_by_name('virtual_resources', self.link)
        if not href:
            raise UnsupportedEngineFeature('This engine does not support virtual '
                                           'resources; engine type: {}'\
                                           .format(self.node_type))
        return VirtualResource(meta=Meta(name=None, href=href, type='virtual_resource'))
        
            
    @property    
    def interface(self):
        """ Get all interfaces, including non-physical interfaces such
        as tunnel or capture interfaces. These are returned as Interface 
        objects and can be used to load specific interfaces to modify, etc.

        :method: GET
        :return: :py:class:smc.elements.interfaces.Interface`
        
        See :py:class:`smc.elements.engines.Interface` for more info
        """
        href = find_link_by_name('interfaces', self.link)
        return Interface(meta=Meta(href=href, name=None, type=None))
    
    @property
    def physical_interface(self):
        """ Returns a PhysicalInterface. This property can be used to
        add physical interfaces to the engine. For example::
        
            engine.physical_interface.add_single_node_interface(....)
            engine.physical_interface.add_node_interface(....)
       
        :method: GET
        :return: :py:class:`smc.elements.interfaces.PhysicalInterface`
        """
        href = find_link_by_name('physical_interface', self.link)
        print "called phys int"
        if not href: #not supported by virtual engines
            raise UnsupportedInterfaceType('Engine type: {} does not support the '
                                           'physical interface type'\
                                           .format(self.node_type))
        return PhysicalInterface(meta=Meta(name=None, href=href, type='physical_interface'))
    
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
        :return: :py:class:`smc.elements.interfaces.VirtualPhysicalInterface`
        """
        href = find_link_by_name('virtual_physical_interface', self.link)
        if not href:
            raise UnsupportedInterfaceType('Only virtual engines support the '
                                           'virtual physical interface type. Engine '
                                           'type is: {}'
                                           .format(self.node_type))
        return VirtualPhysicalInterface(meta=Meta(name=None, href=href, 
                                                  type='virtual_physical_interface'))
    
    @property
    def tunnel_interface(self):
        """ Get only tunnel interfaces for this engine node.
        
        :method: GET
        :return: :py:class:`smc.elements.interfaces.TunnelInterface`
        """
        href = find_link_by_name('tunnel_interface', self.link)
        if not href:
            raise UnsupportedInterfaceType('Tunnel interfaces are only supported on '
                                           'layer 3 single engines or clusters; '
                                           'Engine type is: {}'
                                           .format(self.node_type))
        return TunnelInterface(meta=Meta(name=None, href=href, type='tunnel_interface'))
     
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
    
    def refresh(self, wait_for_finish=False, sleep=3):
        """ Refresh existing policy on specified device. This is an asynchronous 
        call that will return a 'follower' link that can be queried to determine 
        the status of the task. 
        
        See :func:`async_handler` for more information on how to obtain results
        
        Last yield is result href; if wait_for_finish=False, the only yield is 
        the follower href
        
        :method: POST
        :param boolean wait_for_finish: whether to wait in a loop until the upload completes
        :param int sleep: number of seconds to sleep if wait_for_finish=True
        :return: generator yielding updates on progress
        """
        element = SMCElement(
                    href=find_link_by_name('refresh', self.link)).create()
        if element.json:
            return common_api.async_handler(element.json.get('follower'), 
                                            wait_for_finish, sleep)
    
    def upload(self, policy, wait_for_finish=False, sleep=3):
        """ Upload policy to engine. This is used when a new policy is required
        for an engine, or this is the first time a policy is pushed to an engine.
        If an engine already has a policy and the intent is to re-push, then use
        :py:func:`refresh` instead.
        The policy argument can use a wildcard * to specify in the event a full 
        name is not known.
        
            engine = Engine('i-4aea8ad3 (us-east-1a)').load()
            for x in engine.upload('Layer 3*', wait_for_finish=True):
                print x
        
        :param str policy: name of policy to upload to engine
        :param boolean wait_for_finish: whether to wait for async responses
        :param int sleep: number of seconds to sleep if wait_for_finish=True
        :return: generator yielding updates on progress
        """
        element = SMCElement(
                    href=find_link_by_name('upload', self.link),
                    params={'filter': policy}).create()
        if element.json:
            return common_api.async_handler(element.json.get('follower'), 
                                            wait_for_finish, sleep)
        else:
            return "Upload returned a failure message, result: {}".format(element.msg)
    
    def generate_snapshot(self, filename='snapshot.zip'):
        """ Generate and retrieve a policy snapshot from the engine
        This is blocking as file is downloaded
        
        :method: GET
        :param str filename: name of file to save file to, including directory path
        :return: None
        """
        href = find_link_by_name('generate_snapshot', self.link)
        return common_api.fetch_content_as_file(href, filename=filename)
    
    def snapshot(self):
        """ References to policy based snapshots for this engine, including
        the date the snapshot was made
        
        :method: GET
        :return: list of dict with {href,name,type}
        """
        return search.element_by_href_as_json(
                        find_link_by_name('snapshots', self.link))
    
    def export(self, filename='export.zip'): 
        """ Generate export of configuration. Export is downloaded to
        file specified in filename parameter.
        
        :mathod: POST
        :param str filename: if set, the export will download the file. 
        :return: href of export, file download
        """
        element = SMCElement(
                    href=find_link_by_name('export', self.link),
                    params={'filter': self.name}).create()
        
        href = next(common_api.async_handler(element.json.get('follower'), 
                                             display_msg=False))
        return common_api.fetch_content_as_file(href, filename)
    
    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, 'name={}'\
                           .format(self.name))
  
class Node(object):
    """ 
    Node settings to make each engine node controllable individually.
    When Engine().load() is called, setattr will set all instance attributes
    with the contents of the node json. Very few would benefit from being
    modified with exception of 'name'. To change a top level attribute, you
    would call node.modify_attribute(name='value')
    Engine will have a 'has-a' relationship with node and stored as the
    nodes attribute
    
    Instance attributes:
    
    :ivar name: name of node
    :ivar engine_version: software version installed
    :ivar nodeid: node id, useful for commanding engines
    :ivar disabled: whether node is disabled or not
    :ivar href: href of this resource
    """
    node_type = None
    
    def __init__(self, node_type, mydict):
        Node.node_type = node_type
        for k, v in mydict.iteritems():
            setattr(self, k, v)
    
    @property
    def href(self):
        return find_link_by_name('self', self.link)
    
    @classmethod
    def create(cls, name, node_type, nodeid=1):
        """
        :param name
        :param node_type
        :param nodeid
        """  
        node = Node(node_type,
                        {'activate_test': True,
                         'disabled': False,
                         'loopback_node_dedicated_interface': [],
                         'name': name + ' node '+str(nodeid),
                         'nodeid': nodeid})
        return({node_type: 
                vars(node)}) 

    def modify_attribute(self, **kwargs):
        """ Modify attribute/value pair of base node
        
        :param kwargs: key=value
        """
        for k, v in kwargs.iteritems():
            setattr(self, k, v)
            
        latest = search.element_by_href_as_smcresult(self.href)
        return SMCElement(
                    href=self.href, json=vars(self),
                    etag=latest.etag).update()
    
    def fetch_license(self):
        """ Fetch the node level license
        
        :return: SMCResult
        """
        return SMCElement(
                href=find_link_by_name('fetch', self.link)).create()

    def bind_license(self, license_item_id=None):
        """ Auto bind license, uses dynamic if POS is not found
        
        :param str license_item_id: license id
        :return: SMCResult
        """
        params = {'license_item_id': license_item_id}
        return SMCElement(
                href=find_link_by_name('bind', self.link), params=params).create()
        
    def unbind_license(self):
        """ Unbind license on node. This is idempotent. 
        
        :return: SMCResult 
        """
        return SMCElement(
                href=find_link_by_name('unbind', self.link)).create()
        
    def cancel_unbind_license(self):
        """ Cancel unbind for license
        
        :return: SMCResult
        """
        return SMCElement(
                href=find_link_by_name('cancel_unbind', self.link)).create()
    
    def initial_contact(self, enable_ssh=True, time_zone=None, 
                        keyboard=None, 
                        install_on_server=None, 
                        filename=None):
        """ Allows to save the initial contact for for the specified node
        
        :method: POST
        :param boolean enable_ssh: flag to know if we allow the ssh daemon on the specified node
        :param str time_zone: optional time zone to set on the specified node 
        :param str keyboard: optional keyboard to set on the specified node
        :param boolean install_on_server: optional flag to know if the generated configuration 
               needs to be installed on SMC Install server (POS is needed)
        :param str filename: filename to save initial_contact to. If this fails due to IOError,
               SMCResult.content will still have the contact data
        :return: SMCResult: with content attribute set to initial contact info
        """
        result = SMCElement(
                    href=find_link_by_name('initial_contact', self.link),
                    params={'enable_ssh': enable_ssh}).create()
      
        if result.content:
            if filename:
                import os.path
                path = os.path.abspath(filename)
                try:
                    with open(path, "w") as text_file:
                        text_file.write("{}".format(result.content))
                except IOError, io:
                    result.msg = "Error occurred saving initial contact info: %s" % io    
            return result.content
    
    def appliance_status(self):
        """ Gets the appliance status for the specified node 
        for the specific supported engine 
        
        :method: GET
        :return: list of status information
        """
        return search.element_by_href_as_json(
                find_link_by_name('appliance_status', self.link))
    
    def status(self):
        """ Basic status for individual node. Specific information such as node name,
        dynamic package version, configuration status, platform and version.
        
        :method: GET
        :return: dict of status fields returned from SMC
        """
        return search.element_by_href_as_json(
                find_link_by_name('status', self.link))
        
    def go_online(self, comment=None):
        """ Executes a Go-Online operation on the specified node 
        typically done when the node has already been forced offline 
        via :func:`go_offline`
        
        :method: PUT
        :param str comment: (optional) comment to audit
        :return: SMCResult
        """
        params = {'comment': comment}
        return SMCElement(
                    href=find_link_by_name('go_online', self.link),
                    params=params).update()

    def go_offline(self, comment=None):
        """ Executes a Go-Offline operation on the specified node
        
        :method: PUT
        :param str comment: optional comment to audit
        :return: SMCResult
        """
        params = {'comment': comment}
        return SMCElement(
                    href=find_link_by_name('go_offline', self.link),
                    params=params).update()

    def go_standby(self, comment=None):
        """ Executes a Go-Standby operation on the specified node. 
        To get the status of the current node/s, run :func:`status`
        
        :method: PUT
        :param str comment: optional comment to audit
        :return: SMCResult
        """
        params = {'comment': comment}
        return SMCElement(
                    href=find_link_by_name('go_standby', self.link),
                    params=params).update()

    def lock_online(self, comment=None):
        """ Executes a Lock-Online operation on the specified node
        
        :method: PUT
        :param str comment: comment for audit
        :return: SMCResult
        """
        params = {'comment': comment}
        return SMCElement(
                    href=find_link_by_name('lock_online', self.link),
                    params=params).update()
        
    def lock_offline(self, comment=None):
        """ Executes a Lock-Offline operation on the specified node
        Bring back online by running :func:`go_online`.
        
        :method: PUT
        :param str comment: comment for audit
        :return: SMCResult
        """
        params = {'comment': comment}
        return SMCElement(
                    href=find_link_by_name('lock_offline', self.link),
                    params=params).update()
    
    def reset_user_db(self, comment=None):
        """ Executes a Send Reset LDAP User DB Request operation on the 
        specified node
        
        :method: PUT
        :param str comment: comment to audit
        :return: SMCResult
        """
        params = {'comment': comment}
        return SMCElement(
                    href=find_link_by_name('reset_user_db', self.link),
                    params=params).update()
        
    def diagnostic(self, filter_enabled=False):
        """ Provide a list of diagnostic options to enable
        #TODO: implement filter_enabled
        
        :method: GET
        :param boolean filter_enabled: returns all enabled diagnostics
        :return: list of dict items with diagnostic info; key 'diagnostics'
        """
        return search.element_by_href_as_json(
                find_link_by_name('diagnostic', self.link))
    
    def send_diagnostic(self):
        """ Send the diagnostics to the specified node 
        Send diagnostics in payload
        """
        print "Not Yet Implemented"
        
    def reboot(self, comment=None):
        """ Reboots the specified node 
        
        :method: PUT
        :param str comment: comment to audit
        :return: SMCResult
        """
        params = {'comment': comment}
        return SMCElement(
                    href=find_link_by_name('reboot', self.link),
                    params=params).update()
      
    def sginfo(self, include_core_files=False,
               include_slapcat_output=False):
        """ Get the SG Info of the specified node 
        ?include_core_files
        ?include_slapcat_output
        :param include_core_files: flag to include or not core files
        :param include_slapcat_output: flag to include or not slapcat output
        """
        #params = {'include_core_files': include_core_files,
        #          'include_slapcat_output': include_slapcat_output}  
        print "Not Yet Implemented"
   
    def ssh(self, enable=True, comment=None):
        """ Enable or disable SSH
        
        :method: PUT
        :param boolean enable: enable or disable SSH daemon
        :param str comment: optional comment for audit
        :return: SMCResult
        """
        params = {'enable': enable, 'comment': comment}
        return SMCElement(
                    href=find_link_by_name('ssh', self.link),
                    params=params).update()
        
    def change_ssh_pwd(self, pwd=None, comment=None):
        """
        Executes a change SSH password operation on the specified node 
        
        :method: PUT
        :param str pwd: changed password value
        :param str comment: optional comment for audit log
        :return: SMCResult
        """
        json = {'value': pwd}
        params = {'comment': comment}
        return SMCElement(
                    href=find_link_by_name('change_ssh_pwd', self.link),
                    params=params, json=json).update()

    def time_sync(self):
        """ Time synchronize node

        :method: PUT
        :return: SMCResult
        """
        return SMCElement(
                    href=find_link_by_name('time_sync', self.link)).update()
      
    def certificate_info(self):
        """ Get the certificate info of the specified node 
        
        :return: dict with links to cert info
        """
        return search.element_by_href_as_json(
                find_link_by_name('certificate_info', self.link))
    
    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, 'name={},nodeid={}'\
                           .format(self.name, self.nodeid))

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
               location_ref=None):
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
        :return: :py:class:`smc.elements.engine.Engine`
        :raises: :py:class:`smc.api.web.CreateEngineFailed`: Failure to create with reason
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
                               location_ref=location_ref)
       
        href = search.element_entry_point('single_fw')
        result = SMCElement(href=href, json=engine).create()
        if result.href:
            return Engine(name).load()
        else:
            raise CreateEngineFailed('Could not create the engine, '
                                     'reason: {}'.format(result.msg))

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
        :return: :py:class:`smc.elements.engine.Engine`
        :raises: :py:class:`smc.api.web.CreateEngineFailed`: Failure to create with reason
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
        result = SMCElement(href=href, 
                            json=engine).create()
        if result.href:
            return Engine(name).load()
        else:
            raise CreateEngineFailed('Could not create the engine, '
                                     'reason: {}'.format(result.msg))   

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
        :return: :py:class:`smc.elements.engine.Engine`
        :raises: :py:class:`smc.api.web.CreateEngineFailed`: Failure to create with reason
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
        result = SMCElement(href=href, 
                            json=engine).create()
        if result.href:
            return Engine(name).load()
        else:
            raise CreateEngineFailed('Could not create the engine, '
                                     'reason: {}'.format(result.msg))
        
class Layer3VirtualEngine(object):
    """ 
    Create a layer3 virtual engine and map to specified Master Engine
    Each layer 3 virtual firewall will use the same virtual resource that 
    should be pre-created.
        
    To instantiate and create, call 'create' as follows::
    
        engine = Layer3VirtualEngine.create(
                                'myips', 
                                'mymaster_engine, 
                                virtual_engine='ve-3',
                                interfaces=[{'address': '5.5.5.5', 
                                         'network_value': '5.5.5.5/30', 
                                         'interface_id': 0, 
                                         'zone_ref': ''}]
    """
    node_type = 'virtual_fw_node'
    
    def __init__(self, name):
        Node.__init__(self, name)
        pass

    @classmethod
    def create(cls, name, master_engine, virtual_resource, 
               interfaces, default_nat=False, outgoing_intf=0,
               domain_server_address=None, **kwargs):
        """
        :param str name: Name of this layer 3 virtual engine
        :param str master_engine: Name of existing master engine
        :param str virtual_resource: name of pre-created virtual resource
        :param list interfaces: dict of interface details
        :param boolean default_nat: Whether to enable default NAT for outbound
        :param int outgoing_intf: outgoing interface for VE. Specifies interface number
        :param list interfaces: interfaces mappings passed in            
        :return: :py:class:`smc.elements.engine.Engine`
        :raises: :py:class:`smc.api.web.CreateEngineFailed`: Failure to create with reason
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
                               nodes=1, default_nat=default_nat)

            engine.update(virtual_resource=virt_resource_href)
            engine.pop('log_server_ref', None) #Master Engine provides this service
        
        
        href = search.element_entry_point('virtual_fw')
        result = SMCElement(href=href, json=engine).create()
        if result.href:
            return Engine(name).load()
        else:
            raise CreateEngineFailed('Could not create the virtual engine, '
                                     'reason: {}'.format(result.msg))
            
class FirewallCluster(object):
    """ 
    Firewall Cluster
    Creates a layer 3 firewall cluster engine with CVI and NDI's. Once engine is 
    created, and in context, add additional interfaces using engine.physical_interface 
    :py:class:PhysicalInterface.add_cluster_virtual_interface`
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
        :return: :py:class:`smc.elements.engine.Engine`
        :raises: :py:class:`smc.api.web.CreateEngineFailed`: Failure to create with reason
        
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
        result = SMCElement(href=href,
                            json=engine).create()
        if result.href:
            return Engine(name).load()
        else:
            raise CreateEngineFailed('Could not create the firewall, '
                                     'reason: {}'.format(result.msg))
        
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
        :return: :py:class:`smc.elements.engine.Engine`
        :raises: :py:class:`smc.api.web.CreateEngineFailed`: Failure to create with reason
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
        result = SMCElement(href=href, 
                            json=engine).create()
        if result.href:
            return Engine(name).load()
        else:
            raise CreateEngineFailed('Could not create the engine, '
                                     'reason: {}'.format(result.msg))

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
        :raises: :py:class:`smc.api.web.CreateEngineFailed`: Failure to create with reason
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
        result = SMCElement(href=href, 
                            json=engine).create()
        if result.href:
            return Engine(name).load()
        else:
            raise CreateEngineFailed('Could not create the engine, '
                                     'reason: {}'.format(result.msg))
'''
            
class VirtualResource(object):
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
    
    When class is initialized, href should be passed in. This is used to populate
    the SMCElement if create is requested, or may be populated for each resource after
    calling all().
    
    :param href: href should be provided to init to identify base location for virtual
                 resources
    """
    def __init__(self, meta=None, **kwargs):
        self.meta = meta    

    @property
    def href(self):
        if self.meta:
            return self.meta.href
    
    @property
    def name(self):
        if self.meta:
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
        :return: SMCResult
        """
        allocated_domain = domain_helper(domain)
        json = {'name': name,
                'connection_limit': connection_limit,
                'show_master_nic': show_master_nic,
                'vfw_id': vfw_id,
                'allocated_domain_ref': allocated_domain}

        return SMCElement(href=self.href, json=json).create()
      
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

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, 'name={}'\
                           .format(self.name))
    