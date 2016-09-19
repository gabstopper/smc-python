""" 
Element module holding logic to add network elements to SMC. 
All element's are a subclass of SMCElement (is-a). The create() function for each
element type class will generate the proper json for the given element type and returning that
element. The results can then be sent to the SMC through the :mod:`smc.api.common.create`. The
result will be the href for the newly created object.

See SMCElement for more details:
 
:class:`smc.elements.element.SMCElement` for more details.

"""
import collections
import smc.actions.search as search
import smc.api.common
from smc.api.exceptions import SMCOperationFailure
from smc.elements.util import find_link_by_name

Meta = collections.namedtuple("Meta", ["name", "href", "type"])
    
class SMCElement(object):
    """ 
    SMCElement represents the data structure for sending data to
    the SMC API. When calling :mod:`smc.api.common` methods for 
    create, update or delete, this is the required object type.
    
    Common parameters that are needed are stored in this base class
    and are stored as instance attributes:
    
    :ivar json: json data to be sent to SMC
    :ivar etag: required for modify
    :ivar name: name of object
    :ivar href: (required) location of the resource
    :ivar params: If additional URI parameters are needed for href
    """
    def __init__(self, meta=None, **kwargs):
        self.name = None
        self.json = None
        self.etag = None
        self.href = None
        self.params = None
        if meta:
            kwargs.update(meta._asdict())
    
        for key, value in kwargs.iteritems():
            setattr(self, key, value)
            
    def create(self):
        if self.href is None:
            if hasattr(self, 'typeof'):
                #retrieve href from class attribute if available
                self.href = search.element_entry_point(self.typeof)
        #return getattr(smc.api.common, 'create')(self)
        return smc.api.common.create(self)
    
    def update(self):
        return smc.api.common.update(self)
    
    def describe(self):
        """
        Return the json representation of the SMCElement. Useful for
        reviewing to identify key/values that then can be 
        used for modify_attribute.
        
        :return: raw json of SMCElement
        """
        return search.element_by_href_as_json(self.href)
            
    def modify_attribute(self, **kwargs):
        """
        Modify attribute/s of an existing element. The proper way to
        get the context of the element is to use the 'describe' functions
        in :py:class:`smc.elements.collection` class.
        For example, to change the name and IP of an existing host
        object::
        
        for host in describe_hosts(name=['myhost']):
            h.modify_attribute(name='kiley', address='1.1.2.2')
        
        This method will acquire the full json along with etag and href 
        to put the element in context. Most element attributes can be
        modified, with exception of attributes listed as read-only. Common
        attributes can be found in class level documentation.
        
        :param kwargs: key=value pairs to change element attributes
        :return: SMCResult
        """
        result = smc.api.common.fetch_json_by_href(self.href)
        self.json = result.json
        self.etag = result.etag
        for k, v in kwargs.iteritems():
            self.json.update({k: v})
        return self.update()

    def __repr__(self):
        return '{0}(name={1})'.format(self.__class__.__name__, 
                                      self.name.encode('UTF8'))

   
class Host(SMCElement):
    """ Class representing a Host object used in access rules
    
    :param str name: Name of element
    :param str ip: ip address of host object
    :param str secondary_ip: secondary ip address (optional)
    :param str comment: optional comment
    
    Create a host element::
    
        Host('myhost', '1.1.1.1', '1.1.1.2', 'some comment for my host').create()
    """
    typeof = 'host'
    
    def __init__(self, name, address, 
                 secondary_ip=None, comment=None):
        SMCElement.__init__(self)
        secondary = []
        if secondary_ip:
            secondary.append(secondary_ip)
        comment = comment if comment else ''
        self.json = {'name': name,
                     'address': address,
                     'secondary': secondary,
                     'comment': comment }

class Group(SMCElement):
    """ Class representing a Group object used in access rules
    
    :param str name: Name of element
    :param list members: group members by element names
    :param str comment: optional comment
    
    Create a group element::
    
        Group('mygroup').create() #no members
        
    Group with members::
    
        Group('mygroup', ['member1','member2']).create()
    """
    typeof = 'group'
    
    def __init__(self, name, members=None, comment=None):
        SMCElement.__init__(self)
        member_lst = []
        if members:
            member_lst.extend(members)
        comment = comment if comment else ''
        self.json = {'name': name,
                     'element': member_lst,
                     'comment': comment }       

