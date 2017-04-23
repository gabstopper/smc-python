# -*- coding: utf-8 -*-
""" 
Shortcut API to access common operations done by the SMC python API. 

Each function defined is specifically for creating certain object types, engines,
interfaces, routes, policies, etc.

Input validation is done to ensure the correct fields are provided and that 
they are the right type. In addition, in some cases 
other objects will need to be retrieved as a reference to create another object. 
If these references are not resolvable, the create operation can fail. This will do the up
front validation and interact with the SMC operations.

In order to view error messages, do the following in your calling script::

    import logging
    logging.getLogger()
    logging.basicConfig(level=logging.ERROR, format='%(asctime)s %(levelname)s: %(message)s')
    
"""
import logging
import smc.elements.network as network
import smc.elements.service as service
import smc.elements.group as group
import smc.actions.search
from smc.core.engines import Layer3Firewall, Layer2Firewall, IPS
from smc.core.engine import Engine
from smc.elements.helpers import logical_intf_helper

logger = logging.getLogger(__name__)


def host(name, ipaddress, secondary_ip=[], comment=None):
    """ Create host object

    :param name: name, must be unique
    :param ipaddress: ip address of host
    :param secondary_ip[] (optional): additional IP for host
    :param comment (optional)
    :return: :py:class:`smc.api.web.SMCResult`
    """
    return network.Host.create(name, ipaddress,
                               secondary_ip=secondary_ip,
                               comment=comment).create()


def iprange(name, addr_range, comment=None):
    """ Create iprange object

    :param name: name for object
    :param addr_range: ip address range, i.e. 1.1.1.1-1.1.1.10
    :param comment (optional)
    :return: :py:class:`smc.api.web.SMCResult`
    """
    addr = addr_range.split('-')  # just verify each side is valid ip addr
    if len(addr) == 2:  # has two parts
        return network.AddressRange.create(name, addr_range,
                                           comment=comment).create()


def router(name, ipaddress, secondary_ip=None, comment=None):
    """ Create router element

    :param name: name for object
    :param ipaddress: ipv4 address
    :param comment (optional)
    :return: :py:class:`smc.api.web.SMCResult`
    """
    return network.Router.create(name, ipaddress,
                                 secondary_ip=secondary_ip,
                                 comment=comment).create()


def network(name, ip_network, comment=None):
    """ Create network element

    :param name: name for object
    :param ip_network: ipv4 address in cidr or full netmask format (1.1.1.1/24, or 1.1.1.0/255.255.0.0)
    :param comment (optional)
    :return: :py:class:`smc.api.web.SMCResult`
    """
    return network.Network.create(name, ip_network,
                                  comment=comment).create()


def group(name, members=[], comment=None):
    """ Create group element, optionally with members
    Members must already exist in SMC. Before being added to the group a search will be 
    performed for each member specified.
    blah

    :param name: name for object
    :param members: list; i.e. ['element1', 'element2', etc]. Most elements can be used in a group
    :param comment: (optional)
    :return: :py:class:`smc.api.web.SMCResult`
    """
    grp_members = []
    if members:
        for m in members:  # add each member
            found_member = smc.actions.search.element_href(m)
            if found_member:
                logger.debug("Found member: %s, adding to group" % m)
                grp_members.append(found_member)
                continue
            else:
                logger.info(
                    "Element: %s could not be found, not adding to group" % m)

    return group.Group.create(name,
                              members=grp_members,
                              comment=comment).create()


def single_fw(name, mgmt_ip, mgmt_network, mgmt_interface='0', dns=None):
    """ Create single firewall with a single management interface

    :param name: name of single layer 2 fw
    :param mgmt_ip: ip address for management layer 3 interface
    :param mgmt_network: netmask for management network
    :param mgmt_interface: interface id for l3 mgmt
    :param dns: dns servers for management interface (optional)
    :return: :py:class:`smc.core.engine.Engine`
    """
    result = Layer3Firewall.create(name, mgmt_ip, mgmt_network,
                                   mgmt_interface=mgmt_interface,
                                   domain_server_address=dns)
    return result


def single_layer2(name, mgmt_ip, mgmt_network, mgmt_interface='0', inline_interface='1-2',
                  logical_interface='default_eth', dns=None):
    """ Create single layer 2 firewall 
    Layer 2 firewall will have a layer 3 management interface and initially needs atleast 
    one inline or capture interface.

    :param name: name of single layer 2 fw
    :param mgmt_ip: ip address for management layer 3 interface
    :param mgmt_network: netmask for management network
    :param mgmt_interface: interface id for l3 mgmt
    :param inline_interface: int specifying interface id's to be used for inline interfaces (default: [1-2])
    :param logical_interface: name of logical interface, must be unique if using capture and inline interfaces
    :param dns: dns servers for management interface (optional)
    :return: :py:class:`smc.core.engine.Engine`
    """
    result = Layer2Firewall.create(name, mgmt_ip, mgmt_network,
                                   mgmt_interface=mgmt_interface,
                                   inline_interface=inline_interface,
                                   logical_interface=logical_intf_helper(
                                       logical_interface),
                                   domain_server_address=dns)
    return result


