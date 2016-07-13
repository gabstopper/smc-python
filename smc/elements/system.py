import smc.actions.search as search
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
        print "GET version"
    
    def smc_time(self):
        print "GET time"
    
    def last_activated_package(self):
        print "GET package"
    
    def update_package(self):
        "GET update package"
    
    def import_package(self):
        print "POST import package"
        
    def engine_upgrade(self):
        print "GET engine upgrade"
    
    def uncommitted(self):
        pass
    
    def system_properties(self):
        print "GET system properties"
        
    def empty_trash_bin(self):
        print "DELETE trash bin"
        
    def clean_invalid_filters(self):
        pass
    
    def blacklist(self):
        print "POST blacklist"
        
    def licenses(self):
        print "GET licenses"
        
    def license_fetch(self):
        print "GET license fetch"
        
    def license_install(self):
        print "PUT license install"
        
    def license_details(self):
        print "GET license details"
        
    def license_check_for_new(self):
        print "GET license check for new"
        
    def delete_license(self):
        print "PUT delete license"
        
    def virtual_engine_mapping(self):
        print "GET virtual engine mapping"
        
    def references_by_element(self):
        print "GET references by element"
        
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
    