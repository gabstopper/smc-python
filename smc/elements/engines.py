from abc import ABCMeta, abstractmethod
from smc.elements.element import SMCElement
from smc.elements.interfaces import \
   InlineInterface, CaptureInterface, SingleNodeInterface, NodeInterface
import smc.actions.search as search
import smc.api.common as common_api
from smc.api.web import SMCException
from smc.elements.system import SystemInfo

class Engine(object):
    """
    Top level engine class representing settings of the generic engine, independent of
    the engine type. The load method is required to initialize this class properly and 
    is abstract so must be called from a subclass,
    either Node or the direct engine types:
    
    :class:`smc.elements.engines.Layer3Firewall`
    
    :class:`smc.elements.engines.Layer2Firewall`
    
    :class:`smc.elements.engines.IPS`
    
    This is intended to store the top level engine properties and operations specific to 
    the engine.
    
    :class:`smc.elements.engines.Node` class will store information specific to the individual
    node itself such as rebooting, going online/offline, change user pwd, ssh pwd reset, etc.
    """
    
    __metaclass__ = ABCMeta
    
    def __init__(self, name):
        self.name = name #: Name of engine
        self.href = None #: Href location for this engine in SMC
        self.etag = None #saved in case of modifications
        self.engine_version = None #: Engine version
        self.log_server_ref = None #: Reference to log server
        self.cluster_mode = None #: Whether engine node is cluster or single
        self.domain_server_address = [] #: List of domain server addresses
        self.engine_json = None #engine full json
        self.engine_links = [] #links specific to engine level
    
    @abstractmethod    
    def load(self):
        engine = search.element_as_json_with_etag(self.name)
        if engine:
            self.engine_json = engine.json
            self.etag = engine.etag
            self.engine_links.extend(engine.json.get('link'))
            self.domain_server_address.extend(engine.json.get('domain_server_address'))
            self.engine_version = engine.json.get('engine_version')
            self.log_server_ref = engine.json.get('log_server_ref')
            self.cluster_mode = engine.json.get('cluster_mode')
            self.href = self.__load_href('self') #get self href
            return self
        else:
            raise SMCException("Cannot load engine name: %s, please ensure the name is correct"
                               " and the engine exists." % self.name)
    
    @classmethod
    @abstractmethod
    def create(cls):
        engine = {
                "name": cls.name,
                "nodes": [],
                "domain_server_address": [],
                "log_server_ref": cls.log_server_ref,
                "physicalInterfaces": []
                }
        node =  {
                cls.node_type: {
                    "activate_test": True,
                    "disabled": False,
                    "loopback_node_dedicated_interface": [],
                    "name": cls.name + " node 1",
                    "nodeid": 1
                    }
                }
        if cls.domain_server_address:
            rank_i = 0
            for entry in cls.domain_server_address:
                engine.get('domain_server_address').append(
                                            {"rank": rank_i, "value": entry})
        engine.get('nodes').append(node)
        cls.engine_json = engine
        return cls
    
    def refresh(self, wait_for_finish=True):
        """ Refresh existing policy on specified device. This is an asynchronous 
        call that will return a 'follower' link that can be queried to determine 
        the status of the task. 
        
        See :func:`async_handler` for more information on how to obtain results
        
        :method: POST
        :param wait_for_finish: whether to wait in a loop until the upload completes
        :return: generator yielding updates on progress. Last yield is result href;
        if wait_for_finish=False, the only yield is the follower href
        """
        element = SMCElement(href=self.__load_href('refresh')).create()
        return common_api.async_handler(element.json.get('follower'), 
                                        wait_for_finish)
    
    def upload(self, policy=None, wait_for_finish=True):
        """ Upload policy to existing engine. If no policy is specified, and the engine
        has already had a policy installed, this policy will be re-uploaded. 
        
        This is typically used to install a new policy on the engine. If you just
        want to re-push an existing policy, call :func:`refresh`
        
        :param policy: name of policy to upload to engine
        :param wait_for_finish: whether to wait for async responses
        :return: generator yielding updates on progress
        """
        if not policy: #if policy not specified SMC seems to apply some random policy: bug?
            node = self.node_names()[0] if self.node_names else []
            policy = self.status(node=node)[0].get('installed_policy')
    
        element = SMCElement(href=self.__load_href('upload'),
                             params={'filter': policy}).create()
        return common_api.async_handler(element.json.get('follower'), 
                                        wait_for_finish)
    
    def node(self):
        """ Return node/s references for this engine. For a cluster this will
        contain multiple entries. 
        
        :method: GET
        :return: dict list with reference {href, name, type}
        """
        return search.element_by_href_as_json(self.__load_href('nodes')) 
   
    def interface(self):
        """ Get all interfaces, including non-physical interfaces such
        as tunnel or capture interfaces.
        
        :method: GET
        :return: list of dict entries with href,name,type, or None
        """
        return search.element_by_href_as_json(self.__load_href('interfaces')) 
    
    def generate_snapshot(self, filename='snapshot.xml'):
        """ Generate and retrieve a policy snapshot from the engine
        This is blocking as file is downloaded
        
        :method: GET
        :param filename: name of file to save file to, including directory path
        :return: None
        """
        element = SMCElement(href=self.__load_href('generate_snapshot'),
                             filename=filename)
        return common_api.fetch_content_as_file(element)

    def add_route(self, gateway, network):
        """ Add a route to engine. Specify gateway and network. 
        If this is the default gateway, use a network address of
        0.0.0.0/0.
        
        .. note: This will fail if the gateway provided does not have a 
        corresponding interface on the network.
        
        :method: POST
        :param gateway: gateway of an existing interface
        :param network: network address in cidr format
        """
        return SMCElement(href=self.__load_href('add_route'),
                          params={'gateway': gateway, 'network': network}).create()
        
    def blacklist_add(self, src, dst, duration=3600):
        """ Add blacklist entry to engine node by name
    
        :method: POST
        :param name: name of engine node or cluster
        :param src: source to blacklist, can be /32 or network cidr
        :param dst: dest to deny to, 0.0.0.0/32 indicates all destinations
        :param duration: how long to blacklist in seconds
        :return: href for success, or None
        """
        bl = { "name": "",
              "duration": duration,
              "end_point1": { 
                             "name": "", 
                             "address_mode": 
                             "address", 
                             "ip_network": src },
              "end_point2": { 
                             "name": 
                             "", 
                             "address_mode": 
                             "address", 
                             "ip_network": dst }
              }
        return SMCElement(href=self.__load_href('blacklist'),
                          json=bl).create()

    def blacklist_flush(self):
        """ Flush entire blacklist for node name
    
        :method: DELETE
        :param name: name of node or cluster to remove blacklist
        :return: None, or message if failure
        """
        return common_api.delete(self.__load_href('routing'))

    def alias_resolving(self):
        """ Alias definitions defined for this engine 
        Aliases can be used in rules to simplify multiple object creation
        
        :method: GET
        :return: dict list of aliases and their values
        """
        return search.element_by_href_as_json(self.__load_href('alias_resolving'))
       
    def routing_monitoring(self):
        """ Return route information for the engine, including gateway, networks
        and type of route (dynamic, static)
        
        :method: GET
        :return: dict of dict list entries representing routes
        """
        return search.element_by_href_as_json(self.__load_href('routing_monitoring'))
    
    def export(self, filename='export.xml'): 
        """ Generate export on engine. Once the export is complete, 
        a result href is returned. If wait_for_finish is True, this
        will block until the export is complete and then will auto
        fetch the filename and save to value specified in filename
        
        :mathod: POST
        :param filename: if set, the export will download the file. 
        :return: href of export
        """
        element = SMCElement(href=self.__load_href('export'),
                             params={'filter': self.name}).create()
        #wait for the export to be complete, fetch result export by href
        for msg in common_api.async_handler(element.json.get('follower'), 
                                            display_msg=False):
            element.href = msg
        element.filename = filename
        return common_api.fetch_content_as_file(element)
    
    def internal_gateway(self):
        """ Engine level VPN gateway reference
        
        :method: GET
        :return: dict list of internal gateway references
        """
        return search.element_by_href_as_json(self.__load_href('internal_gateway'))
        
    def routing(self):
        """ Retrieve routing json from engine node
        
        :method: GET
        :return: json representing routing configuration
        """
        return search.element_by_href_as_json(self.__load_href('routing'))
    
    def antispoofing(self):
        """ Antispoofing interface information. By default is based on routing
        but can be modified in special cases
        
        :method: GET
        :return: dict of antispoofing settings per interface
        """
        return search.element_by_href_as_json(self.__load_href('antispoofing'))
    
    def snapshot(self):
        """ References to policy based snapshots for this engine, including
        the date the snapshot was made
        
        :method: GET
        :return: dict list with {href,name,type}
        """
        return search.element_by_href_as_json(self.__load_href('snapshots'))
    
    def virtual_resource(self):
        """ Master Engine only 
        Return a list of dict {href,name,type} of virtual resources assigned to
        this master engine 
        """
        return search.element_by_href_as_json(self.__load_href('virtual_resources'))
    
    def virtual_resource_add(self, name, vfw_id, domain='Shared Domain'):
        """ Master Engine only
        Add a virtual resource to this master engine
        
        :param name: name for virtual resource
        :param vfw_id: virtual fw ID, must be unique, indicates the virtual engine instance
        :param domain: Domain to place this virtual resource, default Shared
        :return: SMCResult with href set if success, or msg set if failure
        """
        domain = search.element_href_use_filter(domain, 'admin_domain')
        return SMCElement(href=self.__load_href('virtual_resources'), 
                          json={'allocated_domain_ref': domain,
                                'name': name, 
                                'vfw_id': vfw_id}).create()
    
    def virtual_physical_interface(self):
        """ Master Engine virtual instance only
        A virtual physical interface is for a master engine virtual.
        
        :method: GET
        :return list of dict entries with href,name,type or None
        """
        return search.element_by_href_as_json(self.__load_href('virtual_physical_interface'))
    
    def physical_interface_vlan_add(self, interface_id, vlan_id,
                                    virtual_mapping=None, virtual_resource_name=None):
        """ Add VLAN interface to physical interface
        If virtual mapping is set, this is for a Master Engine and virtual_resource_name
        is then required. 
        
        :param interface_id: physical interface ID for adding this VLAN
        :param vlan_id: number of vlan_id
        :type vlan_id: int
        :param virtual_mapping: The interface ID for the virtual engine. This is
               typically the interface_id-1
        :type virtual_mapping: int
        :param virtual_resource_name: Name of virtual resource for this VLAN if a VE
        :type virtual_resource_name: string
        """
        intf = 'Interface '+str(interface_id)
        for interface in self.physical_interface():
            if interface.get('name') == intf:
                intf = interface.get('href')
                break

        interface = search.element_by_href_as_json(intf)
        vlan = {
                "interface_id": str(interface_id)+'.'+str(vlan_id), #interface_id.vlan_id
                "virtual_mapping": virtual_mapping, #virtual engines interface id mapping
                "virtual_resource_name": virtual_resource_name
        }
        interface.get('vlanInterfaces').append(vlan)
        return SMCElement(href=self.__load_href('physical_interface'),
                             json=interface).create()                           
    
    def physical_interface(self):
        """ Get only physical interfaces for this engine node. Physical interface
        types are Layer3, Layer2 Inline, and Capture interfaces.
       
        :method: GET
        :return: list of dict entries with href,name,type, or None
        """
        return search.element_by_href_as_json(self.__load_href('physical_interface')) 
    
    def physical_interface_del(self, name):
        """ Delete physical interface by name
        To retrieve name, use :func:`physical_interface` to
        list all configured interfaces for this engine
        
        :param name: name of interface (typically 'Interface <num>'
        :return
        """
        href = [interface.get('href')
                for interface in self.interface()
                if interface.get('name') == name]
        if href:
            return common_api.delete(href.pop())
    
    def layer3_interface_add(self, address, network, interfaceid,
                             nodeid=1, is_mgmt=False):
        """ Add layer 3 physical interface
        
        :param ip: ipaddress of interface
        :param ip_network: network address in cidr
        :param interfaceid: id of interface
        :param nodeid: id of node, only used in clusters
        :type nodeid: int
        :param is_mgmt: Whether to make this a management enabled interface
        :type is_mgmt: boolean
        :return: SMCResult
        """
        intf = SingleNodeInterface(address, network, interfaceid, 
                                   nodeid=nodeid, 
                                   is_mgmt=is_mgmt).build()
        return SMCElement(href=self.__load_href('physical_interface'), 
                          json=intf.json.get('physical_interface')).create()
        
    def inline_interface_add(self, interfaceid,
                             logical_interface_ref='default_eth',
                             nodeid=1):
        """ Add layer 2 inline interface 
        
        :param interfaceid: interface ID of the inline pair, i.e. '1-2', '5-6', etc
        :param logical_interface_ref: reference to logical interface
        :param nodeid: node id of interface, only used in clusters
        :type nodeid: int
        :return: SMCResult
        """
        intf = InlineInterface(interfaceid,
                               logical_interface_ref,
                               nodeid).build()
        return SMCElement(href=self.__load_href('physical_interface'), 
                          json=intf.json.get('physical_interface')).create()

    def capture_interface_add(self, interfaceid, 
                              logical_interface_ref='default_eth', 
                              nodeid=1):
        """ Add capture interface to layer2 firewall or IPS engine
        
        :param interfaceid: interface id for capture int
        :param logical_interface_ref: reference to logical interface
        :param nodeid: node id of interface, only used in clusters
        :type nodeid: int
        :return: SMCResult
        """
        intf = CaptureInterface(interfaceid,
                                logical_interface_ref,
                                nodeid).build()
        return SMCElement(href=self.__load_href('physical_interface'),
                          json=intf.json.get('physical_interface')).create()
  
    def tunnel_interface(self):
        """ Get only tunnel interfaces for this engine node.
        
        :method: GET
        :return: list of dict entries with href,name,type, or None
        """
        return search.element_by_href_as_json(self.__load_href('tunnel_interface')) 
    
    def modem_interface(self):
        """ Get only modem interfaces for this engine node.
        
        :method: GET
        :return: list of dict entries with href,name,type, or None
        """
        return search.element_by_href_as_json(self.__load_href('modem_interface'))
    
    def adsl_interface(self):
        """ Get only adsl interfaces for this engine node.
        
        :method: GET
        :return: list of dict entries with href,name,type, or None
        """
        return search.element_by_href_as_json(self.__load_href('adsl_interface'))
    
    def wireless_interface(self):
        """ Get only wireless interfaces for this engine node.
        
        :method: GET
        :return: list of dict entries with href,name,type, or None
        """
        return search.element_by_href_as_json(self.__load_href('wireless_interface'))
    
    def switch_physical_interface(self):
        """ Get only switch physical interfaces for this engine node.
        
        :method: GET
        :return: list of dict entries with href,name,type, or None
        """
        return search.element_by_href_as_json(self.__load_href('switch_physical_interface'))
    
    def __load_href(self, action):
        """ Pull the direct href from engine link list cache """
        href = [entry.get('href') for entry in self.engine_links \
                if entry.get('rel') == action]      
        if href:
            return href.pop()
    
    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)

        
