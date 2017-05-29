"""
Search module provides convenience methods for retrieving specific data from
the SMC. Each method will return data in a certain way with different inputs.
All methods are using :mod:`smc.api.common` methods which wrap any exceptions
and if there are no results, most functions return either None or empty list,
depending on the data content retrieved. See each function documentation for
most information.

Example of retrieving an SMC element by name, as json::

    smc.actions.search.element_as_json('myelement')

Element as json with etag (etag is required for modifications)::

    smc.actions.search.element_as_json_with_etag('myelement')

Get element reference::

    smc.actions.search.element_href('myelement')

All elements by type::

    smc.actions.search.all_elements_by_type('host')
"""
import logging
from smc.api.common import fetch_href_by_name, fetch_json_by_href,\
    fetch_json_by_name, fetch_entry_point, fetch_json_by_post
from smc import session
from smc.api.exceptions import UnsupportedEntryPoint

logger = logging.getLogger(__name__)


def element(name):
    """ Convenience method to get element href by name

    :param name: name of element
    :return: href of element, else None
    :rtype: str,None
    """
    if name:
        return element_href(name)


def element_href(name):
    """ Get specified element href by element name

    :param name: name of element
    :return: string href location of object, else None
    """
    if name:
        element = fetch_href_by_name(name)
        if element.href:
            return element.href


def element_as_json(name):
    """ Get specified element json data by name

    :param name: name of element
    :return: json data representing element, else None
    """
    if name:
        element = fetch_json_by_name(name)
        if element.json:
            return element.json


def element_as_json_with_filter(name, _filter):
    """
    Get specified element json data by name with filter.
    Filter can be any valid element type.

    :param name: name of element
    :param _filter: element filter, host, network, tcp_service,
                    network_elements, services, services_and_applications, etc
    :return: json data representing element, else None
    """
    if name:
        element_href = element_href_use_filter(name, _filter)
        if element_href:
            return element_by_href_as_json(element_href)


def element_as_json_with_etag(name):
    """ Convenience method to return SMCResult that
    holds href, etag and json in result object

    :param name: name of element
    :return: :py:class:`smc.api.web.SMCResult`, else None
    """
    return element_as_smcresult(name)


def element_info_as_json(name):
    """
    Get specified element META data based on search query
    This is the base level search that returns basic object info
    with the following attributes:

    * href: link to element
    * name: name of element
    * type: type of element

    :param str name: name of element
    :return: list dict with meta (href, name, type) if found, otherwise None
    """
    if name:
        element = fetch_href_by_name(name)
        if element.json:
            return element.json


def element_info_as_json_with_filter(name, _filter):
    """
    Top level json meta data (href, name, type) for element

    :param str name: name of element
    :param str _filter: filter of entry point
    :return: list dict with metadata, otherwise None
    """
    if name and _filter:
        element = fetch_href_by_name(name, filter_context=_filter)
        if element.json:
            return element.json


def element_href_use_wildcard(name):
    """ Get element href using a wildcard rather than matching only on the name
    field. This will likely return multiple results.

    :param name: name of element
    :return: list of matched elements
    """
    if name:
        element = fetch_href_by_name(name, exact_match=False)
        return element.json


def element_href_use_filter(name, _filter):
    """ Get element href using filter

    Filter should be a valid entry point value, ie host, router, network,
    single_fw, etc

    :param name: name of element
    :param _filter: filter type, unknown filter will result in no matches
    :return: element href (if found), else None
    """
    if name and _filter:
        element = fetch_href_by_name(name, filter_context=_filter)
        if element.json:
            return element.json.pop().get('href')


def element_by_href_as_json(href, params=None):
    """ Get specified element by href

    :param href: link to object
    :param params: optional search query parameters
    :return: json data representing element, else None
    """
    if href:
        element = fetch_json_by_href(href, params=params)
        if element:
            return element.json


def element_name_by_href(href):
    """
    The element href is known, possibly from a reference in an
    elements json. You want to retrieve the name of this element.

    :param str href: href of element
    :return: str name of element, or None
    """
    if href:
        element = fetch_json_by_href(href)
        if element.json:
            return element.json.get('name')


def element_name_and_type_by_href(href):
    """
    Retrieve the element name and type of element based on the href.
    You may have a href that is within another element reference and
    want more information on that reference.

    :param str href: href of element
    :return: tuple (name, type)
    """
    if href:
        element = fetch_json_by_href(href)
        if element.json:
            for entries in element.json.get('link'):
                if entries.get('rel') == 'self':
                    typeof = entries.get('type')

            return (element.json.get('name'),
                    typeof)