def single_ips(name, mgmt_ip, mgmt_network, mgmt_interface='0', inline_interface='1-2',
               logical_interface='default_eth', dns=None):
    """ Create single IPS 
    :param name: name of single layer 2 fw
    :param mgmt_ip: ip address for management layer 3 interface
    :param mgmt_network: netmask for management network
    :param mgmt_interface: interface id for l3 mgmt
    :param inline_interface: int specifying interface id's to be used for inline interfaces (default: [1-2])
    :param logical_interface: name of logical interface, must be unique if using capture and inline interfaces
    :param dns: dns servers for management interface (optional)
    :return: :py:class:`smc.core.engine.Engine`
    """
    result = IPS.create(name, mgmt_ip, mgmt_network,
                        mgmt_interface=mgmt_interface,
                        inline_interface=inline_interface,
                        logical_interface=logical_intf_helper(
                            logical_interface),
                        domain_server_address=dns)
    return result


def l3interface(name, ipaddress, ip_network, interfaceid):
    """ Add L3 interface for single FW

    :param l3fw: name of firewall to add interface to
    :param ip: ip of interface
    :param network: network for ip
    :param interface_id: interface_id to use
    :return: :py:class:`smc.api.web.SMCResult`
    :raises: LoadEngineFailed
    """
    engine = Engine(name).load()
    result = engine.physical_interface.add_single_node_interface(
        interface_id=interfaceid,
        address=ipaddress,
        network_value=ip_network)
    return result


def l2interface(name, interface_id, logical_interface_ref='default_eth', zone=None):
    """ Add layer 2 inline interface   
    Inline interfaces require two physical interfaces for the bridge and a logical 
    interface to be assigned. By default, interface 1,2 will be used if interface_id is 
    not specified. 
    The logical interface is used by SMC for policy to logically group both interfaces
    It is not possible to have inline and capture interfaces on the same node with the
    same logical interface definition. Automatically create logical interface if it does
    not already exist.

    :param node: node name to add inline interface pair
    :param interface_id [], int values of interfaces to use for inline pair (default: 1,2)
    :param logical_int: logical interface name to map to inline pair (default: 'default_eth')
    :return: :py:class:`smc.api.web.SMCResult`
    :raises: LoadEngineFailed
    """
    engine = Engine(name).load()
    result = engine.physical_interface.add_inline_interface(
        interface_id=interface_id,
        logical_interface_ref=logical_intf_helper(
            logical_interface_ref))
    return result


def capture_interface(name, interface_id, logical_interface_ref='default_eth', zone=None):
    """ Add a capture interface. 
    Capture interfaces can only be added to Layer 2 Firewall or IPS roles.

    :param name: name of layer2 fw or ips to add to
    :param logical_interface_ref: logical interface, will find ref and create if it doesnt exist
    :param zone: optional zone name
    :return: :py:class:`smc.qpi.web.SMCResult`
    :raises: LoadEngineFailed
    """
    engine = Engine(name).load()
    result = engine.physical_interface.add_capture_interface(interface_id=interface_id,
                                                             logical_interface_ref=logical_intf_helper(
                                                                 logical_interface_ref))
    return result


def l3route(name, gateway, ip_network):
    """ Add route to l3fw 
    This could be added to any engine type. Non-routable engine roles (L2/IPS) may
    still require route/s defined on the L3 management interface   

    :param l3fw: name of firewall to add route
    :param gw: next hop router object
    :param ip_network: next hop network behind gw
    :return: :py:class:`smc.qpi.web.SMCResult`
    """
    engine = Engine(name).load()
    return engine.add_route(gateway, ip_network)


def blacklist(name, src, dst, duration=3600):
    """ Add blacklist entry to engine node by name

    :param name: name of engine node or cluster
    :param src: source to blacklist, can be /32 or network cidr
    :param dst: dest to deny to, 0.0.0.0/32 indicates all destinations
    :param duration: how long to blacklist in seconds
    :return: :py:class:`smc.api.web.SMCResult`
    """
    engine = Engine(name).load()
    return engine.blacklist(src, dst, duration)


def blacklist_flush(name):
    """ Flush entire blacklist for node name

    :param name: name of node or cluster to remove blacklist
    :return: None
    :raises: EngineCommandFailed
    """
    engine = Engine(name).load()
    return engine.blacklist_flush()


def bind_license(name):
    """
    Bind license on single node engine

    :param name: name of engine
    :return: None
    :raises: LoadEngineFailed, NodeCommandFailed
    """
    engine = Engine(name).load()
    for node in engine.nodes:
        return node.bind_license()


def unbind_license(name):
    """
    Unbind license on single node engine

    :param name: name of engine
    :return: None
    :raises: LoadEngineFailed, NodeCommandFailed
    """
    engine = Engine(name).load()
    for node in engine.nodes:
        return node.unbind_license()


def cluster_fw(data):
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
    pass
