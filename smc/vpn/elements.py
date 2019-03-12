"""
VPN Elements are used in conjunction with Policy or Route Based VPN configurations.
VPN elements consist of external gateway and VPN site settings that identify 3rd party
gateways to be used as a VPN termination endpoint.

There are several ways to create an external gateway configuration.
A step by step process which first creates a network element to be used in a 
VPN site, then creates the ExternalGatway, an ExternalEndpoint for the gateway,
and inserts the VPN site into the configuration::

    Network.create(name='mynetwork', ipv4_network='172.18.1.0/24')
    gw = ExternalGateway.create(name='mygw')
    gw.external_endpoint.create(name='myendpoint', address='10.10.10.10')
    gw.vpn_site.create(name='mysite', site_element=[Network('mynetwork')])

You can also use the convenience method `update_or_create` on the ExternalGateway
to fully provision in a single step. Note that the ExternalEndpoint and VPNSite also
have an `update_or_create` method to limit the update to those respective
configurations::

    >>> from smc.elements.network import Network
    >>> from smc.vpn.elements import ExternalGateway
    >>> network = Network.get_or_create(name='network-172.18.1.0/24', ipv4_network='172.18.1.0/24')
    >>> 
    >>> g = ExternalGateway.update_or_create(name='newgw',
        external_endpoint=[
            {'name': 'endpoint1', 'address': '1.1.1.1', 'enabled': True},
            {'name': 'endpoint2', 'address': '2.2.2.2', 'enabled': True}],
        vpn_site=[{'name': 'sitea', 'site_element':[network]}])
    >>> g
    ExternalGateway(name=newgw)
    >>> for endpoint in g.external_endpoint:
    ...   endpoint
    ... 
    ExternalEndpoint(name=endpoint1 (1.1.1.1))
    ExternalEndpoint(name=endpoint2 (2.2.2.2))
    >>> for site in g.vpn_site:
    ...   site, site.site_element
    ... 
    (VPNSite(name=sitea), [Network(name=network-172.18.1.0/24)])

.. note:: When calling `update_or_create` from the ExternalGateway, providing the
    parameters for external_endpoints and vpn_site is optional.
"""

from smc.api.exceptions import ElementNotFound
from smc.base.model import SubElement, Element, ElementRef, ElementCreator
from smc.base.collection import create_collection
from smc.base.util import element_resolver
from smc.elements.helpers import location_helper
from smc.base.structs import SerializedIterable
from smc.elements.other import ContactAddress


class GatewaySettings(Element):
    """
    Gateway settings define various VPN related settings that
    are applied at the firewall level such as negotiation 
    timers and mobike settings. A gateway setting is a property
    of an engine::

        engine = Engine('myfw')
        engine.vpn.gateway_settings
    """
    typeof = 'gateway_settings'

    @classmethod
    def create(cls, name, negotiation_expiration=200000,
               negotiation_retry_timer=500,
               negotiation_retry_max_number=32,
               negotiation_retry_timer_max=7000,
               certificate_cache_crl_validity=90000,
               mobike_after_sa_update=False,
               mobike_before_sa_update=False,
               mobike_no_rrc=True):
        """
        Create a new gateway setting profile.

        :param str name: name of profile
        :param int negotiation_expiration: expire after (ms)
        :param int negotiation_retry_timer: retry time length (ms)
        :param int negotiation_retry_max_num: max number of retries allowed
        :param int negotiation_retry_timer_max: maximum length for retry (ms)
        :param int certificate_cache_crl_validity: cert cache validity (seconds)
        :param boolean mobike_after_sa_update: Whether the After SA flag is set
            for Mobike Policy
        :param boolean mobike_before_sa_update: Whether the Before SA flag is
            set for Mobike Policy
        :param boolean mobike_no_rrc: Whether the No RRC flag is set for 
            Mobike Policy
        :raises CreateElementFailed: failed creating profile
        :return: instance with meta
        :rtype: GatewaySettings
        """
        json = {'name': name,
                'negotiation_expiration': negotiation_expiration,
                'negotiation_retry_timer': negotiation_retry_timer,
                'negotiation_retry_max_number': negotiation_retry_max_number,
                'negotiation_retry_timer_max': negotiation_retry_timer_max,
                'certificate_cache_crl_validity': certificate_cache_crl_validity,
                'mobike_after_sa_update': mobike_after_sa_update,
                'mobike_before_sa_update': mobike_before_sa_update,
                'mobike_no_rrc': mobike_no_rrc}

        return ElementCreator(cls, json)


