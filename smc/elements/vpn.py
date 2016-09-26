from smc.elements.element import SMCElement, Meta
import smc.actions.search as search
from smc.api.exceptions import SMCException, LoadPolicyFailed, CreatePolicyFailed,\
    CreateElementFailed, CertificateError
from smc.elements.util import find_link_by_name
                                                      
class InternalGateway(object):
    """ 
    InternalGateway represents the engine side VPN configuration
    This defines settings such as setting VPN sites on protected
    networks and generating certificates.
    This is defined under Engine->VPN within SMC.
    Since each engine has only one internal gateway, this resource
    is loaded immediately when called through engine.internal_gateway
    
    This is a resource of an Engine as it defines engine specific VPN 
    gateway settings::
    
        engine.internal_gateway.describe()
    
    :ivar href: location of this internal gateway
    :ivar etag: etag of internal gateway
    :ivar vpn_site: vpn site object
    :ivar internal_endpoint: interface endpoint mappings (where to enable VPN) 
    """
    def __init__(self, name=None, **kwargs):
        self.name = name
        for key, value in kwargs.iteritems():
            setattr(self, key, value)
    
    def modify_attribute(self, **kwargs):
        """
        Modify attribute
        
        :param kwargs: (key=value)
        :return: SMCResult
        """
        for k, v in kwargs.iteritems():
            setattr(self, k, v)
        return SMCElement(href=self.href, json=vars(self),
                          etag=self.etag).update()
    
    @property
    def etag(self):
        return search.element_by_href_as_smcresult(self.href).etag
    
    @property
    def href(self):
        """ 
        Use this property when adding to a VPN Policy
        """
        return find_link_by_name('self', self.link)
               
    @property
    def vpn_site(self):
        """
        Retrieve VPN Site information for this internal gateway
        
        Find all configured sites for engine::
        
            for site in engine.internal_gateway.vpn_site.all():
                print site
        
        :method: GET
        :return: :py:class:`smc.elements.vpn.VPNSite`
        """
        href = find_link_by_name('vpn_site', self.link)
        return VPNSite(meta=Meta(href=href))
    
    @property
    def internal_endpoint(self):
        """
        Internal Endpoint setting VPN settings to the interface
        
        Find all internal endpoints for an engine::
        
            for x in engine.internal_gateway.internal_endpoint.all():
                print x
                
        :method: GET
        :return: list :py:class:`smc.elements.vpn.InternalEndpoint`
        """
        href = find_link_by_name('internal_endpoint', self.link)
        return InternalEndpoint(meta=Meta(href=href))
    
    def gateway_certificate(self):
        """
        :method: GET
        :return: list
        """
        return search.element_by_href_as_json(
                find_link_by_name('gateway_certificate', self.link))
    
    def gateway_certificate_request(self):
        """
        :method: GET
        :return list
        """
        return search.element_by_href_as_json(
                find_link_by_name('gateway_certificate_request', self.link))    
    
    def generate_certificate(self, certificate_request):
        """
        Generate an internal gateway certificate used for VPN on this engine.
        Certificate request should be an instance of VPNCertificate.
    
        :method: POST
        :param VPNCertificate certificate_request: cert request details
        :return: None
        :raises: 
        """
        result = SMCElement(
                    href=find_link_by_name('generate_certificate', self.link),
                    json=vars(certificate_request)).create()
        if result.msg:
            raise CertificateError(result.msg)
    
    def describe(self):
        """
        Describe the internal gateway by returning the raw json::
            
            print engine.internal_gateway.describe()
        """    
        return vars(self)
                    
    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, 'name={}'
                           .format(self.name))

