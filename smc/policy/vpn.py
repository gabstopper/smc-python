from smc.elements.element import Meta, ElementLocator
from smc.elements.mixins import ModifiableMixin, ExportableMixin, UnicodeMixin
import smc.actions.search as search
from smc.api.exceptions import CreatePolicyFailed,\
    CreateElementFailed
from smc.elements.util import find_link_by_name, bytes_to_unicode
from smc.api.common import SMCRequest
                                                    
class ExternalGateway(UnicodeMixin, ExportableMixin):
    """
    ExternalGateway defines an VPN Gateway for a non-SMC managed device. 
    This will specify details such as the endpoint IP, enabled, 
    balancing mode, etc.
    
    Create the external gateway and view configuration::
    
        mygw = ExternalGateway.create('mygateway')
        mygw.describe()

    Later get configuration for external gateway::
    
        mygw = ExternalGateway('mygateway')
        
    :ivar gateway_profile: link to top level enabled gateway crypto
    :ivar name: name of external gateway
    :ivar trust_all_cas: True|False (default True)
    :ivar vpn_site: vpn_sites associated
    
    :param str name: name of external gateway
    """
    typeof = 'external_gateway'
    href = ElementLocator()
    
    def __init__(self, name, meta=None):
        self._name = name
        self.meta = meta

    @classmethod
    def create(cls, name, trust_all_cas=True):
        """ 
        Create new External Gateway
        
        :param str name: name of external gateway
        :param boolean trust_all_cas: whether to trust all internal CA's
               (default: True)
        :return: :py:class:`smc.policy.vpn.ExternalGateway`
        """
        data = {'name': name,
                'trust_all_cas': trust_all_cas }

        href = search.element_entry_point('external_gateway')
        result = SMCRequest(href=href, json=data).create()
        if result.href:
            return ExternalGateway(name)
        else:
            raise CreateElementFailed('Failed creating external gateway, '
                                      'reason: {}'.format(result.msg))

    @property
    def name(self):
        return bytes_to_unicode(self._name)

    @property
    def link(self):
        result = search.element_by_href_as_json(self.href)
        return result.get('link')
    
    def describe(self):
        return search.element_by_href_as_json(self.href)
    
    @property
    def vpn_site(self):
        """
        A VPN site defines a collection of IP's or networks that
        identify address space that is defined on the other end of
        the VPN tunnel.
        
        :method: GET
        :return: list :py:class:`smc.policy.vpn.VPNSite`
        """
        href = find_link_by_name('vpn_site', self.link)
        return VPNSite(meta=Meta(href=href))

    @property
    def external_endpoint(self):
        """
        An External Endpoint is the IP based definition for the
        destination VPN peers. There may be multiple per External
        Gateway. 
        Add a new endpoint to an existing external gateway::
            
            for x in describe_external_gateways():
                external_gw = x.load()
                external_gw.external_endpoint.create('me', '12.34.56.78') 

        :method: GET
        :return: :py:class:`smc.policy.vpn.ExternalEndpoint`
        """
        href = find_link_by_name('external_endpoint', self.link)
        return ExternalEndpoint(meta=Meta(href=href))

    def __unicode__(self):
        return u'{0}(name={1})'.format(self.__class__.__name__, self.name)
  
    def __repr__(self):
        return repr(unicode(self))

