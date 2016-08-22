from smc.elements.element import SMCElement
import smc.actions.search as search
from smc.api.web import SMCException, LoadPolicyFailed, CreatePolicyFailed,\
    CreateElementFailed
from smc.elements.helpers import find_link_by_name

class ExternalGateway(object):
    """
    ExternalGateway defines an endpoint used in a VPN tunnel. This will specify
    details such as the endpoint IP, enabled, balancing mode, etc. 
    This is required for non-SMC managed FW instances. 
    
    Create the external gateway and add required attributes::
    
      external_gateway = ExternalGateway.create('mygateway')
      
    :ivar: gateway_profile
    :ivar: name
    :ivar: trust_all_cas: True|False
    
    """
    def __init__(self, name=None, **kwargs):
        self.name = name
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    @classmethod
    def create(cls, name, trust_all_cas=True):
        """ 
        :param str name: name of external gateway
        :param boolean trust_all_cas: whether to trust all internal CA's
               (default: True)
        """
        data = {'name': name,
                'trust_all_cas': trust_all_cas }
        
        href = search.element_entry_point('external_gateway')
        result = SMCElement(href=href, json=data).create()
        if result.href:
            return ExternalGateway(name).load()
        else:
            raise CreateElementFailed('Failed creating external gateway, '
                                      'reason: {}'.format(result.msg))

    def load(self):
        external_gateway = search.element_as_json_with_filter(
                                        self.name, 'external_gateway')
        if external_gateway:
            for k, v in external_gateway.iteritems():
                setattr(self, k, v)
            return self
        else:
            raise SMCException('External GW exception, replace this')
        
    def export(self):
        """
        :method: POST
        """
        pass
    
    def vpn_site(self):
        """
        A VPN site defines a collection of IP's or networks that
        identify address space that is defined on the other end of
        the VPN tunnel.
        
        :method: GET
        """
        return search.element_by_href_as_json(
                    find_link_by_name('vpn_site', self.link))
    
    def external_endpoint(self):
        """
        An External Endpoint is the IP based definition for the
        destination VPN peers. There may be multiple per External
        Gateway. 
        
        :method: GET
        """
        return search.element_by_href_as_json(
                    find_link_by_name('external_endpoint', self.link))
    
    def add_external_endpoint(self, external_endpoint):
        """ Add an external endpoint to this External Gateway
        The external endpoint should be created with::
        
          ExternalEndpoint.create()
        
        :param external_endpoint: json representing endpoint
        :return: SMCResult
        """
        return SMCElement(
                    href=find_link_by_name('external_endpoint', self.link), 
                    json=external_endpoint).create()
    
    def add_site(self, name, network_element):
        """
        Add a site with network element to this External Gateway
        
        :param name
        :param list network_element: hrefs for network elements
        """
        data = {'name': name,
                'site_element': network_element}
        
        return SMCElement(
                href=find_link_by_name('vpn_site', self.link),
                json=data).create()
    
    @property
    def href(self):
        return find_link_by_name('self', self.link)
                  
    def __repr__(self):
        return "%s(%r)" % (self.__class__, 'name={}'.format(self.name))

class ExternalEndpoint(object):
    """
    External Endpoint is used by the External Gateway and defines the IP
    and other VPN related settings to identify the VPN peer.    
    """
    def __init__(self, name=None, **kwargs):
        self.name = name
        for k, v in kwargs.iteritems():
            setattr(self, k, v)
            
    @classmethod
    def create(cls, name, address, enabled=True, balancing_mode='active',
               ipsec_vpn=True, nat_t=False, dynamic=False):
        """
        :param str name
        :param str address: address of remote host
        :param boolean enabled: True|False (default: True)
        :param str balancing_mode: active
        :param boolean ipsec_vpn: True|False (default: True)
        :param boolean nat_t: True|False (default: False)
        :param boolean dynamic: is a dynamic VPN (default: False)
        """
        data = {'name': name, 
                'address': address,
                'balancing_mode': balancing_mode,
                'dynamic': dynamic,
                'enabled': enabled,
                'force_nat_t': nat_t,
                'ipsec_vpn': ipsec_vpn }
        return data
        
    def __repr__(self):
        return "%s(%r)" % (self.__class__, 'name={}'.format(self.name))
        
