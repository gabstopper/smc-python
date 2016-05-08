import logging
import smc.elements
from smc.web_api import SMCOperationFailure

logger = logging.getLogger(__name__)


def host(name, ip, secondary_ip=[], comment=None):
    if smc.helpers.is_valid_ipv4(ip):
        entry_href = smc.web_api.get_entry_href('host')        
        host = smc.elements.Host(name, ip, secondary_ip=[], comment=None)            
        
        try:
            r = smc.web_api.http_post(entry_href, host.get_json())           
            logger.info("Success creating single host: %s, href: %s" % (host.name, r))
        except SMCOperationFailure, e:
            logger.error("Failed creating single host: %s, api message: %s" % (host.name, e.msg))                           
    else:
        logger.error("Failed: Invalid IPv4 address specified: %s, create object: %s failed" % (ip, name)) 

    
def router(name, ip):    
    if smc.helpers.is_valid_ipv4(ip):
        entry_href = smc.web_api.get_entry_href('router')
        router = smc.elements.Router(name, ip)
        
        try:
            r = smc.web_api.http_post(entry_href, router.get_json())
            logger.info("Success creating router object: %s, href: %s" % (router.name, r))
        except SMCOperationFailure, e:
            logger.error("Failed creating router object: %s, api message: %s" % (router.name, e.msg))                           
    else:
        logger.error("Failed: Invalid IPv4 address specified: %s, create object: %s failed" % (ip, name)) 

        
def group(name, members=[]):
    entry_href = smc.web_api.get_entry_href('group')
    group = smc.elements.Group(name)   
    
    if members:
        for m in members: #add each member
            found_member = smc.search.get_element(m)
            if found_member:
                logger.debug("Found member: %s, adding to group: %s" % (m, group.name))
                group.members.append(found_member['href'])
                continue
            else:
                logger.info("Element: %s could not be found, not adding to group" % m)    
    try:
        r = smc.web_api.http_post(entry_href, group.get_json())
        logger.info("Success creating group: %s, href: %s" % (group.name, r))
    except SMCOperationFailure, e:
        logger.error("Failed creating group record: %s, api message: %s" % (name, e.msg))
                         
def network(name, ip_network, comment=None):
    pass

def single_fw(name, mgmt_ip, mgmt_network, dns=None, fw_license=False):
    if not smc.helpers.is_ipaddr_in_network(mgmt_ip, mgmt_network):
        logger.error("Failed: Management IP is not in the management network, can't add single_fw")
        return None
   
    available_log_servers = smc.search.get_element_by_entry_point('log_server')
    if not available_log_servers:
        logger.error("Can't seem to find an available Log Server on specified SMC, can't add single_fw: %s" % name)
        return None
    
    single_fw = smc.elements.SingleFW(name, mgmt_ip, mgmt_network)
    
    for found in available_log_servers:
        #TODO: If multiple log servers are present, how to handle - just get the first one
        single_fw.log_server = found['href']
    
    entry_href = smc.web_api.get_entry_href('single_fw') #get entry point for single_fw
    
    logger.debug("Modified json for single_fw: %s" % single_fw.get_json())
    
    try:
        new_href = smc.web_api.http_post(entry_href, single_fw.get_json())
        logger.info("Success creating single firewall: %s, new href: %s" % (single_fw.name, new_href))
        if fw_license: #fw license is specified
            logger.debug("Bind license specified, checking for available license")
            fw_from_link = smc.search.get_element_by_href(new_href)
            link = fw_from_link['nodes'][0]['firewall_node']['link']
            for slot in link:
                if slot['rel'] == 'bind':
                    bind_href = slot['href']
            logger.debug("Found bind href, attempting to call bind engine_license")
            smc.engine_license.bind_license(bind_href)
            logger.info("Successfully bound license to single_fw: %s" % name)               
    except SMCOperationFailure, e:
        logger.error("Create single_fw: %s failed: %s" % (single_fw.name, e.msg))

    
def cluster_fw(data):
    pass

def single_ips(data):
    pass

def cluster_ips(data):
    pass

def master_engine(data):
    pass

def virtual_ips(data):
    pass

def virtual_fw(data):
    pass


if __name__ == '__main__':
    smc.web_api.login('http://172.18.1.150:8082', 'EiGpKD4QxlLJ25dbBEp20001')
    
    smc.create.single_fw('test-run2', '3.3.3.3', '3.3.3.0/24', dns='6.6.6.6', fw_license=True)
    import time
    time.sleep(30)
    smc.remove.element('test-run2')
    
    smc.web_api.logout()