class Node(Engine):
    """
    Node is the individual engine level object that handles interfaces, routes and
    operations specific to the individual nodes such as fetching a license, commanding
    a node online, offline or standby, rebooting, getting sginfo, appliance status and
    changing ssh or changing the user password. 
    All inheriting classes will have access to node level commands available in this
    class.
    It is possible to have more than one node in an engine, specifically with clustering.
    """
    def __init__(self, name):
        Engine.__init__(self, name)
        self.name = name        #: Name of engine
        self.node_type = None   #: Engine node type from SMC
        self.node_links = {}    #node level links
 
    def load(self):
        super(Node, self).load()
        for node in self.engine_json.get('nodes'): #list
            for node_type, node_info in node.iteritems():
                self.node_type = node_type
                #add to dict using node name as {key: [link]}
                self.node_links[node_info.get('name')] = node_info.get('link')
        return self
    
    @classmethod
    def create(cls):
        #nothing to do here, engine has base settings
        return super(Node, cls).create()   
    
    def node_names(self):
        return self.node_links.keys()
        
    def fetch_license(self, node=None):
        """ Allows to fetch the license for the specified node """
        return self._commit_create('fetch', node)

    def bind_license(self, node=None, license_item_id=None):
        """ Allows to bind the optional specified license for the specified 
        node. If no license is specified, an auto bind will be tried.
        
        :param license_item_id: license id, otherwise auto bind will be tried
        """
        params = {'license_item_id': license_item_id}
        return self._commit_create('bind', node, params=params)
        
    def unbind_license(self, node=None):
        """ Allows to unbind the possible already bound license for the 
        specified node. If no license has been found, nothing is done and 
        NO_CONTENT is returned otherwise OK is returned 
        """
        return self._commit_create('unbind', node)
        
    def cancel_unbind_license(self, node=None):
        """ Allows to cancel the possible unbind license for the specified 
        node. If no license has been found, nothing is done and NO_CONTENT 
        is returned otherwise OK is returned.
        """
        return self._commit_create('cancel_unbind', node)
        
    def initial_contact(self, node=None, enable_ssh=True,
                        time_zone=None, keyboard=None, 
                        install_on_server=None, filename=None):
        """ Allows to save the initial contact for for the specified node
        
        :method: POST
        :param node: node to run initial contact command against
        :param enable_ssh: flag to know if we allow the ssh daemon on the specified node
        :param time_zone: optional time zone to set on the specified node 
        :param keyboard: optional keyboard to set on the specified node
        :param install_on_server: optional flag to know if the generated configuration 
        needs to be installed on SMC Install server (POS is needed)
        :param filename: filename to save initial_contact to. If this fails due to IOError,
        SMCResult.content will still have the contact data
        :return: SMCResult, with content attribute set to initial contact info
        """
        result = SMCElement(href=self._load_href('initial_contact').pop(),
                             params = {'enable_ssh': True}).create()
        if result.content:
            if filename:
                import os.path
                path = os.path.abspath(filename)
                try:
                    with open(path, "w") as text_file:
                        text_file.write("{}".format(result.content))
                except IOError, io:
                    result.msg = "Error occurred saving initial contact info: %s" % io    
        return result
        
    def appliance_status(self, node=None):
        """ Gets the appliance status for the specified node 
        for the specific supported engine 
        
        :method: GET
        :param node: Name of node to retrieve from, if single node, can be ignored
        :return: list of status information
        """
        return [search.element_by_href_as_json(status) #TODO: This can return [None]
                for status in self._load_href('appliance_status', node)]

    def status(self, node=None):
        """ Basic status for individual node. Specific information such as node name,
        dynamic package version, configuration status, platform and version.
        
        :method: GET
        :param node: Name of node to retrieve from, otherwise all nodes
        :return: dict of status fields returned from SMC
        """
        return [search.element_by_href_as_json(status) 
                for status in self._load_href('status', node)]
        
    def go_online(self, node=None, comment=None):
        """ Executes a Go-Online operation on the specified node 
        typically done when the node has already been forced offline 
        via :func:`go_offline`
        
        :method: PUT
        :param node: if a cluster, provide the specific node name
        :param comment: optional comment to audit
        :return: href or None
        """
        params = {'comment': comment}
        return self._commit_update('go_online', node, params=params)

    def go_offline(self, node=None, comment=None):
        """ Executes a Go-Offline operation on the specified node
        
        :method: PUT
        :param node: if a cluster, provide the specific node name
        :param comment: optional comment to audit
        :return: SMCResult for success, or None
        """
        params = {'comment': comment}
        return self._commit_update('go_offline', node, params=params)
        
    def go_standby(self, node=None, comment=None):
        """ Executes a Go-Standby operation on the specified node. 
        To get the status of the current node/s, run :func:`status`
        
        :method: PUT
        :param node: if a cluster, provide the specific node name
        :param comment: optional comment to audit
        :return: SMCResult for success, or None
        """
        params = {'comment': comment}
        return self._commit_update('go_standby', node, params=params)
        
    def lock_online(self, node=None, comment=None):
        """ Executes a Lock-Online operation on the specified node
        
        :method: PUT
        :param node: if a cluster, provide the specific node name
        :return: SMCResult for success, or None
        """
        params = {'comment': comment}
        return self._commit_update('lock_online', node, params=params)
        
    def lock_offline(self, node=None, comment=None):
        """ Executes a Lock-Offline operation on the specified node
        Bring back online by running :func:`go_online`.
        
        :method: PUT
        :param node: if a cluster, provide the specific node name
        :return: SMCResult for success, or None
        """
        params = {'comment': comment}
        return self._commit_update('lock_offline', node, params=params)
    
    def reset_user_db(self, node=None, comment=None):
        """ 
        Executes a Send Reset LDAP User DB Request operation on the 
        specified node
        
        :method: PUT
        :param node: if a cluster, provide the specific node name
        :param comment: optional comment to audit
        :return: SMCResult for success, or None
        """
        params = {'comment': comment}
        return self._commit_update('reset_user_db', node, params=params)
        
    def diagnostic(self, node=None, filter_enabled=False):
        """ Provide a list of diagnostic options to enable
        #TODO: implement filter_enabled
        :method: GET
        :param node: if a cluster, provide the specific node name
        :param filter_enabled: returns all enabled diagnostics
        :return: list of dict items with diagnostic info
        """
        return [search.element_by_href_as_json(status) 
                for status in self._load_href('diagnostic', node)]
        
    def send_diagnostic(self, node=None):
        """ Send the diagnostics to the specified node 
        Send diagnostics in payload
        """
        print "POST send diagnostic: %s" % self._load_href('send_diagnostic')
        
    def reboot(self, node=None, comment=None):
        """ Reboots the specified node 
        
        :param node: name of node, or omit if single device
        :return: SMCResult, result.msg is None for success
        """
        params = {'comment': comment}
        return self._commit_update('reboot', node, params=params)
        
    def sginfo(self, node=None, include_core_files=False,
               include_slapcat_output=False):
        """ Get the SG Info of the specified node 
        ?include_core_files
        ?include_slapcat_output
        :param include_core_files: flag to include or not core files
        :param include_slapcat_output: flag to include or not slapcat output
        """
        params = {'include_core_files': include_core_files,
                  'include_slapcat_output': include_slapcat_output}
        print "GET sginfo: %s" % self._load_href('sginfo', node)
        
        element = SMCElement(href=self._load_href('sginfo', node).pop(),
                          params=params, filename='sginfo-ngf-1035')
        
        print common_api.fetch_content_as_file(element)

    def ssh(self, node=None, enable=True, comment=None):
        """ Enable or disable SSH
        
        :method: PUT
        :param enable: enable or disable SSH daemon
        :type enable: boolean
        :param comment: optional comment for audit
        """
        params = {'enable': enable, 'comment': comment}
        return self._commit_update('ssh', node, params=params)
        
    def change_ssh_pwd(self, node=None, pwd=None, comment=None):
        """
        Executes a change SSH password operation on the specified node 
        
        :method: PUT
        :param pwd: changed password value
        :param comment: optional comment for audit log
        """
        json = {'value': pwd}
        params = {'comment': comment}
        return self._commit_update('change_ssh_pwd', node, json=json, 
                                   params=params)
        
    def time_sync(self, node=None):
        """ Time synchronize node

        :return: SMCResult, json attribute set to {value:[]}
        """
        return self._commit_update('time_sync', node)
      
    def certificate_info(self, node=None):
        """ Get the certificate info of the specified node 
        
        :return: list with links to cert info
        """
        return [search.element_by_href_as_json(status) 
                for status in self._load_href('certificate_info', node)]
       
    def _commit_create(self, action, node, params=None):
        href = self._load_href(action, node)
        if href:
            return SMCElement(href=href.pop(),
                              params=params).create()
                                                    
    def _commit_update(self, action, node, json=None, params=None):
        href = self._load_href(action, node)
        if href:
            return SMCElement(href=href.pop(),
                              json=json,
                              params=params,
                              etag=self.etag).update()
                   
    def _load_href(self, action, node=None):
        """ Get href from self.node_links cache based on the node name. 
        If this is a cluster, the node parameter is required. 
        Since these are node level commands, we need to be able to specify
        which node to run against. If not a cluster, then node param is not
        required and is ignored if given.
        :param action: link to get
        :param node: name of node, only used for clusters with multiple nodes
        :return: list of href, or []
        """
        if not self.cluster_mode: #ignore node if single device node
            href = [link.get('href')
                    for node, links in self.node_links.iteritems()
                    for link in links
                    if link.get('rel') == action]
        else: #require node for cluster
            if node and node in self.node_links.keys():
                href = [entry.get('href') 
                        for entry in self.node_links.get(node)
                        if entry.get('rel') == action]
            else:
                return []
        return href

        
