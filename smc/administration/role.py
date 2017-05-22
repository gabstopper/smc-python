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
    Role(name=Monitor), Role(name=Owner), Role(name=Editor), Role(name=Operator),
    Role(name=Superuser)]
    ...
    >>> Role.duplicate(name='dupviewer', role=Role('Viewer'))
    Role(name=dupviewer)

To enable or disable role permissions, use the enable/disable option after retrieving
the Role resource.

Available and current permission settings can be found by calling permissions
attribute::

    >>> role = Role('newrole')
    >>> role.permissions
    [{'alert_mgmt': False}, {'send_advanced_commands': False}, {'license_mgmt': False}, {'element_edit': False},
     {'view_edit_report': False}, {'view_system_alerts': False}, {'view_logs': False}, {'vpn_mgmt': False},
     {'log_pruning_mgmt': False}, {'updates_and_upgrades_mgmt': False}, {'auth_server_user_mgmt': False},
     {'view_audit': False}, {'element_delete': False}, {'element_create': False}, {'upload_policy': False},
     {'send_commands': False}, {'backup_mgmt': False}, {'element_view_content': True}, {'log_mgmt': False},
     {'bookmark_manage': True}, {'admin_mgmt': False}, {'name': 'newrole'}, {'overview_manage': True},
     {'internal_user_mgmt': False}, {'refresh_policy': False}]

Then enable specific roles::

    >>> role.enable(['element_create', 'upload_policy'])

Also disable specific roles::

    >>> role.disable(['element_create', 'upload_policy'])
    
"""
from smc.base.model import Element, ElementCreator
from smc.base.decorators import autocommit

class Role(Element):
    """
    Role class represents granular access control rights that can
    be applied to specific elements (Engines, Policies or Access Control
    Lists).
    """
    typeof = 'role'
    reserved = ['key',
                'link',
                'system', 
                'system_key',  
                'read_only',
                'comment']

    @classmethod
    def duplicate(cls, name, role):
        """
        Copy a role from an existing system role.
        
        :param str name: name of new role
        :param str,Role role: Role to copy
        :raises ElementNotFound: unable to locate role
        :raises CreateElementFailed: failed to create role
        :return: instance with meta
        :rtype: Role
        """
        for attr in Role.reserved:
            role.data.pop(attr, None)
        role.data['name'] = name
    
        return ElementCreator(cls, role.data)
    
    @autocommit(now=False)   
    def enable(self, values, autocommit=False):
        """
        Enable specific permissions on this role. Use :py:attr:`~permissions` to
        view valid permission settings and current value/s. Change is committed
        immediately.
        
        :param list values: list of values by allowed types
        :return: None
        """
        for value in values:
            if value in self.data:
                self.data[value] = True
    
    @autocommit(now=False)
    def disable(self, values, autocommit=False):
        """
        Disable specific permissions on this role. Use :py:attr:`~permissions` to
        view valid permission settings and current value/s. Change is committed
        immediately.
        
        :param list values: list of values by allowed types
        :return: None
        """
        for value in values:
            if value in self.data:
                self.data[value] = False
    
    @property
    def permissions(self):
        """
        Return valid permissions and setting for this role. Permissions are
        returned as a list of dict items, {permission: state}. State for the
        permission is either True or False. Use :meth:`~enable` and
        :meth:`~disable` to toggle role settings.
        
        :return: list of permission settings
        :rtype: list(dict)
        """
        permissions = []
        for permission, value in self.data.items():
            if permission not in Role.reserved:
                permissions.append({permission: value})
        return permissions
            
