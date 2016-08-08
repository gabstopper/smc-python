""" 
Element module holding logic to add network elements to SMC. 
All element's are a subclass of SMCElement (is-a). The create() function for each
element type class will generate the proper json for the given element type and returning that
element. The results can then be sent to the SMC through the :mod:`smc.api.common.create`. The
result will be the href for the newly created object.

See SMCElement for more details:
 
:class:`smc.elements.element.SMCElement` for more details.

"""
import smc.actions.search as search
import smc.api.common

class SMCElement(object):
    """ 
    SMCElement represents the data structure for sending data to
    the SMC API. When calling :mod:`smc.api.common` methods for 
    create, update or delete, this is the required object type.
    
    Common parameters that are needed are stored in this base class
    
    :param json: json data to be sent to SMC
    :param etag: returned during http get and used for modifying elements 
    :param name: name of object, used for str printing from api.common
    :param href: REQUIRED location of the resource
    :param params: If additional URI parameters are needed for href
    :param filename: If stream=True, this specifies name of file to save to
    """
    def __init__(self, **kwargs):
        self.json = None
        self.etag = None
        self.href = None
        self.params = None
        self.filename = None
    
        for key, value in kwargs.items():
            setattr(self, key, value)
            
    def create(self):
        return smc.api.common.create(self)
    
    def update(self):
        return smc.api.common.update(self)

    @classmethod
    def modify(cls, name, **kwargs):
        obj = cls(name, kwargs)
        obj.href = obj.href.rsplit('/', 1)[-1]
        result = search.element_as_smcresult_use_filter(obj.json.get('name'), 
                                                        obj.href)
        if result:
            obj.json = result.json
            obj.etag = result.etag
            obj.href = result.href
        else:
            obj.json = None
        return obj
        
    def _fetch_href(self, element_type):
        self.href = search.element_entry_point(element_type)
        
    def __str__(self):
        sb = []
        for key in self.__dict__:
            sb.append("{key}='{value}'".format(key=key, value=self.__dict__[key]))
        return ', '.join(sb)
  
    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)  

class Host(SMCElement):
    """ Class representing a Host object used in access rules
    
    :param name: Name of element
    :param ip: ip address of host object
    :param secondary_ip: secondary ip address (optional)
    :param comment: optional comment
    
    Create a host element::
    
        Host('myhost', '1.1.1.1', '1.1.1.2', 'some comment for my host').create()
    """
    def __init__(self, name, ip, 
                 secondary_ip=None, comment=None):
        SMCElement.__init__(self)
        secondary = []
        if secondary_ip:
            secondary.append(secondary_ip)
        comment = comment if comment else ''
        self.json = {
                     'name': name,
                     'address': ip,
                     'secondary': secondary,
                     'comment': comment }
        self._fetch_href('host') 

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
    
class IpRange(SMCElement):
    """ Class representing a IpRange object used in access rules
    
    :param name: Name of element
    :param iprange: iprange of element
    :type iprange: string
    :param comment: optional comment
    
    Create an address range element::
    
        IpRange('myrange', '1.1.1.1-1.1.1.5').create()
    """
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
    
    .. note:: ip4_network must be in CIDR format
    
    Create a network element::
    
        Network('mynetwork', '2.2.2.0/24').create()
    """
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
    def __init__(self, name, comment=None):
        SMCElement.__init__(self)
        comment = comment if comment is not None else ''
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
    def __init__(self, name, min_dst_port, max_dst_port=None,
                 comment=None):
        SMCElement.__init__(self)
        comment = comment if comment is not None else ''
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
    def __init__(self, name, min_dst_port, max_dst_port=None,
                 comment=None):
        SMCElement.__init__(self)
        comment = comment if comment is not None else ''
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
    def __init__(self, name, icmp_type, icmp_code=None, comment=None):
        SMCElement.__init__(self)
        comment = comment if comment is not None else ''
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
    def __init__(self, name, comment=None):
        SMCElement.__init__(self)        
        comment = comment if comment is not None else ''
        self.json = { 
                     'name': name,
                     'comment': comment }
        self._fetch_href('logical_interface')
    
class Blacklist(object):
    """ Add a blacklist entry by source / destination
    
    :param src: source address, with cidr, i.e. 10.10.10.10/32
    :param dst: destination address with cidr
    :param duration: length of time to blacklist
    :type duration: int
    """
    def __init__(self, src, dst, name=None, duration=3600):
        self.name = name
        self.duration = duration
        self.end_point1 = {'name': '', 'address_mode': 'address', 'ip_network': src}
        self.end_point2 = {'name': '', 'address_mode': 'address', 'ip_network': dst}
        
    def as_dict(self):
        return self.__dict__
        
class VirtualResource(object):
    def __init__(self, name, vfw_id, domain='Shared',
                 show_master_nic=False,
                 connection_limit=0):
        self.allocated_domain_ref = domain
        self.name = name
        self.connection_limit = connection_limit
        self.show_master_nic = show_master_nic
        self.vfw_id = vfw_id
        self.resolve_domain()
        
    def resolve_domain(self):
        self.allocated_domain_ref = search.element_href_use_filter(
                                        self.allocated_domain_ref, 'admin_domain')   
    def as_dict(self):
        return self.__dict__

class Administrator(SMCElement):
    def __init__(self, name, local_admin=False, allow_sudo=False, superuser=False,
                 admin_domain=None, engine_target_list=None):
        SMCElement.__init__(self)
        self.name = name
        self.local_admin = local_admin
        self.allow_sudo = allow_sudo
        self.superuser = superuser
        self.admin_domain = admin_domain
        self.engine_target_list = engine_target_list

def zone_helper(zone):
    zone_ref = smc.search.element_href_use_filter(zone, 'interface_zone')
    if zone_ref:
        return zone_ref
    else:
        return Zone(zone).create().href
    
def logical_intf_helper(interface):
    intf_ref = smc.search.element_href_use_filter(interface, 'logical_interface')
    if intf_ref:
        return intf_ref
    else:
        return LogicalInterface(interface).create().href