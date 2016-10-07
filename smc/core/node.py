"""
Node level actions for an engine. Once an engine is loaded, all methods
and resources are available to that particular engine. 

For example, to load an engine and run node level commands::

    engine = Engine('myfw').load()
    for node in engine.nodes:
        node.reboot()
        node.bind_license()
        node.go_online()
        node.go_offline()
        ...
        ...
"""
import smc.actions.search as search
from smc.elements.util import find_link_by_name, save_to_file
from smc.api.exceptions import LicenseError, NodeCommandFailed
from smc.api.common import SMCRequest
from smc.elements.mixins import ModifiableMixin

class Node(ModifiableMixin):
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
    :ivar node_type: type of node, i.e. firewall_node, etc
    :ivar nodeid: node id, useful for commanding engines
    :ivar disabled: whether node is disabled or not
    :ivar href: href of this resource
    """
    def __init__(self, meta=None, **kwargs):
        self.meta = meta

    @property
    def name(self):
        return self.meta.name
    
    @property
    def href(self):
        return self.meta.href
    
    @property
    def node_type(self):
        return self.meta.type
    
    @property
    def nodeid(self):
        return self.json.get('nodeid')

    @property
    def link(self):
        return self.json.get('link')

    @classmethod
    def create(cls, name, node_type, nodeid=1):
        """
        Create the node/s for the engine. This isn't called directly,
        instead it is used when engine.create() is called
        
        :param str name: name of node 
        :param str node_type: based on engine type specified 
        :param int nodeid: used to identify which node 
        """  
        node = { node_type: {
                    'activate_test': True,
                    'disabled': False,
                    'loopback_node_dedicated_interface': [],
                    'name': name + ' node '+str(nodeid),
                    'nodeid': nodeid }
                }
        return node

    def fetch_license(self):
        """ 
        Fetch the node level license
        
        :return: None
        :raises: :py:class:`smc.api.exceptions.LicenseError`
        """
        result = SMCRequest(
                    href=find_link_by_name('fetch', self.link)).create()
        if result.msg:
            raise LicenseError(result.msg)

    def bind_license(self, license_item_id=None):
        """ 
        Auto bind license, uses dynamic if POS is not found
        
        :param str license_item_id: license id
        :return: None
        :raises: :py:class:`smc.api.exceptions.LicenseError`
        """
        params = {'license_item_id': license_item_id}
        result = SMCRequest(
                    href=find_link_by_name('bind', self.link), params=params).create()
        if result.msg:
            raise LicenseError(result.msg)
        
    def unbind_license(self):
        """ 
        Unbind a bound license on this node.
        
        :return: None
        :raises: :py:class:`smc.api.exceptions.LicenseError` 
        """
        result = SMCRequest(
                    href=find_link_by_name('unbind', self.link)).create()
        if result.msg:
            raise LicenseError(result.msg)
    
    def cancel_unbind_license(self):
        """ 
        Cancel unbind for license
        
        :return: None
        :raises: :py:class:`smc.api.exceptions.LicenseError`
        """
        result = SMCRequest(
                    href=find_link_by_name('cancel_unbind', self.link)).create()
        if result.msg:
            raise LicenseError(result.msg)
    
    def initial_contact(self, enable_ssh=True, time_zone=None, 
                        keyboard=None, 
                        install_on_server=None, 
                        filename=None):
        """ 
        Allows to save the initial contact for for the specified node
        
        :method: POST
        :param boolean enable_ssh: flag to know if we allow the ssh daemon on the 
               specified node
        :param str time_zone: optional time zone to set on the specified node 
        :param str keyboard: optional keyboard to set on the specified node
        :param boolean install_on_server: optional flag to know if the generated configuration 
               needs to be installed on SMC Install server (POS is needed)
        :param str filename: filename to save initial_contact to
        :return: str initial contact text information
        :raises: :py:class:`smc.api.exceptions.NodeCommandFailed` 
        """
        result = SMCRequest(
                    href=find_link_by_name('initial_contact', self.link),
                    params={'enable_ssh': enable_ssh}).create()
      
        if result.content:
            if filename:
                try:
                    save_to_file(filename, result.content)
                except IOError, e:
                    raise NodeCommandFailed("Error occurred when attempting to "
                                            "save initial contact to file: {}"
                                            .format(e))
            return result.content
    
    def appliance_status(self):
        """ 
        Gets the appliance status for the specified node for the specific 
        supported engine 
        
        :method: GET
        :return: list of status information
        """
        result = search.element_by_href_as_smcresult(
                            find_link_by_name('appliance_status', self.link))
        if result.msg:
            raise NodeCommandFailed(result.msg)
        return ApplianceStatus(**result.json)
    
    def status(self):
        """ 
        Basic status for individual node. Specific information such as node 
        name dynamic package version, configuration status, platform and version.
        
        :method: GET
        :return: :py:class:`~NodeStatus`
        """
        result = search.element_by_href_as_smcresult(
                            find_link_by_name('status', self.link))
        if result.msg:
            raise NodeCommandFailed(result.msg)
        return NodeStatus(**result.json)

    def go_online(self, comment=None):
        """ 
        Executes a Go-Online operation on the specified node 
        typically done when the node has already been forced offline 
        via :func:`go_offline`
        
        :method: PUT
        :param str comment: (optional) comment to audit
        :return: None
        :raises: :py:class:`smc.api.exceptions.NodeCommandFailed`
        """
        params = {'comment': comment}
        result = SMCRequest(
                    href=find_link_by_name('go_online', self.link),
                    params=params).update()
        if result.msg:
            raise NodeCommandFailed(result.msg)

    def go_offline(self, comment=None):
        """ 
        Executes a Go-Offline operation on the specified node
        
        :method: PUT
        :param str comment: optional comment to audit
        :return: None
        :raises: :py:class:`smc.api.exceptions.NodeCommandFailed`
        """
        params = {'comment': comment}
        result = SMCRequest(
                    href=find_link_by_name('go_offline', self.link),
                    params=params).update()
        if result.msg:
            raise NodeCommandFailed(result.msg)

    def go_standby(self, comment=None):
        """ 
        Executes a Go-Standby operation on the specified node. 
        To get the status of the current node/s, run :func:`status`
        
        :method: PUT
        :param str comment: optional comment to audit
        :return: None
        :raises: :py:class:`smc.api.exceptions.NodeCommandFailed`
        """
        params = {'comment': comment}
        result = SMCRequest(
                    href=find_link_by_name('go_standby', self.link),
                    params=params).update()
        if result.msg:
            raise NodeCommandFailed(result.msg)

    def lock_online(self, comment=None):
        """ 
        Executes a Lock-Online operation on the specified node
        
        :method: PUT
        :param str comment: comment for audit
        :return: None
        :raises: :py:class:`smc.api.exceptions.NodeCommandFailed`
        """
        params = {'comment': comment}
        result = SMCRequest(
                    href=find_link_by_name('lock_online', self.link),
                    params=params).update()
        if result.msg:
            raise NodeCommandFailed(result.msg)

    def lock_offline(self, comment=None):
        """ 
        Executes a Lock-Offline operation on the specified node
        Bring back online by running :func:`go_online`.
        
        :method: PUT
        :param str comment: comment for audit
        :return: None
        :raises: :py:class:`smc.api.exceptions.NodeCommandFailed`
        """
        params = {'comment': comment}
        result = SMCRequest(
                    href=find_link_by_name('lock_offline', self.link),
                    params=params).update()
        if result.msg:
            raise NodeCommandFailed(result.msg)
    
    def reset_user_db(self, comment=None):
        """ 
        Executes a Send Reset LDAP User DB Request operation on this
        node.
        
        :method: PUT
        :param str comment: comment to audit
        :return: None
        :raises: :py:class:`smc.api.exceptions.NodeCommandFailed`
        """
        params = {'comment': comment}
        result = SMCRequest(
                    href=find_link_by_name('reset_user_db', self.link),
                    params=params).update()
        if result.msg:
            raise NodeCommandFailed(result.msg)
    
    def diagnostic(self, filter_enabled=False):
        """ 
        Provide a list of diagnostic options to enable
        
        Get all diagnostic/debug settings::
            
            engine = Engine('myfw').load()
            for node in engine:
                for diag in node.diagnostic():
                    print diag
                    
        Add filter_enabled=True argument to see only enabled settings
        
        :method: GET
        :param boolean filter_enabled: returns all enabled diagnostics
        :return: list of dict items with diagnostic info; key 'diagnostics'
        :raises: :py:class:`smc.api.exceptions.NodeCommandFailed`
        """
        href = find_link_by_name('diagnostic', self.link)
        params={'filter_enabled': filter_enabled}
        result = search.element_by_href_as_smcresult(href, params)
        if result.msg:
            raise NodeCommandFailed(result.msg)
        diagnostics=[]
        for diagnostic in result.json.get('diagnostics'):
            diagnostics.append(Diagnostic(**diagnostic))
        return diagnostics

    def send_diagnostic(self, diagnostic):
        """ 
        Enable or disable specific diagnostics on the node.
        Diagnostics enable additional debugging into the audit files. This is
        a dynamic setting that does not require a policy push once a setting 
        is enabled or disabled.
        
        Enable specific debug settings and apply to node::
        
            for node in engine.nodes:
                debug=[]
                for diag in node.diagnostic():
                    if diag.name == 'Protocol Agent':
                        diag.enable()
                        debug.append(diag)
                    elif diag.name == 'Packet filter':
                        diag.enable()
                        debug.append(diag)
            node.send_diagnostic(debug)
        
        :param list diagnostic: :py:class:`smc.core.node.Diagnostic` object
        :return: None
        :raises: :py:class:`smc.api.exceptions.NodeCommandFailed`
        """
        debug=[]
        for setting in diagnostic:
            debug.append(vars(setting))
        result = SMCRequest(
                    href=find_link_by_name('send_diagnostic', self.link),
                    json={'diagnostics': debug}).create()
        if result.msg:
            raise NodeCommandFailed(result.msg)

    def reboot(self, comment=None):
        """ 
        Send reboot command to this node.
        
        :method: PUT
        :param str comment: comment to audit
        :return: None
        :raises: :py:class:`smc.api.exceptions.NodeCommandFailed`
        """
        params = {'comment': comment}
        result = SMCRequest(
                    href=find_link_by_name('reboot', self.link),
                    params=params).update()
        if result.msg:
            raise NodeCommandFailed(result.msg)
        
    def sginfo(self, include_core_files=False,
               include_slapcat_output=False,
               filename='sginfo.zip'):
        """ 
        Get the SG Info of the specified node 
        
        :method: GET
        :param include_core_files: flag to include or not core files
        :param include_slapcat_output: flag to include or not slapcat output
        """
        params = {'include_core_files': include_core_files,
                  'include_slapcat_output': include_slapcat_output}
        result = SMCRequest(href=find_link_by_name('sginfo', self.link),
                            filename=filename).read()
   
    def ssh(self, enable=True, comment=None):
        """ 
        Enable or disable SSH
        
        :method: PUT
        :param boolean enable: enable or disable SSH daemon
        :param str comment: optional comment for audit
        :return: None
        :raises: :py:class:`smc.api.exceptions.NodeCommandFailed`
        """
        params = {'enable': enable, 'comment': comment}
        result = SMCRequest(
                    href=find_link_by_name('ssh', self.link),
                    params=params).update()
        if result.msg:
            raise NodeCommandFailed(result.msg)

    def change_ssh_pwd(self, pwd=None, comment=None):
        """
        Executes a change SSH password operation on the specified node 
        
        :method: PUT
        :param str pwd: changed password value
        :param str comment: optional comment for audit log
        :return: None
        :raises: :py:class:`smc.api.exceptions.NodeCommandFailed`
        """
        json = {'value': pwd}
        params = {'comment': comment}
        result = SMCRequest(
                    href=find_link_by_name('change_ssh_pwd', self.link),
                    params=params, json=json).update()
        if result.msg:
            raise NodeCommandFailed(result.msg)

    def time_sync(self):
        """ 
        Send a time sync command to this node.

        :method: PUT
        :return: None
        :raises: :py:class:`smc.api.exceptions.NodeCommandFailed`
        """
        result = SMCRequest(
                    href=find_link_by_name('time_sync', self.link)).update()
        if result.msg:
            raise NodeCommandFailed(result.msg)
      
    def certificate_info(self):
        """ 
        Get the certificate info of this node.
        
        :return: dict with links to cert info
        """
        return search.element_by_href_as_json(
                find_link_by_name('certificate_info', self.link))
    
    def __getattr__(self, attr):
        if attr == 'json':
            setattr(self, 'json', \
                        search.element_by_href_as_json(self.href))
            return self.json
        raise AttributeError('Unsupported node command: {}'
                             .format(attr))

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, 'name={},node_type={}'
                           .format(self.name,self.node_type))

class NodeStatus(object):
    """
    Node Status carrying attributes that can be checked easily
    
    :ivar dyn_up: dynamic update package version
    :ivar installed_policy: policy name
    :ivar name: name of engine
    :ivar platform: current underlying platform
    :ivar version: version of software installed
    
    :ivar configuration_status:
     
        Return values:
            * Initial no initial configuration file is yet generated.
            * Declared initial configuration file is generated.
            * Configured initial configuration is done with the engine.
            * Installed policy is installed on the engine.

    :ivar status:
    
        Return values:
            Not Monitored/Unknown/Online/Going Online/Locked Online/
            Going Locked Online/Offline/Going Offline/Locked Offline/
            Going Locked Offline/Standby/Going Standby/No Policy Installed
            
    :ivar state:
    
        Return values:
            INITIAL/READY/ERROR/SERVER_ERROR/NO_STATUS/TIMEOUT/
            DELETED/DUMMY
    """

    def __init__(self, **kwargs):
        self.configuration_status = None
        self.dyn_up = None
        self.installed_policy = None
        self.name = None
        self.platform = None
        self.state = None
        self.status = None
        self.version = None
        
        for k,v in kwargs.iteritems():
            setattr(self, k, v)

    def __getattr__(self, value):
        return None

class ApplianceStatus(object):
    """
    Appliance status for file system and other database related information.
    This is normally visible from the SMC Home->firewall node view.
    
    :ivar list interface_statuses: list of interfaces and status fields
    :ivar list hardware_statuses: list of hardware related settings, like db 
          updates, file system and usage
    """
    def __init__(self, interface_statuses=None, 
                 hardware_statuses=None, **kwargs):
        self._interface_statuses = interface_statuses
        self._hardware_statuses = hardware_statuses
        
    @property
    def interface_statuses(self):
        return self._interface_statuses.get('interface_status')
    
    @property
    def hardware_statuses(self):
        return self._hardware_statuses.get('hardware_statuses')
    
class Diagnostic(object):
    """
    Diagnostic (debug) setting that can be enabled or disabled on the
    node. To retrieve the diagnostic options, get the engine context and
    iterate the available nodes::
    
        for node in engine.nodes:
            for diagnostic in node.diagnostics():
                print diagnostic
    
    This class is not called directly.
    :ivar str name: name of diagnostic
    :ivar boolean state: enabled or disabled
    
    :param diagnostic: diagnostic, called from node.diagnostic()
    """
    def __init__(self, diagnostic):
        self.diagnostic = diagnostic
    
    def enable(self):
        self.diagnostic['enabled'] = True
        
    def disable(self):
        self.diagnostic['enabled'] = False
    
    @property
    def name(self):
        return self.diagnostic.get('name')

    @property
    def state(self):
        return self.diagnostic.get('enabled')

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, 'name={},enabled={}'
                           .format(self.name, self.state))