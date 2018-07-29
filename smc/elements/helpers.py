"""
Helper functions to retrieve various elements that may be required by specific
constructors.
"""
from smc.elements.network import Zone
from smc.administration.system import AdminDomain
from smc.elements.other import LogicalInterface, Location
from smc.api.exceptions import ElementNotFound
from smc.base.collection import Search
    

def location_helper(name, search_only=False):
    """
    Location finder by name. If location doesn't exist, create it
    and return the href

    :param str,Element name: location to resolve. If the location is
        by name, it will be retrieved or created, if href, returned
        and if Location, href returned. If None, settings an elements
        location to None will set it to the Default location.
    :param bool search_only: only search for the location, if not found
        do not create
    :return str href: href of location if search_only is not False
    :rtype: str or None
    """ 
    try:
        return name.href
    except AttributeError:
        if name and name.startswith('http'):
            return name
    except ElementNotFound:
        return Location.create(name=name.name).href if not \
            search_only else None
        
    # Get all locations; tmp to support earlier 6.x versions.
    if name is not None:
        locations = [location for location in Search.objects.entry_point(
            'location') if location.name == name]
        if not locations:
            return Location.create(name=name).href if not search_only \
                else None
        return locations[0].href
        

def zone_helper(zone):
    """
    Zone finder by name. If zone doesn't exist, create it and
    return the href

    :param str zone: name of zone (if href, will be returned as is)
    :return str href: href of zone
    """
    if zone is None:
        return None
    elif isinstance(zone, Zone):
        return zone.href
    elif zone.startswith('http'):
        return zone
    return Zone.get_or_create(name=zone).href
    

def logical_intf_helper(interface):
    """
    Logical Interface finder by name. Create if it doesn't exist.
    This is useful when adding logical interfaces to for inline
    or capture interfaces.

    :param interface: logical interface name
    :return str href: href of logical interface
    """
    if interface is None:
        return LogicalInterface.get_or_create(name='default_eth').href
    elif isinstance(interface, LogicalInterface):
        return interface.href
    elif interface.startswith('http'):
        return interface
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