class Layer3Firewall(Node):
    """
    Represents a Layer 3 Firewall configuration.
    To instantiate and create, call 'create' classmethod as follows::
    
        engine = Layer3Firewall.create('mylayer3', '1.1.1.1', '1.1.1.0/24', href_to_log_server)
        
    """ 
    def __init__(self, name):
        Node.__init__(self, name)
        self.node_type = 'firewall_node'

    @classmethod   
    def create(cls, name, mgmt_ip, mgmt_network, log_server=None,
                 mgmt_interface='0', dns=None):
        """ 
        Create a single layer 3 firewall with management interface and DNS
        
        :param name: name of firewall
        :param name: management network ip
        :param mgmt_network: management network in cidr format
        :param log_server: href to log_server instance for fw
        :param mgmt_interface: interface for management from SMC to fw
        :type mgmt_interface: string or None
        :param dns: DNS server addresses
        :type dns: list or None
        :return: Layer3Firewall class with href and engine_json set
        """
        cls.name = name
        cls.node_type = 'firewall_node'
        cls.log_server_ref = log_server if log_server \
            else SystemInfo().first_log_server()  
        cls.domain_server_address = []
        if dns:
            for entry in dns:
                cls.domain_server_address.append(entry)
        
        super(Layer3Firewall, cls).create()
        mgmt = SingleNodeInterface(mgmt_ip, mgmt_network,
                                   interfaceid=mgmt_interface,
                                   is_mgmt=True).build()
        cls.engine_json.get('physicalInterfaces').append(mgmt.json)
        cls.href = search.element_entry_point('single_fw')
        result = SMCElement(href=cls.href, json=cls.engine_json).create()
        if result.href:
            #got referring object location, load and return
            return Layer3Firewall(cls.name).load()
        #else:
        #    return result


