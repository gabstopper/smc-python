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
import base64
from collections import namedtuple
from smc.base.util import save_to_file
from smc.base.model import SubElement, SimpleElement
from smc.api.exceptions import LicenseError, NodeCommandFailed, \
    ResourceNotFound


class Node(SubElement):
    """
    Node settings to make each engine node controllable individually.
    Obtain a reference to a Node by loading an Engine resource.
    Engine will have a 'has-a' relationship with node and stored as the
    nodes attribute.
    ::

        for node in engine.nodes:
            ...

    """
    def __init__(self, **meta):
        super(Node, self).__init__(**meta)
    
    @property
    def type(self):
        """
        Node type
        """
        return self._meta.type

    def rename(self, name):
        # This should be called from engine level
        self.update(name='{} node {}'.format(name, self.nodeid))

    @property
    def nodeid(self):
        """
        ID of this node
        """
        return self.data.get('nodeid')

    @classmethod
    def _load(cls, list_of_nodes):
        nodes = []
        for node in list_of_nodes:
            for typeof, data in node.items():
                cache = SimpleElement(**data)
                node = Node(name=cache.get('name'),
                            href=cache.get_link('self'),
                            type=typeof)
                node.data = cache
                nodes.append(node)
        return nodes

    @classmethod
    def _create(cls, name, node_type, nodeid=1,
                loopback_ndi=None):
        """
        Create the node/s for the engine. This isn't called directly,
        instead it is used when engine.create() is called

        :param str name: name of node
        :param str node_type: based on engine type specified
        :param int nodeid: used to identify which node
        :param list LoopbackInterface loopback_ndi: optional loopback
            interface for node.
        """
        loopback = loopback_ndi if loopback_ndi else []
        node = {node_type: {
            'activate_test': True,
            'disabled': False,
            'loopback_node_dedicated_interface': loopback,
            'name': name + ' node ' + str(nodeid),
            'nodeid': nodeid}
        }
        return node

    def fetch_license(self):
        """
        Fetch the node level license

        :raises LicenseError: fetching license failure with reason
        :return: None
        """
        try:
            self.send_cmd(
                LicenseError,
                resource='fetch')
        
        except ResourceNotFound:
            pass

    def bind_license(self, license_item_id=None):
        """
        Auto bind license, uses dynamic if POS is not found

        :param str license_item_id: license id
        :raises LicenseError: binding license failed, possibly no licenses
        :return: None
        """
        params = {'license_item_id': license_item_id}
        try:
            self.send_cmd(
                LicenseError,
                resource='bind',
                params=params)
        
        except ResourceNotFound:
            pass

    def unbind_license(self):
        """
        Unbind a bound license on this node.

        :raises LicenseError: failure with reason
        :return: None
        """
        try:
            self.send_cmd(
                LicenseError,
                resource='unbind')
        
        except ResourceNotFound:
            pass

    def cancel_unbind_license(self):
        """
        Cancel unbind for license

        :raises LicenseError: unbind failed with reason
        :return: None
        """
        try:
            self.send_cmd(
                LicenseError,
                resource='cancel_unbind')
    
        except ResourceNotFound:
            pass

    def initial_contact(self, enable_ssh=True, time_zone=None,
                        keyboard=None,
                        install_on_server=None,
                        filename=None,
                        as_base64=False):
        """
        Allows to save the initial contact for for the specified node

        :param bool enable_ssh: flag to know if we allow the ssh daemon on the
               specified node
        :param str time_zone: optional time zone to set on the specified node
        :param str keyboard: optional keyboard to set on the specified node
        :param bool install_on_server: optional flag to know if the generated
            configuration needs to be installed on SMC Install server
            (POS is needed)
        :param str filename: filename to save initial_contact to
        :param bool as_base64: return the initial config in base 64 format. Useful
            for cloud based engine deployments as userdata
        :raises NodeCommandFailed: IOError handling initial configuration data
        :return: initial contact text information
        :rtype: str
        """
        try:
            result = self._request(
                NodeCommandFailed,
                resource='initial_contact',
                params={'enable_ssh': enable_ssh}).create()
            
            if result.content:
                if as_base64:
                    result.content = base64.encodestring(
                        result.content.encode()).decode().replace('\n', '')
                    
                if filename:
                    try:
                        save_to_file(filename, result.content)
                    except IOError as e:
                        raise NodeCommandFailed(
                            'Error occurred when attempting to save initial '
                            'contact to file: {}'.format(e))

            return result.content
        except ResourceNotFound as e:
            raise NodeCommandFailed(e)

    @property
    def appliance_status(self):
        """
        Gets the appliance status for the specified node for the specific
        supported engine

        :return: status information for this appliance
        :rtype: list
        """
        result = self.read_cmd(
            NodeCommandFailed,
            resource='appliance_status')
    
        return ApplianceStatus(result)

    def appliance_info(self):
        """
        .. versionadded:: 0.5.7
            Requires SMC version >= 6.3
        
        Retrieve appliance info for this engine.
        
        :return: :py:class:`~ApplianceInfo`
        :raises NodeCommandFailed: Appliance info not supported on
            this node
        """
        if 'appliance_info' in self.data:
            return ApplianceInfo(self.data['appliance_info'])
        raise NodeCommandFailed(
            'Appliance information is not available on this engine')
        
    def status(self):
        """
        Basic status for individual node. Specific information such as node
        name dynamic package version, configuration status, platform and
        version.

        :return: :py:class:`~NodeStatus`
        """
        result = self.read_cmd(
            NodeCommandFailed,
            resource='status')
    
        return NodeStatus(**result)

    def go_online(self, comment=None):
        """
        Executes a Go-Online operation on the specified node
        typically done when the node has already been forced offline
        via :func:`go_offline`

        :param str comment: (optional) comment to audit
        :raises NodeCommandFailed: online not available
        :return: None
        """
        self.upd_cmd(
            NodeCommandFailed,
            resource='go_online',
            params={'comment': comment})

    def go_offline(self, comment=None):
        """
        Executes a Go-Offline operation on the specified node

        :param str comment: optional comment to audit
        :raises NodeCommandFailed: offline not available
        :return: None
        """
        self.upd_cmd(
            NodeCommandFailed,
            resource='go_offline',
            params={'comment': comment})

    def go_standby(self, comment=None):
        """
        Executes a Go-Standby operation on the specified node.
        To get the status of the current node/s, run :func:`status`

        :param str comment: optional comment to audit
        :raises NodeCommandFailed: engine cannot go standby
        :return: None
        """
        self.upd_cmd(
            NodeCommandFailed,
            resource='go_standby',
            params={'comment': comment})

    def lock_online(self, comment=None):
        """
        Executes a Lock-Online operation on the specified node

        :param str comment: comment for audit
        :raises NodeCommandFailed: cannot lock online
        :return: None
        """
        self.upd_cmd(
            NodeCommandFailed,
            resource='lock_online',
            params={'comment': comment})

    def lock_offline(self, comment=None):
        """
        Executes a Lock-Offline operation on the specified node
        Bring back online by running :func:`go_online`.

        :param str comment: comment for audit
        :raises NodeCommandFailed: lock offline failed
        :return: None
        """
        self.upd_cmd(
            NodeCommandFailed,
            resource='lock_offline',
            params={'comment': comment})

    def reset_user_db(self, comment=None):
        """
        Executes a Send Reset LDAP User DB Request operation on this
        node.

        :param str comment: comment to audit
        :raises NodeCommandFailed: failure resetting db
        :return: None
        """
        try:
            self.upd_cmd(
                NodeCommandFailed,
                resource='reset_user_db',
                params={'comment': comment})

        except ResourceNotFound as e:
            raise NodeCommandFailed(e)

    def diagnostic(self, filter_enabled=False):
        """
        Provide a list of diagnostic options to enable

        Get all diagnostic/debug settings::

            >>> for node in engine.nodes:
            ...   node.diagnostic()
            ... 
            [Diagnostic('name=SNMP Monitoring,enabled=False'),
            Diagnostic('name=State synchronisation,enabled=False')]
            ...
            ...

        Add filter_enabled=True argument to see only enabled settings

        :param bool filter_enabled: returns all enabled diagnostics
        :raises NodeCommandFailed: failure getting diagnostics
        :return: list of dict items with diagnostic info; key 'diagnostics'
        """
        params = {'filter_enabled': filter_enabled}
        try:
            result = self.read_cmd(
                NodeCommandFailed,
                resource='diagnostic',
                params=params)

            return [(Diagnostic(**diagnostic))
                    for diagnostic in result.get('diagnostics')]
        except ResourceNotFound as e:
            raise NodeCommandFailed(e)

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
        :raises NodeCommandFailed: error sending diagnostics
        :return: None
        """
        debug = []
        for setting in diagnostic:
            debug.append(vars(setting))
        
        self.send_cmd(
            NodeCommandFailed,
            resource='send_diagnostic',
            json={'diagnostics': debug})
        
    def reboot(self, comment=None):
        """
        Send reboot command to this node.

        :param str comment: comment to audit
        :raises NodeCommandFailed: reboot failed with reason
        :return: None
        """
        self.upd_cmd(
            NodeCommandFailed,
            resource='reboot',
            params={'comment': comment})

    def power_off(self):
        """
        .. versionadded:: 0.5.6
            Requires engine version >=6.3
        
        Power off engine.
         
        :raises NodeCommandFailed: online not available
        :return: None
        """
        try:
            self.upd_cmd(
                NodeCommandFailed,
                resource='power_off')
            
        except ResourceNotFound as e:
            raise NodeCommandFailed(e)
    
    def reset_to_factory(self):
        """
        .. versionadded:: 0.5.6
            Requires engine version >=6.3
        
        Reset the engine to factory defaults.
        
        :raises NodeCommandFailed: online not available
        :return: None
        """
        try:
            self.upd_cmd(
                NodeCommandFailed,
                resource='reset_to_factory')
            
        except ResourceNotFound as e:
            raise NodeCommandFailed(e)

    def sginfo(self, include_core_files=False,
               include_slapcat_output=False,
               filename='sginfo.gz'):
        """
        Get the SG Info of the specified node. Optionally provide
        a filename, otherwise default to 'sginfo.gz'. Once you run
        gzip -d <filename>, the inner contents will be in .tar format.

        :param include_core_files: flag to include or not core files
        :param include_slapcat_output: flag to include or not slapcat output
        :raises NodeCommandFailed: failed getting sginfo with reason
        :return: string path of download location
        :rtype: str
        """
        params = {
            'include_core_files': include_core_files,
            'include_slapcat_output': include_slapcat_output}
        
        result = self._request(
            NodeCommandFailed,
            resource='sginfo',
            filename=filename,
            params=params).read()
        
        return result.content

    def ssh(self, enable=True, comment=None):
        """
        Enable or disable SSH

        :param bool enable: enable or disable SSH daemon
        :param str comment: optional comment for audit
        :raises NodeCommandFailed: cannot enable SSH daemon
        :return: None
        """
        try:
            self.upd_cmd(
                NodeCommandFailed,
                resource='ssh',
                params={
                    'enable': enable,
                    'comment': comment})

        except ResourceNotFound as e:
            raise NodeCommandFailed(e)

    def change_ssh_pwd(self, pwd=None, comment=None):
        """
        Executes a change SSH password operation on the specified node

        :param str pwd: changed password value
        :param str comment: optional comment for audit log
        :raises NodeCommandFailed: cannot change ssh password
        :return: None
        """
        try:
            self.upd_cmd(
                NodeCommandFailed,
                resource='change_ssh_pwd',
                params={'comment': comment},
                json={'value': pwd})
            
        except ResourceNotFound as e:
            raise NodeCommandFailed(e)

    def time_sync(self):
        """
        Send a time sync command to this node.

        :raises NodeCommandFailed: time sync not supported on node
        :return: None
        """
        try:
            self.upd_cmd(
                NodeCommandFailed,
                resource='time_sync')

        except ResourceNotFound as e:
            raise NodeCommandFailed(e)

    def certificate_info(self):
        """
        Get the certificate info of this node. This can return None if the
        engine type does not directly have a certificate, like a virtual engine
        where the master engine manages certificates.

        :return: dict with links to cert info
        """
        return self.read_cmd(resource='certificate_info')


class ApplianceInfo(object):
    """
    Appliance specific information about the given engine node.
    Appliance info is specific to the engine itself and will provide additional
    details about the hardware model, applied license features, if the engine
    has made initial contact and when initial policy upload was made.
    """
    def __init__(self, info=None):
        self.cloud_id = None
        self.cloud_type = None
        self.first_upload_time = None #: When policy was first uploaded
        self.hardware_version = None #: Hardware version of appliance
        self.initial_contact_time = None #: When first contact with SMC was made, in milliseconds
        self.intial_license_remaining_days = None #: License expiry in days
        self.product_name = None #: Appliance model
        self.proof_of_serial = None #: Proof of serial uniquely identifying this engine
        self.software_features = None #: Features of applied license
        self.software_version = None #: Software version
        
        if info:
            for name, value in info.items():
                setattr(self, name, value)
                

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

        for k, v in kwargs.items():
            setattr(self, k, v)

    def __getattr__(self, value):
        return None


class ApplianceStatus(object):
    """
    Appliance status provides information on hardware and
    interface data for the engine node. Call this on the
    engine node to retrieve statuses::

        engine = Engine('sg_vm')
        for x in engine.nodes:
            for status in x.appliance_status.hardware:
                print(status, status.items)
            for status in x.appliance_status.interface:
                print(status, status.items)
    """

    def __init__(self, data):
        self._data = data

    @property
    def hardware(self):
        """
        Hardware status for the engine
        ::
        
            >>> for node in engine.nodes:
            ...    for x in node.appliance_status.hardware:
            ...        print(x)
            HardwareStatus(name=Anti-Malware)
            HardwareStatus(name=File Systems)
            HardwareStatus(name=GTI Cloud)
            HardwareStatus(name=Sandbox)
            HardwareStatus(name=MLC Connection)
            
        :return: iterator :py:class:`smc.core.node.HardwareStatus`
        """
        return HardwareStatus(self._data.get('hardware_statuses'))

    @property
    def interface(self):
        """
        Interface status for the engine
        ::
        
            >>> for node in engine.nodes:
            ...    for x in node.appliance_status.interface:
            ...        print(x)
            InterfaceStatus(interface=0,name=eth0_0,status=Up)
            InterfaceStatus(interface=1,name=eth0_1,status=Up)
            InterfaceStatus(interface=2,name=eth0_2,status=Up)
            InterfaceStatus(interface=3,name=eth0_3,status=Down)

        :return: iterator :py:class:`smc.core.node.InterfaceStatus`
        """
        return InterfaceStatus(self._data.get('interface_statuses'))


class HardwareStatus(object):
    """
    Represents the hardware status of the engine.
    """

    def __init__(self, data):
        self._data = data

    def __iter__(self):
        for states in self._data['hardware_statuses']:
            yield HardwareStatus(states)

    @property
    def name(self):
        return self._data.get('name')

    @property
    def items(self):
        """
        Items returns a namedtuple with label, param and value.
        Label is the key target, i.e. 'Root' in the case of file system.
        Param is the measured element, i.e. 'Partition Size'
        Value is the value of this combination.

        :return: All status for given hardware selection
        :rtype: list namedtuple('label param value')
        """
        totals = []
        for item in self._data.get('items'):
            t = namedtuple('Status', 'label param value')
            for status in item.get('statuses'):
                totals.append(t(status.get('label'),
                                status.get('param'),
                                status.get('value')))
        return totals

    def __str__(self):
        return '{0}(name={1})'.format(self.__class__.__name__, self.name)

    def __repr__(self):
        return str(self)


class InterfaceStatus(object):
    """
    Interface status represents characteristics of
    interfaces on the appliance. These states are merely
    a view to the existing state
    """

    def __init__(self, data):
        self._data = data

    def __iter__(self):
        for states in self._data['interface_status']:
            yield InterfaceStatus(states)

    @property
    def name(self):
        return self._data.get('name')

    @property
    def items(self):
        """
        Interface items are returned as a named tuple and include
        interface id, name, status, link speed, mtu, interface media
        type and how the interface is used (i.e. Normal, Aggregate)

        :return: interface statuses as read-only namedtuple
        :rtype: namedtuple('interface_id name status speed_duplex mtu port capability')
        """
        t = namedtuple(
            'Status',
            'interface_id name status speed mtu port type')
        return t(self._data.get('interface_id'),
                 self._data.get('name'),
                 self._data.get('status'),
                 self._data.get('speed_duplex'),
                 self._data.get('mtu'),
                 self._data.get('port'),
                 self._data.get('capability'))

    def __str__(self):
        return '{0}(interface={1},name={2},status={3})'\
            .format(self.__class__.__name__, self._data.get('interface_id'),
                    self.name, self._data.get('status'))

    def __repr__(self):
        return str(self)


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