class VPNSite(object):
    """
    VPN Site information for gateway
    This will define the protected networks for the external gateway
    
    #TODO: support for modifying site to add additional networks without
    creating new sites.
    
    """
    def __init__(self, **kwargs):
        pass
    
    @classmethod
    def create(cls, name, site_element):
        """
        :param name
        :param list site_element: list of protected networks/hosts
        """
        data = {'name': name,
                'site_element': site_element} 
        return data
    
class VPNPolicy(object):
    """
    Create a new VPN Policy
    When making VPN Policy modifications, you must first call :py:func:`open`, make your
    modifications and then call :py:func:`save` followed by :py:func:`close`.
    
    VPN Policy attributes:
    
    :ivar: name
    :ivar: vpn_profile: reference to used VPN profile
    :ivar: nat: whether NAT is enabled on the VPN policy
    :ivar: mobile_vpn_topology_mode: where to allow remote clients
    """
    def __init__(self, name, **kwargs):
        self.name = name

    @classmethod
    def create(cls, name, nat=False, 
               mobile_vpn_toplogy_mode=None,
               vpn_profile=None):
        """
        Create a new policy based VPN
        
        :param name
        :paran nat: whether to apply NAT to the VPN
        :param mobile_vpn_toplogy_mode: whether to allow remote vpn
        :param vpn_profile: reference to VPN profile, or uses default
        """
        data = {'mobile_vpn_topology_mode': None,
                'name': name,
                'nat': nat,
                'vpn_profile': vpn_profile}
        
        href = search.element_entry_point('vpn')
        result = SMCElement(href=href, 
                            json=data).create()
        if result.href:
            return VPNPolicy(name).load()
        else:
            raise CreatePolicyFailed('VPN Policy create failed. Reason: {}'.format(result.msg))
    
    def load(self):
        print "Loading VPN Policy...."
        policy = search.element_as_json_with_filter(self.name, 'vpn')
        if policy:
            for k, v in policy.iteritems():
                setattr(self, k, v)
            return self
        else:
            raise LoadPolicyFailed('Failed to load VPN policy, please ensure the policy exists')
    
    def central_gateway_node(self):
        """
        Central Gateway Node acts as the hub of a hub-spoke VPN. 
        
        :method: GET
        """
        return search.element_by_href_as_json(
                    find_link_by_name('central_gateway_node', self.link))
    
    def satellite_gateway_node(self):
        """
        Node level settings for confgiured satellite gateways
        
        :method: GET
        """
        return search.element_by_href_as_json(
                    find_link_by_name('satellite_gateway_node', self.link))
    
    def mobile_gateway_node(self):
        """
        :method: GET
        """
        return search.element_by_href_as_json(
                    find_link_by_name('mobile_gateway_node', self.link))
    
    def open(self):
        """
        :method: POST
        """
        return SMCElement(
                href=find_link_by_name('open', self.link)).create()
    
    def save(self):
        """
        :method: POST
        """
        return SMCElement(
                href=find_link_by_name('save', self.link)).create()
    
    def close(self):
        """
        :method: POST
        """
        return SMCElement(
                href=find_link_by_name('close', self.link)).create()
                
    def validate(self):
        """
        :method: GET
        """
        return search.element_by_href_as_json(
                    find_link_by_name('validate', self.link))
       
    def gateway_tunnel(self):
        """
        :method: GET
        """
        return search.element_by_href_as_json(
                    find_link_by_name('gateway_tunnel', self.link))
    
    def export(self):
        """
        :method: POST
        """
        pass
    
    def add_central_gateway(self, gateway):
        """ 
        Add SMC managed internal gateway to the Central Gateways of this VPN
        :param internal_gateway: href for internal gateway. If this is another 
               SMC managed gateway, you can retrieve the href after loading the
               engine. See :py:class:`smc.elements.engines.Engine.internal_gateway`
        """
        gateway_node = find_link_by_name('central_gateway_node', self.link)
        return SMCElement(href=gateway_node,
                          json={'gateway': gateway,
                                'node_usage':'central'}).create()
    
    def add_satellite_gateway(self, gateway):
        """
        Add gateway node as a satellite gateway for this VPN. You must first
        have the gateway object created. This is typically used when you either 
        want a hub-and-spoke topology or the external gateway is a non-SMC 
        managed device.
        """
        gateway_node = find_link_by_name('satellite_gateway_node', self.link)
        return SMCElement(href=gateway_node,
                          json={'gateway': gateway,
                                'node_usage':'satellite'}).create() 
    
    def __repr__(self):
        return "%s(%r)" % (self.__class__, 'policy={}'.format(self.name))       