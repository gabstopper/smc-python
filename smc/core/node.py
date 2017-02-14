"""
Node level actions for an engine. Once an engine is loaded, all methods
and resources are available to that particular engine. 

For example, to load an engine and run node level commands::

    engine = Engine('myfw')
    for node in engine.nodes:
        node.reboot()
        node.bind_license()
        node.go_online()
        node.go_offline()
        ...
        ...
"""
import smc.actions.search as search
from smc.base.util import find_link_by_name, save_to_file
from smc.api.exceptions import LicenseError, NodeCommandFailed
from smc.base.model import Element, prepared_request

class Node(Element):
    """ 
    Node settings to make each engine node controllable individually.
    When Engine() is loaded, setattr will set all instance attributes
    with the contents of the node json. Very few would benefit from being
    modified with exception of 'name'. To change a top level attribute, you
    would call node.modify_attribute(name='value')
    Engine will have a 'has-a' relationship with node and stored as the
    nodes attribute
    
    Instance attributes:
    
    :ivar name: name of node
    :ivar type: type of node, i.e. firewall_node, etc
    :ivar nodeid: node id, useful for commanding engines
    :ivar disabled: whether node is disabled or not
    :ivar href: href of this resource
    """
    def __init__(self, meta=None):
        self.meta = meta

    @property
    def name(self):
        """
        Node name
        """
        return self.meta.name

    @property
    def type(self):
        """ 
        Node type
        """
        return self.meta.type

    @property
    def nodeid(self):
        """
        ID of this node
        """
        return self.cache[1].get('nodeid')

    @classmethod
    def create(cls, name, node_type, nodeid=1):
        """
        Create the node/s for the engine. This isn't called directly,
        instead it is used when engine.create() is called
        
        :param str name: name of node 
        :param str node_type: based on engine type specified 
        :param int nodeid: used to identify which node 
        """  
        node = {node_type: {
                    'activate_test': True,
                    'disabled': False,
                    'loopback_node_dedicated_interface': [],
                    'name': name + ' node '+str(nodeid),
                    'nodeid': nodeid}
                }
        return node

    def fetch_license(self):
        """ 
        Fetch the node level license
        
        :return: None
        :raises: :py:class:`smc.api.exceptions.LicenseError`
        """
        href = find_link_by_name('fetch', self.link)
        if href:
            result = prepared_request(href=href).create()
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
        href = find_link_by_name('bind', self.link)
        if href:
            result = prepared_request(href=href, 
                                      params=params).create()
            if result.msg:
                raise LicenseError(result.msg)
        
    def unbind_license(self):
        """ 
        Unbind a bound license on this node.
        
        :return: None
        :raises: :py:class:`smc.api.exceptions.LicenseError` 
        """
        href = find_link_by_name('unbind', self.link)
        if href:
            result = prepared_request(href=href).create()
            if result.msg:
                raise LicenseError(result.msg)
    
    def cancel_unbind_license(self):
        """ 
        Cancel unbind for license
        
        :return: None
        :raises: :py:class:`smc.api.exceptions.LicenseError`
        """
        href = find_link_by_name('cancel_unbind', self.link)
        if href:
            result = prepared_request(href=href).create()
            if result.msg:
                raise LicenseError(result.msg)
    
    def initial_contact(self, enable_ssh=True, time_zone=None, 
                        keyboard=None, 
                        install_on_server=None, 
                        filename=None):
        """ 
        Allows to save the initial contact for for the specified node
 
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
        href = find_link_by_name('initial_contact', self.link)
        if not href:
            raise NodeCommandFailed('Initial contact not supported on this node type')
        result = prepared_request(href=href,
                                  params={'enable_ssh': enable_ssh}).create()
        if result.content:
            if filename:
                try:
                    save_to_file(filename, result.content)
                except IOError as e:
                    raise NodeCommandFailed("Error occurred when attempting to "
                                            "save initial contact to file: {}"
                                            .format(e))
            return result.content
    
    def appliance_status(self):
        """ 
        Gets the appliance status for the specified node for the specific 
        supported engine 

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

        :param str comment: (optional) comment to audit
        :return: None
        :raises: :py:class:`smc.api.exceptions.NodeCommandFailed`
        """
        params = {'comment': comment}
        result = prepared_request(
                    href=find_link_by_name('go_online', self.link),
                    params=params).update()
        if result.msg:
            raise NodeCommandFailed(result.msg)

    def go_offline(self, comment=None):
        """ 
        Executes a Go-Offline operation on the specified node

        :param str comment: optional comment to audit
        :return: None
        :raises: :py:class:`smc.api.exceptions.NodeCommandFailed`
        """
        params = {'comment': comment}
        result = prepared_request(
                    href=find_link_by_name('go_offline', self.link),
                    params=params).update()
        if result.msg:
            raise NodeCommandFailed(result.msg)

    def go_standby(self, comment=None):
        """ 
        Executes a Go-Standby operation on the specified node. 
        To get the status of the current node/s, run :func:`status`

        :param str comment: optional comment to audit
        :return: None
        :raises: :py:class:`smc.api.exceptions.NodeCommandFailed`
        """
        params = {'comment': comment}
        result = prepared_request(
                    href=find_link_by_name('go_standby', self.link),
                    params=params).update()
        if result.msg:
            raise NodeCommandFailed(result.msg)

    def lock_online(self, comment=None):
        """ 
        Executes a Lock-Online operation on the specified node

        :param str comment: comment for audit
        :return: None
        :raises: :py:class:`smc.api.exceptions.NodeCommandFailed`
        """
        params = {'comment': comment}
        result = prepared_request(
                    href=find_link_by_name('lock_online', self.link),
                    params=params).update()
        if result.msg:
            raise NodeCommandFailed(result.msg)

    def lock_offline(self, comment=None):
        """ 
        Executes a Lock-Offline operation on the specified node
        Bring back online by running :func:`go_online`.

        :param str comment: comment for audit
        :return: None
        :raises: :py:class:`smc.api.exceptions.NodeCommandFailed`
        """
        params = {'comment': comment}
        result = prepared_request(
                    href=find_link_by_name('lock_offline', self.link),
                    params=params).update()
        if result.msg:
            raise NodeCommandFailed(result.msg)
    
    def reset_user_db(self, comment=None):
        """ 
        Executes a Send Reset LDAP User DB Request operation on this
        node.

        :param str comment: comment to audit
        :return: None
        :raises: :py:class:`smc.api.exceptions.NodeCommandFailed`
        """
        params = {'comment': comment}
        href = find_link_by_name('reset_user_db', self.link)
        if not href:
            raise NodeCommandFailed('Reset userdb not supported on this node type')
        result = prepared_request(href=href,
                                  params=params).update()
        if result.msg:
            raise NodeCommandFailed(result.msg)
    
    def diagnostic(self, filter_enabled=False):
        """ 
        Provide a list of diagnostic options to enable
        
        Get all diagnostic/debug settings::
            
            engine = Engine('myfw')
            for node in engine:
                for diag in node.diagnostic():
                    print diag
                    
        Add filter_enabled=True argument to see only enabled settings

        :param boolean filter_enabled: returns all enabled diagnostics
        :return: list of dict items with diagnostic info; key 'diagnostics'
        :raises: :py:class:`smc.api.exceptions.NodeCommandFailed`
        """
        params={'filter_enabled': filter_enabled}
        href = find_link_by_name('diagnostic', self.link)
        if not href:
            raise NodeCommandFailed('Diagnostic not supported on this node type: {}'
                                    .format(self.type))
        result = search.element_by_href_as_smcresult(href, params)
        if result.msg:
            raise NodeCommandFailed(result.msg)
        
        return [(Diagnostic(**diagnostic))
                for diagnostic in result.json.get('diagnostics')]

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
        result = prepared_request(
                    href=find_link_by_name('send_diagnostic', self.link),
                    json={'diagnostics': debug}).create()
        if result.msg:
            raise NodeCommandFailed(result.msg)

    def reboot(self, comment=None):
        """ 
        Send reboot command to this node.

        :param str comment: comment to audit
        :return: None
        :raises: :py:class:`smc.api.exceptions.NodeCommandFailed`
        """
        params = {'comment': comment}
        result = prepared_request(
                    href=find_link_by_name('reboot', self.link),
                    params=params).update()
        if result.msg:
            raise NodeCommandFailed(result.msg)
        
    def sginfo(self, include_core_files=False,
               include_slapcat_output=False,
               filename='sginfo.gz'):
        """ 
        Get the SG Info of the specified node 

        :param include_core_files: flag to include or not core files
        :param include_slapcat_output: flag to include or not slapcat output
        """
        #params = {'include_core_files': include_core_files,
        #          'include_slapcat_output': include_slapcat_output}
        #result = prepared_request(href=find_link_by_name('sginfo', self.link),
        #                          filename=filename).read()
        raise NotImplementedError
   
    def ssh(self, enable=True, comment=None):
        """ 
        Enable or disable SSH

        :param boolean enable: enable or disable SSH daemon
        :param str comment: optional comment for audit
        :return: None
        :raises: :py:class:`smc.api.exceptions.NodeCommandFailed`
        """
        params = {'enable': enable, 'comment': comment}
        href = find_link_by_name('ssh', self.link)
        if not href:
            raise NodeCommandFailed('SSH not supported on this node type: {}'
                                    .format(self.type))
        result = prepared_request(href=href,
                                  params=params).update()
        if result.msg:
            raise NodeCommandFailed(result.msg)

    def change_ssh_pwd(self, pwd=None, comment=None):
        """
        Executes a change SSH password operation on the specified node 

        :param str pwd: changed password value
        :param str comment: optional comment for audit log
        :return: None
        :raises: :py:class:`smc.api.exceptions.NodeCommandFailed`
        """
        params = {'comment': comment}
        href = find_link_by_name('change_ssh_pwd', self.link)
        if not href:
            raise NodeCommandFailed('Change SSH pwd not supported on this node type: {}'
                                    .format(self.type))
        result = prepared_request(href=href,
                                  params=params, 
                                  json={'value': pwd}).update()
        if result.msg:
            raise NodeCommandFailed(result.msg)

    def time_sync(self):
        """ 
        Send a time sync command to this node.

        :return: None
        :raises: :py:class:`smc.api.exceptions.NodeCommandFailed`
        """
        href = find_link_by_name('time_sync', self.link)
        if not href:
            raise NodeCommandFailed('Time sync not supported on this node type: {}'
                                    .format(self.type))
        result = prepared_request(href=href).update()
        if result.msg:
            raise NodeCommandFailed(result.msg)
      
    def certificate_info(self):
        """ 
        Get the certificate info of this node. This can return None if the 
        engine type does not directly have a certificate, like a virtual engine
        where the master engine manages certificates.
        
        :return: dict with links to cert info
        """
        return search.element_by_href_as_json(
                find_link_by_name('certificate_info', self.link))

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
        
        for k,v in kwargs.items():
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
