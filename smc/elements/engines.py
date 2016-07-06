from abc import ABCMeta, abstractmethod
from smc.elements.element import SMCElement
from smc.elements.interfaces import inline_intf, l2_mgmt_interface, \
    l3_mgmt_interface, l3_interface, inline_interface, capture_interface
import smc.actions.search as search
import smc.api.common as common_api
from smc.api.web import SMCException

class Engine(object):
    """
    Top level engine class representing settings of the generic engine, indepdendent of
    the engine type. The load class is abstract and must be called from a descendant class,
    either Node or descendent classes of Node (preferred) such as:
    
    :class:`smc.elements.engines.Layer3Firewall`
    
    :class:`smc.elements.engines.Layer2Firewall`
    
    :class:`smc.elements.engines.IPS`
    
    This is intended to store the top level engine properties and operations specific to 
    the engine itself.
    
    :class:`smc.elements.engines.Node` class will store information specific to the individual
    node itself such as rebooting, going online/offline, change user pwd, ssh pwd reset, etc. 
    All of these methods are inherited by their subclasses.
    """
    
    __metaclass__ = ABCMeta
    
    def __init__(self, name):
        self.name = name
        self.href = None #pulled from self
        self.etag = None #saved in case of modifications
        self.engine_version = None
        self.log_server_ref = None
        self.cluster_mode = None
        self.domain_server_address = []
        self.engine_json = None
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
        node = {
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
    
    def refresh(self):
        print "POST refresh: %s" % self.__load_href('refresh')
    
    def upload(self):
        print "POST upload: %s" % self.__load_href('upload')
    
    def add_route(self):
        print "POST add_route: %s" % self.__load_href('add_route')
    
    def interface(self):
        """ Get all interfaces, including non-physical interfaces such
        as tunnel or capture interfaces.
        
        :method: GET
        :return: list of dict entries with href,name,type, or None
        """
        return search.element_by_href_as_json(self.__load_href('interfaces')) 
    
    def blacklist(self):
        print "POST blacklist: %s" % self.__load_href('blacklist')
    
    def blacklist_flush(self):
        print "DELETE blacklist_flush: %s" % self.__load_href('flush_blacklist')
           
    def generate_snapshot(self):
        print "GET generate_snapshot: %s" % self.__load_href('generate_snapshot')
        #return search.element_by_href_as_json(self.__load_href('generate_snapshot'))
        pass
    
    def export(self):
        print "POST export: %s" % self.__load_href('export')
    
    def routing(self):
        """ Retrieve routing json from engine node
        
        :method: GET
        :return: json representing routing configuration
        """
        return search.element_by_href_as_json(self.__load_href('routing'))
    
    def physical_interface(self):
        """ Get only physical interfaces for this engine node. This will not include
        tunnel interfaces or capture interfaces.
       
        :method: GET
        :return: list of dict entries with href,name,type, or None
        """
        return search.element_by_href_as_json(self.__load_href('physical_interface')) 
    
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
    """
    def __init__(self, name):
        Engine.__init__(self, name)
        self.name = name
        self.node_type = None
        self.node_links = []
        
    def load(self):
        print "Before super, object"
        from pprint import pprint
        pprint(self)
        super(Node, self).load()
        print "After super, object"
        pprint(self)
        for node in self.engine_json.get('nodes'): #list
            for node_type, node_info in node.iteritems():
                self.node_type = node_type
                self.node_links.extend(node_info.get('link'))
        return self
    
    @classmethod
    def create(cls):
        #nothing to do here, engine has base settings
        return super(Node, cls).create()
    
    def update(self):
        element = SMCElement.factory(href=self.href, 
                                    json=self.engine_json, 
                                    etag=self.etag)
        return common_api._update(element)
    
    def add_l3_interface(self, ipaddress, network, interface_id):
        interface = l3_interface(ipaddress, network, interface_id)
        self.engine_json.get('physicalInterfaces').append(interface.json)
    
    def add_inline_interface(self, logical_interface='default_eth', 
                             interface_id='1-2'):
        try:
            assert(isinstance(self, (Layer2Firewall, IPS, Node)))
            logical_href = search.element_href(logical_interface)
            interface = inline_interface(logical_href, 
                                         interface_id=interface_id)
            self.engine_json.get('physicalInterfaces').append(interface.json)
        except AssertionError:
            raise SMCException("Cannot add a layer 2 interface to node type: %s, class: %s" % 
                               (self.node_type, self))     
    
    def add_capture_interface(self, logical_interface='default_eth',
                              interface_id='1'):
        try:
            assert(isinstance(self, (Layer2Firewall, IPS)))
            logical_href = search.element_href(logical_interface)
            interface = capture_interface(logical_href, interface_id)
            self.engine_json.get('physicalInterfaces').append(interface.json)
        except AssertionError:
            raise SMCException("Cannot add a capture interface to node type: %s, class: %s" % 
                               (self.node_type, self)) 
        
    def add_tunnel_interface(self):
        pass
        
    def fetch_license(self):
        print "POST fetch license: %s" % self.__load_href('fetch')
    
    def bind_license(self):
        print "POST bind license: %s" % self.__load_href('bind')
        
    def unbind_license(self):
        print "POST unbind license: %s" % self.__load_href('unbind')
        
    def cancel_unbind_license(self):
        print "POST cancel unbind: %s" % self.__load_href('cancel_unbind')
        
    def initial_contact(self):
        print "POST initial contact: %s" % self.__load_href('initial_contact')
        
    def appliance_status(self): #TODO This causes string formatting problem in SMCOperationFailure
        return search.element_by_href_as_json(self.__load_href('appliance_status'))
        
    def status(self):
        """ Basic status for individual node. Specific information such as node name,
        dynamic package version, configuration status, platform and version.
        
        :return: dict of status fields returned from SMC
        """
        return search.element_by_href_as_json(self.__load_href('status'))
        
    def go_online(self):
        print "PUT go online: %s" % self.__load_href('go_online')
    
    def go_offline(self):
        print "PUT go offline: %s" % self.__load_href('go_offline')
        
    def go_standby(self):
        print "PUT go_standby: %s" % self.__load_href('go_standby')
        
    def lock_online(self):
        print "PUT lock online: %s" % self.__load_href('lock_online')
        
    def lock_offline(self):
        print "PUT lock offline: %s" % self.__load_href('lock_offline')
        
    def reset_user_db(self):
        print "PUT reset user db: %s" % self.__load_href('reset_user_db')
        
    def diagnostic(self):
        print "GET diagnostic: %s" % self.__load_href('diagnostic')
        
    def send_diagnostic(self):
        print "POST send diagnostic: %s" % self.__load_href('send_diagnostic')
        
    def reboot(self):
        print "PUT reboot: %s" % self.__load_href('reboot')
        
    def sginfo(self):
        print "GET sginfo: %s" % self.__load_href('sginfo')
        
    def ssh(self):
        print "PUT ssh: %s" % self.__load_href('ssh')
        
    def change_ssh_pwd(self):
        print "PUT change SSH pwd: %s" % self.__load_href('change_ssh_pwd')
        
    def time_sync(self):
        print "PUT time sync: %s" % self.__load_href('time_sync')
        
    def certificate_info(self):
        print "GET cert info: %s" % self.__load_href('certificate_info')

    def __load_href(self, action):
        href = [entry.get('href') for entry in self.node_links \
                if entry.get('rel') == action]      
        if href:
            return href.pop()
        
class Layer3Firewall(Node):
    """
    Represents a Layer 3 Firewall configuration.
    To instantiate and create, call 'create' classmethod as follows::
    
        engine = Layer3Firewall.create('mylayer3', '1.1.1.1', '1.1.1.0/24', href_to_log_server)
        
    To obtain the log server reference, first call::
        
        smc.search.get_first_log_server()    #first log server found
        smc.search.log_servers()    #all available log servers
        
    """ 
    def __init__(self, name):
        Node.__init__(self, name)
        self.node_type = 'firewall_node'

    @classmethod   
    def create(cls, name, mgmt_ip, mgmt_network, log_server,
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
        cls.log_server_ref = log_server
        cls.domain_server_address = []
        if dns:
            for entry in dns:
                cls.domain_server_address.append(entry)  
        super(Layer3Firewall, cls).create()
        mgmt = l3_mgmt_interface(mgmt_ip, mgmt_network, 
                                 interface_id=mgmt_interface)
        cls.engine_json.get('physicalInterfaces').append(mgmt.json)
        cls.href = search.element_entry_point('single_fw')
        return cls #json    
    

class Layer2Firewall(Node):
    """
    Represents a Layer2 Firewall configuration.
    To instantiate and create, call 'create' classmethod as follows::
    
        engine = Layer2Firewall.create('mylayer2', '1.1.1.1', '1.1.1.0/24', href_to_log_server)
        
    To obtain the log server reference, first call::
        
        smc.search.get_first_log_server()    #first log server found
        smc.search.log_servers()    #all available log servers
        
    """ 
    def __init__(self, name):
        Node.__init__(self, name)
        self.node_type = 'fwlayer2_node'
    
    @classmethod
    def create(cls, name, mgmt_ip, mgmt_network, 
               log_server, mgmt_interface='0', 
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
        cls.log_server_ref = log_server
        cls.domain_server_address = []
        if dns:
            for entry in dns:
                cls.domain_server_address.append(entry)
                   
        super(Layer2Firewall, cls).create()
        mgmt = l2_mgmt_interface(mgmt_ip, mgmt_network, 
                                 interface_id=mgmt_interface)
        
        intf_href = search.get_logical_interface(logical_interface)
        inline = inline_intf(intf_href, interface_id=inline_interface)
    
        cls.engine_json.get('physicalInterfaces').append(mgmt.json)
        cls.engine_json.get('physicalInterfaces').append(inline.json)
        cls.href = search.element_entry_point('single_layer2')
        return cls
        

class IPS(Node):
    """
    Represents an IPS engine configuration.
    To instantiate and create, call 'create' classmethod as follows::
    
        engine = IPS.create('myips', '1.1.1.1', '1.1.1.0/24', href_to_log_server)
        
    To obtain the log server reference, first call::
        
        smc.search.get_first_log_server()    #first log server found
        smc.search.log_servers()    #all available log servers
        
    """ 
    def __init__(self, name):
        Node.__init__(self, name)
        self.node_type = 'ips_node'

    @classmethod
    def create(cls, name, mgmt_ip, mgmt_network, 
               log_server, mgmt_interface='0', 
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
        cls.log_server_ref = log_server
        cls.domain_server_address = []
        if dns:
            for entry in dns:
                cls.domain_server_address.append(entry)
                       
        super(IPS, cls).create()
        mgmt = l2_mgmt_interface(mgmt_ip, mgmt_network, 
                                interface_id=mgmt_interface)
            
        intf_href = search.get_logical_interface(logical_interface)
        inline = inline_intf(intf_href, interface_id=inline_interface)
        
        cls.engine_json.get('physicalInterfaces').append(mgmt.json)
        cls.engine_json.get('physicalInterfaces').append(inline.json)
        cls.href = search.element_entry_point('single_ips')
        return cls

def NodeLoader():
    pass