class Layer2Firewall(Node):
    """
    Represents a Layer2 Firewall configuration.
    To instantiate and create, call 'create' classmethod as follows::
    
        engine = Layer2Firewall.create('mylayer2', '1.1.1.1', '1.1.1.0/24', href_to_log_server)
        
    """ 
    def __init__(self, name):
        Node.__init__(self, name)
        self.node_type = 'fwlayer2_node'
    
    @classmethod
    def create(cls, name, mgmt_ip, mgmt_network, 
               log_server=None, mgmt_interface='0', 
               inline_interface='1-2', logical_interface='default_eth', 
               dns=None):
        """ 
        Create a single layer 2 firewall with management interface, inline interface,
        and DNS
        
        :param name: name of firewall
        :param name: management network ip
        :param mgmt_network: management network in cidr format
        :param log_server: href to log_server instance for fw
        :param mgmt_interface: interface for management from SMC to fw
        :type mgmt_interface: string or None
        :param inline_interface: interface ID's to use for default inline interfaces
        :type inline_interface: string or None (i.e. '1-2')
        :param logical_interface: logical interface to assign to inline interface
        :type logical_interface: string or None
        :param dns: DNS server addresses
        :type dns: list or None
        :return: Layer2Firewall class with href and engine_json set
        """
        cls.name = name
        cls.node_type = 'fwlayer2_node'
        cls.log_server_ref = log_server if log_server \
            else SystemInfo().first_log_server()
        cls.domain_server_address = []
        if dns:
            for entry in dns:
                cls.domain_server_address.append(entry)
        
        super(Layer2Firewall, cls).create()
        mgmt = NodeInterface(mgmt_ip, mgmt_network, 
                             interfaceid=mgmt_interface,
                             is_mgmt=True).build()  
        intf_href = search.get_logical_interface(logical_interface)
        inline = InlineInterface(inline_interface, intf_href).build()
    
        cls.engine_json.get('physicalInterfaces').append(mgmt.json)
        cls.engine_json.get('physicalInterfaces').append(inline.json)
        cls.href = search.element_entry_point('single_layer2')
        result = SMCElement(href=cls.href, json=cls.engine_json).create()
        if result.href:
            #got referring object location, load and return
            return Layer2Firewall(cls.name).load()

