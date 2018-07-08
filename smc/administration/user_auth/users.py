"""
.. versionadded:: 0.6.2
    Requires SMC 6.4.3

The Users module provides an interface to user specific related elements such
as External LDAP domains, Internal domains and external/internal users and 
external/internal groups.

Example of browsing all available external ldap user domains::

    >>> from smc.administration.user_auth.users import ExternalLdapUserDomain
    >>> for domain in ExternalLdapUserDomain.objects.all():
    ...   domain
    ... 
    ExternalLdapUserDomain(name=lepages)

If you know the name of the domain or want to load it directly, do so like other elements::

    >>> ldap = ExternalLdapUserDomain('lepages')
    >>> ldap.ldap_server
    [ActiveDirectoryServer(name=dc)]
    
Find all groups in a specified LDAP domain::

    >>> ldap
    ExternalLdapUserDomain(name=lepages)
    >>> ldap.browse()
    [ExternalLdapUserGroup(name=Computers), ExternalLdapUserGroup(name=Domain Controllers),
     ExternalLdapUserGroup(name=ForeignSecurityPrincipals), ExternalLdapUserGroup(name=Managed Service Accounts),
     ExternalLdapUserGroup(name=Program Data), ExternalLdapUserGroup(name=System), ExternalLdapUserGroup(name=Users),
     ExternalLdapUserGroup(name=resource users)]

Find all users in specific LDAP user group::

    >>> for group in ldap.browse():
    ...   if group.name == 'Users':
    ...     group.browse()
    ... 
    [ExternalLdapUser(name=Administrator), ExternalLdapUserGroup(name=Allowed RODC Password Replication Group),
     ExternalLdapUserGroup(name=Cert Publishers), ExternalLdapUserGroup(name=Cisco ISE Wireless),
     ExternalLdapUserGroup(name=Cloneable Domain Controllers), ExternalLdapUserGroup(name=DHCP Administrators),
     ExternalLdapUserGroup(name=DHCP Users)
     ...

.. note:: Depending on your LDAP directory structure, groups may yield other groups as in the example above


Internal domains, groups and users are configured statically within the SMC. By default, the SMC
comes with an example `InternalDomain` domain configured. 

.. note:: The SMC only supports a single Internal User Domain

Example of fetching an internal domain, browsing it's contents and iterating over the
users and groups to delete a user named 'testuser'::

    >>> from smc.administration.user_auth.users import InternalUserDomain
    >>> domain = InternalUserDomain('InternalDomain')
    >>> domain.browse()
    [InternalUserGroup(name=Mobile VPN users), InternalUserGroup(name=testgroup), InternalUser(name=testuser)]
    >>> for user in domain.browse():
    ...   if user.name == 'testuser':
    ...     user.delete()
    ... 
    >>> domain.browse()
    [InternalUserGroup(name=Mobile VPN users), InternalUserGroup(name=testgroup)]

"""
from smc.base.model import Element, ElementCreator, UserElement
from smc.base.util import element_resolver


class Browseable(object):
    """
    Domain users represents common methods used by Internal and LDAP
    domains to fetch user accounts
    """
    def browse(self):
        """
        Browse the elements nested below this Domain or Group.
        Results could be internal users or groups.
        
        :return: list of Element by type
        :rtype: list
        """
        return [Element.from_meta(**element)
            for element in self.make_request(resource='browse')]
    
    def get_users(self, users):
        """
        Get users from this LDAP domain. User format must be in 
        fully qualified DN syntax, for example::
        
            cn=administrator,cn=users,dc=domain,dc=local
        
        :param list users: users in fully qualified DN syntax
        :raises UserElementNotFound: invalid specified user or domain doesn't exist
        :return: list of users
        :rtype: list(ExternalLdapUser,InternalUser)
        """
        if self.typeof == 'external_ldap_user_domain':
            user_type = ExternalLdapUser
        else:
            user_type = InternalUser

        return [user_type.get('{},domain={}'.format(user, self.name))
            for user in users]
    
    def get_groups(self, groups):
        """
        Get groups from this LDAP domain. Group format must be in 
        fully qualified DN syntax, for example::
        
            cn=domain users,cn=users,dc=lepages,dc=local
            cn=myuser,dc=stonegate
        
        :param list groups: groups in fully qualified DN syntax
        :raises UserElementNotFound: invalid specified group or domain doesn't exist
        :return: list of LDAP groups
        :rtype: list(ExternalLdapUserGroup,InternalUserGroup)
        """
        if self.typeof == 'external_ldap_user_domain':
            user_type = ExternalLdapUserGroup
        else:
            user_type = InternalUserGroup
        
        return [user_type.get('{},domain={}'.format(group, self.name))
            for group in groups]


class InternalUserDomain(Browseable, Element):
    """
    This represents the default internal user Domain. There is one internal
    user domain per SMC. This domain can be used to create users and groups
    that would allow authentication when not using external authentication
    through ExternalLdapUserDomain's.
    """
    typeof = 'internal_user_domain'
        

