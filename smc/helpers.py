import pkg_resources, json, os
import ipaddress
import logging
from ipaddress import AddressValueError

logger = logging.getLogger(__name__)

#TODO: Test fail here
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
    #TODO: python 2.x ipaddress module didnt differentiate string types so convert str to unicode. Py3
    #does not have this problem. Maybe check python version first or require the py2-ipaddress backport
    #ipv4 = mgmt_ip.decode('utf-8')
    try:
        if ipaddress.IPv4Address(ipaddr.decode('utf-8')): #python 2.x
            return True
    except Exception, e:
        logger.error(e)
    
def is_ipaddr_in_network(host_ip, network):
    try:
        if ipaddress.ip_address(host_ip.decode('utf-8')) in ipaddress.ip_network(network.decode('utf-8')):
            return True
    except Exception, e:
        logger.error(e)
           
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
    network = None
    try :
        network = ipaddress.ip_network(net_addr.decode('utf-8'))
    except Exception, e:
        logger.error("Error converting network address: %s, msg: %s" % (net_addr,e))
        return
    return network.exploded