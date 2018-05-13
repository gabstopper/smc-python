"""
The Users module provides an interface to user specific related elements such
as External LDAP domains, Internal domains and external/internal users and 
external/internal groups.
"""
from smc.base.model import Element, ElementCreator, UserElement
from smc.base.util import element_resolver
from smc.api.exceptions import ElementNotFound, CreateElementFailed


class StorableUser(object):
    """
    Domain users represents common methods used by Internal and LDAP
    domains to fetch user accounts
    """
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


class InternalUserDomain(StorableUser, Element):
    """
    An internal user domain specifies users that are created and reside
    on the SMC.
    """
    typeof = 'internal_user_domain'
   

class ExternalLdapUserDomain(StorableUser, Element):
    typeof = 'external_ldap_user_domain'
    
    @classmethod
    def create(cls, name, ldap_server, isdefault=False, auth_method=None, comment=None):
        """
        Create an External LDAP user domain. These are used as containers for
        retrieving user and groups from the configured LDAP server/s. If you
        have multiple authentication methods supported for your LDAP server,
        or have none configured, you can set the `auth_method` to
        a supported AuthenticationService.
        
        :param str name: name of external LDAP domain
        :param list(str,ActiveDirectoryServer) ldap_server: list of existing
            authentication servers in href or element format
        :param bool isdefault: set this to 'Default LDAP domain'
        :param str,AuthenticationService auth_method: authentication method to
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
    def update_or_create(cls, name, with_status=False, **kwargs):
        """
        Update or create LDAP User Domain
        
        :param dict kwargs: kwargs to satisfy the `create` constructor arguments
            if the element doesn't exist or attributes to change
        :raises CreateElementFailed: failed creating element
        :raises ElementNotFound: referenced elements are not found
        :return: element instance by type or 3-tuple if with_status set
        """
        updated, created = False, False
        try:
            element = ExternalLdapUserDomain.get(name)
        except ElementNotFound:
            try:
                element = ExternalLdapUserDomain.create(name, **kwargs)
                created = True
            except TypeError:
                raise CreateElementFailed('%s: %r not found and missing '
                    'constructor arguments to properly create.' % 
                    (cls.__name__, name))
    
        if not created:
            for ldap_server in kwargs.pop('ldap_server', []):
                if ldap_server.href not in element.data.get('ldap_server', []):
                    element.data.setdefault('ldap_server', []).append(
                        ldap_server.href)
                    updated = True
            if kwargs.get('auth_method') and kwargs['auth_method'].href != \
                element.data.get('auth_method'):
                element.data['auth_method'] = kwargs.pop('auth_method').href
                updated = True
            
            if kwargs.get('comment') and kwargs['comment'] != element.comment:
                element.data['comment'] = kwargs['comment']
                updated = True
    
        if updated:
            element.update()
        
        if with_status:
            return element, updated, created    
        return element

    @property
    def auth_method(self):
        """
        Default authentication method for this LDAP User Domain. Can
        also be set on the LDAP server as well.
        
        :rtype: AuthenticationService
        """
        return Element.from_href(self.data.get('auth_method'))
    
    @property
    def ldap_server(self):
        """
        LDAP Servers associated with this ExternalLdapUserDomain. You must
        have at least one ldap server but can have multiple.
        
        :rtype: ActiveDirectoryServer
        """
        return [Element.from_href(server) for server in self.data.get('ldap_server', [])]

    
class ExternalLdapUserGroup(UserElement):
    """
    This represents an external LDAP Group defined on an external LDAP server.
    
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
        return ElementCreator(cls, json={'name': name, 'unique_id': user_dn})

        
class InternalUserGroup(UserElement):
    """
    This represents an internal user group defined within the SMC only
    
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
        