def element_attribute_by_href(href, attr_name):
    """
    The element href is known and you want to retrieve a specific
    attribute from that element.

    For example, if you want a specific attribute by it's name::

        search.element_attribute_by_href(href_to_resource, 'name')

    :param str href: href of element
    :param str attr_name: name of attribute
    :return: str value of attribute
    """
    if href:
        element = fetch_json_by_href(href)
        if element.json:
            return element.json.get(attr_name)


def element_by_href_as_smcresult(href, params=None):
    """ Get specified element returned as an SMCResult object

    :param href: href direct link to object
    :return: :py:class:`smc.api.web.SMCResult` with etag, href and
             element field holding json, else None
    """
    if href:
        element = fetch_json_by_href(href, params=params)
        if element:
            return element


def element_as_smcresult(name):
    """ Get specified element returned as an SMCResult object

    :param name: name of object
    :return: :py:class:`smc.api.web.SMCResult`, else None
    """
    if name:
        element = fetch_json_by_name(name)
        if element:
            return element


def element_as_smcresult_use_filter(name, _filter):
    """ Return SMCResult object and use search filter to
    find object

    :param name: name of element to find
    :param _filter: filter to use, i.e. tcp_service, host, etc
    :return: :py:class:`smc.api.web.SMCResult`
    """
    if name:
        element = fetch_href_by_name(name, filter_context=_filter)
        if element.msg:
            return element
        if element.json:
            return element_by_href_as_smcresult(element.json.pop().get('href'))


def element_href_by_batch(list_to_find, filter=None):  # @ReservedAssignment
    """ Find batch of entries by name. Reduces number of find calls from
    calling class.

    :param list list_to_find: list of names to find
    :param filter: optional filter, i.e. 'tcp_service', 'host', etc
    :return: list: {name: href, name: href}, href may be None if not found
    """
    try:
        if filter:
            return [{k: element_href_use_filter(k, filter)
                     for k in list_to_find}]
        return [{k: element_href(k) for k in list_to_find}]
    except TypeError:
        logger.error("{} is not iterable".format(list_to_find))


def all_elements_by_type(name):
    """ Get specified elements based on the entry point verb from SMC api
    To get the entry points available, you can get these from the session::

        session.cache.entry_points

    Execution will get the entry point for the element type, then get all
    elements that match.

    For example::

        search.all_elements_by_type('host')

    :param name: top level entry point name
    :raises: `smc.api.exceptions.UnsupportedEntryPoint`
    :return: list with json representation of name match, else None
    """
    if name:
        entry = element_entry_point(name)
        if entry:  # in case an invalid entry point is specified
            result = element_by_href_as_json(entry)
            return result


def all_entry_points():  # get from session cache
    """ Get all SMC API entry points """
    return session.entry_points.all()


def element_entry_point(name):
    """ Get specified element from cache based on the entry point verb from
    SMC api. To get the entry points available, you can call
    ``session.cache.entry_points``
    For example::

        element_entry_point('log_server')

    :param name: top level entry point name
    :return: href: else None
    """
    if name:
        try:
            return fetch_entry_point(name)
        except UnsupportedEntryPoint:
            pass


def search_unused():
    """ Search for all unused elements
    :return: list of dict items holding href,type and name
    """
    return element_by_href_as_json(fetch_entry_point('search_unused'))


def search_duplicate():
    """ Search for duplicate IP address elements.
    It is also possible to filter the search by name, comment, or IP address

    :return: list of dict items holding href,type and name
    """
    return element_by_href_as_json(fetch_entry_point('search_duplicate'))


def element_references(element_href):
    """
    Return references for an element given the element href. The result is
    filtered based on the SMCResult. If error, empty list is returned

    :param str element_href: element reference
    :return: list list of references where element is used
    """
    href = fetch_entry_point('references_by_element')
    result = fetch_json_by_post(href=href,
                                json={'value': element_href})
    if result.json:
        return result.json
    return []


def element_references_as_smcresult(element_href):
    """
    Return references for an element given the element href. The
    return is the full SMCResult object.

    :param str element_href: element reference
    :return: :py:class:`smc.api.web.SMCResult`
    """
    href = fetch_entry_point('references_by_element')
    return fetch_json_by_post(href=href,
                              json={'value': element_href})


def get_ospf_default_profile():
    """ Convenience method to return the href of the ospf default
    profile

    :return: href of ospf default profile
    """
    profiles = all_elements_by_type('ospfv2_profile')
    if profiles:
        for ospf in profiles:
            profile = element_by_href_as_json(ospf.get('href'))
            if profile.get('system') is True:
                return ospf.get('href')