class ExternalLdapUserDomain(Browseable, Element):
    typeof = 'external_ldap_user_domain'
    
    @classmethod
    def create(cls, name, ldap_server, isdefault=False, auth_method=None, comment=None):
        """
        Create an External LDAP user domain. These are used as containers for
        retrieving user and groups from the configured LDAP server/s. If you
        have multiple authentication methods supported for your LDAP server,
        or have none configured, you can set the `auth_method` to
        a supported AuthenticationMethod.
        
        :param str name: name of external LDAP domain
        :param list(str,ActiveDirectoryServer) ldap_server: list of existing
            authentication servers in href or element format
        :param bool isdefault: set this to 'Default LDAP domain'
        :param str,AuthenticationMethod auth_method: authentication method to
            use. Usually set when multiple are defined in LDAP service or
            none are defined.
        :param str comment: optional comment
        :raises CreateElementFailed: failed to create
        :rtype: ExternalLdapUserDomain
        """
        return ElementCreator(cls,
            json={'name': name, 'ldap_server': element_resolver(ldap_server),
                  'auth_method': element_resolver(auth_method),
                  'isdefault': isdefault, 'comment': comment})
    
    @classmethod
    def update_or_create(cls, with_status=False, **kwargs):
        """
        Update or create LDAP User Domain
        
        :param dict kwargs: kwargs to satisfy the `create` constructor arguments
            if the element doesn't exist or attributes to change
        :raises CreateElementFailed: failed creating element
        :raises ElementNotFound: referenced elements are not found
        :return: element instance by type or 3-tuple if with_status set
        """
        if 'ldap_server' in kwargs:
            kwargs.update(ldap_server=element_resolver(kwargs.pop('ldap_server')))
        
        element, updated, created = super(ExternalLdapUserDomain, cls).update_or_create(
            with_status=True, **kwargs)
        
        if with_status:
            return element, updated, created
        return element

    @property
    def auth_method(self):
        """
        Default authentication method for this LDAP User Domain. Can
        also be set on the LDAP server as well.
        
        :rtype: AuthenticationMethod
        """
        return Element.from_href(self.data.get('auth_method'))
    
    @property
    def base_dn(self):
        pass
    
    @property
    def ldap_server(self):
        """
        LDAP Servers associated with this ExternalLdapUserDomain. You must
        have at least one ldap server but can have multiple.
        
        :rtype: ActiveDirectoryServer
        """
        return [Element.from_href(server) for server in self.data.get('ldap_server', [])]

    
class ExternalLdapUserGroup(Browseable, UserElement):
    """
    This represents an external LDAP Group defined on an external LDAP server.
    Retrieving an external LDAP group can be done by specifying the full DN
    of the group::
    
    ExternalLdapUserGroup.get('cn=Users,dc=lepages,dc=local,domain=lepages')
    
    :ivar str name: name of ldap user
    :ivar str unique_id: the fully qualified DN for the group
    """
    typeof = 'external_ldap_user_group'

    
class ExternalLdapUser(UserElement):
    """
    This represents an external LDAP User defined on an external LDAP server.
    
    :ivar str name: name of ldap user
    :ivar str unique_id: the fully qualified DN for the user
    """
    typeof = 'external_ldap_user'


class InternalUser(UserElement):
    """
    This represents an internal user defined within the SMC only
    You can retrieve an internal user by referencing it by either
    name::
    
        InternalUser('myuser')
        
    or by getting using full dn::
    
        InternalUser.get('cn=myuser,cn=mygroup,domain=myinternaldomain')
    
    :ivar str name: name of user
    :ivar str unique_id: the fully qualified DN for the user
    """
    typeof = 'internal_user'

    @classmethod
    def create(cls, name, user_dn):
        """
        Create an internal user. When creating a user be sure to include
        the internal domain as `domain=` to map to the proper group.
        
        Provide the full user DN in format:
            `cn=myuser,cn=mygroup,domain=myinternaldomain`
        
        Add a user example::
        
            InternalUser.create(
                name='goog',user_dn='cn=goog,dc=stonegate,domain=InternalDomain')
            
        :param str name: name of user that is displayed in SMC    
        :param str user_dn: user DN to add. It is expected that the
            internal group and domain exist
        :rtype: InternalUser
        """
        #TODO: Can't add user to user group
        json = {'name': name, 'unique_id': user_dn}
        return ElementCreator(cls, json)

        
class InternalUserGroup(Browseable, UserElement):
    """
    This represents an internal user group defined within the SMC only
    You can retrieve an internal user by referencing it by either
    name::
    
        InternalUserGroup('Mobile VPN users')
        
    or by getting using full dn::
    
        InternalUserGroup.get('cn=Mobile VPN users,dc=stonegate,domain=InternalDomain')
    
    :ivar str name: name of user
    :ivar str unique_id: the fully qualified DN for the user
    """
    typeof = 'internal_user_group'
    
    @classmethod
    def create(cls, name=None, user_dn=None):
        """
        Create an internal group. When creating a group be sure to include
        the internal domain as `domain=` to map to the proper group. The
        name is typically the same value as the CN.
        
        Provide the full group DN in format:
            `cn=mynewgroup,dc=stonegate,domain=InternalDomain`
        
        Example of creating an internal user group in the InternalDomain and
        under the group stonegate::
        
            InternalUserGroup.create(
                name='testgroup', user_dn='cn=testgroup,dc=stonegate,domain=InternalDomain')
    
        :param str name: Name of group
        :param user_dn: User DN for the group with CN value equal to the name of the group
            You must also provide domain to specify which internal domain to create the group
        :raises CreateElementFailed: failed to create user group
        :rtype: InternalUserGroup
        """
        return ElementCreator(cls, json={'name': name, 'unique_id': user_dn})
    
