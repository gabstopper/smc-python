""" 
Element module holding logic to add network elements to SMC. 
Subclasses of SMCElement are objects that are individually added to the
SMC and used in other configurations. For example, Host objects would be
added and used in policies, NAT rules, etc. 
SMCElement base class is generic and more like a dispatcher class that uses 
CRUD operations to add, remove or modify elements. 

See SMCElement for more details:
 
:class:`smc.elements.element.SMCElement` for more details.

"""
from collections import namedtuple
import smc.actions.search as search
from smc.api.common import SMCRequest
from smc.elements.mixins import ModifiableMixin
from smc.elements.util import find_link_by_name
from smc.api.exceptions import MissingRequiredInput

class Meta(namedtuple('Meta', 'name href type')):
    def __new__(cls, href, name=None, type=None): # @ReservedAssignment
        return super(Meta, cls).__new__(cls, name, href, type)

class SMCElement(ModifiableMixin):
    """ 
    SMCElement represents the data structure for sending data to
    the SMC API in an SMCRequest. This object type represents most
    generic element types.
    
    Common parameters that are needed are stored in this base class
    and are stored as instance attributes:
   
    :ivar meta: meta data for element
    :ivar json: json data to be sent to SMC
    :ivar name: name of object
    :ivar href: (required) location of the resource
    """
    def __init__(self, meta=None, **kwargs):
        self.meta = meta
        self.name = None
        self.json = None
        self.href = None
        if self.meta:
            for k, v in meta._asdict().iteritems():
                setattr(self, k, v)
        
    def create(self):
        if self.href is None:
            # self.href will be None if an element is being created
            # for the first time vs. a POST after the object has been
            # created.
            if hasattr(self, 'typeof'):
                self.href = search.element_entry_point(self.typeof)
        return SMCRequest(**vars(self)).create()
    
    def update(self):
        return SMCRequest(**vars(self)).update()
    
    def delete(self):
        return SMCRequest(href=self.href).delete()
    
    def read(self):
        return SMCRequest(**vars(self)).read()
    
    def describe(self):
        """
        Return the json representation of the SMCElement. Useful for
        reviewing to identify key/values that then can be 
        used for modify_attribute.
        
        :return: raw json of SMCElement
        """
        return search.element_by_href_as_json(self.href)

    def __repr__(self):
        return '{0}(name={1})'.format(self.__class__.__name__, 
                                      self.name)

   
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
    """
    .. note:: Country requires SMC API version >= 6.1
    """
    pass

class URLListApplication(SMCElement):
    pass

class IPListGroup(SMCElement):
    """
    .. note:: IPListGroup requires SMC API version >= 6.1
    """
    pass

class IPList(SMCElement):
    """
    IPList represent a custom list of IP addresses, networks or
    ip ranges (IPv4 or IPv6). These are used in source/destination
    fields of a rule for policy enforcement.
    
    .. note:: IPList requires SMC API version >= 6.1
    
    Create an empty IPList::
    
        IPList(name='mylist').create()
        
    Create an IPList with initial content::
    
        IPList(name='mylist', iplist=['1.1.1.1','1.1.1.2', '1.2.3.4']).create()
        
    Example of downloading the IPList in text format::
    
        location = describe_ip_lists(name=[name])
        if location:
            iplist = location[0]
            iplist.download(filename='iplist.txt', as_type='txt')
  
    Example of uploading an IPList as a zip file::
    
        location = describe_ip_lists(name=[name])
        if location:
            iplist = location[0]
            iplist.upload(filename='/path/to/iplist.zip')
        
    :param str name: name of ip list
    :param list iplist: list of ipaddress
    """
    typeof = 'ip_list'
    
    def __init__(self, name, meta=None, iplist=None):
        SMCElement.__init__(self, meta=meta)
        self.name = name
        self.iplist = iplist

    def download(self, filename=None, as_type='zip'):
        """
        Download the IPList. List format can be either zip, text or
        json. For large lists, it is recommended to use zip encoding.
        Filename is required for zip downloads.
        
        :param str filename: Name of file to save to (required for zip)
        :param str as_type: type of format to download in |txt|json|zip (default)
        :raises: IOError: if problem writing to destination filename
        :return: :py:class:`smc.api.web.SMCResult`
        """
        
        if as_type == 'zip':
            if filename is None:
                raise MissingRequiredInput('Filename must be specified when '
                                           'downloading IPList as a zip file.')
            self.headers=None
            filename = '{}'.format(filename)
        elif as_type =='txt':
            self.headers={'accept':'text/plain'}
    
        self.href = find_link_by_name('ip_address_list', self.link)
        self.filename = filename
        return self.read()
    
    def upload(self, filename=None, json=None, as_type='zip'):
        """
        Upload an IPList to the SMC. The contents of the upload
        are not incremental to what is in the existing IPList.
        So if the intent is to add new entries, you must first retrieve
        the existing and append to the content, then upload.
        The only upload type that can be done without loading a file as
        the source is as_type='json'. 
        
        :param str filename: required for zip/txt uploads
        :param str json: required for json uploads
        :param str as_type: type of format to upload in: txt|json|zip (default)
        :raises: IOError: if filename specified cannot be loaded
        :return: :py:class:`smc.api.web.SMCResult`
        """      
        headers={'content-type': 'multipart/form-data'}
        files=None
        if filename:
            files = {'ip_addresses': open(filename, 'rb')}
        if as_type == 'json':
            headers={'accept':'application/json',
                     'content-type':'application/json'}
        elif as_type == 'txt': #txt
            self.params={'format':'txt'}
        self.href = find_link_by_name('ip_address_list', self.link)
        self.headers = headers
        self.files = files
        self.json = json
        return super(IPList, self).create()
       
    def create(self):
        """
        Create an IP List. It is also possible to add entries by supplying
        a list of IPs/networks, although this is optional. You can also 
        use upload/download to add to the iplist.
        """
        self.json={'name': self.name}
        result = super(IPList, self).create()
        if result.href and self.iplist:
            links = search.element_by_href_as_json(result.href)
            self.json = {'ip': self.iplist}
            self.href = find_link_by_name('ip_address_list', links.get('link'))
            return super(IPList, self).create()
        return result
    
    @property
    def link(self):
        if not self.json:
            self.json = search.element_by_href_as_json(self.meta.href)
        return self.json.get('link')
        
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