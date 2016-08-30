""" 
Element module holding logic to add network elements to SMC. 
All element's are a subclass of SMCElement (is-a). The create() function for each
element type class will generate the proper json for the given element type and returning that
element. The results can then be sent to the SMC through the :mod:`smc.api.common.create`. The
result will be the href for the newly created object.

See SMCElement for more details:
 
:class:`smc.elements.element.SMCElement` for more details.

"""
from pprint import pformat
import smc.actions.search
import smc.api.common
from smc.api.exceptions import SMCOperationFailure
    
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
    def __init__(self, **kwargs):
        self.name = None
        self.json = None
        self.etag = None
        self.href = None
        self.params = None
    
        for key, value in kwargs.items():
            setattr(self, key, value)
            
    def create(self):
        return smc.api.common.create(self)
    
    def update(self):
        return smc.api.common.update(self)
    
    def describe(self):
        """
        Return a pprint representation of the SMCElement. Useful for
        reviewing the raw json to identify key/values that then can be 
        used for modify_attribute.
        
        :return: raw json of SMCElement
        """
        return pformat(smc.actions.search.element_by_href_as_json(self.href))
            
    def modify_attribute(self, **kwargs):
        """
        Modify attribute/s of an existing element. The proper way to
        get the context of the element is to use the 'describe' functions
        in :py:class:`smc.elements.collections` class.
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
        
    def _fetch_href(self, element_type):
        self.href = smc.actions.search.element_entry_point(element_type)
        
    def __repr__(self):
        try:
            return "%s(%r)" % (self.__class__, "name={},type={}".format(
                                    self.name, self.type))
        except AttributeError:
            return "%s(%r)" % (self.__class__, "name={}".format(self.name))
    
class Host(SMCElement):
    """ Class representing a Host object used in access rules
    
    :param name: Name of element
    :param ip: ip address of host object
    :param secondary_ip: secondary ip address (optional)
    :param comment: optional comment
    
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
        self.json = {
                     'name': name,
                     'address': address,
                     'secondary': secondary,
                     'comment': comment }
        self._fetch_href(Host.typeof) 

class Group(SMCElement):
    """ Class representing a Group object used in access rules
    
    :param name: Name of element
    :param members: group members by element names
    :type members: list or None
    :param comment: optional comment
    
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
        self.json = {
                     'name': name,
                     'element': member_lst,
                     'comment': comment }       
        self._fetch_href('group')
    
class AddressRange(SMCElement):
    """ Class representing a IpRange object used in access rules
    
    :param name: Name of element
    :param iprange: iprange of element
    :type iprange: string
    :param comment: optional comment
    
    Create an address range element::
    
        IpRange('myrange', '1.1.1.1-1.1.1.5').create()
    """
    typeof = 'address_range'
    
    def __init__(self, name, iprange, comment=None):
        SMCElement.__init__(self)        
        comment = comment if comment else ''
        self.json = {
                     'name': name,
                     'ip_range': iprange,
                     'comment': comment }
        self._fetch_href('address_range')

class Router(SMCElement):
    """ Class representing a Router object used in access rules
    
    :param name: Name of element
    :param address: ip address of host object
    :type address: string
    :param secondary_ip: secondary ip address (optional)
    :param comment: optional comment
    
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
        self.json = {
                     'name': name,
                     'address': address,
                     'secondary': secondary }
        self._fetch_href('router')  

class Network(SMCElement):
    """ Class representing a Network object used in access rules   
    
    :param name: Name of element
    :param ip4_network: network cidr
    :param comment: optional comment   

    Create a network element::
    
        Network('mynetwork', '2.2.2.0/24').create()
        
    .. note:: ip4_network must be in CIDR format
    """
    typeof = 'network'
    
    def __init__(self, name, ip4_network, comment=None):
        SMCElement.__init__(self)        
        comment = comment if comment else ''
        self.json = {
                     'name': name,
                     'ipv4_network': ip4_network,
                     'comment': comment }
        self._fetch_href('network')