class GatewayProfile(Element):
    """
    Gateway Profiles describe the capabilities of a Gateway, i.e. supported
    cipher, hash, etc. Gateway Profiles of Internal Gateways are read-only
    and computed from the firewall version and FIPS mode.
    Gateway Profiles of External Gateways are user-defined.
    """
    typeof = 'gateway_profile'

    def capabilities(self):
        pass


class ExternalGateway(Element):
    """
    External Gateway defines an VPN Gateway for a non-SMC managed device. 
    This will specify details such as the endpoint IP, and VPN site
    protected networks. Example of manually provisioning each step::

        Network.create(name='mynetwork', ipv4_network='172.18.1.0/24')
        gw = ExternalGateway.create(name='mygw')
        gw.external_endpoint.create(name='myendpoint', address='10.10.10.10')
        gw.vpn_site.create(name='mysite', site_element=[Network('mynetwork')])
    
    :ivar GatewayProfile gateway_profile: A gateway profile will define the
        capabilities (i.e. crypto) allowed for this VPN.
    """
    typeof = 'external_gateway'
    gateway_profile = ElementRef('gateway_profile')

    @classmethod
    def create(cls, name, trust_all_cas=True):
        """ 
        Create new External Gateway

        :param str name: name of test_external gateway
        :param bool trust_all_cas: whether to trust all internal CA's
               (default: True)
        :return: instance with meta
        :rtype: ExternalGateway
        """
        json = {'name': name,
                'trust_all_cas': trust_all_cas}

        return ElementCreator(cls, json)

    @classmethod
    def update_or_create(cls, name, external_endpoint=None, vpn_site=None,
        trust_all_cas=True, with_status=False):
        """
        Update or create an ExternalGateway. The ``external_endpoint`` and
        ``vpn_site`` parameters are expected to be a list of dicts with key/value
        pairs to satisfy the respective elements create constructor. VPN Sites will
        represent the final state of the VPN site list. ExternalEndpoint that are
        pre-existing will not be deleted if not provided in the ``external_endpoint``
        parameter, however existing elements will be updated as specified.
        
        :param str name: name of external gateway
        :param list(dict) external_endpoint: list of dict items with key/value
            to satisfy ExternalEndpoint.create constructor
        :param list(dict) vpn_site: list of dict items with key/value to satisfy
            VPNSite.create constructor
        :param bool with_status: If set to True, returns a 3-tuple of
            (ExternalGateway, modified, created), where modified and created
            is the boolean status for operations performed.
        :raises ValueError: missing required argument/s for constructor argument
        :rtype: ExternalGateway
        """
        if external_endpoint:
            for endpoint in external_endpoint:
                if 'name' not in endpoint:
                    raise ValueError('External endpoints are configured '
                        'but missing the name parameter.')
        
        if vpn_site:
            for site in vpn_site:
                if 'name' not in site:
                    raise ValueError('VPN sites are configured but missing '
                        'the name parameter.')
                # Make sure VPN sites are resolvable before continuing
                sites = [element_resolver(element, do_raise=True)
                    for element in site.get('site_element', [])]
                site.update(site_element=sites)
        
        updated = False
        created = False
        try:
            extgw = ExternalGateway.get(name)
        except ElementNotFound:
            extgw = ExternalGateway.create(name, trust_all_cas)
            created = True
        
        if external_endpoint:
            for endpoint in external_endpoint:
                _, modified, was_created = ExternalEndpoint.update_or_create(
                    extgw, with_status=True, **endpoint)
                if was_created or modified:
                    updated = True
        
        if vpn_site:
            for site in vpn_site:
                _, modified, was_created = VPNSite.update_or_create(extgw,
                    name=site['name'], site_element=site.get('site_element'),
                    with_status=True)
                if was_created or modified:
                    updated = True

        if with_status:
            return extgw, updated, created
        return extgw

    @property
    def vpn_site(self):
        """
        A VPN site defines a collection of IP's or networks that
        identify address space that is defined on the other end of
        the VPN tunnel.

        :rtype: CreateCollection(VPNSite)
        """
        return create_collection(
            self.get_relation('vpn_site'),
            VPNSite)

    @property
    def external_endpoint(self):
        """
        An External Endpoint is the IP based definition for the destination
        VPN peers. There may be multiple per External Gateway.  Add a new
        endpoint to an existing test_external gateway::

            >>> list(ExternalGateway.objects.all())
            [ExternalGateway(name=cisco-remote-side), ExternalGateway(name=remoteside)]
            >>> gateway.external_endpoint.create('someendpoint', '12.12.12.12')
            'http://1.1.1.1:8082/6.1/elements/external_gateway/22961/external_endpoint/27467'

        :rtype: CreateCollection(ExternalEndpoint)
        """
        return create_collection(
            self.get_relation('external_endpoint'),
            ExternalEndpoint)

    @property
    def trust_all_cas(self):
        """
        Gateway setting identifying whether all CA's specified in the
        profile are supported or only specific ones.

        :rtype: bool
        """
        return self.data.get('trust_all_cas')