class InternalEndpoint(object):
    """
    InternalEndpoint lists the VPN endpoints either enabled or disabled for
    VPN. You should enable the endpoint for the interface that will be the
    VPN endpoint. You may also need to enable NAT-T and ensure IPSEC is enabled.
    This is defined under Engine->VPN->EndPoints in SMC. This class is a property
    of the engines internal gateway and not accessed directly.
    
    To see all available internal endpoint (VPN gateways) on a particular
    engine, get the engine context first::
        
        engine = Engine('myengine').load()
        for endpt in engine.internal_gateway.internal_endpoint.all():
            print endpt
    
    :ivar deducted_name: name of the endpoint is based on the interface
    :ivar dynamic: True|False
    :ivar enabled: True|False
    :ivar ipsec_vpn: True|False
    :ivar nat_t: True|False
    
    :param href: pass in href to init which will have engine insert location  
    """
    def __init__(self, meta=None, **kwargs):
        self.meta = meta
    
    @property
    def name(self):
        return self.meta.name
        
    @property
    def href(self):
        return self.meta.href
  
    @property
    def etag(self):
        pass

    def modify_attribute(self, **kwargs):
        """
        Modify an internal attribute of the internal endpoint
        For example, enabling one of the interfaces to accept VPN
        traffic::
        
            for gateway in engine.internal_gateway.internal_endpoint.all():
                if gateway.name.startswith('50.50.50.50'):
                    print gateway.describe()
                    gateway.modify_attribute(nat_t=True,enabled=True)
            
        :return: SMCResult
        """
        #TODO: Review... Maybe a better way?
        return SMCElement(href=self.href).modify_attribute(**kwargs)
       
    def describe(self):
        """
        Return json representation of element
        
        :return: raw json 
        """
        return search.element_by_href_as_json(self.href)
    
    def all(self):
        """
        Return all internal endpoints
        
        :return: list :py:class:`smc.elements.vpn.InternalEndpoint`
        """
        gateways=[]
        for gateway in search.element_by_href_as_json(self.href):
            gateways.append(InternalEndpoint(meta=Meta(**gateway)))
        return gateways
    
    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, 'name={}'
                           .format(self.name))
        