class AddressRange(SMCElement):
    """ Class representing a IpRange object used in access rules
    
    :param str name: Name of element
    :param str iprange: iprange of element
    :param str comment: optional comment
    
    Create an address range element::
    
        IpRange('myrange', '1.1.1.1-1.1.1.5').create()
    """
    typeof = 'address_range'
    
    def __init__(self, name, iprange, comment=None):
        SMCElement.__init__(self)        
        comment = comment if comment else ''
        self.json = {'name': name,
                     'ip_range': iprange,
                     'comment': comment }

class Router(SMCElement):
    """ Class representing a Router object used in access rules
    
    :param str name: Name of element
    :param str address: ip address of host object
    :param str secondary_ip: secondary ip address (optional)
    :param str comment: optional comment
    
    Create a router element::
    
        Router('myrouter', '1.2.3.4', comment='my router comment').create()
    """
    typeof = 'router'
    
    def __init__(self, name, address, 
                 secondary_ip=None, comment=None):
        SMCElement.__init__(self)
        secondary = []
        if secondary_ip:
            secondary.append(secondary_ip)       
        comment = comment if comment else ''
        self.json = {'name': name,
                     'address': address,
                     'secondary': secondary }

class Network(SMCElement):
    """ Class representing a Network object used in access rules   
    
    :param str name: Name of element
    :param str ip4_network: network cidr
    :param str comment: optional comment   

    Create a network element::
    
        Network('mynetwork', '2.2.2.0/24').create()
        
    .. note:: ip4_network must be in CIDR format
    """
    typeof = 'network'
    
    def __init__(self, name, ip4_network, comment=None):
        SMCElement.__init__(self)        
        comment = comment if comment else ''
        self.json = {'name': name,
                     'ipv4_network': ip4_network,
                     'comment': comment }

class DomainName(SMCElement):
    """ Represents a domain name used as FQDN in policy
    Use this object to reference a DNS resolvable FQDN or
    partial domain name to be used in policy.
    
    :param str name: name of domain, i.e. lepages.net, www.lepages.net
    
    Create a domain based network element::
    
        DomainName('mydomain.net').create()
    """
    typeof = 'domain_name'
    
    def __init__(self, name, comment=None):
        SMCElement.__init__(self)
        comment = comment if comment else ''
        self.json = {'name': name,
                     'comment': comment}

class TCPService(SMCElement):
    """ Represents a TCP based service in SMC
    TCP Service can use a range of ports or single port. If using
    single port, set only min_dst_port. If using range, set both
    min_dst_port and max_dst_port. 
    
    :param str name: name of tcp service
    :param int min_dst_port: minimum destination port value
    :param int max_dst_port: maximum destination port value
    
    Create a TCP Service for port 5000::
    
        TCPService('tcpservice', 5000, comment='my service').create()
    """
    typeof = 'tcp_service'
    
    def __init__(self, name, min_dst_port, max_dst_port=None,
                 comment=None):
        SMCElement.__init__(self)
        comment = comment if comment else ''
        max_dst_port = max_dst_port if max_dst_port is not None else ''
        self.json = {'name': name,
                     'min_dst_port': min_dst_port,
                     'max_dst_port': max_dst_port,
                     'comment': comment }

class UDPService(SMCElement):
    """ Represents a UDP based service in SMC
    TCP Service can use a range of ports or single port. If using
    single port, set only min_dst_port. If using range, set both
    min_dst_port and max_dst_port. 
    
    :param str name: name of udp service
    :param int min_dst_port: minimum destination port value
    :param int max_dst_port: maximum destination port value
    
    Create a UDP Service for port range 5000-5005::
    
        UDPService('udpservice', 5000, 5005).create()
    """
    typeof = 'udp_service'
    
    def __init__(self, name, min_dst_port, max_dst_port=None,
                 comment=None):
        SMCElement.__init__(self)
        comment = comment if comment else ''
        max_dst_port = max_dst_port if max_dst_port is not None else ''
        self.json = {'name': name,
                     'min_dst_port': min_dst_port,
                     'max_dst_port': max_dst_port,
                     'comment': comment }