class ElementContactAddress(SerializedIterable):
    def __init__(self, smcresult, subelement):
        self._subelement = subelement # Original element
        self._etag = smcresult.etag
        super(ElementContactAddress, self).__init__(smcresult.json.get(
            'contact_addresses', []), ContactAddress)
    
    def create(self, location_ref, address, dynamic=False, overwrite_existing=False):
        """
        Create a contact address for the given element. Address is always
        a required field. If the contact address should be dynamic, then
        the value of the address field should be assigned by the DHCP
        interface name, i.e.::
        
            external_endpoint.contact_addresses.create(
                location=Location('foo'),
                address='First DHCP Interface ip', dynamic=True)
                
        :param str,Location location_ref: href or Location element
        :param address: string repesenting address
        :param bool dynamic: whether address is dynamic or static
        :param bool overwrite_existing: whether to keep existing locations or
            to overwrite default: False
        :return: None
        :raises: ActionCommandFailed
        """
        json=[{'location_ref': location_helper(location_ref),
              'address': address,
              'dynamic': dynamic}]
        
        if not overwrite_existing:
            json.extend(addr.data for addr in self.items)
        
        return self._subelement.make_request(
            resource='contact_addresses',
            method='update',
            etag=self._etag,
            json={'contact_addresses': json})
#     
#     def create_many(self, list_of_addresses, preserve_existing=False, **kw):
#         """
#         Create many contact addresses. If preserve_existing is set
#         to true, any existing contact addresses will be preserved,
#         otherwise overwritten.
#         
#         Args should be a list in the following format::
#         
#             {
#               "multi_contact_addresses" : [ {
#                 "location_ref" : "...",
#                 "addresses" : [ "...", "..." ]
#               }, {
#                 "location_ref" : "...",
#                 "addresses" : [ "...", "..." ]
#               } ]
#             }
#         
#             external_endpoint.contact_addresses.create_many(
#                 [{'location_ref': Location, 'addresses': ['1.1.1.1'], 'dynamic': False},
#                  {'location_ref': Location2, 'addresses': ['2.2.2.2', '2.2.2.3'], 'dynamic': False}]
#         
#         :param bool preserve_existing: preserve any existing contact addresses,
#             otherwise overwrite
#         :param list kw: list of individual contact addresses in same format as
#             `create` constructor
#         :return: None
#         :raises: ActionCommandFailed
#         """
#         if preserve_existing:
#             print("Preserve the existing!")
#         
#         return self._subelement.make_request(
#             resource='contact_addresses',
#             method='update',
#             etag=self._etag,
#             json={'multi_contact_addresses': list_of_addresses})
             
    def delete(self, location=None, address=None):
        if location or address:
            pass


    
