"""
User module to hold accounts related to users (admin or local) in the SMC

You can create an Admin User, enable superuser, enable/disable the account,
assign local access to engines, and change the account password for SMC or
engine access.
"""
from smc.base.model import Element, ElementCreator, prepared_request
from smc.api.exceptions import ModificationFailed

class UserCommon(object):
    def enable_disable(self):
        """ Toggle enable and disable of administrator account
        
        :raises: :py:class: `smc.api.exceptions.ModificationFailed`
        :return: None
        """
        prepared_request(ModificationFailed,
                         href=self._link('enable_disable')).update()

    def change_password(self, password):
        """ Change user password

        :param str password: new password
        :return: :py:class:`smc.api.web.SMCResult`
        """
        prepared_request(ModificationFailed,
                         href=self._link('change_password'), 
                         params={'password': password}).update()
                                

class AdminUser(UserCommon, Element):
    """ Represents an Adminitrator account on the SMC
    Use the constructor to create the user.

    :param name: name of admin
    :param boolean local_admin: should be local admin on specified engines
    :param boolean allow_sudo: allow sudo on specified engines
    :param boolean superuser: is a super user (no restrictions) in SMC
    :param admin_domain: reference to admin domain, shared by default
    :param list engine_target: ref to engines for local admin access

    Create an Admin::

        admin = AdminUser.create(name='dlepage', superuser=True)

    If modifications are required after you can access the admin and
    make changes::

        admin = AdminUser('dlepage')
        admin.change_password('mynewpassword1')
        admin.enable_disable()
    """
    typeof = 'admin_user'

    def __init__(self, name, meta=None):
        super(AdminUser, self).__init__(name, meta)
        pass

    @classmethod
    def create(cls, name, local_admin=False, allow_sudo=False,
               superuser=False, admin_domain=None, enabled=True,
               engine_target=None):
        engines = [] if engine_target is None else engine_target
        cls.json = {'name': name,
                    'enabled': enabled,
                    'allow_sudo': allow_sudo,
                    'engine_target': engines,
                    'local_admin': local_admin,
                    'superuser': superuser}
        
        return ElementCreator(cls)

    def change_engine_password(self, password):
        """ Change Engine password for engines on allowed
        list.

        :param str password: password for engine level
        :raises: :py:class: `smc.api.exceptions.ModificationFailed`
        :return: None
        """
        prepared_request(ModificationFailed,
                         href=self._link('change_engine_password'), 
                         params={'password': password}).update()

class ApiClient(UserCommon, Element):
    """
    Represents an API Client
    """
    typeof = 'api_client'

    def __init__(self, name, meta=None):
        super(ApiClient, self).__init__(name, meta)
        pass
    