class IPService(SMCElement):
    """ Represents an IP-Proto service in SMC
    IP Service is represented by a protocol number. This will display
    in the SMC under Services -> IP-Proto. It may also show up in 
    Services -> With Protocol if the protocol is tied to a Protocol Agent.
    
    :param str name: name of ip-service
    :param int protocol_number: ip proto number for this service
    
    Create an IP Service for protocol 93 (AX.25)::
    
        IPService('ipservice', 93).create()
    """
    typeof = 'ip_service'
    
    def __init__(self, name, protocol_number, comment=None):
        SMCElement.__init__(self)
        comment = comment if comment else ''
        self.json = {'name': name,
                     'protocol_number': protocol_number,
                     'comment': comment }

class EthernetService(SMCElement): #TODO: Error 500 Database problem
    """ Represents an ethernet based service in SMC
    Ethernet service only supports adding 'eth'2 frame type. 
    Ethertype should be the ethernet2 ethertype code in decimal 
    (hex to decimal) format
    
    **Not Yet Fully Implemented**
    """
    typeof = 'ethernet_service'
    
    def __init__(self, name, frame_type='eth2', ethertype=None, comment=None):
        SMCElement.__init__(self)
        comment = comment if comment else ''
        self.json = {'frame_type': frame_type,
                     'name': name,
                     'value1': ethertype,
                     'comment': comment }

class Protocol(SMCElement):
    """ Represents a protocol module in SMC 
    Add is not possible 
    """
    typeof = 'protocol'
    
    def __init__(self):
        SMCElement.__init__(self)
        pass

class ICMPService(SMCElement):
    """ Represents an ICMP Service in SMC
    Use the RFC icmp type and code fields to set values. ICMP
    type is required, icmp code is optional but will make the service
    more specific if type codes exist.
    
    :param str name: name of service
    :param int icmp_type: icmp type field
    :param int icmp_code: icmp type code
    
    Create an ICMP service using type 3, code 7 (Dest. Unreachable)::
    
        ICMPService('api-icmp', 3, 7).create()
    """
    typeof = 'icmp_service'
    
    def __init__(self, name, icmp_type, icmp_code=None, comment=None):
        SMCElement.__init__(self)
        comment = comment if comment else ''
        icmp_code = icmp_code if icmp_code else ''
        self.json = {'name': name,
                     'icmp_type': icmp_type,
                     'icmp_code': icmp_code,
                     'comment': comment }

class ICMPIPv6Service(SMCElement):
    """ Represents an ICMPv6 Service type in SMC
    Set the icmp type field at minimum. At time of writing the
    icmp code fields were all 0.
    
    :param str name: name of service
    :param int icmp_type: ipv6 icmp type field
    
    Create an ICMPv6 service for Neighbor Advertisement Message::
    
        ICMPIPv6Service('api-Neighbor Advertisement Message', 139).create()
    """
    typeof = 'icmp_ipv6_service'
    
    def __init__(self, name, icmp_type, comment=None):
        SMCElement.__init__(self)
        comment = comment if comment else ''
        self.json = {'name': name,
                     'icmp_type': icmp_type,
                     'comment': comment }

class ServiceGroup(SMCElement):
    """ Represents a service group in SMC. Used for grouping
    objects by service. Services can be "mixed" TCP/UDP/ICMP/
    IPService, Protocol or other Service Groups.
    Element is an href to the location of the resource.
    
    :param str name: name of service group
    :param list element: list of elements to add to service group
    
    Create a TCP and UDP Service and add to ServiceGroup::
    
        tcp1 = TCPService('api-tcp1', 5000).create()
        udp1 = UDPService('api-udp1', 5001).create()
        ServiceGroup('servicegroup', element=[tcp1.href, udp1.href]).create()
    """
    typeof = 'service_group'
    
    def __init__(self, name, element=None, comment=None):
        SMCElement.__init__(self)
        comment = comment if comment else ''
        elements = []
        if element:
            elements.extend(element)
        self.json = {'name': name,
                     'element': elements,
                     'comment': comment }

