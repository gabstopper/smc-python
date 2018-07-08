"""
Classes for VSS Containers
"""
from smc.base.model import Element, ElementCreator, prepared_request
from smc.core.engines import MasterEngine
from smc.api.exceptions import CreateEngineFailed, CreateElementFailed
from smc.core.node import Node
from smc.base.util import element_resolver
from smc.core.engine import Engine


class VSSContainer(MasterEngine):
    typeof = 'vss_container'

    def __init__(self, name, **meta):
        super(VSSContainer, self).__init__(name, **meta)

    @classmethod
    def create(cls, name, vss_def=None):
        """
        Create a VSS Container. This maps to the Service Manager
        within NSX.

        vss_def is optional and has the following definition:

            {"isc_ovf_appliance_model": 'virtual',
             "isc_ovf_appliance_version": '',
             "isc_ip_address": '192.168.4.84', # IP of manager, i.e. OSC
             "isc_vss_id": '',
             "isc_virtual_connector_name": 'smc-python'}

        :param str name: name of container
        :param dict vss_def: dict of optional settings
        """
        vss_def = {} if vss_def is None else vss_def
        json = {
            'master_type': 'dcl2fw',
            'name': name,
            'vss_isc': vss_def
        }
        return ElementCreator(cls, json)

    @property
    def container_node(self):
        return [VSSContainerNode(**node)
                for node in self.make_request(resource='vss_container_node')]

    @property
    def default_settings(self):
        return self.make_request(resource='default_settings')

    @property
    def isc_settings(self):
        """
        ISC Settings provide top level information about the VSS
        container.

            {'isc_virtual_connector_name': 'nsx',
             'isc_ovf_appliance_version': '6.2.1.20170614095114',
             'isc_vss_id': '94', 'isc_ovf_appliance_model':
             'NGFW-CLOUD', 'isc_ip_address': '172.18.1.42'}
        """
        return self.make_request(resource='isc_settings')

    @property
    def vss_contexts(self):
        """
        Return all virtual contexts for this VSS Container.

        :return list VSSContext
        """
        return [VSSContext(**context)
                for context in self.make_request(resource='vss_contexts')]

    @property
    def security_groups(self):
        return [SecurityGroup(**group)
                for group in self.make_request(resource='security_groups')]

    def remove_security_group(self, name):
        """
        Remove a security group from container
        """
        for group in self.security_groups:
            if group.isc_name == name:
                group.delete()

    def add_security_group(self, name, isc_id):
        """
        Create a new security group.

        :param str name: NSX security group name
        :param str isc_id: NSX Security Group objectId
            i.e. (securitygroup-14)
        :raises CreateElementFailed: failed to create
        :rtype: SecurityGroup
        """
        return SecurityGroup.create(
            name=name,
            isc_id=isc_id,
            vss_container=self)

    def add_context(self, isc_name, isc_policy_id, isc_traffic_tag):
        """
        Create the VSS Context within the VSSContainer

        :param str isc_name: ISC name, possibly append policy name??
        :param str isc_policy_id: Policy ID in SMC (the 'key' attribute)
        :param str isc_traffic_tag: NSX groupId (serviceprofile-145)
        :raises CreateEngineFailed: failed to create
        :return: VSSContext
         """
        return VSSContext.create(
            isc_name=isc_name,
            isc_policy_id=isc_policy_id,
            isc_traffic_tag=isc_traffic_tag,
            vss_container=self)

    @property
    def upload_result(self):
        pass


class VSSContainerNode(Node):

    def __init__(self, **meta):
        super(VSSContainerNode, self).__init__(**meta)

    @classmethod
    def create(cls, name, vss_container, vss_node_def,
               comment=None):
        """
        Create VSS node. This is the engines dvFilter management
        interface within the NSX agent.

        vss_node_def dict has the following definition:

            {"management_ip": '1.1.1.1',
             "management_netmask": '24',
             "isc_hypervisor": "default",
             "management_gateway": '1.1.1.254',
             "contact_ip": None}

        :param str name: name of node
        :param VSSContainer vss_container: container to nest this node
        :param dict vss_node_def: node definition settings
        """
        json = {
            'name': name,
            'vss_node_isc': vss_node_def,
            'comment': comment
        }
        node = prepared_request(
            CreateEngineFailed,
            href=vss_container.get_relation('vss_container_node'),
            json=json).create().href

        return VSSContainerNode(name=json['name'], href=node)

    @property
    def isc_settings(self):
        """
        Return ISC settings for this node

        {'contact_ip': '4.4.4.6',
         'isc_hypervisor': 'default',
         'management_gateway': '2.2.2.1',
         'management_ip': '4.4.4.6',
         'management_netmask': 24}
        """
        return self.make_request(resource='isc_settings')


class VSSContext(Engine):
    typeof = 'vss_context'

    def __init__(self, name, **meta):
        super(VSSContext, self).__init__(name, **meta)

    @classmethod
    def create(cls, isc_name, isc_policy_id, isc_traffic_tag, vss_container):
        """
        Create the VSS Context within the VSSContainer

        :param str name: ISC name, possibly append policy name??
        :param str isc_policy_id: Policy ID in SMC (the 'key' attribute)
        :param str isc_traffic_tag: NSX groupId (serviceprofile-145)
        :param VSSContainer vss_container: VSS Container to get create
            context
        :raises CreateEngineFailed
        :rtype: VSSContext
         """
        container = element_resolver(vss_container)
        json = {
            'vc_isc': {
                'isc_name': isc_name,
                'isc_policy_id': isc_policy_id,
                'isc_traffic_tag': isc_traffic_tag
            }
        }

        href = prepared_request(
            CreateEngineFailed,
            href=container + '/vss_context',
            json=json).create().href
        
        # Element will be automatically named so retrieve it
        return Element.from_href(href)

    @property
    def isc_settings(self):
        """
        ISC Settings are used to provide information about the
        security policy mapping for the engine.

        :return dict of engine vc_isc attribute

        'vc_isc': {'isc_name': 'isc_VMPolicy',
                   'isc_policy_id': 17,
                   'isc_traffic_tag': 'serviceprofile-145'},
        """
        return self.make_request(resource='isc_settings')


class SecurityGroup(Element):
    """
    Security Groups used for VSSContainers

    :ivar str isc_id: NSX security group objectId
    :ivar str isc_name: name of NSX Security group
    :ivar str obsolete: is the element obsolete; i.e. container
        referencing group used in rule no longer exists
    """
    typeof = 'security_group'

    def __init__(self, name, **meta):
        super(SecurityGroup, self).__init__(name, **meta)

    @classmethod
    def create(cls, name, isc_id, vss_container):
        """
        Create a new security group.

        :param str name: name of group
        :param str isc_id: NSX Security Group objectId
        :param str isc_name: NSX Security Group name
        :param VSSContainer vss_container: VSS Container to add the
            security group to.
        :raises: CreateElementFailed
        :return SecurityGroup
        """
        json = {
            'name': name,
            'isc_name': name,
            'isc_id': isc_id
        }
        href = prepared_request(
            CreateElementFailed,
            href=vss_container.get_relation('security_groups'),
            json=json).create().href

        return Element.from_href(href)

