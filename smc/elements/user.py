"""
User module to hold accounts related to users (admin or local) in the SMC

You can create an Admin User, enable superuser, enable/disable the account,
assign local access to engines, and change the account password for SMC or
engine access.

It is possible to fully provision an Admin User with specific permissions and
roles and initial password.

Create the admin::
    
    admin = AdminUser.create(name='auditor', superuser=False)

.. note:: If the Admin User should have unrestricted access, set ``superuser=True`` and
    skip the below sections related to adding permissions and roles.
    
Permissions relate to elements that the user will have access to (Policies, Engines or
AccessControlLists) and the domain where the privileges apply (default is 'Shared Domain').

Create a permission using the default domain of Shared, granting access to a specific
engine and firewall policy::

    permission = Permission.create(
        granted_elements=[Engine('vm'), FirewallPolicy('VM Policy')], 
        role=Role('Viewer'))

Create a second permission granting access to all firewalls in the domain 'mydomain'::

    domain_perm = Permission.create(
        granted_elements=[AccessControlList('ALL Firewalls')],
        role=Role('Owner'),
        domain=AdminDomain('mydomain'))

Add the permissions to the Admin User::

    admin.add_permission([permission, domain_perm])

Set an initial password for the Admin User::

    admin.change_password('Newpassword1')

.. note:: Roles are used to define what granular controls will be available to the assigned
    user, such as read/read write/all. AccessControlLists encapsulate elements into a single
    container for re-use.
    
.. seealso:: :class:`smc.administration.role.Role` and 
    :class:`smc.administration.access_rights.AccessControlList` for more information.

"""
from smc.base.model import Element, ElementCreator, prepared_request
from smc.api.exceptions import ModificationFailed
from smc.administration.access_rights import Permission


class UserMixin(object):
    """
    User Mixin class providing common operations for Admin Users and 
    API Clients.
    """
    def enable_disable(self):
        """
        Toggle enable and disable of administrator account.
        Change is committed immediately.

        :raises UpdateElementFailed: failed with reason
        :return: None
        """
        self.update(href=self.data.get_link('enable_disable'))

    def change_password(self, password):
        """
        Change user password. Change is committed immediately.

        :param str password: new password
        :return: None
        """
        prepared_request(
            ModificationFailed,
            href=self.data.get_link('change_password'),
            params={'password': password}
        ).update()

    def add_permission(self, permission):
        """
        Add a permission to this Admin User. A role defines permissions that
        can be enabled or disabled. Elements define the target for permission
        operations and can be either Access Control Lists, Engines or Policy
        elements. Domain specifies where the access is granted. The Shared
        Domain is default unless specific domain provided. Change is committed
        at end of method call.
        
        :param permission: permission/s to add to admin user
        :type permission: list(Permission)
        :raises UpdateElementFailed: failed updating admin user
        :return: None
        """
        if 'permissions' not in self.data:
            self.data['superuser'] = False
            self.data['permissions'] = {'permission':[]}
        
        for p in permission:
            self.data['permissions']['permission'].append(p._as_dict())
        self.update()
        
    @property
    def permissions(self):
        """
        Return each permission role mapping for this Admin User. A permission
        role will have 3 fields:
        
        * Domain
        * Role (Viewer, Operator, etc)
        * Elements (Engines, Policies, or ACLs)
        
        :return: permissions as list
        :rtype: list(Permission)
        """
        if 'permissions' in self.data:
            _permissions = self.data['permissions']['permission']
            return [Permission(**perm) for perm in _permissions]
        return []
               
   
class AdminUser(UserMixin, Element):
    """ Represents an Adminitrator account on the SMC
    Use the constructor to create the user.

    Create an Admin::

        >>> AdminUser.create(name='dlepage', superuser=True)
        AdminUser(name=dlepage)

    If modifications are required after you can access the admin and
    make changes::

        admin = AdminUser('dlepage')
        admin.change_password('mynewpassword1')
        admin.enable_disable()
        
    Attributes available:
    
    :ivar bool allow_sudo: is this account allowed to sudo on an engine.
    :ivar bool local_admin: is the admin a local admin
    :ivar bool superuser: is this account a superuser for SMC
    """
    typeof = 'admin_user'

    def __init__(self, name, **meta):
        super(AdminUser, self).__init__(name, **meta)
        pass

    @classmethod
    def create(cls, name, local_admin=False, allow_sudo=False,
               superuser=False, enabled=True, engine_target=None,
               comment=None):
        """
        Create an admin user account.

        :param str name: name of account
        :param bool local_admin: is a local admin only
        :param bool allow_sudo: allow sudo on engines
        :param bool superuser: is a super administrator
        :param bool enabled: is account enabled
        :param str engine_target: engine to allow remote access to
        :raises CreateElementFailed: failure creating element with reason
        :return: instance with meta
        :rtype: AdminUser
        """
        engines = [] if engine_target is None else engine_target
    
        json = {'name': name,
                'enabled': enabled,
                'allow_sudo': allow_sudo,
                'engine_target': engines,
                'local_admin': local_admin,
                'superuser': superuser,
                'comment': comment}
        
        return ElementCreator(cls, json)
        
    @property
    def enabled(self):
        """
        Read only enabled status
        
        :rtype: bool
        """
        return self.data.get('enabled')

    def change_engine_password(self, password):
        """ Change Engine password for engines on allowed
        list.

        :param str password: password for engine level
        :raises ModificationFailed: failed setting password on engine
        :return: None
        """
        prepared_request(
            ModificationFailed,
            href=self.data.get_link('change_engine_password'),
            params={'password': password}
        ).update()


class ApiClient(UserMixin, Element):
    """
    Represents an API Client
    """
    typeof = 'api_client'

    def __init__(self, name, **meta):
        super(ApiClient, self).__init__(name, **meta)
        pass

    @classmethod
    def create(cls, name, enabled=True, superuser=True):
        """
        Create a new API Client. Once client is created,
        you can create a new password by::

            >>> client = ApiClient.create('myclient')
            >>> print(client)
            ApiClient(name=myclient)
            >>> client.change_password('mynewpassword')

        :param str name: name of client
        :param bool enabled: enable client
        :param bool superuser: is superuser account
        :raises CreateElementFailed: failure creating element with reason
        :return: instance with meta
        :rtype: ApiClient
        """
        json = {'enabled': enabled,
                'name': name,
                'superuser': superuser}

        return ElementCreator(cls, json)

    '''    
    def one_time_password(self, password):
        """
        Generate a one-time password for a single session. As the
        method implies, the password will be expired after single use.
        Use :func:`change_password` if you want a multi-use password.
        
        :param str password: one-time password value
        :raises: :py:class:`smc.api.exceptions.ModificationFailed`
        :return: None
        """
        prepared_request(ModificationFailed,
                         href=self._resource.change_password,
                         params={'one_time_password': password},
                         etag=self.etag,
                         ).update()
    '''