class ExternalEndpoint(UnicodeMixin, ModifiableMixin):
    """
    External Endpoint is used by the External Gateway and defines the IP
    and other VPN related settings to identify the VPN peer. This is created
    to define the details of the non-SMC managed gateway. This class is a property
    of :py:class:`smc.policy.vpn.ExternalGateway` and should not be called 
    directly.
    
    :ivar name: name of external endpoint
    :ivar href: pass in href to init which will have engine insert location   
    """
    def __init__(self, meta=None):
        self.meta = meta

    def create(self, name, address, enabled=True, balancing_mode='active',
               ipsec_vpn=True, nat_t=False, dynamic=False):
        """
        Create an external endpoint. Define common settings for that
        specify the address, enabled, nat_t, name, etc.
        
        :param str name: name of external endpoint
        :param str address: address of remote host
        :param boolean enabled: True|False (default: True)
        :param str balancing_mode: active
        :param boolean ipsec_vpn: True|False (default: True)
        :param boolean nat_t: True|False (default: False)
        :param boolean dynamic: is a dynamic VPN (default: False)
        :return: :py:class:`smc.api.web.SMCResult`
        """
        json = {'name': name,
                'address': address,
                'balancing_mode': balancing_mode,
                'dynamic': dynamic,
                'enabled': enabled,
                'nat_t': nat_t,
                'ipsec_vpn': ipsec_vpn}
        return SMCRequest(href=self.href, json=json).create()

    @property
    def name(self):
        return self.meta.name

    @property
    def href(self):
        return self.meta.href
    
    def describe(self):
        """
        Return json representation of element
        
        :return: raw json 
        """
        return search.element_by_href_as_json(self.href)
    
    def all(self):
        """
        Show all defined external endpoints
        
        :return: list :py:class:`smc.policy.vpn.ExternalEndpoint`
        """
        endpoints=[]
        for endpoint in search.element_by_href_as_json(self.href):
            endpoints.append(ExternalEndpoint(meta=Meta(**endpoint)))
        return endpoints
    
    def __unicode__(self):
        return u'{0}(name={1})'.format(self.__class__.__name__, self.name)
  
    def __repr__(self):
        return repr(unicode(self))
  
class VPNSite(UnicodeMixin, ModifiableMixin):
    """
    VPN Site information for an internal or external gateway
    Sites are used to encapsulate hosts or networks as 'protected' for VPN
    policy configuration.
    
    Create a new vpn site for an engine::
        
        engine = Engine('myengine').load()
        network = describe_networks(name=['network-192.168.5.0/25'])
        for site in site_network:
            engine.internal_gateway.vpn_site.create('newsite', [site.href])
    
    This class is a property of :py:class:`smc.core.engine.InternalGateway` or
    :py:class:`smc.policy.vpn.ExternalGateway` and should not be accessed directly.
    
    :ivar name: name of VPN site
    :ivar site_element: list of network elements behind this site
    """
    def __init__(self, meta=None):
        self.meta = meta
 
    @property
    def name(self):
        return self.meta.name
        
    @property
    def href(self):
        return self.meta.href

    def create(self, name, site_element):
        """
        Create a VPN site for an internal or external gateway

        :param str name: name of site
        :param list site_element: list of protected networks/hosts
        :return: :py:class:`smc.api.web.SMCResult`
        """
        json={'name': name, 'site_element': site_element}
        return SMCRequest(href=self.href,json=json).create()
    
    def describe(self):
        """
        Return json representation of element
        
        :return: dict raw json
        """
        return search.element_by_href_as_json(self.href)
    
    def all(self):
        """
        Return all sites for this engine
        
        :return: list VPNSite
        """
        sites=[]
        for site in search.element_by_href_as_json(self.href):
            sites.append(VPNSite(meta=Meta(**site)))
        return sites
    
    def __unicode__(self):
        return u'{0}(name={1})'.format(self.__class__.__name__, self.name)
  
    def __repr__(self):
        return repr(unicode(self))

class VPNProfile(UnicodeMixin):
    """
    Represents a VPNProfile configuration used by the VPNPolicy
    """
    typeof = 'vpn_profile'
    href = ElementLocator()
    
    def __init__(self, name, meta=None):
        self.name = name
        self.meta = meta
    
    @property
    def link(self):
        result = search.element_by_href_as_json(self.href)
        return result.get('link')

    def describe(self):
        """
        Show the element json
        
        :return: json of element
        """
        return search.element_by_href_as_json(self.href)

    def __unicode__(self):
        return u'{0}(name={1})'.format(self.__class__.__name__, self.name)
  
    def __repr__(self):
        return repr(unicode(self))
    
