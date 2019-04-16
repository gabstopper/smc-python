"""
Authentication Servers represent server definitions used to authenticate remote
users.

If you need to use Active Directory for user authentication, you can use these
modules to provision AD servers and LDAP domains. 

An example of creating an Active Directory Server instance with additional
domain controllers (you can omit the `domain_controller` attribute and the value
specified in `address` will be the only DC used)::

    ldap = AuthenticationMethod('LDAP Authentication')
    
    dc1 = DomainController(user='foo', ipaddress='1.1.1.1', password='mypassword')
    dc2 = DomainController(user='foo2', ipaddress='1.1.1.1', password='mypassword')
    
    ActiveDirectoryServer.create(
        name='myactivedirectory',
        address='10.10.10.10',
        base_dn='dc=domain,dc=net',
        bind_user_id='cn=admin,cn=users,dc=domain,dc=net',
        bind_password='somecrazypassword',
        supported_method=[ldap],    # <-- enable LDAP authentication on this service
        domain_controller=[dc1, dc2]) # <-- add additional domain controllers
        
You can find AuthenticationMethod elements using the normal collections::

    for service in AuthenticationMethod.objects.all():
        ...
        
Create an External LDAP User Domain that uses the Active Directory server/s that
exist within the SMC::

    ExternalLdapUserDomain.create(name='myldapdomain',
        ldap_server=[ActiveDirectoryServer('myactivedirectory')],
        isdefault=True)
    
The above will result in synchronizing the Active Directory users and groups into
an LDAP domain called 'myldapdomain'.

.. seealso:: :class:`smc.administration.user_auth.users`

"""

from smc.base.model import ElementCreator, Element, ElementRef, ElementList
from smc.api.exceptions import CreateElementFailed
from smc.base.structs import NestedDict
from smc.base.util import element_resolver
from smc.elements.servers import ContactAddressMixin


class AuthenticationMethod(Element):
    """
    An Authentication Service represents an authentication capability
    such as LDAP, RADIUS or TACACS+. These services are used when
    configuring server resources such as ActiveDirectoryServer, or
    user authentication settings within a policy. 
    """
    typeof = 'authentication_service'
        

class DomainController(NestedDict):
    """
    Represents a domain controller element that can be used to provide
    additional domain controllers for an Active Directory configuration.
    
    :param str user: username for authentication
    :param str ipaddress: ip address for domain controller
    :param str password: password for AD domain controller
    :param str server_type: required for SMC version >=6.5. Value can be
        'dc' or 'exchange'.
    :param int expiration_time: required for SMC version >=6.5. Value
        specifies how long how user ID should be considered valid. For
        example 28800 is 8 hours
    """
    def __init__(self, user, ipaddress, password, **kw):
        dc = dict(user=user,
                  ipaddress=ipaddress,
                  password=password,
                  **kw)
        super(DomainController, self).__init__(data=dc)
    
    def __eq__(self, other):
        if isinstance(other, DomainController):
            return other.user == self.user and other.ipaddress == self.ipaddress
        return False
    
    def __ne__(self, other):
        return not self == other
    
    def __repr__(self):
        return 'DomainController(ipaddress={})'.format(self.ipaddress)


