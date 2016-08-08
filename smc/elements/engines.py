import re
from abc import ABCMeta, abstractmethod
from smc.elements.element import SMCElement, Blacklist, VirtualResource
from smc.elements.interfaces import VirtualPhysicalInterface, PhysicalInterface
import smc.actions.search as search
import smc.api.common as common_api
from smc.api.web import SMCException, SMCResult
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
                "physicalInterfaces": [] }
        if cls.domain_server_address:
            rank_i = 0
            for entry in cls.domain_server_address:
                engine.get('domain_server_address').append(
                                            {"rank": rank_i, "value": entry})
        cls.engine_json = engine
        return cls.engine_json
    
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
        return SMCElement(href=self.__load_href('blacklist'),
                          json=Blacklist(src, dst, duration).as_dict()).create()

    def blacklist_flush(self):
        """ Flush entire blacklist for node name
    
        :method: DELETE
        :param name: name of node or cluster to remove blacklist
        :return: None, or message if failure
        """
        return common_api.delete(self.__load_href('flush_blacklist'))

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
        """ Generate export of configuration. Export is downloaded to
        file specified in filename parameter.
        
        :mathod: POST
        :param filename: if set, the export will download the file. 
        :return: href of export
        """
        element = SMCElement(href=self.__load_href('export'),
                             params={'filter': self.name}).create()
        
        for msg in common_api.async_handler(element.json.get('follower'), 
                                            display_msg=False):
            element.href = msg
        element.filename = filename
        file_download = common_api.fetch_content_as_file(element)
        if not file_download.msg:
            print "Export successful, saved to file: {}".format(file_download.content)
    
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
        
        :return: list of dict { href, name, type } which hold virtual resources
                 assigned to the master engine
        """
        return search.element_by_href_as_json(self.__load_href('virtual_resources'))
    
    def virtual_resource_add(self, name, vfw_id, domain='Shared Domain',
                             show_master_nic=False):
        """ Master Engine only
        
        Add a virtual resource to this master engine
        
        :param name: name for virtual resource
        :param vfw_id: virtual fw ID, must be unique, indicates the virtual engine instance
        :param domain: Domain to place this virtual resource, default Shared
        :param show_master_nic: Show master NIC mapping in virtual engine interface view
        :return: SMCResult with href set if success, or msg set if failure
        """
        return SMCElement(href=self.__load_href('virtual_resources'),
                          json=VirtualResource(name, vfw_id, 
                                               domain=domain,
                                               show_master_nic=show_master_nic).as_dict()).create()
    
    def virtual_physical_interface(self):
        """ Master Engine virtual instance only
        
        A virtual physical interface is for a master engine virtual instance.
        
        :method: GET
        :return: list of dict entries with href,name,type or None
        """
        return search.element_by_href_as_json(self.__load_href('virtual_physical_interface'))
    
    def physical_interface(self):
        """ Get only physical interfaces for this engine node. Physical interface
        types are Layer3, Layer2 Inline, and Capture interfaces.
       
        :method: GET
        :return: list of dict entries with href,name,type, or None
        """
        return search.element_by_href_as_json(self.__load_href('physical_interface'))        
    
    def physical_interface_del(self, interface_id):
        """ Delete physical interface by name, can be a single layer 3
        interface, capture or an inline interface. In the case of inline, use
        the interface range: '1-2' (inline interface 1 and 2)
        
        To retrieve configured interfaces for this engine, 
        use :func:`physical_interface`
        
        :param interface_id: number of interface to remove
        :type  interface_id: string
        :return SMCResult
        """
        intf_href = self._load_interface(interface_id)
        if intf_href:
            return common_api.delete(intf_href)
        else:
            return SMCResult(msg='Cannot find interface: %s to delete, doing nothing.' % interface_id)

    def physical_interface_get(self, interface_id):
        """ Return the raw representation of the physical interface by interface id 
        This is used as a callback for modifying an existing interface 
        
        :param interface_id: interface id to retrieve
        :return json representing physical interface
        """
        intf = self._load_interface(interface_id)
        if intf:
            interface = search.element_by_href_as_smcresult(intf)
            return interface.json

    def add_physical_interfaces(self, interfaces):
        """ Add interfaces to this specific engine
        
        :param interfaces: Interfaces represents a Physical Interface configuration
        
        See :py:mod:`smc.elements.element.interfaces` for more information on interfaces
        """
        intf_href = self.__load_href('physical_interface')
        
        return SMCElement(href=intf_href, json=interfaces).create()
    
    def update_physical_interface(self, physical_interface):
        intf = self._load_interface(physical_interface.get('interface_id'))
        if intf:
            interface = search.element_by_href_as_smcresult(intf)
            print SMCElement(href=self._load_interface('0'),
                             json=physical_interface.data, etag=interface.etag).update()

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
    
    def _load_interface(self, interface_id):
        """ Find the interface href by querying the specified interface id """
        intf_href = None
        for intf in self.physical_interface():
            try: #Inline
                begin, end = interface_id.split('-')
                tmp = re.match(r'Interface (\d+) - Interface (\d+)', intf.get('name'))
                if tmp and (tmp.group(1) == begin and tmp.group(2) == end):
                    intf_href = intf.get('href')
                    break
            except ValueError: #Single
                tmp = re.match(r'Interface (\d+)', intf.get('name'))
                if tmp and tmp.group(1) == interface_id:
                    intf_href = intf.get('href')
                    break
        return intf_href

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
        super(Node, cls).create()
        if not hasattr(cls, 'nodes'): #if cluster, represents number of nodes
            cls.nodes = 1
        for nodeid in range(1, cls.nodes+1): #start with nodeid=1
            node =  {
                     cls.node_type: {
                        "activate_test": True,
                        "disabled": False,
                        "loopback_node_dedicated_interface": [],
                        "name": cls.name + " node " + str(nodeid),
                        "nodeid": nodeid }
                     }
            cls.engine_json.get('nodes').append(node)
        return cls.engine_json   
    
    def node_names(self):
        """ Return a list of all nodes by name
        
        :return: list of node names
        """
        return self.node_links.keys()
        
    def fetch_license(self, node=None):
        """ Allows to fetch the license for the specified node
        
        :return: SMCResult. If fail, msg will be set with reason
        """
        return self._commit_create('fetch', node)

    def bind_license(self, node=None, license_item_id=None):
        """ Allows to bind the optional specified license for the specified 
        node. If no license is specified, an auto bind will be tried which will
        include available dynamic licenses
        
        :param license_item_id: license id, otherwise auto bind will be tried
        :return: SMCResult, if fail, msg will be set with reason
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
        result = SMCElement(href=self._load_href('initial_contact', node).pop(),
                            params = {'enable_ssh': enable_ssh}).create()
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
    
        engine = Layer3Firewall.create('mylayer3', '1.1.1.1', '1.1.1.0/24')
        
    """ 
    def __init__(self, name):
        Node.__init__(self, name)
        self.node_type = 'firewall_node'

    @classmethod   
    def create(cls, name, mgmt_ip, mgmt_network, log_server=None,
                 mgmt_interface=0, dns=None, zone_ref=None, 
                 default_nat=False):
        """ 
        Create a single layer 3 firewall with management interface and DNS
        
        :param name: name of firewall
        :param name: management network ip
        :param mgmt_network: management network in cidr format
        :param log_server: href to log_server instance for fw
        :param mgmt_interface: interface for management from SMC to fw
        :type mgmt_interface: int
        :param dns: DNS server addresses
        :type dns: list
        :param zone_ref: zone name for management interface (created if not found)
        :param default_nat: Whether to enable default NAT for outbound
        :type default_nat: default False, specify whether to enable default NAT
        :return: self
        :raises: :py:class:`smc.api.web.SMCException`: Failure to create with reason
        """
        cls.name = name
        cls.node_type = 'firewall_node'
        cls.log_server_ref = log_server if log_server \
            else SystemInfo().first_log_server()  
        cls.domain_server_address = []
        if dns:
            for entry in dns:
                cls.domain_server_address.append(entry)
        
        physical = PhysicalInterface(mgmt_interface)
        physical.add_single_node_interface(mgmt_ip, 
                                           mgmt_network,
                                           is_mgmt=True,
                                           zone_ref=zone_ref)

        super(Layer3Firewall, cls).create()
        
        if default_nat:
            cls.engine_json['default_nat'] = True
            
        cls.engine_json.get('physicalInterfaces').append(physical.as_dict())
        
        cls.href = search.element_entry_point('single_fw')
        result = SMCElement(href=cls.href, json=cls.engine_json).create()
        if result.href:
            #got referring object location, load and return
            return Layer3Firewall(cls.name).load()
        else:
            raise SMCException('Could not create the engine, reason: %s' % result.msg)
        
class Layer2Firewall(Node):
    """
    Represents a Layer2 Firewall configuration.
    To instantiate and create, call 'create' classmethod as follows::
    
        engine = Layer2Firewall.create('mylayer2', '1.1.1.1', '1.1.1.0/24')
        
    """ 
    def __init__(self, name):
        Node.__init__(self, name)
        self.node_type = 'fwlayer2_node'
    
    @classmethod
    def create(cls, name, mgmt_ip, mgmt_network, 
               log_server=None, mgmt_interface=0, 
               inline_interface='1-2', logical_interface='default_eth', 
               dns=None, zone_ref=None):
        """ 
        Create a single layer 2 firewall with management interface, inline interface,
        and DNS
        
        :param name: name of firewall
        :param name: management network ip
        :param mgmt_network: management network in cidr format
        :param log_server: href to log_server instance for fw
        :param mgmt_interface: interface for management from SMC to fw
        :type mgmt_interface: int
        :param inline_interface: interface ID's to use for default inline interfaces
        :type inline_interface: string or None (i.e. '1-2')
        :param logical_interface: logical interface to assign to inline interface
        :type logical_interface: string
        :param dns: DNS server addresses
        :type dns: list
        :param zone_ref: zone name for management interface (created if not found)
        :return: self
        :raises: :py:class:`smc.api.web.SMCException`: Failure creating engine
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
        
        physical = PhysicalInterface(mgmt_interface)
        physical.add_node_interface(mgmt_ip, mgmt_network, 
                                    is_mgmt=True,
                                    zone_ref=zone_ref)

        intf_href = search.element_href_use_filter(logical_interface, 'logical_interface')
        
        inline = PhysicalInterface(inline_interface)
        inline.add_inline_interface(intf_href)
        
        cls.engine_json.get('physicalInterfaces').append(physical.as_dict())
        cls.engine_json.get('physicalInterfaces').append(inline.as_dict())
                
        cls.href = search.element_entry_point('single_layer2')
        
        result = SMCElement(href=cls.href, json=cls.engine_json).create()
        if result.href:
            #got referring object location, load and return
            return Layer2Firewall(cls.name).load()
        else:
            raise SMCException('Could not create the engine, reason: %s' % result.msg)

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
               dns=None, zone_ref=None):
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
        :param zone_ref: zone name for management interface (created if not found)
        :return: self
        :raises: :py:class:`smc.api.web.SMCException`: Failure to create with reason
        """
        cls.name = name
        cls.node_type = 'ips_node'
        cls.log_server_ref = log_server if log_server \
            else SystemInfo().first_log_server()
        cls.domain_server_address = []
        if dns:
            for entry in dns:
                cls.domain_server_address.append(entry)
                       
        physical = PhysicalInterface(mgmt_interface)
        physical.add_node_interface(mgmt_ip, mgmt_network, is_mgmt=True,
                                    zone_ref=zone_ref)
              
        intf_href = search.element_href_use_filter(logical_interface, 'logical_interface')
      
        inline = PhysicalInterface(inline_interface)
        inline.add_inline_interface(intf_href)
        
        super(IPS, cls).create()
        cls.engine_json.get('physicalInterfaces').append(physical.as_dict())
        cls.engine_json.get('physicalInterfaces').append(inline.as_dict())
        
        cls.href = search.element_entry_point('single_ips')
        result = SMCElement(href=cls.href, json=cls.engine_json).create()
        if result.href:
            #got referring object location, load and return
            return IPS(cls.name).load()
        else:
            raise SMCException('Could not create the engine, reason: %s' % result.msg)
        
class Layer3VirtualEngine(Node):
    """ Create a layer3 virtual engine and map to specified Master Engine
    
    Each layer 3 virtual firewall will use the same virtual resource that 
    should be pre-created.
        
    To instantiate and create, call 'create' as follows::
    
        engine = Layer3VirtualEngine.create('myips', 
                                            'mymaster_engine, 
                                            virtual_engine='ve-3',
                                            kwargs=[{'ipaddress': '5.5.5.5', 
                                                     'mask': '5.5.5.5/30', 
                                                     'interface_id': 0, 
                                                     'zone': ''}]
    """
    def __init__(self, name):
        Node.__init__(self, name)
        self.node_type = 'virtual_fw_node'
    
    @classmethod
    def create(cls, name, master_engine, virtual_resource, dns=None,
               default_nat=False, outgoing_intf=0, **kwargs):
        """
        :param name: Name of this layer 3 virtual engine
        :param master_engine: Name of existing master engine. This assumes the
               master engine and physical interfaces are already created
        :param virtual_resource: name of pre-created virtual resource
        :param default_nat: Whether to enable default NAT for outbound
        :type default_nat: boolean
        :param outgoing_intf: outgoing interface for VE. Specifies interface number
        :param kwargs: Interfaces mappings passed in            
        :return: self
        :raises: :py:class:`smc.api.web.SMCException`: Failure to create with reason
        """
        cls.name = name
        cls.node_type = 'virtual_fw_node'
        cls.domain_server_address = []
        cls.log_server_ref = None
        if dns:
            for entry in dns:
                cls.domain_server_address.append(entry)
                       
        super(Layer3VirtualEngine, cls).create()

        if default_nat:
            cls.engine_json['default_nat'] = True

        #Get reference to virtual resource
        virt_resource_href = None
        master_engine = Node(master_engine).load()
        for virt_resource in master_engine.virtual_resource():
            if virt_resource.get('name') == virtual_resource:
                virt_resource_href = virt_resource.get('href')
                break
        if not virt_resource_href:
            return SMCResult(msg='Cannot find virtual resource, cannot add VE')
        
        cls.engine_json['virtual_resource'] = virt_resource_href
            
        if kwargs:
            for interface in kwargs.get('interfaces'): #get interface info
               
                physical = VirtualPhysicalInterface(interface.get('interface_id'))
                physical.add_single_node_interface(interface.get('ipaddress'),
                                                   interface.get('mask'),
                                                   zone_ref=interface.get('zone'),
                                                   outgoing_intf=outgoing_intf)
    
                cls.engine_json.get('physicalInterfaces').append(physical.as_dict())
            cls.href = search.element_entry_point('virtual_fw')
            
        result = SMCElement(href=cls.href, json=cls.engine_json).create()
        if result.href:
            return Layer3VirtualEngine(cls.name).load()
        else:
            raise SMCException('Could not create the firewall, reason: %s' % result.msg)

class FirewallCluster(Node):
    """ Creates a layer 3 firewall cluster engine with nodes """
    def __init__(self, name):
        Node.__init__(self, name)
        self.node_type = 'firewall_node'
    
    @classmethod
    def create(cls, name, cluster_virtual, cluster_mask, 
               macaddress, cluster_nic, nodes, 
               log_server=None, dns=None, zone_ref=None):
        """
        :param name: name of cluster engine
        :param cluster_virtual: ip of cluster CVI
        :param cluster_mask: ip netmask of cluster CVI
        :param macaddress: macaddress for packet dispatch clustering
        :param cluster_nic: nic id to use for primary interface
        :param nodes: ipaddress/netmask/nodeid combination for cluster nodes
        :type nodes: list of dict [{ipaddress, netmask}]
        :param log_server: (optional) specify a log server reference
        :param dns: (optional) specify DNS servers for engine
        :param zone_ref: zone name for management interface (created if not found)
        :return: self
        :raises: :py:class:`smc.api.web.SMCException`: Failure to create with reason
        """
        cls.name = name
        cls.node_type = 'firewall_node'
        cls.log_server_ref = log_server if log_server \
            else SystemInfo().first_log_server()
        cls.nodes = len(nodes) #identify how many nodes to process
        cls.domain_server_address = []
        if dns:
            for entry in dns:
                cls.domain_server_address.append(entry)

        physical = PhysicalInterface(cluster_nic)
        physical.add_cluster_virtual_interface(cluster_virtual, 
                                               cluster_mask,
                                               macaddress, 
                                               nodes, 
                                               is_mgmt=True,
                                               zone_ref=zone_ref)
        super(FirewallCluster, cls).create()
        
        cls.engine_json.get('physicalInterfaces').append(physical.as_dict())
        cls.href = search.element_entry_point('fw_cluster')
        
        result = SMCElement(href=cls.href,
                            json=cls.engine_json).create()
        if result.href:
            return FirewallCluster(cls.name).load()
        else:
            raise SMCException('Could not create the firewall, reason: %s' % result.msg)