class IPS(Node):
    """
    Represents an IPS engine configuration.
    To instantiate and create, call 'create' classmethod as follows::
    
        engine = IPS.create('myips', '1.1.1.1', '1.1.1.0/24')
        
    """ 
    def __init__(self, name):
        Node.__init__(self, name)
        self.node_type = 'ips_node'

    @classmethod
    def create(cls, name, mgmt_ip, mgmt_network, 
               log_server=None, mgmt_interface='0', 
               inline_interface='1-2', logical_interface='default_eth', 
               dns=None):
        """ 
        Create a single layer 2 firewall with management interface, inline interface
        and DNS
        
        :param name: name of ips engine
        :param name: management network ip
        :param mgmt_network: management network in cidr format
        :param log_server: href to log_server instance for fw
        :param mgmt_interface: interface for management from SMC to fw
        :type mgmt_interface: string or None
        :param inline_interface: interface ID's to use for default inline interfaces
        :type inline_interface: string or None (i.e. '1-2')
        :param logical_interface: logical interface to assign to inline interface
        :type logical_interface: string or None
        :param dns: DNS server addresses
        :type dns: list or None
        :return: IPS class with href and engine_json set
        """
        cls.name = name
        cls.node_type = 'ips_node'
        cls.log_server_ref = log_server if log_server \
            else SystemInfo().first_log_server()
        cls.domain_server_address = []
        if dns:
            for entry in dns:
                cls.domain_server_address.append(entry)
                       
        super(IPS, cls).create()      
        mgmt = NodeInterface(mgmt_ip, mgmt_network, 
                             interfaceid=mgmt_interface,
                             is_mgmt=True).build()
            
        intf_href = search.get_logical_interface(logical_interface)
        inline = InlineInterface(inline_interface, intf_href).build()
        
        cls.engine_json.get('physicalInterfaces').append(mgmt.json)
        cls.engine_json.get('physicalInterfaces').append(inline.json)
        cls.href = search.element_entry_point('single_ips')
        result = SMCElement(href=cls.href, json=cls.engine_json).create()
        if result.href:
            #got referring object location, load and return
            return IPS(cls.name).load()
        
