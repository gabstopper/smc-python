import smc
import logging
from pprint import pprint
from smc.operationfailure import OperationFailure

logger = logging.getLogger(__name__)

def blacklist_add(src, dst, duration="3600"):
    if smc.helpers.is_valid_ipv4(src) and smc.helpers.is_valid_ipv4(dst):
        
        entry = smc.web_api.get_entry_href('blacklist')   
        bl_template = smc.helpers.get_json_template('blacklist.json') 
        
        print "Blah"  
        if bl_template:  
            bl_template['duration'] = duration
            bl_template['end_point1']['ip_network'] = src + '/32'
            bl_template['end_point2']['ip_network'] = dst + '/0'
        print bl_template
        try:
            smc.web_api.http_post('http://172.18.1.150:8082/6.0/elements/fw_cluster/116/blacklist', bl_template)
        except OperationFailure, e:
            print "Error!: %s" % e.msg
                
    else:
        #logger.error("Invalid IP address given for blacklist entry, src: %s, dst: %s" % (src,dst))  
        print "Invalid IP address given for blacklist entry, src: %s, dst: %s" % (src,dst)







if __name__ == '__main__':
    smc.login('http://172.18.1.150:8082', 'EiGpKD4QxlLJ25dbBEp20001')
    sg_vm = smc.search.filter_by_type('fw_cluster', 'sg_vm')
    link = smc.search.get_element_by_href(sg_vm['href'])
    pprint(link['link'])
    blacklist_add('1.1.1.1', '0.0.0.0')
    smc.logout()