class ActiveDirectoryServer(ContactAddressMixin, Element):
    """
    Create an Active Directory Element.
    
    At a minimum you must provide the name, address and base_dn for the connection.
    If you do not provide bind_user_id and bind_password, the connection type will
    use anonymous authentication (not recommended).
    
    You can also pass kwargs to customize aspects of the AD server configuration.
    Valid kwargs are:
    
    :param TLSProfile tls_profile: TLS profile used when ldaps or start_tls specified
    :param str user_id_attr: The name that the server uses for the UserID Attribute
        (default: sAMAccountName)
    :param str user_principal_name: The name of the attribute for storing the users UPN
        (default: userPrincipalName)
    :param str display_name_attr_name: The attribute storing the users friendly name
        (default: displayName)
    :param str email: The attribute storing the users email address (default: email)
    :param str group_member_attr: The attribute storing group membership details
        (default: member)
    :param str job_title_attr_name: The attribute storing users job title (default: title)
    :param str frame_ip_attr_name: The attribute storing the users IP address when user
        is authenticated via RADIUS (default: msRADIUSFramedIPAddress)
    :param str mobile_attr_name: The attribute storing the users mobile (default: mobile)
    :param str office_location_attr: The attribute storing the users office location
        (default: physicalDeliveryOfficeName)
    :param str photo: The attribute with users photo used for display (default: photo)
    :param list group_object_class: If your Active Directory or LDAP server has LDAP object
        classes that are not defined in the SMC by default, you must add those object classes
        to the LDAP Object classes in the server properties (default: ['group', 'organizationUnit',
        'organization', 'country', 'groupOfNames', 'sggroup']
    :param list user_object_class: LDAP classes used for user identification (default:
        ['inetOrgPerson','organizationalPerson', 'person', 'sguser'])
    :param str client_cert_based_user_search: Not implemented
    :param int auth_port: required when internet authentication service is enabled (default: 1812)
    :param str auth_ipaddress: required when internet authentication service is enabled
    :param str shared_secret: required when internet authentication service is enabled
    :param int retries: Used with IAS. Number of times firewall will try to connect to the
        RADIUS or TACACS+ authentication server if the connection fails (default: 2)
    """
    typeof = 'active_directory_server'
    tls_profile = ElementRef('tls_profile_ref')
    supported_method = ElementList('supported_method')
    
    @classmethod
    def create(cls, name, address, base_dn, bind_user_id=None, bind_password=None,
        port=389, protocol='ldap', tls_profile=None, tls_identity=None,
        domain_controller=None, supported_method=None, timeout=10, max_search_result=0,
        page_size=0, internet_auth_service_enabled=False, retries=3, **kwargs):
        """
        Create an AD server element using basic settings. You can also provide additional
        kwargs documented in the class description::
        
            ActiveDirectoryServer.create(name='somedirectory',
                address='10.10.10.10',
                base_dn='dc=domain,dc=net',
                bind_user_id='cn=admin,cn=users,dc=domain,dc=net',
                bind_password='somecrazypassword')
        
        Configure NPS along with Active Directory::
        
            ActiveDirectoryServer.create(name='somedirectory5',
                address='10.10.10.10',
                base_dn='dc=lepages,dc=net',
                internet_auth_service_enabled=True,
                retries=3,
                auth_ipaddress='10.10.10.15',
                auth_port=1900,
                shared_secret='123456')
                
        :param str name: name of AD element for display
        :param str address: address of AD server
        :param str base_dn: base DN for which to retrieve users, format is 'dc=domain,dc=com'
        :param str bind_user_id: bind user ID credentials, fully qualified. Format is
            'cn=admin,cn=users,dc=domain,dc=com'. If not provided, anonymous bind is used
        :param str bind_password: bind password, required if bind_user_id set
        :param int port: LDAP bind port, (default: 389)
        :param str protocol: Which LDAP protocol to use, options 'ldap/ldaps/ldap_tls'. If
            ldaps or ldap_tls is used, you must provide a tls_profile element (default: ldap)
        :param str,TLSProfile tls_profile by element of str href. Used when protocol is set
            to ldaps or ldap_tls
        :param str,TLSIdentity tls_identity: check server identity when establishing TLS connection
        :param list(DomainController) domain_controller: list of domain controller objects to
            add an additional domain controllers for AD communication
        :param list(AuthenticationMethod) supported_method: authentication services allowed
            for this resource
        :param int timeout: The time (in seconds) that components wait for the server to reply
        :param int max_search_result: The maximum number of LDAP entries that are returned in
            an LDAP response (default: 0 for no limit)
        :param int page_size: The maximum number of LDAP entries that are returned on each page
            of the LDAP response. (default: 0 for no limit)
        :param bool internet_auth_service_enabled: whether to attach an NPS service to this
            AD controller (default: False). If setting to true, provide kwargs values for
            auth_ipaddress, auth_port and shared_secret
        :raises CreateElementFailed: failed creating element
        :rtype: ActiveDirectoryServer
        """
        json={'name': name, 'address': address, 'base_dn': base_dn,
              'bind_user_id': bind_user_id, 'bind_password': bind_password,
              'port': port, 'protocol': protocol, 'timeout': timeout,
              'domain_controller': domain_controller or [], 'retries': retries,
              'max_search_result': max_search_result, 'page_size': page_size,
              'internet_auth_service_enabled': internet_auth_service_enabled,
              'supported_method': element_resolver(supported_method) or []}
        
        for obj_class in ('group_object_class', 'user_object_class'):
            json[obj_class] = kwargs.pop(obj_class, [])
        
        if protocol in ('ldaps', 'ldap_tls'):
            if not tls_profile:
                raise CreateElementFailed('You must provide a TLS Profile when TLS '
                    'connections are configured to the AD controller.')
            json.update(tls_profile_ref=element_resolver(tls_profile),
                        tls_identity=tls_identity)
        
        if internet_auth_service_enabled:
            ias = {'auth_port': kwargs.pop('auth_port', 1812),
                   'auth_ipaddress': kwargs.pop('auth_ipaddress', ''),
                   'shared_secret': kwargs.pop('shared_secret')}
            json.update(ias)
        
        json.update(kwargs)
        return ElementCreator(cls, json)
    
    @classmethod
    def update_or_create(cls, with_status=False, **kwargs):
        """
        Update or create active directory configuration.
        
        :param dict kwargs: kwargs to satisfy the `create` constructor arguments
            if the element doesn't exist or attributes to change
        :raises CreateElementFailed: failed creating element
        :return: element instance by type or 3-tuple if with_status set
        """
        element, updated, created = super(ActiveDirectoryServer, cls).update_or_create(
            defer_update=True, **kwargs)
        
        if not created:
            domain_controller = kwargs.pop('domain_controller', [])
            if domain_controller:
                current_dc_list = element.domain_controller
            for dc in domain_controller:
                if dc not in current_dc_list:
                    element.data.setdefault('domain_controller', []).append(dc.data)
                    updated = True
        
        if updated:
            element.update()
        if with_status:
            return element, updated, created
        return element

    @property
    def domain_controller(self):
        """
        List of optional domain controllers specified for this AD resource.
        When adding domain controllers through update_or_create, only domain
        controllers that do not already exist are added.
        
        :rtype: list(DomainController)
        """
        return [DomainController(**dc) for dc in self.data.get('domain_controller', [])]
    
    def check_connectivity(self):
        """
        Return a status for this active directory controller
        
        :raises ActionCommandFailed: failed to check connectivity with reason
        :rtype: bool
        """
        return self.make_request(
            href=self.get_relation('check_connectivity')) is None
        
