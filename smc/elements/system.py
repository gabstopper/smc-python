import smc.actions.search as search
from smc.api.web import SMCException
from smc.api import common


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
        return common.delete(self._load_href('empty_trash_bin'))
        
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
        
    def export_elements(self):
        print "POST export elements"
        
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
        pass
    
    def layer3_firewalls(self):
        pass
    
    def layer2_firewalls(self):
        pass
    
    def ips_engines(self):
        pass
    