class DomainName(SMCElement):
    """ Represents a domain name used as FQDN in policy
    Use this object to reference a DNS resolvable FQDN or
    partial domain name to be used in policy.
    
    :param name: name of domain, i.e. lepages.net, www.lepages.net
    
    Create a domain based network element::
    
        DomainName('mydomain.net').create()
    """
    typeof = 'domain_name'
    
    def __init__(self, name, comment=None):
        SMCElement.__init__(self)
        comment = comment if comment else ''
        self.json = {
                     'name': name,
                     'comment': comment}
        self._fetch_href('domain_name')

class TCPService(SMCElement):
    """ Represents a TCP based service in SMC
    TCP Service can use a range of ports or single port. If using
    single port, set only min_dst_port. If using range, set both
    min_dst_port and max_dst_port. 
    
    :param name: name of tcp service
    :param min_dst_port: minimum destination port value
    :type min_dst_port: int
    :param max_dst_port: maximum destination port value
    :type max_dst_port: int
    
    Create a TCP Service for port 5000::
    
        TCPService('tcpservice', 5000, comment='my service').create()
    """
    typeof = 'tcp_service'
    
    def __init__(self, name, min_dst_port, max_dst_port=None,
                 comment=None):
        SMCElement.__init__(self)
        comment = comment if comment else ''
        max_dst_port = max_dst_port if max_dst_port is not None else ''
        self.json = {
                     'name': name,
                     'min_dst_port': min_dst_port,
                     'max_dst_port': max_dst_port,
                     'comment': comment }
        self._fetch_href('tcp_service')

class UDPService(SMCElement):
    """ Represents a UDP based service in SMC
    TCP Service can use a range of ports or single port. If using
    single port, set only min_dst_port. If using range, set both
    min_dst_port and max_dst_port. 
    
    :param name: name of udp service
    :param min_dst_port: minimum destination port value
    :type min_dst_port: int
    :param max_dst_port: maximum destination port value
    :type max_dst_port: int
    
    Create a UDP Service for port range 5000-5005::
    
        UDPService('udpservice', 5000, 5005).create()
    """
    typeof = 'udp_service'
    
    def __init__(self, name, min_dst_port, max_dst_port=None,
                 comment=None):
        SMCElement.__init__(self)
        comment = comment if comment else ''
        max_dst_port = max_dst_port if max_dst_port is not None else ''
        self.json = {
                     'name': name,
                     'min_dst_port': min_dst_port,
                     'max_dst_port': max_dst_port,
                     'comment': comment }
        self._fetch_href('udp_service')
    
class IPService(SMCElement):
    """ Represents an IP-Proto service in SMC
    IP Service is represented by a protocol number. This will display
    in the SMC under Services -> IP-Proto. It may also show up in 
    Services -> With Protocol if the protocol is tied to a Protocol Agent.
    
    :param name: name of ip-service
    :param protocol_number: ip proto number for this service
    :type protocol_number: int
    
    Create an IP Service for protocol 93 (AX.25)::
    
        IPService('ipservice', 93).create()
    """
    typeof = 'ip_service'
    
    def __init__(self, name, protocol_number, comment=None):
        SMCElement.__init__(self)
        comment = comment if comment else ''
        self.json = {
                     'name': name,
                     'protocol_number': protocol_number,
                     'comment': comment }
        self._fetch_href('ip_service')

