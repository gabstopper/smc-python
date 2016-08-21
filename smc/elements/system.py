import smc.actions.search as search
from smc.elements.element import SMCElement, Blacklist
import smc.api.common as common_api
from smc.api.web import SMCException

class System(object):
    def __init__(self):
        self.last_activated_package_id = None
        self.version = None
        self.system_links = []
    
    def load(self):
        system = search.element_by_href_as_json(search.element_entry_point('system'))
        if system:
            self.system_links.extend(system.get('link'))
            self.version = system.get('version')
            self.last_activated_package_id = system.get('last_activated_package_id')
            return self
        else:
            raise SMCException("Exception retrieving system settings")
        
    def smc_version(self):
        """ Return the SMC version """
        return search.element_by_href_as_json(self._load_href('smc_version'))
    
    def smc_time(self):
        """ Return the SMC time """
        return search.element_by_href_as_json(self._load_href('smc_time'))
    
    def last_activated_package(self):
        """ Return the last activated package by id """
        return search.element_by_href_as_json(self._load_href('last_activated_package')).get('value')
    
    def update_package(self):
        """ Show all update packages on SMC 
        :return: dict of href,name,type
        """
        return search.element_by_href_as_json(self._load_href('update_package'))
    
    def update_package_download(self, package_id=None):
        """ 
        POST to download after grabbing the package by id
        :method: POST
        """
        available = {} #{ package_id: [link_hrefs] }
        for package in self.update_package():
            state = search.element_by_href_as_json(package.get('href'))
            if state.get('state') == 'available':
                available[state.get('package_id')] = state.get('link')             
        newest = max(available.keys())
        if newest:
            for download in available.get(newest):
                if download.get('rel') == 'download':
                    print download.get('href')
        else:
            print "No downloads available"
        
    def update_package_activate(self, package_id):
        """ Call activate on package after getting """
        pass
            
    def import_package(self):
        print "POST import package"
        
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
        if not engine_version:
            return search.element_by_href_as_json(self._load_href('engine_upgrade'))
        else:
            return search.element_by_href_as_json(engine_version)
    
    def engine_upgrade_download(self, path):
        """ Download the engine upgrade
        
        First call :py:func:`engine_upgrade` to obtain the link path to the 
        engine upgrade. Call this function with the download POST link.
        :param path: href path to engine download  
        :return: SMCResult. Will return follower link but download in the background.
        """
        return SMCElement(href=path).create()
        
    def uncommitted(self):
        pass
    
    def system_properties(self):
        """ List of all properties applied to the SMC """
        return search.element_by_href_as_json(self._load_href('system_properties'))
        
    def empty_trash_bin(self):
        """ Empty system level trash bin """
        return common_api.delete(self._load_href('empty_trash_bin'))
        
    def clean_invalid_filters(self):
        pass
    
    def blacklist(self, src, dst, duration=3600):
        """ Add blacklist to all defined engines
        Use the cidr netmask at the end of src and dst, such as:
        1.1.1.1/32, etc.
        
        :param src: source of the entry
        :param dst: destination of blacklist entry
        :return: SMCResult, href if success, msg if error
        """
        element = Blacklist(src, dst, duration)
        from pprint import pprint
        pprint(element)
        element.href = self._load_href('blacklist')
        return element.create()
        
    def licenses(self):
        """ List of all engine related licenses
        This will provide details related to whether the license is bound,
        granted date, expiration date, etc.
        
        :return: list of dictionary items specific to all engine licenses
        """
        return search.element_by_href_as_json(self._load_href('licenses'))
        
    def license_fetch(self):
        return search.element_by_href_as_json(self._load_href('license_fetch'))
        
    def license_install(self):
        print "PUT license install"
        
    def license_details(self):
        """
        This represents the license details for the SMC. This will include information
        with regards to the POL/POS, features, type, etc
        
        :return: dictionary of key/values
        """
        return search.element_by_href_as_json(self._load_href('license_details'))
        
    def license_check_for_new(self):
        """ Check for new SMC license """
        return search.element_by_href_as_json(self._load_href('license_check_for_new'))
        
    def delete_license(self):
        print "PUT delete license"
    
    def visible_virtual_engine_mapping(self):
        """ Return list of dictionary mappings for master engines and virtual engines 
        :return: list of dict items related to master engines and virtual engine mappings
        """
        return search.element_by_href_as_json(self._load_href('visible_virtual_engine_mapping'))
    
    #TODO: doesnt return anything    
    def references_by_element(self):
        return search.element_by_href_as_json(self._load_href('references_by_element'))
        
    def export_elements(self, type_of=None, filename='export_elements.zip'):
        """
        Export elements from SMC.
        
        Valid types are: 
        all (All Elements)|nw (Network Elements)|ips (IPS Elements)|
        sv (Services)|rb (Security Policies)|al (Alerts)|
        vpn (VPN Elements)
        
        :param type: type of element
        :param filename: Name of file for export
        """
        params = {'recursive': True,
                  'type': type_of}
        element = SMCElement(href=self._load_href('export_elements'),
                             params=params).create()
        if not element.msg:
            href = next(common_api.async_handler(element.json.get('follower'), 
                                                 display_msg=False))     
        else:
            return element
        
        return common_api.fetch_content_as_file(href, filename)
        
    def import_elements(self):
        print "POST import elements"
    
    def _load_href(self, action):
        href = [entry.get('href') for entry in self.system_links \
                if entry.get('rel') == action]      
        if href:
            return href.pop()
        
class SystemInfo(System):
    def __init__(self):
        System.__init__(self)
        super(SystemInfo, self).load()
    
    def log_servers(self):
        return search.log_servers()
    
    def first_log_server(self):
        return search.get_first_log_server()
    
    def engines(self):
        engines = []
        for func in ['single_fw', 'fw_cluster', 'single_layer2', 
                     'layer2_cluster', 'single_ips', 'ips_cluster',
                     'master_engine', 'virtual_fw', 'virtual_ips']:
            result = getattr(self, func)
            engines.extend(result())
        return engines 
    
    def single_fw(self):
        return search.all_elements_by_type('single_fw')
    
    def fw_cluster(self):
        return search.all_elements_by_type('fw_cluster')
        
    def single_layer2(self):
        return search.all_elements_by_type('single_layer2')
    
    def layer2_cluster(self):
        return search.all_elements_by_type('layer2_cluster')
    
    def single_ips(self):
        return search.all_elements_by_type('single_ips')
    
    def ips_cluster(self):
        return search.all_elements_by_type('ips_cluster')
    
    def master_engine(self):
        return search.all_elements_by_type('master_engine')
    
    def virtual_fw(self):
        return search.all_elements_by_type('virtual_fw')
    
    def virtual_ips(self):
        return search.all_elements_by_type('virtual_ips')