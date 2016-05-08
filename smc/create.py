import json
import logging
import smc
from smc.web_api import SMCOperationFailure

logger = logging.getLogger(__name__)


def create_host(name, ip, secondary_ip=[], comment=None):
    if smc.helpers.is_valid_ipv4(ip):
        entry_href = smc.web_api.get_entry_href('host')
        
        host_template = smc.helpers.get_json_template('host.json')
        host_template['name'] = name
        host_template['address'] = ip
        if comment:
            host_template['comment'] = comment
        if secondary_ip:
            for addr in secondary_ip:
                host_template['secondary'].append(addr)
            
        try:
            r = smc.web_api.http_post(entry_href, host_template)
            logger.info("Success creating single host: %s, href: %s" % (name, r))
        except SMCOperationFailure, e:
            logger.error("Failed creating single host: %s, api message: %s" % (name, e.msg))                           
    else:
        logger.error("Failed: Invalid IPv4 address specified: %s, create object: %s failed" % (ip, name)) 
    
def create_router(name, ip):
    if smc.helpers.is_valid_ipv4(ip):
        entry_href = smc.web_api.get_entry_href('router')
        router_template = smc.helpers.get_json_template('router.json')
        router_template['name'] = name
        router_template['address'] = ip
        try:
            r = smc.web_api.http_post(entry_href, router_template)
            logger.info("Success creating router object: %s, href: %s" % (name, r))
        except SMCOperationFailure, e:
            logger.error("Failed creating router object: %s, api message: %s" % (name, e.msg))                           
    else:
        logger.error("Failed: Invalid IPv4 address specified: %s, create object: %s failed" % (ip, name)) 
        
def create_group(group, members=[]):
    entry_href = smc.web_api.get_entry_href('group')
    
    group_template = smc.helpers.get_json_template('group.json')
    group_template['name'] = group
    if members:
        for m in members: #add each member
            found_member = smc.search.get_element(m)
            if found_member:
                logger.debug("Found member: %s, adding to group: %s" % (m, group))
                group_template['element'].append(found_member['href'])
                continue
            else:
                logger.info("Element: %s could not be found, not adding to group" % m)
    try:
        r = smc.web_api.http_post(entry_href, group_template)
        logger.info("Success creating group: %s, href: %s" % (group, r))
    except SMCOperationFailure, e:
        logger.error("Failed creating group record: %s, api message: %s" % (group, e.msg))
                         

def create_single_fw(name, mgmt_ip, mgmt_network, dns=None, fw_license=False):
    if not smc.helpers.is_ipaddr_in_network(mgmt_ip, mgmt_network):
        logger.error("Failed: Management IP is not in the management network, can't add single_fw")
        return None
   
    available_log_servers = smc.search.get_element_by_entry_point('log_server')
    if not available_log_servers:
        logger.error("create_single_fw: Can't seem to find an available Log Server on specified SMC, can't add single_fw")
        return None
    
    for found in available_log_servers:
        #TODO: If multiple log servers are present, how to handle - just get the first one
        log_server_href = found['href']
    
    entry_href = smc.web_api.get_entry_href('single_fw') #get entry point for single_fw
    
    fw_template = smc.helpers.get_json_template('single_fw.json') #get single_fw json template
        
    for k,v in fw_template.iteritems():    
        if k == 'name':
            fw_template[k] = name
        elif k == 'nodes':
            fw_template[k][0]['firewall_node']['name'] = name + ' node 1'
        elif k == 'physicalInterfaces':
            fw_template[k][0]['physical_interface']['interfaces'][0]['single_node_interface']['address'] = mgmt_ip
            fw_template[k][0]['physical_interface']['interfaces'][0]['single_node_interface']['network_value'] = mgmt_network
        elif k == 'log_server_ref':
            fw_template[k] = log_server_href
        elif k == 'domain_server_address':
            if dns:
                fw_template[k].append({"rank": 0, "value": dns})
 
    logger.debug("Modified json for POST: %s" % json.dumps(fw_template))
    
    try:
        new_href = smc.web_api.http_post(entry_href, fw_template)
        logger.info("Success creating single firewall: %s, new href: %s" % (name, new_href))
        if fw_license: #fw license is specified
            logger.debug("bind license specified, checking for available license")
            fw_from_link = smc.search.get_element_by_href(new_href)
            link = fw_from_link['nodes'][0]['firewall_node']['link']
            for slot in link:
                if slot['rel'] == 'bind':
                    bind_href = slot['href']
            logger.debug("Found bind href, attempting to call bind engine_license")
            smc.engine_license.bind_license(bind_href)
            logger.info("Successfully bound license to single_fw: %s" % name)               
    except SMCOperationFailure, e:
        logger.error("Create single fw failed: %s" % e.msg)
    
def create_cluster_fw(data):
    pass

def create_single_ips(data):
    pass

def create_cluster_ips(data):
    pass

def create_master_engine(data):
    pass

def create_virtual_ips(data):
    pass

def create_virtual_fw(data):
    pass


if __name__ == '__main__':
    smc.web_api.login('http://172.18.1.150:8082', 'EiGpKD4QxlLJ25dbBEp20001')
    
    smc.remove.remove_group('group with no members')
    smc.remove.remove_group('anewgroup') 
    smc.remove.remove_host('ami2')
    smc.remove.remove_host('test')
    #group = smc.search.get_element('Skype Servers', 'group')
    #print smc.search.get_element_by_href(group['href'])
    create_group('group with no members')
    create_host('ami', '1.1.1.1')
    create_host('ami2', '2.2.2.2')
    create_group('anewgroup', ['ami','ami23'])
    create_single_fw('test-run', '3.3.3.3', '3.3.3.0/24')
    
    create_router('mynewrouter', '5.5.5.5')
    
    smc.web_api.logout()