class EthernetService(SMCElement): #TODO: Error 500 Database problem
    """ Represents an ethernet based service in SMC
    Ethernet service only supports adding 'eth'2 frame type. 
    Ethertype should be the ethernet2 ethertype code in decimal 
    (hex to decimal) format 
    """
    typeof = 'ethernet_service'
    
    def __init__(self, name, frame_type='eth2', ethertype=None, comment=None):
        SMCElement.__init__(self)
        comment = comment if comment else ''
        self.json = {
                     'frame_type': frame_type,
                     'name': name,
                     'value1': ethertype,
                     'comment': comment }
        self._fetch_href('ethernet_service')

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
    
    :param name: name of service
    :param icmp_type: icmp type field
    :type icmp_type: int
    :param icmp_code: icmp type code
    :type icmp_code: int
    
    Create an ICMP service using type 3, code 7 (Dest. Unreachable)::
    
        ICMPService('api-icmp', 3, 7).create()
    """
    typeof = 'icmp_service'
    
    def __init__(self, name, icmp_type, icmp_code=None, comment=None):
        SMCElement.__init__(self)
        comment = comment if comment else ''
        icmp_code = icmp_code if icmp_code else ''
        self.json = {
                     'name': name,
                     'icmp_type': icmp_type,
                     'icmp_code': icmp_code,
                     'comment': comment }
        self._fetch_href('icmp_service')

class ICMPIPv6Service(SMCElement):
    """ Represents an ICMPv6 Service type in SMC
    Set the icmp type field at minimum. At time of writing the
    icmp code fields were all 0.
    
    :param name: name of service
    :param icmp_type: ipv6 icmp type field
    :type icmp_type: int
    
    Create an ICMPv6 service for Neighbor Advertisement Message::
    
        ICMPIPv6Service('api-Neighbor Advertisement Message', 139).create()
    """
    typeof = 'icmp_ipv6_service'
    
    def __init__(self, name, icmp_type, comment=None):
        SMCElement.__init__(self)
        comment = comment if comment else ''
        self.json = {
                     'name': name,
                     'icmp_type': icmp_type,
                     'comment': comment }
        self._fetch_href('icmp_ipv6_service')

class ServiceGroup(SMCElement):
    """ Represents a service group in SMC. Used for grouping
    objects by service. Services can be "mixed" TCP/UDP/ICMP/
    IPService, Protocol or other Service Groups.
    Element is an href to the location of the resource.
    
    :param name: name of service group
    :param element: list of elements to add to service group
    :type element: list
    
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
        self.json = {
                     'name': name,
                     'element': elements,
                     'comment': comment }
        self._fetch_href('service_group')
    
class TCPServiceGroup(SMCElement):
    """ Represents a TCP Service group
    
    :param name: name of tcp service group
    :param element: tcp services by href
    :type element: list
    
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
        self.json = {
                     'name': name,
                     'element': elements,
                     'comment': comment }
        self._fetch_href('tcp_service_group')

class UDPServiceGroup(SMCElement):
    """ UDP Service Group 
    Used for storing UDP Services or UDP Service Groups.
    
    :param name: name of service group
    :param element: UDP services or service group by reference
    :type element: list
    
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
        self.json = {
                     'name': name,
                     'element': elements,
                     'comment': comment }
        self._fetch_href('udp_service_group')
    
class IPServiceGroup(SMCElement):
    """ IP Service Group
    Used for storing IP Services or IP Service Groups
    
    :param name: name of service group
    :param element: IP services or IP service groups by ref
    :type element: list
    """
    typeof = 'ip_service_group'
    
    def __init__(self, name, element=None, comment=None):
        SMCElement.__init__(self)
        comment = comment if comment else ''
        elements = []
        if element:
            elements.extend(element)
        self.json = {
                     'name': name,
                     'element': elements,
                     'comment': comment }
        self._fetch_href('ip_service_group')

class Zone(SMCElement):
    """ Class representing a zone used on physical interfaces and
    used in access control policy rules
    
    :param zone: name of zone
    
    Create a zone::
        
        Zone('myzone').create()
    """
    typeof = 'interface_zone'
    
    def __init__(self, zone):
        SMCElement.__init__(self)
        self.json = {'name': zone}
        self._fetch_href('interface_zone') 
       