class VPNPolicy(UnicodeMixin, ExportableMixin):
    """
    Create a new VPN Policy
    
    vpn = VPNPolicy.create('myVPN')
    print vpn.vpn_profile
    print vpn.describe()
    
    When making VPN Policy modifications, you must first call :py:func:`open`, 
    make your modifications and then call :py:func:`save` followed by 
    :py:func:`close`.
    
    :ivar name: name of policy
    :ivar vpn_profile: reference to used VPN profile
    :ivar nat: whether NAT is enabled on the VPN policy
    :ivar mobile_vpn_topology_mode: where to allow remote clients
    """
    typeof = 'vpn'
    href = ElementLocator()
    
    def __init__(self, name, meta=None):
        self._name = name
        self.meta = meta

    @property
    def name(self):
        return bytes_to_unicode(self._name)
    
    @classmethod
    def create(cls, name, nat=False, mobile_vpn_toplogy_mode=None,
               vpn_profile=None):
        """
        Create a new policy based VPN
        
        :param name: name of vpn policy
        :param boolean nat: whether to apply NAT to the VPN (default False)
        :param mobile_vpn_toplogy_mode: whether to allow remote vpn
        :param str vpn_profile: reference to VPN profile, or uses default
        """
        json = {'mobile_vpn_topology_mode': None,
                'name': name,
                'nat': nat,
                'vpn_profile': vpn_profile}
        
        href = search.element_entry_point(cls.typeof)
        result = SMCRequest(href=href,
                            json=json).create()
        if result.href:
            return VPNPolicy(name)
        else:
            raise CreatePolicyFailed('VPN Policy create failed. Reason: {}'
                                     .format(result.msg))
    
    @property
    def link(self):
        result = search.element_by_href_as_json(self.href)
        return result.get('link')
    
    @property
    def nat(self):
        """ 
        Is NAT enabled on this vpn policy
        
        :return: True|False
        """
        result = search.element_by_href_as_json(self.href)
        return result.get('nat')

    @property
    def vpn_profile(self):
        """
        Specified VPN Profile used by this VPN Policy
        
        :return: `~VPNProfile`
        """
        result = search.element_by_href_as_json(self.href)
        return result.get('vpn_profile')

    def central_gateway_node(self):
        """
        Central Gateway Node acts as the hub of a hub-spoke VPN. 
        
        :method: GET
        """
        return search.element_by_href_as_json(
                    find_link_by_name('central_gateway_node', self.link))
    
    def satellite_gateway_node(self):
        """
        Node level settings for configured satellite gateways
        
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
        :return: :py:class:`smc.api.web.SMCResult`
        """
        return SMCRequest(
                href=find_link_by_name('open', self.link)).create()
    
    def save(self):
        """
        :method: POST
        :return: :py:class:`smc.api.web.SMCResult`
        """
        return SMCRequest(
                href=find_link_by_name('save', self.link)).create()
    
    def close(self):
        """
        :method: POST
        :return: :py:class:`smc.api.web.SMCResult`
        """
        return SMCRequest(
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
    
    def add_central_gateway(self, gateway):
        """ 
        Add SMC managed internal gateway to the Central Gateways of this VPN
        
        :param gateway: href for internal gateway. If this is another 
               SMC managed gateway, you can retrieve the href after loading the
               engine. See :py:class:`smc.core.engines.Engine.internal_gateway`
               
        :return: :py:class:`smc.api.web.SMCResult`
        """
        gateway_node = find_link_by_name('central_gateway_node', self.link)
        return SMCRequest(href=gateway_node,
                          json={'gateway': gateway,
                                'node_usage':'central'}).create()
    
    def add_satellite_gateway(self, gateway):
        """
        Add gateway node as a satellite gateway for this VPN. You must first
        have the gateway object created. This is typically used when you either 
        want a hub-and-spoke topology or the external gateway is a non-SMC 
        managed device.
        
        :return: :py:class:`smc.api.web.SMCResult`
        """
        gateway_node = find_link_by_name('satellite_gateway_node', self.link)
        return SMCRequest(href=gateway_node,
                          json={'gateway': gateway,
                                'node_usage':'satellite'}).create() 
    
    @staticmethod
    def add_internal_gateway_to_vpn(internal_gateway_href, vpn_policy, 
                                vpn_role='central'):
        """
        Add an internal gateway (managed engine node) to a VPN policy
        based on the internal gateway href.
        
        :param str internal_gateway_href: href for engine internal gw
        :param str vpn_policy: name of vpn policy
        :param str vpn_role: central|satellite
        :return: boolean True for success
        """
        from smc.elements.collection import describe_vpn
        success=False
        for vpn in describe_vpn():
            if vpn.name.startswith(vpn_policy):
                vpn.open()
                if vpn_role == 'central':
                    vpn.add_central_gateway(internal_gateway_href)
                else:
                    vpn.add_satellite_gateway(internal_gateway_href)
                vpn.save()
                vpn.close()
                success=True
                break
        return success
 
    def describe(self):
        """
        Return json representation of this VPNPolicy
        
        :return: json for VPN Policy
        """
        return search.element_by_href_as_json(self.href)

    def __unicode__(self):
        return u'{0}(name={1})'.format(self.__class__.__name__, self.name)

    def __repr__(self):
        return repr(unicode(self))
        
class VPNCertificate(object):
    """
    Create a new VPN Certificate for an internal gateway
        
    :param str country: Country code (2 characters), will be used for for 
           subject name creation
    :param str locality: will be used for for subject name creation
    :param str organization: will be used subject name creation
    :param str common_name: will be used for for subject name creation
    :param str signature_algorithm: The signature algorithm used
           Can be one of the following:
           "dsa_sha_1" | "dsa_sha_224" | "dsa_rsa_256" | "rsa_md5" | "rsa_sha_1" |
           "rsa_sha_256" | "rsa_sha_384" | "rsa_sha_512" | "ecdsa_sha_1" | 
           "ecdsa_sha_256" | "ecdsa_sha_384" | "ecdsa_sha_512"
    :param str public_key_algorithm: The public key algorithm used
           Can be one of the following:
           "dsa" | "rsa" | "ecdsa"
    :param int public_key_length: Length in bits of the public key 
           (some restrictions may apply based on specified settings)
    :param str organization_unit: will be used for subject name creation
    :param str state_province: will be used for for subject name creation
    :param str certificate_authority_ref: Reference to the internal certificate 
           authority that will be used for self signing the generated certificate 
           request.
            
    Example of creating a certificate for a specific VPN internal gateway::
           
        cert = VPNCertificate(organization='myorg', common_name='amazon-fw')
        engine = Engine('myengine').load()
        engine.internal_gateway.generate_certificate(cert)      
    """
    def __init__(self, organization, common_name, public_key_algorithm="dsa",
                 signature_algorithm="rsa_sha_256", public_key_length=2048, 
                 country=None, organization_unit=None, state_province=None, 
                 locality=None, certificate_authority_href=None):
        self.country = country
        self.locality = locality
        self.organization = organization
        self.common_name = common_name
        self.signature_algorithm = signature_algorithm
        self.public_key_algorithm = public_key_algorithm
        self.public_key_length = public_key_length
        self.organization_unit = organization_unit
        self.state_province = state_province
        self.certificate_authority_href = certificate_authority_href
        if not self.certificate_authority_href:
            self.default_certificate_authority()
    
    def default_certificate_authority(self):
        """
        Used internally to find the href of the SMC's VPN Certificate Authority
        """
        authorities = search.all_elements_by_type('vpn_certificate_authority')
        for authority in authorities:
            self.certificate_authority_href = authority.get('href')
