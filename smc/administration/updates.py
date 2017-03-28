"""
Functionality related to updating dynamic update packages and 
engine upgrades
"""
from .tasks import Task, task_handler
from smc.base.model import prepared_request, SubElement
from smc.api.exceptions import ResourceNotFound, ActionCommandFailed

class PackageMixin(object):
    """
    Manages downloads and activations of update packages and software
    upgrades
    """
    def download(self, wait_for_finish=False, sleep=3):
        """
        Download Package or Engine Update
        
        :method: POST
        :param boolean wait_for_finish: wait for download to complete
        :param int sleep: number of seconds to sleep if wait_for_finish=True
        :raises: :py:class:`smc.api.exceptions.ActionCommandFailed` with reason
        :raises: :py:class:`smc.api.exceptions.TaskRunFailed`
        :return: Generator messages or final href of follower resource
        """ 
        try:
            result = prepared_request(ActionCommandFailed,
                                      href=self.resource.download).create()
                    
            return task_handler(Task(**result.json), 
                                wait_for_finish=wait_for_finish, 
                                sleep=sleep)
        except ResourceNotFound:
            raise ActionCommandFailed('Package cannot be downloaded, package state: {}'
                                      .format(self.state))
        
    def activate(self, resource=None, wait_for_finish=False, sleep=3):
        """
        Activate this package on the SMC
        
        :param list resource: node href's to activate on. Resource is only 
               required for software upgrades
        :param boolean wait_for_finish: True|False, whether to wait 
               for update messages
        :param int sleep: number of seconds to sleep if wait_for_finish=True
        :raises: :py:class:`smc.api.exceptions.ActionCommandFailed` with reason
        :raises: :py:class:`smc.api.exceptions.TaskRunFailed`
        :return: generator Task generator with updates
        """
        try:
            result = prepared_request(ActionCommandFailed,
                                      href=self.resource.activate,
                                      json={'resource': resource}
                                      ).create()
            
            return task_handler(Task(**result.json), 
                                wait_for_finish=wait_for_finish, 
                                sleep=sleep)
        except ResourceNotFound:
            raise ActionCommandFailed('Activation failed, resource is not available')
    
    @property
    def release_notes(self):
        """
        HTTP location of the release notes
        """
        return self.data.get('release_notes')
    
class EngineUpgrade(PackageMixin, SubElement):
    """
    Engine Upgrade package management
    
    For example, to check engine upgrades and find a specific
    one, then download for installation::
    
        for upgrade in system.engine_upgrade():
            print "Available upgrade: {}".format(upgrade)
            if upgrade.name == 
                'Security Engine upgrade 6.0.1 build 16019 for x86-64':
                for msg in upgrade.download():
                    print msg
    """            
    def __init__(self, **meta):
        super(EngineUpgrade, self).__init__(**meta)
        pass

    @property
    def release_date(self):
        """
        Release date for this engine upgrade
        """
        return self.data.get('release_date')
    
    @property
    def version(self):
        """
        Engine upgrade version
        """
        return self.data.get('version')
    
    @property
    def platform(self):
        """
        Platform for this engine upgrade
        """
        return self.data.get('platform')
    
class UpdatePackage(PackageMixin, SubElement):
    """
    Container for managing update packages on SMC
    
    Download and activate a package::
        
        system = System()
        print(system.last_activated_package)
        
        for package in system.update_package():
            if package.name == 'Update Package 788': #Use specific package
                for msg in package.download(wait_for_finish=True): 
                    print msg
                package.activate() #Activate it on SMC
    
    :ivar state: state of the package               
    """
    def __init__(self, **meta):
        super(UpdatePackage, self).__init__(**meta)
        pass

    @property
    def activation_date(self):
        """
        Date this update was activated, if any
        """
        return self.data.get('activation_date')
    
    @property
    def package_id(self):
        """
        ID of the package. These will increment as new versions
        are released.
        """
        return self.data.get('package_id')
    
    @property
    def release_date(self):
        """
        Date of release
        """
        return self.data.get('release_date')
    
    @property
    def state(self):
        """
        State of this package, i.e. Active, available
        """
        return self.data.get('state')
    