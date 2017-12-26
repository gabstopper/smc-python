"""
Administrator Role elements specify a restricted set of permissions that
include the right to create, edit, and delete elements.

Each administrator can have several different Administrator Roles applied to
different sets of elements. There are some default Administrator Roles, but if
you want to customize the permissions in any way, you must create custom
Administrator Role elements.

Create a new role is done by using the create classmethod. By default the role
will not have any permissions set::

    >>> from smc.administration.role import Role
    >>> role = Role.create(name='mynewrole')

A role has many attributes (mostly boolean) that can be enabled, therefore the
simplest way to create a new role is to duplicate an existing role.
::

    >>> list(Role.objects.all())
    [Role(name=myeditor), Role(name=Logs Viewer), Role(name=Reports Manager), Role(name=Owner),
     Role(name=Viewer), Role(name=Operator), Role(name=Monitor), Role(name=Editor),
     Role(name=Superuser)]
    ...

Duplicate an existing role to simplify making modifications on permissions::

    >>> role = Role('Editor')
    >>> role.duplicate('customeditor')
    Role(name=customeditor)

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

Then enable specific roles by specifying the keys to enable::

    >>> role.enable(['element_create', 'upload_policy'])

Also disable specific roles::

    >>> role.disable(['element_create', 'upload_policy'])
    
Once modification is complete, call update on the role::

    >>> role.update()
    'http://172.18.1.151:8082/6.4/elements/role/10'
    
"""
from smc.base.model import Element, ElementCreator


class Role(Element):
    """
    Role class represents granular access control rights that can
    be applied to specific elements (Engines, Policies or Access Control
    Lists).
    """
    typeof = 'role'
    _reserved = ('comment', 'key', 'link', 'name', 'read_only', 'system')
 
    @classmethod
    def create(cls, name, comment=None):
        """
        Create a new role. The role will not have any permissions by default
        so it will be required to call enable on the role after creation.
        
        :param str name: name of role
        :param str comment: comment for role
        :raises CreateElementFailed: failed to create role
        :rtype: Role
        """
        json = {'name': name, 'comment': comment}
        return ElementCreator(cls, json)
    
    def enable(self, values):
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
    
    def disable(self, values):
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
            if permission not in self._reserved:
                permissions.append({permission: value})
        return permissions
            
