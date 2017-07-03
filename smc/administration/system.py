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
from smc.base.model import prepared_request, SubElement
from smc.administration.updates import EngineUpgrade, UpdatePackage
from smc.administration.license import Licenses
from smc.api.common import fetch_json_by_post
from smc.api.exceptions import ActionCommandFailed
from smc.administration.tasks import DownloadTask


class System(SubElement):
    """
    System level operations such as SMC version, time, update packages,
    and updating engines
    """

    def __init__(self, **meta):
        entry = search.element_entry_point('system')
        super(System, self).__init__(href=entry)
        pass

    @property
    def smc_version(self):
        """
        Return the SMC version
        """
        return self.data.get_json('smc_version').get('value')

    @property
    def smc_time(self):
        """
        Return the SMC time
        """
        return self.data.get_json('smc_time').get('value')

    @property
    def last_activated_package(self):
        """
        Return the last activated package by id
        """
        return self.data.get_json('last_activated_package').get('value')

    def empty_trash_bin(self):
        """
        Empty system level trash bin

        :raises ActionCommandFailed: failed removing trash
        :return: None
        """
        prepared_request(
            ActionCommandFailed,
            href=self.data.get_link('empty_trash_bin')
            ).delete()

    def update_package(self):
        """
        Show all update packages on SMC

        :return: list :py:class:`smc.administration.updates.UpdatePackage`
        """
        return [UpdatePackage(**update)
                for update in self.data.get_json('update_package')]

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
        :return: settings in raw dict format
        :rtype: dict
        """
        return [EngineUpgrade(**upgrade)
                for upgrade in self.data.get_json('engine_upgrade')]

    def uncommitted(self):
        pass

    def system_properties(self):
        """
        List of all properties applied to the SMC
        """
        return self.data.get_json('system_properties')

    def clean_invalid_filters(self):
        pass

    def blacklist(self, src, dst, duration=3600):
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

        """
        prepared_request(ActionCommandFailed,
                         href=self.data.get_link('blacklist'),
                         json=prepare_blacklist(src, dst, duration)
                         ).create()

    @property
    def licenses(self):
        """
        List of all engine related licenses
        This will provide details related to whether the license is bound,
        granted date, expiration date, etc.
        ::

            for license in system.licenses:
                print(license, license.expiration_date)
                .....

        :return: list :py:class:`smc.administration.license.Licenses`
        """
        return Licenses(self.data.get_json('licenses'))

    def license_fetch(self):
        """
        Fetch available licenses for this SMC
        """
        return self.data.get_json('license_fetch')

    def license_install(self):
        raise NotImplementedError

    def license_details(self):
        """
        This represents the license details for the SMC. This will include
        information with regards to the POL/POS, features, type, etc

        :return: dictionary of key/values
        """
        return self.data.get_json('license_details')

    def license_check_for_new(self):
        """
        Check for new SMC license
        """
        return self.data.get_json('license_check_for_new')

    def delete_license(self):
        raise NotImplementedError

    def visible_virtual_engine_mapping(self):
        """
        Mappings for master engines and virtual engines

        :return: list of dict items related to master engines and virtual
            engine mappings
        """
        return self.data.get_json('visible_virtual_engine_mapping')

    def references_by_element(self, element_href):
        """
        Return all references to element specified.

        :param str element_href: element reference
        :return: list list of references where element is used
        """
        result = fetch_json_by_post(
            href=self.data.get_link('references_by_element'),
            json={'value': element_href})
        if result.json:
            return result.json
        else:
            return []

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
        :return: DownloadTask
        """
        valid_types = ['all', 'nw', 'ips', 'sv', 'rb', 'al', 'vpn']
        if typeof not in valid_types:
            typeof = 'all'

        task = prepared_request(
            href=self.data.get_link('export_elements'),
            params={'recursive': True,
                    'type': typeof}
            ).create().json

        return DownloadTask(
                filename=filename, task=task)

    def active_alerts_ack_all(self):
        """
        Acknowledge all active alerts in the SMC
        :raises ActionCommandFailed: Failure during acknowledge with reason
        :raises ResourceNotFound: resource supported in version >= 6.2
        :return: None
        """
        prepared_request(
            ActionCommandFailed,
            href=self.data.get_link('active_alerts_ack_all')
            ).delete()

    def import_elements(self):
        raise NotImplementedError

    def unlicensed_components(self):
        raise NotImplementedError

    def snapshot(self):
        raise NotImplementedError
