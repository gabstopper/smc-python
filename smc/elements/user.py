"""
User module to hold accounts related to users (admin or local) in the SMC

You can create an Admin User, enable superuser, enable/disable the account,
assign local access to engines, and change the account password for SMC or
engine access.

"""
from smc.base.model import Element, ElementCreator, prepared_request
from smc.base.decorators import autocommit
from smc.api.exceptions import ModificationFailed
from smc.elements.other import AdminDomain
from smc.base.util import element_resolver


class UserMixin(object):
    def enable_disable(self):
        """
        Toggle enable and disable of administrator account

        :raises: :py:class: `smc.api.exceptions.ModificationFailed`
        :return: None
        """
        self.update(href=self.resource.enable_disable)

    def change_password(self, password):
        """
        Change user password

        :param str password: new password
        :return: None
        """
        prepared_request(
            ModificationFailed,
            href=self.resource.change_password,
            params={'password': password}
        ).update()

    @autocommit
    def add_permission(self, role, elements, domain='Shared Domain',
                       autocommit=True):
        """
        Add a permission to this Admin User. A role defines permissions that
        can be enabled or disabled. Elements define the target for permission
        operations and can be either Access Control Lists, Engines or Policy
        elements. Domain specifies where the access is granted. The Shared
        Domain is default unless specific domain provided.
        
        :param str,Role role: Role reference within SMC
        :param list elements: elements to grant permissions to (policy,
            engines, or access control list).
        :param str,AdminDomain domain: domain to grant access (default:
            Shared Domain)
        :param bool autocommit: autocommit save after calling this function.
            (default: True)
        :raises UpdateElementFailed: failed updating admin user
        :return: None
        """
        domain = AdminDomain(domain).href
        role = element_resolver(role)
        elements = element_resolver(elements)
        
        if 'permissions' not in self.data:
            self.data['superuser'] = False
    
        permission = self.data.get(
            'permissions', {'permission': []})
        permission['permission'].append({
            'granted_domain_ref': domain,
            'granted_elements': elements,
            'role_ref': role})
        self.data['permissions'] = permission                  

    
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
               superuser=False, enabled=True, engine_target=None):
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
                'superuser': superuser}
        
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
            href=self.resource.change_engine_password,
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
                         href=self.resource.change_password,
                         params={'one_time_password': password},
                         etag=self.etag,
                         ).update()
    '''
