import pkg_resources, json, os
import logging
import ipaddress

logger = logging.getLogger(__name__)


def get_json_template(template_name):
    resource_package = __name__  ## this is so files can be retrieved when in egg
    resource_path = os.path.join('/elements/templates', template_name)
    template = pkg_resources.resource_string(resource_package, resource_path)
    
    v = None
    try:
        v = json.loads(template)
    except ValueError, e:
        logger.error("Exception occurred when loading json template: %s. ValueError was: %s" % (template, e))
    return v
 
def is_valid_ipv4(ipaddr):
    #TODO: python 2.x ipaddress module needs unicode string, python 2 convert from binary 
    try:
        if ipaddress.IPv4Address(ipaddr.decode('utf-8')): #python 2.x
            return True
    except Exception, e:
        logger.error(e.message.replace("u'","'"))
    return None
    
def is_ipaddr_in_network(host_ip, network):
    try:
        if ipaddress.ip_address(host_ip.decode('utf-8')) in ipaddress.ip_network(network.decode('utf-8')):
            return True
    except Exception, e:
        logger.error(e.message.replace("u'","'"))
    return None
           
def ipaddr_as_network(net_addr):
    """ network can be 255.255.255.0 or /24 formats 
        Args:
            * net_addr: network address, either 1.1.1.1/255.255.255.0, or 1.1.1.1./24
        Returns:
            Validated address in CIDR format
            None if invalid
        Raises: 
            ValueError if host bits set do not fall into cidr
    """
    try :
        return ipaddress.ip_network(net_addr.decode('utf-8')).exploded
    except Exception, e:
        logger.error(e.message.replace("u'","'"))
    return None
