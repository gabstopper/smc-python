""""
Module that represents server based configurations
"""
import smc.actions.search as search
from smc.elements.util import find_link_by_name
from smc.elements.element import ElementLocator
from smc.elements.helpers import location_helper
from smc.api.common import SMCRequest
from smc.elements.mixins import ExportableMixin, UnicodeMixin

class ManagementServer(UnicodeMixin, ExportableMixin):
    """
    Management Server configuration. Most configuration settings are better set
    through the SMC UI, such as HA, however this object can be used to do simple
    tasks such as add a contact addresses to the Management Server when a security
    engine needs to communicate over NAT.
    
    It's easiest to get the management server reference through a collection::
    
        for server in describe_management_servers():
            print server.name
    
    Or load it directly if the name is known::
    
        mgmt = ManagementServer('Management Server')
        print mgmt.contact_addresses()
            
    :param name: name of management server
    """
    typeof = 'mgt_server'
    href = ElementLocator()
    
    def __init__(self, name, meta=None):
        self.name = name
        self.meta = meta
            
    @property
    def etag(self):
        return search.element_by_href_as_smcresult(self.href).etag

    @property
    def link(self):
        result = search.element_by_href_as_json(self.href)
        return result.get('link')

    def search_category_tags_from_element(self):
        pass
        
    def contact_addresses(self):
        """
        View contact addresses for this management server. To add contact
        addresses, call :py:func:`add_contact_address`
       
        :return: list dict of contact addresses {location_ref,addresses}
        """
        result = search.element_by_href_as_json(
                                find_link_by_name('contact_addresses', self.link))
        if result:
            return result.get('multi_contact_addresses')
        else:
            return []

    def add_contact_address(self, contact_address, location):
        """
        Add a contact address to this management server::

            mgt = ManagementServer('Management Server')
            print mgt.add_contact_address('33.3.3.3', 'MyNewLocation')
                
        :param str contact_address: IP address used as contact address
        :param str location: Name of location to use, will be created if
               it doesn't exist
        :return: :py:class:`smc.api.web.SMCResult`
        """
        addresses = _add_contact_address(self.contact_addresses(), 
                                         contact_address=contact_address, 
                                         location=location)
        return SMCRequest(
                    href=find_link_by_name('contact_addresses', self.link),
                    json=addresses, etag=self.etag).update()

    def __unicode__(self):
        return u'{0}(name={1})'.format(self.__class__.__name__, self.name)
  
    def __repr__(self):
        return repr(unicode(self))
        
class LogServer(UnicodeMixin, ExportableMixin):
    """
    Log Server elements are used to receive log data from the security engines
    Most settings on Log Server generally do not need to be changed, however it
    may be useful to set a contact address location and IP mapping if the Log Server
    needs to be reachable from an engine across NAT
    
     It's easiest to get the management server reference through a collection::
    
        for server in describe_log_servers():
            print server.name
    
    Or load it directly if the name is known::
    
        server = LogServer('Log Server 1.1.1.1')
        print server.contact_addresses()
    """
    typeof = 'log_server'
    href = ElementLocator()
    
    def __init__(self, name, meta=None):
        self.name = name
        self.meta = meta

    @property
    def etag(self):
        return search.element_by_href_as_smcresult(self.href).etag
        
    @property
    def link(self):
        result = search.element_by_href_as_json(self.href)
        return result.get('link')

    def contact_addresses(self):
        """
        View contact addresses for this management server. To add contact
        addresses, call :py:func:`add_contact_address`
        
        :return: list dict of contact addresses {location_ref,addresses}
        """
        result = search.element_by_href_as_json(
                                find_link_by_name('contact_addresses', self.link))
        if result:
            return result.get('multi_contact_addresses')
        else:
            return []
    
    def add_contact_address(self, contact_address, location):
        """
        Add a contact address to the Log Server::
        
            server = LogServer('LogServer 172.18.1.25')
            print server.add_contact_address('44.44.44.4', 'ARmoteLocation')
        
        :param str contact_address: IP address used as contact address
        :param str location: Name of location to use, will be created if
               it doesn't exist
        :return: :py:class:`smc.api.web.SMCResult`
        """
        addresses = _add_contact_address(self.contact_addresses(), 
                                         contact_address=contact_address,
                                         location=location)
        return SMCRequest(
                    href=find_link_by_name('contact_addresses', self.link),
                    json=addresses, etag=self.etag).update()
    
    def __unicode__(self):
        return u'{0}(name={1})'.format(self.__class__.__name__, self.name)
  
    def __repr__(self):
        return repr(unicode(self))
        
def _add_contact_address(addresses, contact_address, location):
    """
    :param addresses: existing contact addresses from call to 
           contact_addresses()
    :param str contact_address: contact address provided for server
    :param str location: location of element, created if it doesnt exist
    """
    location_ref = location_helper(location)
    addr = {'addresses': [contact_address],
            'location_ref': location_ref}
    
    if addresses:
        addresses.get('multi_contact_addresses').append(addr)
    else:
        addresses = {'multi_contact_addresses':[]}
        addresses.get('multi_contact_addresses').append(addr)
    return addresses
            