class TCPServiceGroup(SMCElement):
    """ Represents a TCP Service group
    
    :param str name: name of tcp service group
    :param list element: tcp services by href
    
    Create TCP Services and add to TCPServiceGroup::
    
        tcp1 = TCPService('api-tcp1', 5000).create()
        tcp2 = TCPService('api-tcp2', 5001).create()
        ServiceGroup('servicegroup', element=[tcp1.href, tcp2.href]).create()
    """ 
    typeof = 'tcp_service_group'
       
    def __init__(self, name, element=None, comment=None):
        SMCElement.__init__(self)
        comment = comment if comment else ''
        elements = []
        if element:
            elements.extend(element)
        self.json = {'name': name,
                     'element': elements,
                     'comment': comment }

class UDPServiceGroup(SMCElement):
    """ UDP Service Group 
    Used for storing UDP Services or UDP Service Groups.
    
    :param str name: name of service group
    :param list element: UDP services or service group by reference
    
    Create two UDP Services and add to UDP service group::
    
        udp1 = UDPService('udp-svc1', 5000).create()
        udp2 = UDPService('udp-svc2', 5001).create()
        UDPServiceGroup('udpsvcgroup', element=[udp1.href, udp2.href]).create()
    """
    typeof = 'udp_service_group'
    
    def __init__(self, name, element=None, comment=None):
        SMCElement.__init__(self)
        comment = comment if comment else ''
        elements = []
        if element:
            elements.extend(element)
        self.json = {'name': name,
                     'element': elements,
                     'comment': comment }

class IPServiceGroup(SMCElement):
    """ IP Service Group
    Used for storing IP Services or IP Service Groups
    
    :param str name: name of service group
    :param list element: IP services or IP service groups by ref
    """
    typeof = 'ip_service_group'
    
    def __init__(self, name, element=None, comment=None):
        SMCElement.__init__(self)
        comment = comment if comment else ''
        elements = []
        if element:
            elements.extend(element)
        self.json = {'name': name,
                     'element': elements,
                     'comment': comment }

class Location(SMCElement):
    """
    Locations are used by elements to identify when they are behind a NAT
    connection. For example, if you have an engine that connects to the SMC
    across the internet using a public address, a location will be the tag
    applied to the Management Server (with contact address) and on the engine
    to identify how to connect. In this case, the location will map to a contact
    address using a public IP.
    
    :param str name: name of location
    
    .. note:: Locations require SMC API version >= 6.1
    """
    typeof = 'location'

    def __init__(self, name):
        SMCElement.__init__(self)
        self.json = {'name': name}
        
class SecurityGroup(SMCElement):
    pass

class Country(SMCElement):
    pass

class URLListApplication(SMCElement):
    pass

class IPListGroup(SMCElement):
    pass

class IPList(SMCElement):
    pass
    
class Zone(SMCElement):
    """ Class representing a zone used on physical interfaces and
    used in access control policy rules
    
    :param str zone: name of zone
    
    Create a zone::
        
        Zone('myzone').create()
    """
    typeof = 'interface_zone'
    
    def __init__(self, zone):
        SMCElement.__init__(self)
        self.json = {'name': zone}
  
class LogicalInterface(SMCElement):
    """
    Logical interface is used on either inline or capture interfaces. If an
    engine has both inline and capture interfaces (L2 Firewall or IPS role),
    then you must use a unique Logical Interface on the interface type.
    
    :param str name: name of logical interface
    
    Create a logical interface::
    
        LogicalInterface('mylogical_interface').create()    
    """
    typeof = 'logical_interface'
    
    def __init__(self, name, comment=None):
        SMCElement.__init__(self)        
        comment = comment if comment else ''
        self.json = {'name': name,
                     'comment': comment }

