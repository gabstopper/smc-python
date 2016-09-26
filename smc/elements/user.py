"""
User module to hold accounts related to users (admin or local) in the SMC

You can create an Admin User, enable superuser, enable/disable the account,  
assign local access to engines, and change the account password for SMC or
engine access.
"""
import smc.api.common as common_api
import smc.actions.search as search
from smc.elements.util import find_link_by_name
from smc.api.exceptions import ElementNotFound, TaskRunFailed
from smc.elements.element import SMCElement, Meta
from smc.actions.tasks import task_handler, Task


class AdminUser(SMCElement):
    """ Represents an Adminitrator account on the SMC
    Use the constructor to create the user. 
    
    :param name: name of admin
    :param boolean local_admin: should be local admin on specified engines
    :param boolean allow_sudo: allow sudo on specified engines
    :param boolean superuser: is a super user (no restrictions) in SMC
    :param admin_domain: reference to admin domain, shared by default
    :param list engine_target: ref to engines for local admin access
    
    Create an Admin::
        
        admin = AdminUser(name='dlepage', superuser=True).create()
        
    If modifications are required after you can load the admin and
    make changes::
    
        for x in collection.describe_admin_users():
            if x.name == 'dlepage':
                admin = x.load()
                admin.change_password('mynewpassword1')
                admin.enable_disable()
    """
    typeof = 'admin_user'
    
    def __init__(self, name, local_admin=False, allow_sudo=False, 
                 superuser=False, admin_domain=None, enabled=True,
                 engine_target=None, href=None, meta=None, **kwargs):
        SMCElement.__init__(self)
        self.name = name
        self.meta = meta
        engines = []
        if engine_target:
            engines.extend(engine_target)
        self.json = {'name': name,
                     'enabled': enabled,
                     'allow_sudo': allow_sudo,
                     'engine_target': engines,
                     'local_admin': local_admin,
                     'superuser': superuser }
    
    def load(self):
        """
        Load Admin by name
        """
        if not self.meta:
            result = search.element_info_as_json_with_filter(self.name, self.typeof)
            if result:
                self.meta = Meta(**result)
            else:
                raise ElementNotFound("Admin name: {} is not found, cannot modify."
                                      .format(self.name))
        result = search.element_by_href_as_smcresult(self.meta.href)
        self.json = result.json
        return self
 
    @property
    def link(self):
        return self.json.get('link')

    def change_password(self, password):
        """ Change admin password 
        
        :method: PUT
        :param str password: new password
        :return: SMCResult
        """
        self.href = find_link_by_name('change_password', self.link)
        self.params = {'password': password}
        return self.update()
           
    def change_engine_password(self, password):
        """ Change Engine password for engines on allowed
        list.
        
        :method: PUT
        :param str password: password for engine level
        :return: SMCResult
        """
        self.href = find_link_by_name('change_engine_password', self.link)
        self.params = {'password': password}
        pass
    
    def enable_disable(self):
        """ Toggle enable and disable of administrator account
        
        :method: PUT
        :return: SMCResult
        """
        self.href = find_link_by_name('enable_disable', self.link)
        return self.update()
        
    def export(self, filename='admin.zip', wait_for_finish=False):
        """ Export the contents of this admin
        
        :method: POST
        :param str filename: Name of file to export to
        :return: SMCResult
        :raises: :py:class:`smc.api.exceptions.TaskRunFailed`
        """
        self.href = find_link_by_name('export', self.link)
        self.params = {}
        element = self.create()
       
        task = task_handler(Task(**element.json), 
                            wait_for_finish=wait_for_finish,
                            filename=filename)
        return task

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, "name={}".format(self.name)) 
    