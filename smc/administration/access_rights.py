"""
Access Control Lists are assigned to SMC admin accounts to grant limited
access permissions to either Engines, Policies or Domains.
"""

from smc.base.model import Element, ElementCreator
from smc.base.util import element_resolver
from smc.elements.other import AdminDomain


class AccessControlList(Element):
    """
    An ACL is assigned to an AdminUser to grant limited access permissions
    to either Engines, Policies or Domains. The access control list will have
    'granted elements' that represent the elements that apply to this
    permission. The SMC provides default ACL's that can be used or new ones
    can be created.
    Find all available ACL's::
    
        >>> AccessControlList.objects.all()

    """
    typeof = 'access_control_list'

    def __init__(self, name, **meta):
        super(AccessControlList, self).__init__(name, **meta)

    @classmethod
    def create(cls, name, granted_element=None):
        """
        Create a new ACL
        
        :param str name: Name of ACL
        :param list granted_elements: Elements to grant access to. Can be
            engines, policies or other acl's.
        :type granted_elements: list(str,Element)
        :raises CreateElementFailed: failed creating ACL
        :return: instance with meta
        :rtype: AccessControlList
        """
        granted_element = element_resolver(granted_element)
        json = {'name': name,
                'granted_element': granted_element}
    
        return ElementCreator(cls, json)

    @property
    def permissions(self):
        """
        Elements associated to this permission. Granted elements can be
        Engines, Policies or other Access Control Lists.

        :return: Element class deriving from :py:class:`smc.base.model.Element`
        """
        return [Element.from_href(e) for e in self.granted_element]

    def add_permission(self, elements):
        """
        Add permission/s to this ACL. By default this change is committed
        after the method is called.
        
        :param list elements: Elements to grant access to. Can be engines,
            policies, or other ACLs
        :type elements: list(str,Element)
        :raises UpdateElementFailed: Failed updating permissions
        :return: None
        """
        elements = element_resolver(elements)
        self.data['granted_element'].extend(elements)
        self.update()
        
    def remove_permission(self, elements):
        """    
        Remove permission/s to this ACL. Change is committed at end of
        method call.
        
        :param list elements: list of element/s to remove
        :type elements: list(str,Element)
        :raises UpdateElementFailed: Failed modifying permissions
        :return: None
        """
        elements = element_resolver(elements)
        for element in elements:
            if element in self.granted_element:
                self.data['granted_element'].remove(element)
        self.update()


class Permission(object):
    """
    Permissions are added to admin users that do not have super user access
    rights. An Admin User can also have multiple permissions. There are three
    primary fields associated with a permission:
    
    * Domain to grant access
    * Elements to grant access to (Engines, Policies or AccessControlLists)
    * Role
    
    A permission might be used to grant read-only access to specific policies
    or firewalls (read-only vs read write). It can also be specific to the 
    Admin Domain.
    """
    def __init__(self, granted_elements=None, role_ref=None,
                 granted_domain_ref=None):
        self._domain = granted_domain_ref
        self._role = role_ref
        self._elements = granted_elements
        
    @classmethod
    def create(cls, granted_elements, role, domain=None):
        """
        Create a permission.
        
        :param list granted_elements: Elements for this permission. Can
            be engines, policies or ACLs
        :type granted_elements: list(str,Element)
        :param str,Role role: role for this permission
        :param str,Element domain: domain to apply (default: Shared Domain)
        :rtype: Permission
        """
        if not domain:
            domain = AdminDomain('Shared Domain')
        json = {
            'granted_domain_ref': element_resolver(domain),
            'role_ref': element_resolver(role),
            'granted_elements': element_resolver(granted_elements)}

        return Permission(**json)
    
    @property
    def granted_elements(self):
        """
        List of elements this permission has rights to. Elements will be of type
        Engine, Policy or ACLs
        
        :rtype: list(Element)
        """
        return [Element.from_href(element) for element in self._elements]
    
    @property
    def role_ref(self):
        """
        Specific Role assigned to this permission. A role is what allows read/write
        access to specific operations on the granted elements
        
        :rtype: Role
        """
        return Element.from_href(self._role)
    
    @property
    def granted_domain_ref(self):
        """
        Domain this permission applies to. Shared Domain if unspecified.
        
        :rtype: AdminDomain
        """
        return Element.from_href(self._domain)
    
    def _as_dict(self):
        """
        Internal representation in dict format. Used when adding permission
        to AdminUser.
        """
        return {'granted_domain_ref': self._domain,
                'role_ref': self._role,
                'granted_elements': self._elements}
    
    def __repr__(self):
        return "{0}(granted_elements={1},role_ref='{2}',granted_domain_ref='{3}')"\
            .format(
                self.__class__.__name__,
                self.granted_elements,
                self.role_ref,
                self.granted_domain_ref
        )