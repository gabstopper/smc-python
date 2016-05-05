import logging
import smc
from smc.engine_license import OperationFailure

logger = logging.getLogger(__name__)

def remove_host(name):
    host = smc.search.filter_by_type('host', name)
    if host:
        logger.debug("Removing host: %s at %s" % (name, host['href']))
        try:
            smc.web_api.http_delete(host['href'])
            logger.info("Successfully removed host: %s" % name)
        except OperationFailure, e:
            logger.error("Failed removing host: %s, msg: %s" % (name, e.msg))
    else:
        logger.info("No host named: %s, nothing to remove" % name)

def remove_group(name):
    group = smc.search.filter_by_type('group', name)
    if group:
        logger.debug("Removing group: %s at %s" % (name, group['href']))
        try:
            smc.web_api.http_delete(group['href'])
            logger.info("Successfully removed group: %s" % name)
        except OperationFailure, e:
            logger.error("Failed removing group: %s, msg: %s" % (name, e.msg))
    else:
        logger.info("No group named: %s, nothing to remove" % name)
        
def remove_single_fw(name):
    #entry_href = web_api.get_entry_href('single_fw') #from cache
    #fw = search.filter_by_entry_point(entry_href, name)
    fw = smc.search.filter_by_type('single_fw', name)
    if fw:
        logger.debug("Removing single_fw: %s at %s" % (name, fw['href']))
        try:
            smc.web_api.http_delete(fw['href'])
            logger.info("Successfully removed single firewall: %s" % name)
        except OperationFailure, e:
            logger.error("Failed removing single fw: %s, msg: %s" % (name, e.msg))
    else:
        logger.info("No single firewall named: %s, nothing to remove" % name)

def remove_cluster_fw(data):
    pass

def remove_single_ips(data):
    pass

def remove_cluster_ips(data):
    pass

def remove_master_engine(data):
    pass

def remove_virtual_ips(data):
    pass

def remove_virtual_fw(data):
    pass


if __name__ == '__main__':
    smc.web_api.login('http://172.18.1.150:8082', 'EiGpKD4QxlLJ25dbBEp20001')
    remove_host('test')
    remove_host('ami')
    smc.remove_group('yoyo')
    smc.web_api.logout()