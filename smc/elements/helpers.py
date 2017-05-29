"""
Helper functions to retrieve various elements that may be required by specific
constructors.
"""
from smc.elements.network import Zone
from smc.elements.other import LogicalInterface, Location, AdminDomain
from smc.api.exceptions import ElementNotFound
from smc.api.common import fetch_no_filter


def location_helper(name):
    """
    Location finder by name. If location doesn't exist, create it
    and return the href

    :param str name
    :return str href: href of location
    """
    locations = [Location(**location) 
                 for location in fetch_no_filter('location', name)]
    if not locations:
        return Location.create(name=name).href
    return locations[0].href


def zone_helper(zone):
    """
    Zone finder by name. If zone doesn't exist, create it and
    return the href

    :param str zone: name of zone
    :return str href: href of zone
    """
    return Zone.get_or_create(name=zone).href


def logical_intf_helper(interface):
    """
    Logical Interface finder by name. Create if it doesn't exist

    :param interface: logical interface name
    :return str href: href of logical interface
    """
    return LogicalInterface.get_or_create(name=interface).href


def domain_helper(name):
    """
    Find a domain based on name

    :return: href of domain
    :rtype: str
    """
    try:
        return AdminDomain(name).href
    except ElementNotFound:
        pass