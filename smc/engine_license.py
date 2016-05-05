import smc
import logging
from smc.operationfailure import OperationFailure

logger = logging.getLogger(__name__)

def get_dynamic_license():
    """ Check for unbound dynamic licenses or return None """
    licenses = smc.search.get_element_by_entry_point('licenses')
    license_id = None 
    for l in licenses['license']:
        if l['bindings'] == 'dynamic' and l['binding_state'] == 'Unassigned':
            logger.debug("Found a dynamic license; License_info: %s" % l)
            license_id = l['license_id']
            break
    if license_id:
        return license_id
    else:
        logger.error("No dynamic licenses were found. Cannot license security engine")
        
def bind_license(node_bind_license_href, license_id=None):
    """ Bind license using dynamic license, or set license_id. For hardware FW's with
    a POS, call fetch_license with POST instead. It will retrieve it's license from SMC """
    license_id = get_dynamic_license()
    t = { 'license_id' : license_id }
    try:
        smc.web_api.http_post(node_bind_license_href, t)
    except OperationFailure, e:
        print "Error binding license: %s" % e.msg
    