from smc.base.model import SubElement, SubElementCreator
from smc.api.exceptions import CreateElementFailed
from smc.base.model import Element, ElementCreator
from smc.base.collection import create_collection
from smc.base.util import element_resolver


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
    protected networks. Example of full provisioning::

        Network.create(name='mynetwork', ipv4_network='172.18.1.0/24')
        gw = ExternalGateway.create(name='mygw')
        gw.external_endpoint.create(name='myendpoint', address='10.10.10.10')
        gw.vpn_site.create(name='mysite', site_element=[Network('mynetwork')])

    """
    typeof = 'external_gateway'

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

    @property
    def vpn_site(self):
        """
        A VPN site defines a collection of IP's or networks that
        identify address space that is defined on the other end of
        the VPN tunnel.

        :return: collection of :class:`smc.vpn.elements.VPNSite`
        :rtype: create_collection
        """
        return create_collection(
            self.get_relation('vpn_site'),
            VPNSite)

    @property
    def external_endpoint(self):
        """
        An External Endpoint is the IP based definition for the
        destination VPN peers. There may be multiple per External
        Gateway. 
        Add a new endpoint to an existing test_external gateway::

            >>> list(ExternalGateway.objects.all())
            [ExternalGateway(name=cisco-remote-side), ExternalGateway(name=remoteside)]
            >>> gateway.external_endpoint.create('someendpoint', '12.12.12.12')
            'http://1.1.1.1:8082/6.1/elements/external_gateway/22961/external_endpoint/27467'

        :return: collection of :class:`smc.vpn.elements.ExternalEndpoint`
        :rtype: create_collection
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

    @property
    def gateway_profile(self):
        """
        Return the Gateway Profile for this external gateway. A gateway
        profile will define the capabilities (i.e. crypto) allowed for this VPN.

        :return: :class:`.GatewayProfile`
        """
        return Element.from_href(self.data.get('gateway_profile'))


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
    
    """
    typeof = 'external_endpoint'
    
    def create(self, name, address=None, enabled=True, balancing_mode='active',
               ipsec_vpn=True, nat_t=False, force_nat_t=False, dynamic=False,
               ike_phase1_id_type=None, ike_phase1_id_value=None):
        """
        Create an test_external endpoint. Define common settings for that
        specify the address, enabled, nat_t, name, etc. You can also omit
        the IP address if the endpoint is dynamic. In that case, you must
        also specify the ike_phase1 settings.

        :param str name: name of test_external endpoint
        :param str address: address of remote host
        :param bool enabled: True|False (default: True)
        :param str balancing_mode: active
        :param bool ipsec_vpn: True|False (default: True)
        :param bool nat_t: True|False (default: False)
        :param bool force_nat_t: True|False (default: False)
        :param bool dynamic: is a dynamic VPN (default: False)
        :param int ike_phase1_id_type: If using a dynamic endpoint, you must
            set this value. Valid options: 0=DNS name, 1=Email, 2=DN, 3=IP Address
        :param str ike_phase1_id_value: value of ike_phase1_id. Required if
            ike_phase1_id_type and dynamic set.
        :raises CreateElementFailed: create element with reason
        :return: newly created element
        :rtype: ExternalEndpoint
        """
        json = {'name': name,
                'address': address,
                'balancing_mode': balancing_mode,
                'dynamic': dynamic,
                'enabled': enabled,
                'nat_t': nat_t,
                'force_nat_t': force_nat_t,
                'ipsec_vpn': ipsec_vpn}
        
        if dynamic:
            json.pop('address')
            json.update(
                ike_phase1_id_type=ike_phase1_id_type,
                ike_phase1_id_value=ike_phase1_id_value)
        
        return SubElementCreator(
            self.__class__,
            href=self.href,
            json=json)

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
        if self.enabled:
            self.data['enabled'] = False
        else:
            self.data['enabled'] = True
        self.update()

    def enable_disable_force_nat_t(self):
        """
        Enable or disable NAT-T on this endpoint. If enabled, it will be
        disabled and vice versa.

        :return: None
        """
        if self.force_nat_t:
            self.data['force_nat_t'] = False
        else:
            self.data['force_nat_t'] = True
        self.update()


class VPNSite(SubElement):
    """
    VPN Site information for an internal or test_external gateway
    Sites are used to encapsulate hosts or networks as 'protected' for VPN
    policy configuration.

    Create a new vpn site for an engine::

        engine = Engine('myengine')
        network = Network('network-192.168.5.0/25') #get resource
        engine.vpn.sites.create('newsite', [network.href])

    This class is a property of :py:class:`smc.core.engine.InternalGateway`
    or :py:class:`smc.vpn.elements.ExternalGateway` and should not be accessed
    directly.
    """
    typeof = 'vpn_site'
    
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
        
        return SubElementCreator(
            self.__class__,
            href=self.href,
            json=json)

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

    @property
    def gateway(self):
        return Element.from_href(self.data.get('gateway'))

       
class VPNProfile(Element):
    """
    Represents a VPNProfile configuration used by the PolicyVPN
    """
    typeof = 'vpn_profile'


        