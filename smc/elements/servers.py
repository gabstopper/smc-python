""""
Module that represents server based configurations
"""
from smc.base.model import prepared_request
from smc.elements.helpers import location_helper
from smc.base.model import Element
from smc.api.exceptions import ModificationFailed

class ManagementServer(Element):
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

    def search_category_tags_from_element(self):
        pass
        
    def contact_addresses(self):
        """
        View contact addresses for this management server. To add contact
        addresses, call :py:func:`add_contact_address`
       
        :return: list dict of contact addresses {location_ref,addresses}
        """
        result = self.resource.get('contact_addresses')
        if result:
            return result.get('multi_contact_addresses')
        else:
            return []
        
    def add_contact_address(self, contact_address, location):
        """
        Add a contact address to this management server::

            >>> from smc.elements.servers import ManagementServer
            >>> mgmt = ManagementServer('Management Server')
            >>> print(mgmt.contact_addresses())
            ...
                
        :param str contact_address: IP address used as contact address
        :param str location: Name of location to use, will be created if
               it doesn't exist
        :raises: :py:class:`smc.api.exceptions.ModificationFailed`
        :return: None
        """
        addresses = _add_contact_address(self.contact_addresses(), 
                                         contact_address=contact_address, 
                                         location=location)
        prepared_request(ModificationFailed,
                         href=self.resource.contact_addresses,
                         json=addresses, etag=self.etag
                         ).update()

    def remove_contact_address(self, location):
        """
        Remove contact address by name of location. You can obtain all contact
        addresses by calling :py:func:`contact_addresses`.
        
        :param str location: href of location
        :raises: :py:class:`smc.api.exceptions.ModificationFailed`
        :return: None
        """
        json = _remove_contact_address(self.contact_addresses(), location)
        
        prepared_request(ModificationFailed,
                         href=self.resource.contact_addresses,
                         json=json, etag=self.etag
                         ).update()
        
class LogServer(Element):
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

    def contact_addresses(self):
        """
        View contact addresses for this management server. To add contact
        addresses, call :py:func:`add_contact_address`
        
        :return: list dict of contact addresses {location_ref,addresses}
        """
        result = self.resource.get('contact_addresses')
        if result:
            return result.get('multi_contact_addresses')
        else:
            return []
    
    def add_contact_address(self, contact_address, location):
        """
        Add a contact address to the Log Server::
        
            server = LogServer('LogServer 172.18.1.25')
            server.add_contact_address('44.44.44.4', 'ARmoteLocation')
        
        :param str contact_address: IP address used as contact address
        :param str location: Name of location to use, will be created if
               it doesn't exist
        :raises: :py:class: `smc.api.exceptions.ModificationFailed`
        :return: None
        """
        addresses = _add_contact_address(self.contact_addresses(), 
                                         contact_address=contact_address,
                                         location=location)
        prepared_request(ModificationFailed,
                         href=self.resource.contact_addresses,
                         json=addresses, etag=self.etag
                         ).update()
    
    def remove_contact_address(self, location):
        """
        Remove contact address by name of location. You can obtain all contact
        addresses by calling :py:func:`contact_addresses`.
        
        :param str location: href of location
        :raises: :py:class: `smc.api.exceptions.ModificationFailed`
        :return: None
        """
        json = _remove_contact_address(self.contact_addresses(), location)
        
        prepared_request(ModificationFailed,
                         href=self.resource.contact_addresses,
                         json=json, etag=self.etag
                         ).update()
                    
def _add_contact_address(addresses, contact_address, location):
    """
    :param list addresses: existing contact addresses from call to 
           contact_addresses()
    :param str contact_address: contact address provided for server
    :param str location: location of element, created if it doesnt exist
    """
    location_ref = location_helper(location)
    addr = {'addresses': [contact_address],
            'location_ref': location_ref}
    
    addresses = [] if not addresses else addresses
    addresses.append(addr)
    return {'multi_contact_addresses': addresses}

def _remove_contact_address(addresses, location):
    """
    Remove contact address 
    
    :param list addresses: existing contact addresses from call to
           contact_addresses()
    :param str location: location name to remove
    """
    addresses = [locations for locations in addresses 
                 if locations['location_ref'] != location]
        
    return {'multi_contact_addresses': addresses}
            