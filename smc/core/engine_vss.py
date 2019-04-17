"""
Classes for VSS Containers
"""
from smc.base.model import Element, ElementCreator, ElementRef
from smc.core.engines import MasterEngine
from smc.core.node import Node
from smc.base.util import element_resolver
from smc.core.engine import Engine
from smc.administration.tasks import Task
from smc.base.collection import sub_collection
from smc.api.common import fetch_entry_point


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
        :raises CreateElementFailed: failed creating with reason
        :rtype: VSSContainer
        """
        vss_def = {} if vss_def is None else vss_def
        json = {
            'master_type': 'dcl2fw',
            'name': name,
            'vss_isc': vss_def
        }
        return ElementCreator(cls, json)

    @property
    def nodes(self):
        """
        Return the nodes for this VSS Container
        
        :rtype: SubElementCollection(VSSContainerNode)
        """
        resource = sub_collection(
            self.get_relation('vss_container_node'), 
            VSSContainerNode) 
        resource._load_from_engine(self, 'nodes') 
        return resource

    @property
    def container_node(self):
        return self.nodes

    @property
    def isc_settings(self):
        """
        ISC Settings provide top level information about the VSS
        container. For the native NSX implementation, only the
        `isc_virtual_connector_name` and `isc_vss_id` fields are
        used. The virtual_connector_name is the NSX service name
        i.e. (service-520). The isc_vss_id is the NSX service
        instance (deployment) name i.e.(serviceinstance-508).
        
            {'isc_virtual_connector_name': 'nsx',
             'isc_ovf_appliance_version': '6.2.1.20170614095114',
             'isc_vss_id': '94', 'isc_ovf_appliance_model':
             'NGFW-CLOUD', 'isc_ip_address': '172.18.1.42'}
        """
        return self.data.get('vss_isc', {})
  
    @property
    def vss_contexts(self):
        """
        Return all virtual contexts for this VSS Container.

        :return list VSSContext
        """
        result = self.make_request(
            href=fetch_entry_point('visible_virtual_engine_mapping'),
            params={'filter': self.name})
    
        if 'mapping' in result:
            return [Element.from_href(ve)
                for ve in result['mapping'][0].get('virtual_engine', [])]
        return [] # pre-6.5

    @property
    def security_groups(self):
        """
        Security Groups for this VSS container. Security Groups are added
        automatically based on assigned NSX groups in vCenter Security Policy.
        
        :rtype: list(SecurityGroup)
        """
        return [SecurityGroup(**group)
            for group in self.make_request(resource='security_groups')]

    def remove_security_group(self, name):
        """
        Remove a security group from container
        """
        for group in self.security_groups:
            if group.isc_name == name:
                group.delete()

    def add_security_group(self, name, isc_id, comment=None):
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
            vss_container=self,
            comment=comment)

    def add_context(self, isc_name, isc_policy_id, isc_traffic_tag):
        """
        Create the VSS Context within the VSSContainer

        :param str isc_name: ISC name, possibly append policy name??
        :param str isc_policy_id: Policy ID in SMC (the 'key' attribute)
        :param str isc_traffic_tag: NSX groupId (serviceprofile-145)
        :raises CreateElementFailed: failed to create
        :return: VSSContext
        """
        if 'add_context' in self.data.links: # SMC >=6.5
            element = ElementCreator(
                VSSContext,
                href=self.get_relation('add_context'),
                json = {
                    'name': isc_name,
                    'vc_isc': {
                        'isc_name': isc_name,
                        'isc_policy_id': isc_policy_id,
                        'isc_traffic_tag': isc_traffic_tag
                    }
                })
        else: # SMC < 6.5
            element = VSSContext.create(
                isc_name=isc_name,
                isc_policy_id=isc_policy_id,
                isc_traffic_tag=isc_traffic_tag,
                vss_container=self)
        
        # Delete cache since the virtualResources node is attached to
        # the engine json
        self._del_cache()
        return element

    @property
    def upload_result(self):
        pass


class VSSContainerNode(Node):
    typeof = 'vss_container_node'
    
    def __init__(self, **meta):
        super(VSSContainerNode, self).__init__(**meta)
    
    @classmethod
    def create(cls, name, vss_container, vss_node_def,
               comment=None):
        """
        Create VSS node. This is the engines dvFilter management
        interface within the NSX agent.
        
        .. seealso:: `~.isc_settings` for documentation on the
            vss_node_def dict

        :param str name: name of node
        :param VSSContainer vss_container: container to nest this node
        :param dict vss_node_def: node definition settings
        :raises CreateElementFailed: created failed with reason
        :rtype: VSSContainerNode
        """
        element = ElementCreator(cls,
            href=vss_container.get_relation('vss_container_node'),
            json={
                'name': name,
                'vss_node_isc': vss_node_def,
                'comment': comment
            })
        vss_container._del_cache() # Removes references to linked container
        return element

    @property
    def isc_settings(self):
        """
        Return ISC settings for this node. These are set during the
        create process.
        
            {'contact_ip': '4.4.4.6',
             'isc_hypervisor': 'default',
             'management_gateway': '2.2.2.1',
             'management_ip': '4.4.4.6',
             'management_netmask': 24}
        
        :param str contact_ip: ip address for this node used as management
        :param str isc_hypervisor: unused
        :param str management_gateway: gateway as set by the NSX agent
        :param str management_ip: management IP
        :param str management_netmask: CIDR netmask for management IP
        :rtype: dict
        """
        return self.data.get('vss_node_isc')
        

class VSSContext(Engine):
    typeof = 'vss_context'
    virtual_resource = ElementRef('virtual_resource')
    
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
        :raises CreateElementFailed
        :rtype: VSSContext
         """
        container = element_resolver(vss_container)
        return ElementCreator(cls,
            href=container + '/vss_context',
            json = {
                'vc_isc': {
                    'isc_name': isc_name,
                    'isc_policy_id': isc_policy_id,
                    'isc_traffic_tag': isc_traffic_tag
                }
            })
    
    def remove_from_master_node(self, wait_for_finish=False, timeout=20, **kw):
        """
        Remove this VSS Context from it's parent VSS Container.
        This is required before calling VSSContext.delete(). It preps
        the engine for removal.
        
        :param bool wait_for_finish: wait for the task to finish
        :param int timeout: how long to wait if delay
        :type: TaskOperationPoller
        """
        return Task.execute(self, 'remove_from_master_node',
            timeout=timeout, wait_for_finish=wait_for_finish, **kw)
    
    def move_to_master_node(self, master):
        pass
    
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
        return self.data.get('vc_isc')


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
    def create(cls, name, isc_id, vss_container, comment=None):
        """
        Create a new security group.
        
        Find a security group::
        
            SecurityGroup.objects.filter(name)
        
        .. note:: The isc_id (securitygroup-10, etc) represents the
            internal NSX reference for the Security Composer group.
            This is placed in the comment field which makes it
            a searchable field using search collections

        :param str name: name of group
        :param str isc_id: NSX Security Group objectId
        :param str isc_name: NSX Security Group name
        :param VSSContainer vss_container: VSS Container to add the
            security group to.
        :param str comment: comment, making this searchable
        :raises: CreateElementFailed
        :return SecurityGroup
        """
        return ElementCreator(cls,
            href=vss_container.get_relation('security_groups'),
            json = {
                'name': name,
                'isc_name': name,
                'isc_id': isc_id,
                'comment': comment or isc_id
            })
