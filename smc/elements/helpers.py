"""
Helper functions to retrieve various elements that may be required by specific
constructors.
"""
import smc.actions.search as search
from smc.elements.network import Zone
from smc.elements.other import LogicalInterface, Location
from smc.api.exceptions import ElementNotFound


def location_helper(name):
    """
    Location finder by name. If location doesn't exist, create it
    and return the href

    :param str name
    :return str href: href of location
    """
    location = None
    try:  # SMC >= 6.1.1, locations now searchable
        location = Location(name).href
    except ElementNotFound:
        location_lst = [x
                        for x in search.all_elements_by_type('location')
                        if x.get('name') == name]
        # SMC <= SMC 6.1
        if location_lst:
            location = location_lst[0].get('href')
    if location:
        return location
    else:
        return Location.create(name).href


def zone_helper(zone):
    """
    Zone finder by name. If zone doesn't exist, create it and
    return the href

    :param str zone: name of zone
    :return str href: href of zone
    """
    zone_ref = search.element_href_use_filter(zone, 'interface_zone')
    if zone_ref:
        return zone_ref
    else:
        return Zone.create(zone).href


def logical_intf_helper(interface):
    """
    Logical Interface finder by name. Create if it doesn't exist

    :param interface: logical interface name
    :return str href: href of logical interface
    """
    intf_ref = search.element_href_use_filter(interface, 'logical_interface')
    if intf_ref:
        return intf_ref
    else:
        return LogicalInterface.create(interface)


def domain_helper(name):
    """
    Find a domain based on name

    :return: href of domain
    :rtype: str
    """
    domain = search.element_href_use_filter(name, 'admin_domain')
    if domain:
        return domain