class ExternalGateway(object):
    """
    ExternalGateway defines an VPN Gateway for a non-SMC managed device. 
    This will specify details such as the endpoint IP, enabled, 
    balancing mode, etc. Load needs to be called on this resource in order
    to get the context to change the configuration.
    
    Create the external gateway and load configuration::
    
        mygw = ExternalGateway.create('mygateway')

    Later get configuration for external gateway::
    
        mygw = ExternalGateway('mygateway').load()
        
    :ivar gateway_profile: link to top level enabled gateway crypto
    :ivar name: name of external gateway
    :ivar trust_all_cas: True|False (default True)
    :ivar vpn_site: vpn_sites associated
    
    :param href: pass in href to init which will have engine insert location
    """
    typeof = 'external_gateway'
    
    def __init__(self, name=None, meta=None, **kwargs):
        self.name = name
        self.meta = meta

    @classmethod
    def create(cls, name, trust_all_cas=True):
        """ 
        Create new External Gateway
        
        :param str name: name of external gateway
        :param boolean trust_all_cas: whether to trust all internal CA's
               (default: True)
        """
        data = {'name': name,
                'trust_all_cas': trust_all_cas }

        result = SMCElement(json=data, typeof=cls.typeof).create()
        if result.href:
            return ExternalGateway(name).load()
        else:
            raise CreateElementFailed('Failed creating external gateway, '
                                      'reason: {}'.format(result.msg))

    def load(self):
        """
        Load external gateway settings
        
        :return: ExternalGateway
        """
        if not self.meta:
            self.meta = Meta(**search.element_as_json_with_filter(
                                        self.name, 'external_gateway'))
        result = search.element_by_href_as_smcresult(self.meta.href)
        if result:   
            self.json = {}
            for k, v in result.json.iteritems():
                self.json.update({k: v})
            return self
        else:
            raise SMCException('External GW exception, replace this')
    
    @property
    def href(self):
        return self.meta.href
        
    @property
    def link(self):
        if hasattr(self, 'json'):
            return self.json.get('link')

    @property
    def vpn_site(self):
        """
        A VPN site defines a collection of IP's or networks that
        identify address space that is defined on the other end of
        the VPN tunnel.
        
        :method: GET
        :return: list :py:class:`smc.elements.vpn.VPNSite`
        """
        href = find_link_by_name('vpn_site', self.link)
        return VPNSite(meta=Meta(name=None, href=href, type='vpn_site'))

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
        :return: :py:class:`smc.elements.vpn.ExternalEndpoint`
        """
        href = find_link_by_name('external_endpoint', self.link)
        return ExternalEndpoint(meta=Meta(name=None, href=href, type='external_endpoint'))
    
    def export(self):
        """
        :method: POST
        """
        pass

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, 'name={}'
                           .format(self.name))

class ExternalEndpoint(object):
    """
    External Endpoint is used by the External Gateway and defines the IP
    and other VPN related settings to identify the VPN peer. This is created
    to define the details of the non-SMC managed gateway. This class is a property
    of :py:class:`smc.elements.vpn.ExternalGateway` and should not be called 
    directly.
    
    :param href: pass in href to init which will have engine insert location   
    """
    def __init__(self, meta=None, **kwargs):
        self.meta = meta

    def create(self, name, address, enabled=True, balancing_mode='active',
               ipsec_vpn=True, nat_t=False, dynamic=False):
        """
        Create an external endpoint. Define common settings for that
        specify the address, enabled, nat_t, name, etc.
        
        :param str name
        :param str address: address of remote host
        :param boolean enabled: True|False (default: True)
        :param str balancing_mode: active
        :param boolean ipsec_vpn: True|False (default: True)
        :param boolean nat_t: True|False (default: False)
        :param boolean dynamic: is a dynamic VPN (default: False)
        """
        json = {'name': name,
                'address': address,
                'balancing_mode': balancing_mode,
                'dynamic': dynamic,
                'enabled': enabled,
                'nat_t': nat_t,
                'ipsec_vpn': ipsec_vpn}
        return SMCElement(href=self.href, json=json).create()

    @property
    def name(self):
        return self.meta.name

    @property
    def href(self):
        return self.meta.href

    def modify_attribute(self, **kwargs):
        """
        Modify an existing external endpoint.
        
        For example, set an endpoint with address '2.2.2.2' to
        disabled::
        
            external_gateway = ExternalGateway('externalgw').load()
            for endpoint in external_gateway.external_endpoint.all():
                if endpoint.name.startswith('myhost2'):
                    endpoint.modify_attribute(enabled=False)
                    
        :return: SMCResult
        """
        return SMCElement(href=self.href).modify_attribute(**kwargs)
    
    def describe(self):
        """
        Return json representation of element
        
        :return: raw json 
        """
        return search.element_by_href_as_json(self.href)
    
    def all(self):
        """
        Show all defined external endpoints
        
        :return list :py:class:smc.elements.vpn.ExternalEndpoint`
        """
        endpoints=[]
        for endpoint in search.element_by_href_as_json(self.href):
            endpoints.append(ExternalEndpoint(meta=Meta(**endpoint)))
        return endpoints
    
    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, 'name={}'
                           .format(self.meta.name))
        
class VPNSite(object):
    """
    VPN Site information for an internal or external gateway
    Sites are used to encapsulate hosts or networks as 'protected' for VPN
    policy configuration.
    
    Create a new vpn site for an engine::
        
        engine = Engine('myengine').load()
        site_network = describe_networks(name=['network-192.168.5.0/25'])
        for site in site_network:
            site_network = site.href
        engine.internal_gateway.vpn_site.create('newsite', [site_network])
    
    This class is a property of :py:class:`smc.elements.vpn.InternalGateway` or
    :py:class:`smc.elements.vpn.ExternalGateway` and should not be accessed directly.
    
    :ivar name: name of VPN site
    :ivar site_element: list of network elements behind this site
    
    :param href: pass in href to init which will have engine insert location
    """
    def __init__(self, meta=None, **kwargs):
        self.meta = meta
 
    @property
    def name(self):
        return self.meta.name
        
    @property
    def href(self):
        return self.meta.href

    def create(self, name, site_element):
        """
        :param name: name of site
        :param list site_element: list of protected networks/hosts
        :return: VPNSite json
        """
        json={'name': name, 'site_element': site_element}
        return SMCElement(href=self.href,json=json).create()
    
    def modify_attribute(self, **kwargs):
        """
        Modify attribute of VPN site. Site_element is a list, if 
        a new site_element attribute is provided, this list will 
        overwrite the previous::
        
            hosts = collections.describe_networks(name=['172.18.1.0'], 
                                                        exact_match=False)
            h = [host.href for host in hosts]
            for site in engine.internal_gateway.vpn_site.all():
                if site.name == 'newsite':
                    site.modify_attribute(site_element=h)
        """
        return SMCElement(href=self.href).modify_attribute(**kwargs)

    def describe(self):
        """
        Return json representation of element
        
        :return: raw json of SMCElement
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
    
    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, 'name={}'
                           .format(self.name))

class VPNProfile(object):
    """
    Represents a VPNProfile configuration used by the VPNPolicy
    """
    def __init__(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)
    
class VPNPolicy(object):
    """
    Create a new VPN Policy
    When making VPN Policy modifications, you must first call :py:func:`open`, 
    make your modifications and then call :py:func:`save` followed by 
    :py:func:`close`.
    
    :ivar name: name of policy
    :ivar vpn_profile: reference to used VPN profile
    :ivar nat: whether NAT is enabled on the VPN policy
    :ivar mobile_vpn_topology_mode: where to allow remote clients
    """
    typeof = 'vpn'

    def __init__(self, name, meta=None, **kwargs):
        self.name = name
        self.meta = meta
        for k, v in kwargs.iteritems():
            setattr(self, k, v)

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

        result = SMCElement(typeof=cls.typeof,
                            json=json).create()
        if result.href:
            return VPNPolicy(name).load()
        else:
            raise CreatePolicyFailed('VPN Policy create failed. Reason: {}'.format(result.msg))
    
    def load(self):
        """
        Load VPN Policy and store associated json in self.json attribute
        
        :return: VPNPolicy
        """
        if not self.meta:
            result = search.element_info_as_json(self.name)
            if result:
                self.meta = Meta(**result)
            else:
                raise LoadPolicyFailed('Failed to load VPN policy, please ensure the policy exists.')
        result = search.element_by_href_as_smcresult(self.meta.href)
        self.json = result.json
        return self    
    
    @property
    def link(self):
        if hasattr(self, 'json'):
            return self.json.get('link')
        else:
            raise AttributeError("You must load the VPN Policy before accessing resources.")
    
    @property
    def vpn_profile(self):
        return self.json.get('vpn_profile')

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
        :return: SMCResult
        """
        return SMCElement(
                href=find_link_by_name('open', self.link)).create()
    
    def save(self):
        """
        :method: POST
        :return: SMCResult
        """
        return SMCElement(
                href=find_link_by_name('save', self.link)).create()
    
    def close(self):
        """
        :method: POST
        :return: SMCResult
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
        
        :param gateway: href for internal gateway. If this is another 
               SMC managed gateway, you can retrieve the href after loading the
               engine. See :py:class:`smc.core.engines.Engine.internal_gateway`
               
        :return: SMCResult
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
        
        :return: SMCResult
        """
        gateway_node = find_link_by_name('satellite_gateway_node', self.link)
        return SMCElement(href=gateway_node,
                          json={'gateway': gateway,
                                'node_usage':'satellite'}).create() 
    
    def describe(self):
        """
        Return json representation of this VPNPolicy
        
        :return: json
        """
        return vars(self)

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, 'name={}'\
                           .format(self.name))

class VPNCertificate(object):
    def __init__(self, organization, common_name, public_key_algorithm="dsa",
                 signature_algorithm="rsa_sha_256", public_key_length=2048, 
                 country=None, organization_unit=None, state_province=None, 
                 locality=None, certificate_authority_href=None):
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
        authorities = search.all_elements_by_type('vpn_certificate_authority')
        for authority in authorities:
            self.certificate_authority_href = authority.get('href')    