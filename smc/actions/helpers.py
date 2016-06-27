import ipaddress

import logging
logger = logging.getLogger(__name__)

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
        logger.error(e.message.replace("u'", "'"))
    return False

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
        logger.error(e.message.replace("u'", "'"))
    return False

def ipaddr_as_network(net_addr):
    """ Get ipaddr as network cide
    Network can be 255.255.255.0 or /24 formats 
    :params net_addr: network address, either 1.1.1.1/255.255.255.0, or 1.1.1.1./24
    :return Validated address in CIDR format or None if invalid
    """
    try:
        return ipaddress.ip_network(net_addr.decode('utf-8')).exploded
    except Exception, e:
        logger.error(e.message.replace("u'", "'"))
    return None