class Layer3VirtualEngine(Node):
    def __init__(self, name):
        Node.__init__(self, name)
        self.node_type = 'virtual_fw_node'
    
    @classmethod
    def create(cls, name, master_engine, virtual_resource, dns=None, **kwargs):
        """ Create a layer3 virtual engine and map to specified Master Engine
        Each layer 3 virtual firewall will use the same virtual resource that 
        should be pre-created. 
        
        To create the virtual resource::
        
            engine.virtual_resource_add(virtual_engine_name='ve-1', vfw_id=1)
            
        See :func:`engine.virtual_resource_add` for more information.
        
        .. note:: Virtual engine interface id's are staggered based on a master
                  engine having some pre-configured. For example, if the master
                  engine is using physical interface 0 for management, the virtual
                  engine will start with interface index 1. However, the interface
                  naming within the virtual engine configuration will start numbering
                  at interface 0!
        
        :param name: Name of this layer 3 virtual engine
        :param master_engine: Name of existing master engine. This assumes the
               interfaces are already created
        :param virtual_resource: name of pre-created virtual resource
        :param kwargs: If additional interfaces are required, provide a list of 
               dictionary items in the format of:
               [{'ipaddress':'1.1.1.1', 'mask':'1.1.1.1/30', 'interface_id': 3}]
        """
        cls.name = name
        cls.node_type = 'virtual_fw_node'
        cls.domain_server_address = []
        cls.log_server_ref = None
        if dns:
            for entry in dns:
                cls.domain_server_address.append(entry)
                       
        super(Layer3VirtualEngine, cls).create()
        
        #Get reference to virtual resource
        master_engine = Node(master_engine).load()
        for virt_resource in master_engine.virtual_resource():
            if virt_resource.get('name') == virtual_resource:
                virt_resource_href = virt_resource.get('href')
                break
        cls.engine_json['virtual_resource'] = virt_resource_href
            
        if kwargs:
            for interface in kwargs.get('kwargs'): #get interface info
                iface = SingleNodeInterface(interface.get('ipaddress'),
                                            interface.get('mask'),
                                            interface.get('interface_id'),
                                            zone=interface.get('zone')).build()
                iface.json['virtual_physical_interface'] = iface.json.pop('physical_interface')
                new_iface = iface.json.get('virtual_physical_interface')
                new_iface.pop('cvi_mode')
                new_iface.pop('virtual_engine_vlan_ok')
                new_iface.pop('sync_parameter')
                if interface.get('interface_id') == 0:
                    auth = new_iface.get('interfaces')[0].get('single_node_interface')
                    auth['auth_request'] = True #required for virtual engine
                cls.engine_json.get('physicalInterfaces').append(iface.json) 
        
            cls.href = search.element_entry_point('virtual_fw')
        
            return SMCElement(href=cls.href, json=cls.engine_json).create()  