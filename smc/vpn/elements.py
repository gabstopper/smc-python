from smc.base.model import Meta
import smc.actions.search as search
from smc.api.exceptions import CreateElementFailed
from smc.base.util import find_link_by_name
from smc.base.model import Element, ElementCreator, prepared_request
                    
class ExternalGateway(Element):
    """
    ExternalGateway defines an VPN Gateway for a non-SMC managed device. 
    This will specify details such as the endpoint IP, enabled, 
    balancing mode, etc.
    
    Create the test_external gateway and view configuration::
    
        mygw = ExternalGateway.create('mygateway')
        mygw.describe()

    Later get configuration for test_external gateway::
    
        mygw = ExternalGateway('mygateway')
        
    :ivar gateway_profile: link to top level enabled gateway crypto
    :ivar name: name of test_external gateway
    :ivar trust_all_cas: True|False (default True)
    :ivar vpn_site: vpn_sites associated
    
    :param str name: name of test_external gateway
    """
    typeof = 'external_gateway'
    
    def __init__(self, name, meta=None):
        self._name = name
        self.meta = meta

    @classmethod
    def create(cls, name, trust_all_cas=True):
        """ 
        Create new External Gateway
        
        :param str name: name of test_external gateway
        :param boolean trust_all_cas: whether to trust all internal CA's
               (default: True)
        :return: :py:class:`smc.vpn.elements.ExternalGateway`
        """
        cls.json = {'name': name,
                    'trust_all_cas': trust_all_cas}

        result = ElementCreator(cls)
        if result.href:
            return ExternalGateway(name)
        else:
            raise CreateElementFailed('Failed creating test_external gateway, '
                                      'reason: {}'.format(result.msg))
    
    @property
    def vpn_site(self):
        """
        A VPN site defines a collection of IP's or networks that
        identify address space that is defined on the other end of
        the VPN tunnel.
        
        :method: GET
        :return: list :py:class:`smc.vpn.elements.VPNSite`
        """
        href = find_link_by_name('vpn_site', self.link)
        return VPNSite(meta=Meta(href=href))

    @property
    def external_endpoint(self):
        """
        An External Endpoint is the IP based definition for the
        destination VPN peers. There may be multiple per External
        Gateway. 
        Add a new endpoint to an existing test_external gateway::
            
            for x in describe_external_gateways():
                external_gw = x.load()
                external_gw.external_endpoint.create('me', '12.34.56.78') 

        :method: GET
        :return: :py:class:`smc.vpn.elements.ExternalEndpoint`
        """
        href = find_link_by_name('external_endpoint', self.link)
        return ExternalEndpoint(meta=Meta(href=href))

class ExternalEndpoint(Element):
    """
    External Endpoint is used by the External Gateway and defines the IP
    and other VPN related settings to identify the VPN peer. This is created
    to define the details of the non-SMC managed gateway. This class is a property
    of :py:class:`smc.vpn.elements.ExternalGateway` and should not be called 
    directly.
    
    :ivar name: name of test_external endpoint
    :ivar href: pass in href to init which will have engine insert location   
    """
    def __init__(self, meta=None):
        self.meta = meta

    def create(self, name, address, enabled=True, balancing_mode='active',
               ipsec_vpn=True, nat_t=False, dynamic=False):
        """
        Create an test_external endpoint. Define common settings for that
        specify the address, enabled, nat_t, name, etc.
        
        :param str name: name of test_external endpoint
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
        
        return prepared_request(href=self.href, json=json).create()

    @property
    def name(self):
        return self.meta.name

    def all(self):
        """
        Show all defined test_external endpoints
        
        :return: list :py:class:`smc.vpn.elements.ExternalEndpoint`
        """
        return [ExternalEndpoint(meta=Meta(**gw))
                for gw in search.element_by_href_as_json(self.href)]

class VPNSite(Element):
    """
    VPN Site information for an internal or test_external gateway
    Sites are used to encapsulate hosts or networks as 'protected' for VPN
    policy configuration.
    
    Create a new vpn site for an engine::
        
        engine = Engine('myengine').load()
        network = Network('network-192.168.5.0/25') #get resource
        engine.internal_gateway.vpn_site.create('newsite', [network.href])

    This class is a property of :py:class:`smc.core.engine.InternalGateway` or
    :py:class:`smc.vpn.elements.ExternalGateway` and should not be accessed directly.
    
    :ivar name: name of VPN site
    :ivar site_element: list of network elements behind this site
    """
    def __init__(self, meta=None):
        self.meta = meta

    def create(self, name, site_element):
        """
        Create a VPN site for an internal or test_external gateway

        :param str name: name of site
        :param list site_element: list of protected networks/hosts
        :return: :py:class:`smc.api.web.SMCResult`
        """
        json={'name': name, 'site_element': site_element}
        return prepared_request(href=self.href, json=json).create()

    @property
    def name(self):
        return self.meta.name

    def all(self):
        """
        Return all sites for this engine
        
        :return: list VPNSite
        """
        return [VPNSite(meta=Meta(**site))
                for site in search.element_by_href_as_json(self.href)]

class VPNProfile(Element):
    """
    Represents a VPNProfile configuration used by the VPNPolicy
    """
    typeof = 'vpn_profile'

    def __init__(self, name, meta=None):
        self._name = name
        self.meta = meta
        
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