class ExternalEndpoint(SubElement):
    """
    External Endpoint is used by the External Gateway and defines the IP
    and other VPN related settings to identify the VPN peer. This is created
    to define the details of the non-SMC managed gateway. This class is a property
    of :py:class:`smc.vpn.elements.ExternalGateway` and should not be called 
    directly.
    Add an endpoint to existing External Gateway::
    
        gw = ExternalGateway('aws')
        gw.external_endpoint.create(name='aws01', address='2.2.2.2')
    
    .. versionchanged:: 0.7.0
    
        When using SMC >= 6.5, you should also provide a value for connection_type_ref when
        creating the element, for example::
    
            gw = ExternalGateway('aws')
            gw.external_endpoint.create(name='aws01', address='2.2.2.2', connection_type=ConnectionType('Active'))
    
    """
    typeof = 'external_endpoint'
    
    def create(self, name, address=None, enabled=True, ipsec_vpn=True,
               nat_t=False, force_nat_t=False, dynamic=False,
               ike_phase1_id_type=None, ike_phase1_id_value=None,
               connection_type_ref=None, **kw):
        """
        Create an test_external endpoint. Define common settings for that
        specify the address, enabled, nat_t, name, etc. You can also omit
        the IP address if the endpoint is dynamic. In that case, you must
        also specify the ike_phase1 settings.

        :param str name: name of test_external endpoint
        :param str address: address of remote host
        :param bool enabled: True|False (default: True)
        :param bool ipsec_vpn: True|False (default: True)
        :param bool nat_t: True|False (default: False)
        :param bool force_nat_t: True|False (default: False)
        :param bool dynamic: is a dynamic VPN (default: False)
        :param int ike_phase1_id_type: If using a dynamic endpoint, you must
            set this value. Valid options: 0=DNS name, 1=Email, 2=DN, 3=IP Address
        :param str ike_phase1_id_value: value of ike_phase1_id. Required if
            ike_phase1_id_type and dynamic set.
        :param ConnectionType connection_type_ref: SMC>=6.5 setting. Specifies the
            mode for this endpoint; i.e. Active, Aggregate, Standby
        :raises CreateElementFailed: create element with reason
        :return: newly created element
        :rtype: ExternalEndpoint
        """
        json = {'name': name,
                'address': address,
                'dynamic': dynamic,
                'enabled': enabled,
                'nat_t': nat_t,
                'force_nat_t': force_nat_t,
                'ipsec_vpn': ipsec_vpn}
        
        json.update(kw)
        if dynamic:
            json.pop('address')
            json.update(
                ike_phase1_id_type=ike_phase1_id_type,
                ike_phase1_id_value=ike_phase1_id_value)
        
        if connection_type_ref:
            json.update(connection_type_ref=element_resolver(connection_type_ref))
        
        return ElementCreator(
            self.__class__,
            href=self.href,
            json=json)

    @classmethod
    def update_or_create(cls, external_gateway, name, with_status=False, **kw):
        """
        Update or create external endpoints for the specified external gateway.
        An ExternalEndpoint is considered unique based on the IP address for the
        endpoint (you cannot add two external endpoints with the same IP). If the
        external endpoint is dynamic, then the name is the unique identifier.
        
        :param ExternalGateway external_gateway: external gateway reference
        :param str name: name of the ExternalEndpoint. This is only used as
            a direct match if the endpoint is dynamic. Otherwise the address
            field in the keyword arguments will be used as you cannot add
            multiple external endpoints with the same IP address.
        :param bool with_status: If set to True, returns a 3-tuple of
            (ExternalEndpoint, modified, created), where modified and created
            is the boolean status for operations performed.
        :param dict kw: keyword arguments to satisfy ExternalEndpoint.create
            constructor
        :raises CreateElementFailed: Failed to create external endpoint with reason
        :raises ElementNotFound: If specified ExternalGateway is not valid
        :return: if with_status=True, return tuple(ExternalEndpoint, created). Otherwise
            return only ExternalEndpoint.
        """
        if 'address' in kw:
            external_endpoint = external_gateway.external_endpoint.get_contains(
                '({})'.format(kw['address']))
        else:
            external_endpoint = external_gateway.external_endpoint.get_contains(name)
        
        updated = False
        created = False
        if external_endpoint:  # Check for changes
            if 'connection_type_ref' in kw: # 6.5 only
                kw.update(connection_type_ref=element_resolver(kw.pop('connection_type_ref')))
            
            for name, value in kw.items(): # Check for differences before updating
                if getattr(external_endpoint, name, None) != value:
                    external_endpoint.data[name] = value
                    updated = True
            if updated:
                external_endpoint.update()
        else:
            external_endpoint = external_gateway.external_endpoint.create(
                name, **kw)
            created = True
        
        if with_status:
            return external_endpoint, updated, created
        return external_endpoint

    @property
    def force_nat_t(self):
        """
        Whether force_nat_t is enabled on this endpoint.

        :rtype: bool
        """
        return self.data.get('force_nat_t')

    @property
    def enabled(self):
        """
        Whether this endpoint is enabled.

        :rtype: bool
        """
        return self.data.get('enabled')

    def enable_disable(self):
        """
        Enable or disable this endpoint. If enabled, it will be disabled
        and vice versa.

        :return: None
        """
        self.update(enabled=True) if not self.enabled else \
            self.update(enabled=False)

    def enable_disable_force_nat_t(self):
        """
        Enable or disable NAT-T on this endpoint. If enabled, it will be
        disabled and vice versa.

        :return: None
        """
        self.update(force_nat_t=True) if not self.force_nat_t else \
            self.update(force_nat_t=False)
    
    @property
    def contact_addresses(self):
        """
        Contact Addresses are a mutable collection of contact addresses
        assigned to a supported element.
        
        :rtype: ElementContactAddress
        """
        return ElementContactAddress(self.make_request(
            resource='contact_addresses', raw_result=True), self)


