"""
Module that controls aspects of the System itself, such as updating dynamic
packages, updating engines, applying global blacklists, etc.

To load the configuration for system, do::

    >>> from smc.administration.system import System
    >>> system = System()
    >>> system.smc_version
    '6.2.0 [10318]'
    >>> system.last_activated_package
    '881'
    >>> for pkg in system.update_package():
    ...   print(pkg)
    ...
    UpdatePackage(name=Update Package 889)
    UpdatePackage(name=Update Package 888)
    UpdatePackage(name=Update Package 887)

"""
import smc.actions.search as search
from smc.elements.other import prepare_blacklist
from smc.base.model import SubElement, Element, ElementCreator
from smc.administration.updates import EngineUpgrade, UpdatePackage
from smc.administration.license import Licenses
from smc.api.exceptions import TaskRunFailed, ActionCommandFailed
from smc.administration.tasks import DownloadTask
from smc.base.util import millis_to_utc


class System(SubElement):
    """
    System level operations such as SMC version, time, update packages,
    and updating engines
    """

    def __init__(self):
        entry = search.element_entry_point('system')
        super(System, self).__init__(href=entry)

    @property
    def smc_version(self):
        """
        Return the SMC version
        """
        return self.make_request(
            resource='smc_version').get('value')

    @property
    def smc_time(self):
        """
        Return the SMC time as datetime object in UTC
        
        :rtype datetime
        """
        return millis_to_utc(
            int(self.make_request(
                resource='smc_time').get('value')))

    @property
    def last_activated_package(self):
        """
        Return the last activated package by id
        
        :raises ActionCommandFailed: failure to retrieve resource
        """
        return self.make_request(
            resource='last_activated_package').get('value')

    def empty_trash_bin(self):
        """
        Empty system level trash bin

        :raises ActionCommandFailed: failed removing trash
        :return: None
        """
        self.make_request(
            method='delete',
            resource='empty_trash_bin')

    def update_package(self):
        """
        Show all update packages on SMC

        :raises ActionCommandFailed: failure to retrieve resource
        :rtype: list(UpdatePackage)
        """
        return [UpdatePackage(**update)
                for update in self.make_request(resource='update_package')]

    def update_package_import(self):
        pass

    def engine_upgrade(self, engine_version=None):
        """
        List all engine upgrade packages available

        Call this function without parameters to see available engine
        versions. Once you have found the engine version to upgrade, use
        the engine_version=href to obtain the guid. Obtain the download
        link and POST to download using
        engine_upgrade_download(download_link) to download the update.

        :param engine_version: Version of engine to retrieve
        :raises ActionCommandFailed: failure to retrieve resource
        :return: settings in raw dict format
        :rtype: dict
        """
        return [EngineUpgrade(**upgrade)
                for upgrade in self.make_request(resource='engine_upgrade')]

    def uncommitted(self):
        pass

    def system_properties(self):
        """
        List of all properties applied to the SMC
        
        :raises ActionCommandFailed: failure to retrieve resource
        """
        return self.make_request(resource='system_properties')

    def clean_invalid_filters(self):
        pass

    def blacklist(self, src, dst, duration=3600, **kw):
        """
        Add blacklist to all defined engines.
        Use the cidr netmask at the end of src and dst, such as:
        1.1.1.1/32, etc.

        :param src: source of the entry
        :param dst: destination of blacklist entry
        :raises ActionCommandFailed: blacklist apply failed with reason
        :return: None

        .. seealso:: :class:`smc.core.engine.Engine.blacklist`. Applying
            a blacklist at the system level will be a global blacklist entry
            versus an engine specific entry.
        
        .. note:: If more advanced blacklist is required using source/destination
            ports and protocols (udp/tcp), use kw to provide these arguments. See
            :py:func:`smc.elements.other.prepare_blacklist` for more details.
        """
        self.make_request(
            method='create',
            resource='blacklist',
            json=prepare_blacklist(src, dst, duration, **kw))

    @property
    def licenses(self):
        """
        List of all engine related licenses
        This will provide details related to whether the license is bound,
        granted date, expiration date, etc.
        ::

            >>> for license in system.licenses:
            ...    if license.bound_to.startswith('Management'):
            ...        print(license.proof_of_license)
            abcd-efgh-ijkl-mnop

        :raises ActionCommandFailed: failure to retrieve resource
        :rtype: list(Licenses)
        """
        return Licenses(self.make_request(resource='licenses'))

    def license_fetch(self, proof_of_serial):
        """
        Request a license download for the specified POS (proof of serial).
        
        :param str proof_of_serial: proof of serial number of license to fetch
        :raises ActionCommandFailed: failure to retrieve resource
        """
        return self.make_request(
            resource='license_fetch',
            params={'proofofserial': proof_of_serial})

    def license_install(self, license_file):
        """
        Install a new license.
        
        :param str license_file: fully qualified path to the
            license jar file.
        :raises: ActionCommandFailed
        :return: None
        """
        self.make_request(
            method='update',
            resource='license_install',
            files={
                'license_file': open(license_file, 'rb')
            })

    def license_details(self):
        """
        This represents the license details for the SMC. This will include
        information with regards to the POL/POS, features, type, etc

        :raises ActionCommandFailed: failure to retrieve resource
        :return: dictionary of key/values
        """
        return self.make_request(resource='license_details')

    def license_check_for_new(self):
        """
        Launch the check and download of licenses on the Management Server.
        This task can be long so call returns immediately.
        
        :raises ActionCommandFailed: failure to retrieve resource
        """
        return self.make_request(resource='license_check_for_new')

    def delete_license(self):
        raise NotImplementedError

    def visible_virtual_engine_mapping(self):
        """
        Mappings for master engines and virtual engines

        :raises ActionCommandFailed: failure to retrieve resource
        :return: list of dict items related to master engines and virtual
            engine mappings
        """
        return self.make_request(resource='visible_virtual_engine_mapping')

    def references_by_element(self, element_href):
        """
        Return all references to element specified.

        :param str element_href: element reference
        :return: list of references where element is used
        :rtype: list(dict)
        """
        result = self.make_request(
            method='create',
            resource='references_by_element',
            json={
                'value': element_href})
        return result

    def export_elements(self, filename='export_elements.zip', typeof='all'):
        """
        Export elements from SMC.

        Valid types are:
        all (All Elements)|nw (Network Elements)|ips (IPS Elements)|
        sv (Services)|rb (Security Policies)|al (Alerts)|
        vpn (VPN Elements)

        :param type: type of element
        :param filename: Name of file for export
        :raises TaskRunFailed: failure during export with reason
        :rtype: DownloadTask
        """
        valid_types = ['all', 'nw', 'ips', 'sv', 'rb', 'al', 'vpn']
        if typeof not in valid_types:
            typeof = 'all'

        task = self.make_request(
            TaskRunFailed,
            method='create',
            resource='export_elements',
            params={
                'recursive': True,
                'type': typeof})

        return DownloadTask(
                filename=filename, task=task)

    def active_alerts_ack_all(self):
        """
        Acknowledge all active alerts in the SMC. Only valid for
        SMC version >= 6.2.
    
        :raises ActionCommandFailed: Failure during acknowledge with reason
        :return: None
        """
        self.make_request(
            method='delete',
            resource='active_alerts_ack_all')

    def import_elements(self, import_file):
        """
        Import elements into SMC. Specify the fully qualified path
        to the import file.
        
        :param str import_file: system level path to file
        :raises: ActionCommandFailed
        :return: None
        """
        self.make_request(
            method='create',
            resource='import_elements',
            files={
                'import_file': open(import_file, 'rb')
                })

    def unlicensed_components(self):
        raise NotImplementedError
    
    @property
    def mgt_integration_configuration(self):
        """
        Retrieve the management API configuration for 3rd party integration
        devices.
        
        :raises ActionCommandFailed: failure to retrieve resource
        """
        return self.make_request(resource='mgt_integration_configuration')


class AdminDomain(Element):
    """
    Administrative domain element. Domains are used to provide object
    based segmentation within SMC. If domains are in use, you can
    log in directly to a domain to modify contents within that domain.
        
    Find all available domains::
    
        >>> list(AdminDomain.objects.all())
        [AdminDomain(name=Shared Domain)]
  
    .. note:: Admin Domains require and SMC license.
    """
    typeof = 'admin_domain'
   
    @classmethod
    def create(cls, name, comment=None):
        """
        Create a new Admin Domain element for SMC objects.
        
        Example::
    
            >>> AdminDomain.create(name='mydomain', comment='mycomment')
            >>> AdminDomain(name=mydomain) 
        
        :param str name: name of domain
        :param str comment: optional comment
        :raises CreateElementFailed: failed creating element with reason
        :return: instance with meta
        :rtype: AdminDomain
        """
        json = {'name': name,
                'comment': comment}
        
        return ElementCreator(cls, json)
