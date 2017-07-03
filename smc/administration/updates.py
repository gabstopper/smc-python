"""
Functionality related to updating dynamic update packages and
engine upgrades
"""
from smc.base.model import prepared_request, SubElement
from smc.api.exceptions import ResourceNotFound, ActionCommandFailed
from smc.administration.tasks import Task, TaskOperationPoller


class PackageMixin(object):
    """
    Manages downloads and activations of update packages and software
    upgrades
    """

    def download(self, timeout=5,
                 wait_for_finish=False):
        """
        Download Package or Engine Update

        :param int timeout: timeout between queries
        :raises ActionCommandFailed: task kick off failed
        :raises TaskRunFailed: failure during task status
        :return: Task or TaskOperationPoller
        """
        try:
            task = prepared_request(
                ActionCommandFailed,
                href=self.data.get_link('download')
            ).create().json

            return TaskOperationPoller(
                task=task, timeout=timeout,
                wait_for_finish=wait_for_finish)

        except ResourceNotFound:
            raise ActionCommandFailed(
                'Package cannot be downloaded, package state: {}' .format(
                    self.state))

    def activate(self, resource=None, timeout=3,
                 wait_for_finish=False):
        """
        Activate this package on the SMC

        :param list resource: node href's to activate on. Resource is only
               required for software upgrades
        :param int timeout: timeout between queries
        :raises ActionCommandFailed: failure during activation (downloading, etc)
        :raises TaskRunFailed: failure during task run
        :return: generator Task generator with updates
        """
        try:
            task = prepared_request(
                ActionCommandFailed,
                href=self.data.get_link('activate'),
                json={'resource': resource}
            ).create().json

            return TaskOperationPoller(
                task=task, timeout=timeout,
                wait_for_finish=wait_for_finish)

        except ResourceNotFound:
            raise ActionCommandFailed(
                'Activation failed, resource is not available')

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
                task = package.download().wait()
                if task.success:
                    package.activate() #Activate it on SMC

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