class AdminUser(SMCElement):
    """ Represents an Adminitrator account on the SMC
    Use the constructor to create the user. 
    
    :param name: name of admin
    :param boolean local_admin: should be local admin on specified engines
    :param boolean allow_sudo: allow sudo on specified engines
    :param boolean superuser: is a super user (no restrictions) in SMC
    :param admin_domain: reference to admin domain, shared by default
    :param list engine_target: ref to engines for local admin access
    
    Create an Admin::
        
        admin = AdminUser(name='dlepage', superuser=True).create()
        
    If modifications are required after you can load the admin and
    make changes::
    
        for x in collection.describe_admin_users():
            if x.name == 'dlepage':
                admin = x.load()
                admin.change_password('mynewpassword1')
                admin.enable_disable()
    """
    typeof = 'admin_user'
    
    def __init__(self, name, local_admin=False, allow_sudo=False, 
                 superuser=False, admin_domain=None, enabled=True,
                 engine_target=None, href=None, meta=None, **kwargs):
        SMCElement.__init__(self)
        self.name = name
        self.meta = meta
        self.href = href
        engines = []
        if engine_target:
            engines.extend(engine_target)
        self.json = {'name': name,
                     'enabled': enabled,
                     'allow_sudo': allow_sudo,
                     'engine_target': engines,
                     'local_admin': local_admin,
                     'superuser': superuser }
    
    def load(self):
        """
        Load Admin by name
        """
        if not self.meta:
            self.meta = Meta(**search.element_info_as_json(self.name))
        result = search.element_by_href_as_smcresult(self.meta.href)
        if result:
            self.json = result.json
        return self
    
        result = search.element_as_smcresult_use_filter(
                                            self.name, self.typeof)
        self.etag = result.etag
        for k, v in result.json.iteritems():
            self.json.update({k: v})
        return self
 
    @property
    def link(self):
        return self.json.get('link')

    def change_password(self, password):
        """ Change admin password 
        
        :method: PUT
        :param str password: new password
        :return: SMCResult
        """
        self.href = find_link_by_name('change_password', self.link)
        self.params = {'password': password}
        return self.update()
           
    def change_engine_password(self, password):
        """ Change Engine password for engines on allowed
        list.
        
        :method: PUT
        :param str password: password for engine level
        :return: SMCResult
        """
        self.href = find_link_by_name('change_engine_password', self.link)
        self.params = {'password': password}
        pass
    
    def enable_disable(self):
        """ Toggle enable and disable of administrator account
        
        :method: PUT
        :return: SMCResult
        """
        self.href = find_link_by_name('enable_disable', self.link)
        return self.update()
        
    def export(self, filename='admin.zip'): #TODO: This fails, SMC error
        """ Export the contents of this admin
        
        :method: POST
        :param str filename: Name of file to export to
        :return: SMCResult
        """
        self.href = find_link_by_name('export', self.link)
        self.params = {}
        element = self.create()
        try:
            href = next(smc.api.common.async_handler(
                                            element.json.get('follower'), 
                                            display_msg=False))    
        except SMCOperationFailure, e:
            return e.smcresult
        else:
            return smc.api.common.fetch_content_as_file(href, filename)
            
    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, "name={}".format(self.name)) 
    
class Blacklist(SMCElement):
    """ Add a blacklist entry by source / destination
    A blacklist can be added directly from the engine node, or from
    the system context. If submitting from the system context, it becomes
    a global blacklist.
    
    :param src: source address, with cidr, i.e. 10.10.10.10/32
    :param dst: destination address with cidr
    :param int duration: length of time to blacklist
    """
    def __init__(self, src, dst, duration=3600, name=None):
        SMCElement.__init__(self)
        self.json = {'name': name,
                     'duration': duration,
                     'end_point1': {'name': '', 'address_mode': 'address',
                                    'ip_network': src},
                     'end_point2': {'name': '', 'address_mode': 'address',
                                    'ip_network': dst}}

class ContactAddress(SMCElement):
    """
    Contact Addresses are used to by Locations to identify the IP address/es 
    assigned to the location. This identifies how an engine, SMC, Log Server, 
    or any element can be contacted when behind a NAT connection.
    
    :param list addresses: list of IP addresses for contact address
    :param str location: location href to map this contact address to
    """
    def __init__(self, addresses, location):
        SMCElement.__init__(self)
        assert(isinstance(addresses, list))
        self.json = {'addresses': addresses,
                     'location': location }