class VPNSite(SubElement):
    """
    VPN Site information for an internal or test_external gateway
    Sites are used to encapsulate hosts or networks as 'protected' for VPN
    policy configuration.

    Create a new vpn site for an engine::

        engine = Engine('myengine')
        network = Network('network-192.168.5.0/25') #get resource
        engine.vpn.sites.create('newsite', [network.href])

    Sites can also be added to ExternalGateway's as well::
    
        extgw = ExternalGateway('mygw')
        extgw.vpn_site.create('newsite', [Network('foo')])

    This class is a property of :py:class:`smc.core.engine.InternalGateway`
    or :py:class:`smc.vpn.elements.ExternalGateway` and should not be accessed
    directly.
    
    :ivar InternalGateway,ExternalGateway gateway: gateway referenced
    """
    typeof = 'vpn_site'
    gateway = ElementRef('gateway')
    
    def create(self, name, site_element):
        """
        Create a VPN site for an internal or external gateway

        :param str name: name of site
        :param list site_element: list of protected networks/hosts
        :type site_element: list[str,Element]
        :raises CreateElementFailed: create element failed with reason
        :return: href of new element
        :rtype: str
        """
        site_element = element_resolver(site_element)
        json = {
            'name': name,
            'site_element': site_element}
        
        return ElementCreator(
            self.__class__,
            href=self.href,
            json=json)
    
    @classmethod
    def update_or_create(cls, external_gateway, name, site_element=None,
            with_status=False):
        """
        Update or create a VPN Site elements or modify an existing VPN
        site based on value of provided site_element list. The resultant
        VPN site end result will be what is provided in the site_element
        argument (can also be an empty list to clear existing).
        
        :param ExternalGateway external_gateway: The external gateway for
            this VPN site
        :param str name: name of the VPN site
        :param list(str,Element) site_element: list of resolved Elements to
            add to the VPN site
        :param bool with_status: If set to True, returns a 3-tuple of
            (VPNSite, modified, created), where modified and created
            is the boolean status for operations performed.
        :raises ElementNotFound: ExternalGateway or unresolved site_element
        """
        site_element = [] if not site_element else site_element
        site_elements = [element_resolver(element) for element in site_element]
        vpn_site = external_gateway.vpn_site.get_exact(name)
        updated = False
        created = False
        if vpn_site: # If difference, reset
            if set(site_elements) != set(vpn_site.data.get('site_element', [])):
                vpn_site.data['site_element'] = site_elements
                vpn_site.update()
                updated = True
            
        else:
            vpn_site = external_gateway.vpn_site.create(
                name=name, site_element=site_elements)
            created = True
        
        if with_status:
            return vpn_site, updated, created
        return vpn_site
                
    @property
    def name(self):
        name = super(VPNSite, self).name
        if not name:
            return self.data.get('name')
        return name
    
    @property
    def site_element(self):
        """
        Site elements for this VPN Site.

        :return: Elements used in this VPN site
        :rtype: list(Element)
        """
        return [Element.from_href(element)
                for element in self.data.get('site_element')]

    def add_site_element(self, element):
        """
        Add a site element or list of elements to this VPN.

        :param list element: list of Elements or href's of vpn site
            elements
        :type element: list(str,Network)
        :raises UpdateElementFailed: fails due to reason
        :return: None
        """
        element = element_resolver(element)
        self.data['site_element'].extend(element)
        self.update()

       
