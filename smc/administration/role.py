"""
Administrator Role elements specify a restricted set of permissions that
include the right to create, edit, and delete elements.

Each administrator can have several different Administrator Roles applied to
different sets of elements. There are some default Administrator Roles, but if
you want to customize the permissions in any way, you must create custom
Administrator Role elements.

A role has many attributes (mostly boolean) that can be enabled, therefore the
simplest way to create a new role is to duplicate an existing role.
::

    >>> from smc.administration.role import Role
    >>> list(Role.objects.all())
    [Role(name=Reports Manager), Role(name=Reporter), Role(name=Viewer), Role(name=Logs Viewer),
    Role(name=Monitor), Role(name=Owner), Role(name=Editor), Role(name=Operator), Role(name=Superuser)]
    ...
    >>> Role.duplicate(name='newrole', role=Role('Viewer'))
    'http://172.18.1.150:8082/6.2/elements/role/10'
    
"""
from smc.base.model import Element, ElementCreator

class Role(Element):
    typeof = 'role'
    
    @classmethod
    def duplicate(cls, name, role):
        """
        Copy a role from an existing system role.
        
        :param str name: name of new role
        :param str,Role role: Role to copy
        :raises ElementNotFound: unable to locate role
        :raises CreateElementFailed: failed to create role
        :return: href of new role
        :rtype: str
        """
        for attr in ['key',
                     'link',
                     'system', 
                     'system_key',  
                     'read_only']:
            role.data.pop(attr, None)
        role.data['name'] = name
    
        return ElementCreator(cls, role.data)
        
    
'''
{u'admin_mgmt': False,
 u'alert_mgmt': False,
 u'auth_server_user_mgmt': False,
 u'backup_mgmt': False,
 u'bookmark_manage': False,
 u'comment': u'Monitor Administrator Role',
 u'element_create': False,
 u'element_delete': False,
 u'element_edit': False,
 u'element_view_content': False,
 u'internal_user_mgmt': False,
 u'key': 4,
 u'license_mgmt': False,
 u'link': [{u'href': u'http://172.18.1.151:8082/6.2/elements/role/4',
            u'rel': u'self',
            u'type': u'role'}],
 u'log_mgmt': False,
 u'log_pruning_mgmt': False,
 u'name': u'Monitor',
 u'overview_manage': False,
 u'read_only': True,
 u'refresh_policy': False,
 u'send_advanced_commands': False,
 u'send_commands': False,
 u'system': True,
 u'system_key': 4,
 u'updates_and_upgrades_mgmt': False,
 u'upload_policy': False,
 u'view_audit': False,
 u'view_edit_report': False,
 u'view_logs': False,
 u'view_system_alerts': False,
 u'vpn_mgmt': False}
 '''
    