class LogicalInterface(SMCElement):
    """
    Logical interface is used on either inline or capture interfaces. If an
    engine has both inline and capture interfaces (L2 Firewall or IPS role),
    then you must use a unique Logical Interface on the interface type.
    
    :param name: name of logical interface
    
    Create a logical interface::
    
        LogicalInterface('mylogical_interface').create()    
    """
    typeof = 'logical_interface'
    
    def __init__(self, name, comment=None):
        SMCElement.__init__(self)        
        comment = comment if comment else ''
        self.json = { 
                     'name': name,
                     'comment': comment }
        self._fetch_href('logical_interface')    

class AdminUser(SMCElement):
    """ Represents an Adminitrator account on the SMC
    Use the constructor to create the user. 
    
    :param name: name of admin
    :param local_admin: should be local admin on specified engines
    :type local_admin: boolean
    :param allow_sudo: allow sudo on specified engines
    :type allow_sudo: boolean
    :param superuser: is a super user (no restrictions) in SMC
    :type superuser: boolean
    :param admin_domain: reference to admin domain, shared by default
    :param engine_target: ref to engines for local admin access
    :type engine_target: list
    
    If modifications are required after, call 
    :py:func:`smc.elements.element.SMCElement.modify` then update::
    
        admin = AdminUser.modify('myadmin')
        admin.change_password('new password')
        admin.update()
    """
    def __init__(self, name, local_admin=False, allow_sudo=False, 
                 superuser=False, admin_domain=None, 
                 engine_target=None):
        SMCElement.__init__(self)
        engines = []
        if engine_target:
            engines.extend(engine_target)
        self.json = {
                    'allow_sudo': allow_sudo,
                    'enabled': True,
                    'engine_target': engines,
                    'local_admin': True,
                    'name': name,
                    'superuser': superuser }
        self._fetch_href('admin_user') 
            
    def change_password(self, password):
        """ Change admin password 
        
        :method: PUT
        :param password: new password
        :return: SMCResult
        """
        self._reset_href('change_password')
        self.params = {'password': password}
        return self.update()
           
    def change_engine_password(self, password):
        """ Change Engine password for engines on allowed
        list.
        
        :method: PUT
        :param password: password for engine level
        :return: SMCResult
        """
        self._reset_href('change_engine_password')
        self.params = {'password': password}
        pass
    
    def enable_disable(self):
        """ Toggle enable and disable of administrator account
        
        :method: PUT
        :return: SMCResult
        """
        self._reset_href('enable_disable')
        return self.update()
        
    def export(self, filename='admin.zip'): #TODO: This fails, SMC error
        """ Export the contents of this admin
        
        :param filename: Name of file to export to
        :return: SMCResult, href filled for success, msg for fail
        """
        self._reset_href('export')
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
            
    def _reset_href(self, action):
        links = self.json.get('link')
        for entry in links:
            if entry.get('rel') == action:
                self.href = entry.get('href')
                break

class Blacklist(SMCElement):
    """ Add a blacklist entry by source / destination
    Since blacklist can be applied at the engine level as well
    as system level, href will need to be set before calling create.
    
    :param src: source address, with cidr, i.e. 10.10.10.10/32
    :param dst: destination address with cidr
    :param duration: length of time to blacklist
    :type duration: int
    """
    def __init__(self, src, dst, name=None, duration=3600):
        SMCElement.__init__(self)
        self.json = {
                     'name': name,
                     'duration': duration,
                     'end_point1': {'name': '', 'address_mode': 'address',
                                    'ip_network': src},
                     'end_point2': {'name': '', 'address_mode': 'address',
                                    'ip_network': dst}
                     }

def zone_helper(zone):
    zone_ref = smc.actions.search.element_href_use_filter(zone, 'interface_zone')
    if zone_ref:
        return zone_ref
    else:
        return Zone(zone).create().href
    
def logical_intf_helper(interface):
    intf_ref = smc.actions.search.element_href_use_filter(interface, 'logical_interface')
    if intf_ref:
        return intf_ref
    else:
        return LogicalInterface(interface).create().href