class VPNProfile(Element):
    """
    A VPN Profile is used to specify cryptography and other Policy VPN specific
    features. Every PolicyVPN requires a VPNProfile. The system will provide
    common profiles labeled as System Element that can be used without
    modification.
    """
    typeof = 'vpn_profile'

    @classmethod
    def create(cls, name, comment=None, **kw):
        """
        Create a VPN Profile. There are a variety of kwargs that can
        can be and also retrieved about a VPN Profile. Keyword parameters
        are specified below. To access a valid keyword, use the standard
        dot notation.
        
        To validate supported keyword attributes for a VPN Profile, consult
        the native SMC API docs for your version of SMC. You can also optionally
        print the element contents after retrieving the element and use
        `update` to modify the element.
        
        For example::
        
            vpn = VPNProfile.create(name='mySecureVPN', comment='test comment')
            pprint(vars(vpn.data))
        
        Then once identifying the attribute, update the relevant top level
        attribute values::
        
            vpn.update(sa_life_time=128000, tunnel_life_time_seconds=57600)
        
        :param str name: Name of profile
        :param str comment: optional comment
        :raises CreateElementFailed: failed creating element with reason
        :rtype: VPNProfile
        """
        kw.update(name=name, comment=comment)
        return ElementCreator(cls, json=kw)
    
    @property
    def capabilities(self):
        """
        Capabilities are all boolean values that specify features or
        cryptography features to enable or disable on this VPN profile.
        To update or change these values, you can use the built in `update`
        with a key of 'capabilities' and dict value of attributes, i.e::
        
            vpn = VPNProfile('mySecureVPN')
            pprint(vpn.capabilities) # <-- show all options
            vpn.update(capabilities={'sha2_for_ipsec': True, 'sha2_for_ike': True})
        
        :rtype: dict
        """
        return self.data.get('capabilities', {})


class ConnectionType(Element):
    """
    .. versionadded:: 0.7.0
        Introduced in SMC 6.5 to provide a way to group VPN element types
    
    ConnectionTypes are used in various VPN configurations such as an
    ExternalGateway endpoint element to define how the endpoint should
    be treated, i.e. active, aggregate or standby.
    
    :ivar int connectivity_group: connectivity group for this connection type
    :ivar str mode: mode, valid options: 'active', 'aggregate', 'standby'
    """
    typeof = 'connection_type'
    
    @classmethod
    def create(cls, name, mode='active', connectivity_group=1, comment=None):
        return ElementCreator(cls,
            json={'name': name,
                  'mode': mode,
                  'comment': comment,
                  'connectivity_group': connectivity_group})
        

        