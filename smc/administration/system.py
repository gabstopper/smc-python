"""
Module that controls aspects of the System itself, such as updating dynamic packages,
updating engines, applying global blacklists, etc.

To load the configuration for system, do::

    from smc.administration.system import System
    system = System()
    print system.smc_version
    print system.last_activated_package
    for pkg in system.update_package():
        print pkg

"""
import smc.actions.search as search
from smc.base.util import find_link_by_name
from smc.elements.other import prepare_blacklist
from .tasks import task_handler, Task
from smc.base.model import Meta, prepared_request
from smc.administration.updates import EngineUpgrade, UpdatePackage
from smc.api.common import fetch_json_by_post

class System(object):
    """
    System level operations such as SMC version, time, update packages, 
    and updating engines
    
    :ivar smc_version: version of SMC
    :ivar smc_time: SMC time
    :ivar last_activated_package: latest update package installed
    """
    def __init__(self):
        pass
    
    @property
    def href(self):
        return search.element_entry_point('system') 

    @property
    def link(self):
        result = search.element_by_href_as_json(self.href)
        return result.get('link')

    @property    
    def smc_version(self):
        """ Return the SMC version """
        return search.element_by_href_as_json(
                    find_link_by_name('smc_version', self.link)).get('value')
    
    @property
    def smc_time(self):
        """ Return the SMC time """
        return search.element_by_href_as_json(
                    find_link_by_name('smc_time', self.link)).get('value')
    
    @property
    def last_activated_package(self):
        """ Return the last activated package by id """
        return search.element_by_href_as_json(
                find_link_by_name('last_activated_package', self.link)).get('value')
    
    def empty_trash_bin(self):
        """ Empty system level trash bin """
        href = find_link_by_name('empty_trash_bin', self.link)
        return prepared_request(href=href).delete()

    def update_package(self):
        """ Show all update packages on SMC 
        
        :return: dict of href,name,type
        """
        updates=[]
        for update in search.element_by_href_as_json(
                            find_link_by_name('update_package', self.link)):
            updates.append(UpdatePackage(meta=Meta(**update)))
        return updates

    def update_package_import(self):
        pass
        
    def engine_upgrade(self, engine_version=None):
        """ List all engine upgrade packages available 
        
        Call this function without parameters to see available engine
        versions. Once you have found the engine version to upgrade, use
        the engine_version=href to obtain the guid. Obtain the download
        link and POST to download using 
        engine_upgrade_download(download_link) to download the update.
        
        :param engine_version: Version of engine to retrieve
        :return: dict of settings
        """
        upgrades=[]
        for upgrade in search.element_by_href_as_json(
                            find_link_by_name('engine_upgrade', self.link)):
            upgrades.append(EngineUpgrade(meta=Meta(**upgrade)))
        return upgrades
    
    def uncommitted(self):
        pass
    
    def system_properties(self):
        """ List of all properties applied to the SMC """
        return search.element_by_href_as_json(
                        find_link_by_name('system_properties', self.link))
        
    def clean_invalid_filters(self):
        pass
    
    def blacklist(self, src, dst, duration=3600):
        """ Add blacklist to all defined engines
        Use the cidr netmask at the end of src and dst, such as:
        1.1.1.1/32, etc.
        
        :param src: source of the entry
        :param dst: destination of blacklist entry
        :return: :py:class:`smc.api.web.SMCResult`
        """
        return prepared_request(
                    href=find_link_by_name('blacklist', self.link),
                    json=prepare_blacklist(src, dst, duration)).create()

    def licenses(self):
        """ List of all engine related licenses
        This will provide details related to whether the license is bound,
        granted date, expiration date, etc.
        
        :return: list of dictionary items specific to all engine licenses
        """
        return search.element_by_href_as_json(
                        find_link_by_name('licenses', self.link))
        
    def license_fetch(self):
        return search.element_by_href_as_json(
                        find_link_by_name('license_fetch', self.link))
        
    def license_install(self):
        raise NotImplementedError
        
    def license_details(self):
        """
        This represents the license details for the SMC. This will include information
        with regards to the POL/POS, features, type, etc
        
        :return: dictionary of key/values
        """
        return search.element_by_href_as_json(
                        find_link_by_name('license_details', self.link))
        
    def license_check_for_new(self):
        """ Check for new SMC license """
        return search.element_by_href_as_json(
                        find_link_by_name('license_check_for_new', self.link))
        
    def delete_license(self):
        raise NotImplementedError
    
    def visible_virtual_engine_mapping(self):
        """ Return list of dictionary mappings for master engines and virtual engines 
        
        :return: list of dict items related to master engines and virtual engine mappings
        """
        return search.element_by_href_as_json(
                        find_link_by_name('visible_virtual_engine_mapping', self.link))
    
    def references_by_element(self, element_href):
        """
        Return all references to element specified.
        
        :param str element_href: element reference
        :return: list list of references where element is used
        """
        href = find_link_by_name('references_by_element', self.link)
        result = fetch_json_by_post(href=href,
                                    json={'value': element_href})
        if result.json:
            return result.json
        else:
            return []
    
    def export_elements(self, filename='export_elements.zip', typeof='all',
                        wait_for_finish=False):
        """
        Export elements from SMC.
        
        Valid types are: 
        all (All Elements)|nw (Network Elements)|ips (IPS Elements)|
        sv (Services)|rb (Security Policies)|al (Alerts)|
        vpn (VPN Elements)
        
        :param type: type of element
        :param filename: Name of file for export
        :return: :py:class:`smc.api.web.SMCResult`
        :raises: :py:class:`smc.api.exceptions.TaskRunFailed`
        """
        valid_types = ['all', 'nw', 'ips', 'sv', 'rb', 'al', 'vpn']
        if not typeof in valid_types:
            typeof = 'all'
        params = {'recursive': True,
                  'type': typeof}
        element = prepared_request(href=find_link_by_name('export_elements', self.link),
                               params=params).create()
    
        task = task_handler(Task(**element.json), 
                            wait_for_finish=wait_for_finish, 
                            filename=filename)
        return task

    def import_elements(self):
        raise NotImplementedError

    def certificate_authority(self):
        return search.element_by_href_as_json(
                        href=find_link_by_name('certificate_authority', self.link))
    
    def unlicensed_components(self):
        raise NotImplementedError

    def snapshot(self):
        raise NotImplementedError
