""""
Module that represents server based configurations
"""
from smc.base.model import prepared_request
from smc.elements.helpers import location_helper
from smc.base.model import Element
from smc.api.exceptions import ModificationFailed
from smc.elements.other import ServerContactAddress


class ServerCommon(object):
    def contact_addresses(self):
        """
        View contact addresses for this management server. To add contact
        addresses, call :py:func:`add_contact_address`

        :return: contact addresses in format {location_ref,addresses}
        :rtype: list(dict)
        """
        result = self._resource.get('contact_addresses')
        if result:
            return [ServerContactAddress(addresses)
                    for addresses in result.get('multi_contact_addresses')]
        return []

    def add_contact_address(self, contact_address, location):
        """
        Add a contact address to the Log Server::

            server = LogServer('LogServer 172.18.1.25')
            server.add_contact_address('44.44.44.4', 'ARmoteLocation')

        :param str contact_address: IP address used as contact address
        :param str location: Name of location to use, will be created if
               it doesn't exist
        :raises ModificationFailed: failed adding contact address
        :return: None
        """
        href = self._resource.contact_addresses
        existing = self._resource.get(href, as_smcresult=True)
        addresses = _add_contact_address(
            existing.json,
            ServerContactAddress.create(contact_address, location))

        prepared_request(
            ModificationFailed,
            href=href,
            json=addresses,
            etag=existing.etag
        ).update()

    def remove_contact_address(self, location):
        """
        Remove contact address by name of location. You can obtain all contact
        addresses by calling :func:`contact_addresses`.

        :param str location: href of location
        :raises ModificationFailed: failed removing contact address
        :return: None
        """
        href = self._resource.contact_addresses
        existing = self._resource.get(href, as_smcresult=True)
        if existing:
            location_ref = location_helper(location)
            addresses = _remove_contact_address(existing.json, location_ref)

            prepared_request(
                ModificationFailed,
                href=href,
                json=addresses,
                etag=existing.etag
            ).update()


class ManagementServer(ServerCommon, Element):
    """
    Management Server configuration. Most configuration settings are better set
    through the SMC UI, such as HA, however this object can be used to do simple
    tasks such as add a contact addresses to the Management Server when a security
    engine needs to communicate over NAT.

    It's easiest to get the management server reference through a collection::

        >>> list(Search('mgt_server').objects.all())
        [ManagementServer(name=Management Server)]

    Or load it directly if the name is known and show any contact addresses::

        mgmt = ManagementServer('Management Server')
        mgmt.contact_addresses()

    :param name: name of management server
    """
    typeof = 'mgt_server'

    def __init__(self, name, **meta):
        super(ManagementServer, self).__init__(name, **meta)
        pass


class LogServer(ServerCommon, Element):
    """
    Log Server elements are used to receive log data from the security engines
    Most settings on Log Server generally do not need to be changed, however it
    may be useful to set a contact address location and IP mapping if the Log Server
    needs to be reachable from an engine across NAT

     It's easiest to get the management server reference through a collection::

        >>> list(Search('log_server').objects.all())
        [LogServer(name=LogServer 172.18.1.150)]

    Or load it directly if the name is known::

        >>> server = LogServer('LogServer 172.18.1.150')
        >>> print(server.contact_addresses())
        ...
    """
    typeof = 'log_server'

    def __init__(self, name, **meta):
        super(LogServer, self).__init__(name, **meta)
        pass


def _add_contact_address(existing, new):
    """
    Add contact address
    :param dict existing: raw json from call to contact_addresses
    :param new ServerContactAddress
    :rtype: dict
    """
    if existing:
        added = False  # Added to existing?
        for addresses in existing['multi_contact_addresses']:
            if addresses.get('location_ref') == new.location_ref:
                addresses.get('addresses').append(new.addresses[0])
                added = True
                break
        if not added:
            existing['multi_contact_addresses'].append(new.data)
    else:
        existing = {'multi_contact_addresses': [new.data]}

    return existing


def _remove_contact_address(existing, location):
    """
    Remove contact address 

    :param list addresses: existing contact addresses from call to
           contact_addresses()
    :param str location: location name to remove
    """
    addrlist = existing.get('multi_contact_addresses')
    addresses = [locations for locations in addrlist
                 if locations['location_ref'] != location]

    return {'multi_contact_addresses': addresses}
