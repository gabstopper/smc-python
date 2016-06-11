import pkg_resources, json, os
import logging
import ipaddress

logger = logging.getLogger(__name__)


def get_json_template(template_name):
    """ Get the json template file specified as template name
    Used for element templates
    :param template_name: name of template
    :return json of template, None if error
    """
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
    """ Is the ipv4 provided valid
    :param ipaddr: ip address provided
    :return True if valid, None otherwise
    """
    #TODO: python 2.x ipaddress module needs unicode string, python 2 convert from binary 
    try:
        if ipaddress.IPv4Address(ipaddr.decode('utf-8')): #python 2.x
            return True
    except Exception, e:
        logger.error(e.message.replace("u'","'"))
    return None
    
def is_ipaddr_in_network(host_ip, network):
    """ Check if host ip is in the network specified
    :param host_ip: host ip address provided
    :param network: network address provided
    :return True if valid, None if error
    """
    try:
        if ipaddress.ip_address(host_ip.decode('utf-8')) in ipaddress.ip_network(network.decode('utf-8')):
            return True
    except Exception, e:
        logger.error(e.message.replace("u'","'"))
    return None
           
def ipaddr_as_network(net_addr):
    """ Get ipaddr as network cide
    Network can be 255.255.255.0 or /24 formats 
    :params net_addr: network address, either 1.1.1.1/255.255.255.0, or 1.1.1.1./24
    :return Validated address in CIDR format or None if invalid
    """
    try :
        return ipaddress.ip_network(net_addr.decode('utf-8')).exploded
    except Exception, e:
        logger.error(e.message.replace("u'","'"))
    return None
