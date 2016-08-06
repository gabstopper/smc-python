import smc.actions.search as search
from smc.elements.element import SMCElement
import smc.api.common as common_api
from smc.api.web import SMCException


class System(object):
    def __init__(self):
        self.last_activated_package = None
        self.version = None
        self.system_links = []
    
    def load(self):
        system = search.element_by_href_as_json(search.element_entry_point('system'))
        if system:
            self.system_links.extend(system.get('link'))
            self.version = system.get('version')
            self.last_activated_package = system.get('last_activated_package')
            return self
        else:
            raise SMCException("Exception retrieving system settings")
        
    def smc_version(self):
        return search.element_by_href_as_json(self._load_href('smc_version'))
    
    def smc_time(self):
        return search.element_by_href_as_json(self._load_href('smc_time'))
    
    def last_activated_package(self):
        return search.element_by_href_as_json(self._load_href('last_activated_package'))
    
    def update_package(self):
        return search.element_by_href_as_json(self._load_href('update_package'))
    
    def import_package(self):
        print "POST import package"
        
    def engine_upgrade(self):
        return search.element_by_href_as_json(self._load_href('engine_upgrade'))
    
    def uncommitted(self):
        pass
    
    def system_properties(self):
        return search.element_by_href_as_json(self._load_href('system_properties'))
        
    def empty_trash_bin(self):
        return common_api.delete(self._load_href('empty_trash_bin'))
        
    def clean_invalid_filters(self):
        pass
    
    def blacklist(self):
        print "POST blacklist"
        
    def licenses(self):
        return search.element_by_href_as_json(self._load_href('licenses'))
        
    def license_fetch(self):
        print "GET license fetch"
        
    def license_install(self):
        print "PUT license install"
        
    def license_details(self):
        return search.element_by_href_as_json(self._load_href('license_details'))
        
    def license_check_for_new(self):
        return search.element_by_href_as_json(self._load_href('license_check_for_new'))
        
    def delete_license(self):
        print "PUT delete license"
    
    #TODO: doesnt return anything    
    def virtual_engine_mapping(self):
        return search.element_by_href_as_json(self._load_href('virtual_engine_mapping'))
    
    #TODO: doesnt return anything    
    def references_by_element(self):
        return search.element_by_href_as_json(self._load_href('references_by_element'))
        
    def export_elements(self, type_of=None, filename='export_elements.zip'):
        """
        Export elements from SMC.
        
        Valid types are: 
        all (All Elements)|nw (Network Elements)|ips (IPS Elements)|sv (Services)|
        rb (Security Policies)|al (Alerts)|vpn (VPN Elements)
        
        :param type: type of element
        :param filename: Name of file for export
        """
        params = {'recursive': True,
                  'type': type_of}
        element = SMCElement(href=self._load_href('export_elements'),
                             params=params).create()
        
        for msg in common_api.async_handler(element.json.get('follower'), 
                                            display_msg=False):
            element.href = msg
        element.filename = filename
        file_download = common_api.fetch_content_as_file(element)
        if not file_download.msg:
            print "Export successful, saved to file: {}".format(file_download.content)
        
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
        for func in ['single_fw', 'fw_cluster']:
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
    
    def ips_engines(self):
        pass
    