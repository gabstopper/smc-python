"""
Functionality related to updating dynamic update packages and 
engine upgrades
"""
from smc.base.util import find_link_by_name
from .tasks import Task, task_handler
import smc.actions.search as search
from smc.base.model import prepared_request

class PackageMixin(object):
    """
    Manages downloads and activations of update packages and software
    upgrades
    """
    @property
    def name(self):
        return self.meta.name
    
    @property
    def href(self):
        return self.meta.href 
    
    def download(self, wait_for_finish=False, sleep=3):
        """
        Download Package or Engine Update
        
        :method: POST
        :param boolean wait_for_finish: wait for download to complete
        :param int sleep: number of seconds to sleep if wait_for_finish=True
        :return: Generator messages or final href of follower resource
        """ 
        pkg = self.package_info()
        download_link = find_link_by_name('download', pkg.get('link'))
        if download_link:
            result = prepared_request(href=download_link).create()
                    
            task = task_handler(Task(**result.json), 
                                wait_for_finish=wait_for_finish, 
                                sleep=sleep)
            return task
        else:
            return ['Package cannot be downloaded, package state: {}'.format(\
                                                                    self.state)]
    
    def activate(self, resource=None, wait_for_finish=False, sleep=3):
        """
        Activate this package on the SMC
        
        :param list resource: node href's to activate on. Resource is only 
               required for software upgrades
        :param boolean wait_for_finish: True|False, whether to wait 
               for update messages
        :param int sleep: number of seconds to sleep if wait_for_finish=True
        :return: Update messages or final URI for follower link
        :raises: :py:class:`smc.api.exceptions.TaskRunFailed`
        """
        pkg = self.package_info()
        activate_link = find_link_by_name('activate', pkg.get('link'))
        if activate_link:
            result = prepared_request(href=activate_link,
                                  json={'resource': resource}).create()
            
            task = task_handler(Task(**result.json), 
                                wait_for_finish=wait_for_finish, 
                                sleep=sleep)
            return task
    
    def package_info(self):
        """
        Retrieve view of package info as dict
        
        :return: dict package info in json format
        """
        return search.element_by_href_as_json(self.href)
    
    def __repr__(self):
        return '{0}(name={1})'.format(self.__class__.__name__, self.name)
    
class EngineUpgrade(PackageMixin):
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
    def __init__(self, meta=None):
        self.meta = meta

class UpdatePackage(PackageMixin):
    """
    Container for managing update packages on SMC

    Example of checking for new Update Packages, picking a specific
    package, and waiting for activation::
    
    Download and activate a package::
        
        system = System()
        print system.last_activated_package
        
        for package in system.update_package():
            if package.name == 'Update Package 788':
                for msg in package.download(wait_for_finish=True):
                    print msg
                package.activate()
                        
    :ivar state: state of the package                 
    """
    def __init__(self, meta=None):
        self.meta = meta

    @property
    def state(self):
        pkg = self.package_info()
        return pkg.get('state')
