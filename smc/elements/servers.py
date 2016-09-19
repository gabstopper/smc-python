""""
Module that represents server based configurations
"""
import smc.actions.search as search
from smc.elements.util import find_link_by_name
from smc.elements.element import SMCElement, Meta

class ManagementServer(object):
    """
    Management Server configuration. Most configuration settings are better set
    through the SMC UI, such as HA, however this object can be used to do simple
    tasks such as add a contact addresses to the Management Server when a security
    engine needs to communicate over NAT.
    
    It's easiest to get the management server reference through a collection::
    
        for server in describe_management_servers():
            s = server.load()
            
    :param name: name of management server
    
    """
    def __init__(self, name, meta=None, **kwargs):
        self.name = name
        self.meta = meta
    
    def load(self):
        if not self.meta:
            self.meta = Meta(**search.element_info_as_json(self.name))
        result = search.element_by_href_as_smcresult(self.meta.href)
        if result:
            self.json = result.json
        return self
    
    @property
    def href(self):
        if self.meta:
            return self.meta.href
            
    @property
    def etag(self):
        if self.meta:
            return search.element_by_href_as_smcresult(self.meta.href).etag

    @property
    def link(self):
        if self.json:
            return self.json.get('link')
        else:
            raise AttributeError("You must call load on the Management Server "
                                 "before accessing resources.")

    def export(self):
        pass
    
    def search_category_tags_from_element(self):
        pass
        
    def contact_addresses(self):
        """
        View contact addresses for this management server. To add contact
        addresses, call :py:func:`add_contact_address`
        
        :return: contact address json
        """
        return search.element_by_href_as_json(
                    find_link_by_name('contact_addresses', self.link))

    def add_contact_address(self, contact_address):
        """
        Add a contact address to this management server::
        
            contact = ContactAddress(['123.123.123.123'], 
                                      location_helper('mylocation'))
            for server in describe_management_servers():
                s = server.load()
                s.add_contact_address(contact)
                
        :param contact_address: ContactAddress element
        :return: SMCResult
        """
        addresses = _add_contact_address(self.contact_addresses(), contact_address)
        return SMCElement(
                    href=find_link_by_name('contact_addresses', self.link),
                    json=addresses, etag=self.etag).update()

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, 'name={}'\
                           .format(self.name))
        
class LogServer(object):
    """
    Log Server elements are used to receive log data from the security engines
    Most settings on Log Server generally do not need to be changed, however it
    may be useful to set a contact address location and IP mapping if the Log Server
    needs to be reachable from an engine across NAT
    
    It's easiest to get a log server reference through a collection::
    
        for server in describe_log_servers():
            s = server.load()
    """
    def __init__(self, name, meta=None, **kwargs):
        self.name = name
        self.meta = meta
    
    def load(self):
        if not self.meta:
            self.meta = Meta(**search.element_info_as_json(self.name))
        result = search.element_by_href_as_smcresult(self.meta.href)
        if result:
            self.json = result.json
        return self
    
    @property
    def href(self):
        if self.meta:
            return self.meta.href
            
    @property
    def etag(self):
        if self.meta:
            return search.element_by_href_as_smcresult(self.meta.href).etag
        
    @property
    def link(self):
        if self.json:
            return self.json.get('link')
        else:
            raise AttributeError("You must call load on the Log Server before "
                                 "accessing resources.")

    def export(self):
        """
        :method: POST
        """
        pass
    
    def contact_addresses(self):
        return search.element_by_href_as_json(
                        find_link_by_name('contact_addresses', self.link))
    
    def add_contact_address(self, contact_address):
        """
        Add a contact address to the Log Server::
        
            contact = ContactAddress(['123.123.123.123'], 
                                      location_helper('mylocation'))
            for server in describe_management_servers():
                s = server.load()
                s.add_contact_address(contact)
        
        :param contact_address: ContactAddress element
        :return: SMCResult
        """
        addresses = _add_contact_address(self.contact_addresses(), contact_address)
        return SMCElement(
                    href=find_link_by_name('contact_addresses', self.link),
                    json=addresses, etag=self.etag).update()
    
    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, 'name={}'\
                           .format(self.name))
        
def _add_contact_address(addresses, contact_address):
    if addresses:
        addresses.get('multi_contact_addresses').append(contact_address.json)
    else:
        addresses = {'multi_contact_addresses':[]}
        addresses.get('multi_contact_addresses').append(contact_address.json)
    return addresses
            