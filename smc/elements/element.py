""" 
Element module holding logic to add network elements to SMC. Network elements 
subclass SMCElement. 
SMCElement base class is generic and acts as a dispatcher class that uses 
CRUD operations to add, remove or modify elements that can be called from the
child classes of SMCElement.

Elements can be retrieved through either describe_* methods, or if you know the
name of the element, by loading it directly. 

By using describe methods::

    for host in describe_host():
        print host
        
:py:class:`smc.elements.collection` for more details.

Loading directly::

    host = Host('myhost')
    
Once the element is in context, it is possible to perform available operations on 
that element. 

For example, to delete an element by name::

    Host('myhost').delete()
    
Or view the details of the element::

    Host('myhost').describe()

"""
from collections import namedtuple
import smc.actions.search as search
from smc.api.common import SMCRequest
from smc.elements.mixins import ModifiableMixin, ExportableMixin, UnicodeMixin
from smc.elements.util import find_link_by_name, \
    bytes_to_unicode, unicode_to_bytes
from smc.api.exceptions import MissingRequiredInput, ElementNotFound

class ElementLocator(object):
    """
    There are two ways to get an elements location, either through the 
    describe_xxx methods which is then stored in the instance meta attribute, 
    or by specifying the resource directly. Elements not using this descriptor 
    are loaded through meta by a reference of a top level related object.
    
    If the element is going to be loaded directly, it must have a class attribute
    'typeof' to specify the element type. That is used in this descriptor as a 
    search filter to find the href location of the element. 
    """
    def __get__(self, instance, cls=None):
        #Does the instance already have meta data
        if instance.meta:
            return instance.meta.href
        else:
            if hasattr(instance, 'typeof'):
                element = search.element_info_as_json_with_filter(
                                                instance.name, instance.typeof)
                if element:
                    instance.meta = Meta(**element[0])
                    return instance.meta.href
                raise ElementNotFound('Cannot find specified element: {}, type: {}'
                                      .format(unicode_to_bytes(instance.name), 
                                              instance.typeof))
            else:
                raise ElementNotFound('This class does not have the required attribute '
                                      'and cannot be referenced directly, type: {}'
                                      .format(instance))

class Meta(namedtuple('Meta', 'name href type')):
    """
    Internal namedtuple used to store top level element information. When 
    doing base level searches, SMC API will return only meta data for the
    element that has name, href and type.
    Meta has the same data structure returned from 
    :py:func:`smc.actions.search.element_info_as_json`
    """
    def __new__(cls, href, name=None, type=None): # @ReservedAssignment
        return super(Meta, cls).__new__(cls, name, href, type)

class SMCElement(UnicodeMixin, ExportableMixin, ModifiableMixin):
    """
    SMCElement is the base class for all network and other elements.
    This base class acts as a dispatcher and encapsulates features common
    to all elements. Each SMCElement sub-class has a class attribute 'typeof'
    which is the SMC entry point for elements of that type.
    
    :ivar meta: meta data for element
    :ivar name: name of object
    :ivar href: location of the resource
    """
    href = ElementLocator()
    
    def __init__(self, name, meta=None, **kwargs):
        self._name = name #<str>
        self.meta = meta
    
    @property
    def name(self):
        return bytes_to_unicode(self._name)
    
    @classmethod
    def _create(cls):
        return SMCRequest(
                    href=search.element_entry_point(cls.typeof),
                    json=cls.json).create()

    def _read(self, href=None):
        return SMCRequest(href=href, **vars(self)).read()

    def delete(self):
        """
        Delete the element
        
        :return: :py:class:`smc.api.web.SMCResult`
        """
        return SMCRequest(href=self.href).delete()

    def describe(self):
        """
        Show the element details, all json
        
        :return: dict of element json
        """
        return search.element_by_href_as_json(self.href)

    @property
    def link(self):
        result = search.element_by_href_as_json(self.href)
        return result.get('link')
    
    def __unicode__(self):
        return u'{0}(name={1})'.format(self.__class__.__name__, self.name)
  
    def __repr__(self):
        return repr(unicode(self))

class Host(SMCElement):
    """ 
    Class representing a Host object used in access rules
    
    Create a host element with ipv4::
    
        Host.create(name='myhost', address='1.1.1.1', 
                    secondary_ip=['1.1.1.2'], 
                    comment='some comment for my host')
    
    Create a host element with ipv6 and secondary ipv4 address::
        
        Host.create(name='mixedhost', 
                    ipv6_address='2001:cdba::3257:9652', 
                    secondary_ip=['1.1.1.1'])

    .. note:: either ipv4 or ipv6 address is required
    """
    typeof = 'host'
    
    def __init__(self, name, meta=None):
        SMCElement.__init__(self, name, meta)
        pass
    
    @classmethod
    def create(cls, name, address=None, ipv6_address=None, 
               secondary_ip=None, comment=None):
        """
        Create the host element
        
        :param str name: Name of element
        :param str address: ipv4 address of host object (optional if ipv6)
        :param str ipv6_address: ipv6 address (optional if ipv4)
        :param str secondary_ip: secondary ip address (optional)
        :param str comment: comment (optional)
        :return: :py:class:`smc.api.web.SMCResult`
        """
        address = None if address is None else address
        ipv6_address = None if ipv6_address is None else ipv6_address
        secondary = [] if secondary_ip is None else secondary_ip
        comment = comment if comment else ''
        cls.json = {'name': name,
                    'address': address,
                    'ipv6_address': ipv6_address,
                    'secondary': secondary,
                    'comment': comment}
        return cls._create()

class Group(SMCElement):
    """ 
    Class representing a Group object used in access rules
    Groups can hold other network element types as well as
    other groups.

    Create a group element::
    
        Group.create('mygroup') #no members
        
    Group with members::
    
        Group.create('mygroup', ['member1','member2'])
    """     
    typeof = 'group'

    def __init__(self, name, meta=None):
        SMCElement.__init__(self, name, meta)
        pass
        
    @classmethod
    def create(cls, name, members=None, comment=None):
        """
        Create the group
        
        :param str name: Name of element
        :param list members: group members by element names
        :param str comment: optional comment
        :return: :py:class:`smc.qpi.web.SMCResult`
        """
        comment = None if comment is None else comment
        members = [] if members is None else members
        cls.json = {'name': name,
                    'element': members,
                    'comment': comment}
        return cls._create()
        
    def update_members(self, members):
        """
        Update group members with member list. This will overwrite 
        previous group members. If the intent is to add/remove specific
        members, call :meth:`~obtain_members`, save the list and rebuild a new
        list, then call :meth:`~update_members`.
        
        :param list members: list of new members for group
        :return: :py:class:`smc.api.web.SMCResult`
        """
        self.modify_attribute(element=members)
    
    def obtain_members(self):
        """
        Obtain all group members from this group
        
        :return: list of group members referenced in group
        """
        return self.link.get('element')
    
    def empty_members(self):
        """
        :return: None
        """
        self.modify_attribute(element=[])

class AddressRange(SMCElement):
    """ 
    Class representing a IpRange object used in access rules
    
    Create an address range element::
    
        IpRange.create('myrange', '1.1.1.1-1.1.1.5')
    """
    typeof = 'address_range'
    
    def __init__(self, name, meta=None):
        SMCElement.__init__(self, name, meta)        
        pass
    
    @classmethod
    def create(cls, name, iprange, comment=None):
        """
        Create an AddressRange element
        
        :param str name: Name of element
        :param str iprange: iprange of element
        :param str comment: comment (optional)
        :return: :py:class:`smc.api.web.SMCResult`
        """
        comment = comment if comment else ''
        cls.json = {'name': name,
                    'ip_range': iprange,
                    'comment': comment}
        return cls._create()

class Router(SMCElement):
    """ 
    Class representing a Router object used in access rules
    
    Create a router element with ipv4 address::
    
        Router.create('myrouter', '1.2.3.4', comment='my router comment')
        
    Create a router element with ipv6 address::
        
        Host.create(name='mixedhost', 
                    ipv6_address='2001:cdba::3257:9652')
    
    .. note:: either ipv4 or ipv6 address is required
    """
    typeof = 'router'
    
    def __init__(self, name, meta=None):
        SMCElement.__init__(self, name, meta)
        pass
        
    @classmethod
    def create(cls, name, address=None, ipv6_address=None, 
               secondary_ip=None, comment=None):
        """
        Create the router element
        
        :param str name: Name of element
        :param str address: ip address of host object (optional if ipv6)
        :param str ipv6_address: ipv6 address (optional if ipv4)
        :param str secondary_ip: secondary ip address (optional)
        :param str comment: comment (optional)
        :return: :py:class:`smc.api.web.SMCResult`
        """ 
        address = None if address is None else address
        ipv6_address = None if ipv6_address is None else ipv6_address   
        secondary = [] if secondary_ip is None else secondary_ip 
        comment = comment if comment else ''
        cls.json = {'name': name,
                    'address': address,
                    'ipv6_address': ipv6_address,
                    'secondary': secondary }
        return cls._create()

class Network(SMCElement):
    """ 
    Class representing a Network object used in access rules
    Network format should be CIDR based.  
    
    Create an ipv4 network element::
    
        Network.create('mynetwork', '2.2.2.0/24')
    
    Create an ipv6 network element:
    
        Network.create(name='mixednetwork', ipv6_network='fc00::/7')
    
    .. note:: either an ipv4_network or ipv6_network must be specified
    """
    typeof = 'network'
    
    def __init__(self, name, meta=None):
        SMCElement.__init__(self, name, meta) 
        pass       
        
    @classmethod
    def create(cls, name, ipv4_network=None, ipv6_network=None, 
               comment=None):
        """
        Create the network element
        
        :param str name: Name of element
        :param str ipv4_network: network cidr (optional if ipv6)
        :param str ipv6_network: network cidr (optional if ipv4)
        :param str comment: comment (optional)
        :return: :py:class:`smc.api.web.SMCResult` 
        """
        ipv4_network = None if ipv4_network is None else ipv4_network
        ipv6_network = None if ipv6_network is None else ipv6_network
        comment = comment if comment else ''
        cls.json = {'name': name,
                    'ipv4_network': ipv4_network,
                    'ipv6_network': ipv6_network,
                    'comment': comment}
        return cls._create()

class DomainName(SMCElement):
    """ 
    Represents a domain name used as FQDN in policy
    Use this object to reference a DNS resolvable FQDN or
    partial domain name to be used in policy.
    
     Create a domain based network element::
    
        DomainName.create('mydomain.net')
    """
    typeof = 'domain_name'
    
    def __init__(self, name, meta=None):
        SMCElement.__init__(self, name, meta)
        pass
    
    @classmethod
    def create(cls, name, comment=None):
        """
        Create domain name element
        
        :param str name: name of domain, i.e. lepages.net, www.lepages.net
        :return: :py:class:`smc.api.web.SMCResult`
        """
        comment = comment if comment else ''
        cls.json = {'name': name,
                    'comment': comment}
        return cls._create()

class TCPService(SMCElement):
    """ 
    Represents a TCP based service in SMC
    TCP Service can use a range of ports or single port. If using
    single port, set only min_dst_port. If using range, set both
    min_dst_port and max_dst_port. 
    
    Create a TCP Service for port 5000::
    
        TCPService.create('tcpservice', 5000, comment='my service')
    """
    typeof = 'tcp_service'
    
    def __init__(self, name, meta=None):
        SMCElement.__init__(self, name, meta)
        pass
        
    @classmethod
    def create(cls, name, min_dst_port, max_dst_port=None,
               comment=None):
        """
        Create the TCP service
        
        :param str name: name of tcp service
        :param int min_dst_port: minimum destination port value
        :param int max_dst_port: maximum destination port value
        :return: :py:class:`smc.api.web.SMCResult`
        """
        comment = comment if comment else ''
        max_dst_port = max_dst_port if max_dst_port is not None else ''
        cls.json = {'name': name,
                    'min_dst_port': min_dst_port,
                    'max_dst_port': max_dst_port,
                    'comment': comment}
        return cls._create()

class UDPService(SMCElement):
    """ 
    UDP Services can use a range of ports or single port. If using
    single port, set only min_dst_port. If using range, set both
    min_dst_port and max_dst_port. 
    
    Create a UDP Service for port range 5000-5005::
    
        UDPService('udpservice', 5000, 5005).create()
    """
    typeof = 'udp_service'
    
    def __init__(self, name, meta=None):
        SMCElement.__init__(self, name, meta)
        pass
        
    @classmethod
    def create(cls, name, min_dst_port, max_dst_port=None,
               comment=None):
        """
        Create the UDP Service
        
        :param str name: name of udp service
        :param int min_dst_port: minimum destination port value
        :param int max_dst_port: maximum destination port value
        :return: :py:class:`smc.api.web.SMCResult`
        """
        comment = comment if comment else ''
        max_dst_port = max_dst_port if max_dst_port is not None else ''
        cls.json = {'name': name,
                    'min_dst_port': min_dst_port,
                    'max_dst_port': max_dst_port,
                    'comment': comment}
        return cls._create()

class IPService(SMCElement):
    """ 
    Represents an IP-Proto service in SMC
    IP Service is represented by a protocol number. This will display
    in the SMC under Services -> IP-Proto. It may also show up in 
    Services -> With Protocol if the protocol is tied to a Protocol Agent.
    
    Create an IP Service for protocol 93 (AX.25)::
    
        IPService('ipservice', 93).create()
    """
    typeof = 'ip_service'
    
    def __init__(self, name, meta=None):
        SMCElement.__init__(self, name, meta)
        pass
        
    @classmethod
    def create(cls, name, protocol_number, comment=None):
        """
        Create the IP Service
        
        :param str name: name of ip-service
        :param int protocol_number: ip proto number for this service
        :return: :py:class:`smc.api.web.SMCResult`
        """
        comment = comment if comment else ''
        cls.json = {'name': name,
                    'protocol_number': protocol_number,
                    'comment': comment}
        return cls._create()

class EthernetService(SMCElement):
    """ 
    Represents an ethernet based service in SMC
    Ethernet service only supports adding 'eth'2 frame type. 
    Ethertype should be the ethernet2 ethertype code in decimal 
    (hex to decimal) format
    
    **Not Yet Fully Implemented**
    """
    typeof = 'ethernet_service'
    
    def __init__(self, name, meta=None):
        SMCElement.__init__(self, name, meta)
        pass

    @classmethod
    def create(cls, name, frame_type='eth2', ethertype=None, comment=None):
        comment = comment if comment else ''
        cls.json = {'frame_type': frame_type,
                    'name': name,
                    'value1': ethertype,
                    'comment': comment}
        return cls._create()

class Protocol(SMCElement):
    """ Represents a protocol module in SMC 
    Add is not possible 
    """
    typeof = 'protocol'
    
    def __init__(self, name, meta=None):
        SMCElement.__init__(self, name, meta)
        pass

class ICMPService(SMCElement):
    """ 
    Represents an ICMP Service in SMC
    Use the RFC icmp type and code fields to set values. ICMP
    type is required, icmp code is optional but will make the service
    more specific if type codes exist.
    
    Create an ICMP service using type 3, code 7 (Dest. Unreachable)::
    
        ICMPService.create(name='api-icmp', icmp_type=3, icmp_code=7)
    """
    typeof = 'icmp_service'
    
    def __init__(self, name, meta=None):
        SMCElement.__init__(self, name, meta)
        pass
        
    @classmethod
    def create(cls, name, icmp_type, icmp_code=None, comment=None):
        """
        Create the ICMP service element
        
        :param str name: name of service
        :param int icmp_type: icmp type field
        :param int icmp_code: icmp type code
        :return: :py:class:`smc.api.web.SMCResult`
        """
        comment = comment if comment else ''
        icmp_code = icmp_code if icmp_code else ''
        cls.json = {'name': name,
                    'icmp_type': icmp_type,
                    'icmp_code': icmp_code,
                    'comment': comment}
        return cls._create()

class ICMPIPv6Service(SMCElement):
    """ 
    Represents an ICMPv6 Service type in SMC
    Set the icmp type field at minimum. At time of writing the
    icmp code fields were all 0.
    
    Create an ICMPv6 service for Neighbor Advertisement Message::
    
        ICMPIPv6Service.create('api-Neighbor Advertisement Message', 139)
    """
    typeof = 'icmp_ipv6_service'
    
    def __init__(self, name, meta=None):
        SMCElement.__init__(self, name, meta)
        pass
  
    @classmethod
    def create(cls, name, icmp_type, comment=None):
        """
        Create the ICMPIPv6 service element
        
        :param str name: name of service
        :param int icmp_type: ipv6 icmp type field
        :return: :py:class:`smc.qpi.web.SMCResult`
        """
        comment = comment if comment else ''
        cls.json = {'name': name,
                    'icmp_type': icmp_type,
                    'comment': comment}
        return cls._create()

class ServiceGroup(SMCElement):
    """ 
    Represents a service group in SMC. Used for grouping
    objects by service. Services can be "mixed" TCP/UDP/ICMP/
    IPService, Protocol or other Service Groups.
    Element is an href to the location of the resource.
    
    Create a TCP and UDP Service and add to ServiceGroup::
    
        tcp1 = TCPService.create('api-tcp1', 5000)
        udp1 = UDPService.create('api-udp1', 5001)
        ServiceGroup.create('servicegroup', element=[tcp1.href, udp1.href])
    """
    typeof = 'service_group'
    
    def __init__(self, name, meta=None):
        SMCElement.__init__(self, name, meta)
        pass

    @classmethod
    def create(cls, name, element=None, comment=None):
        """
        Create the TCP/UDP Service group element
        
        :param str name: name of service group
        :param list element: list of elements to add to service group
        :return: :py:class:`smc.api.web.SMCResult`
        """
        comment = comment if comment else ''
        elements = [] if element is None else element
        cls.json = {'name': name,
                    'element': elements,
                    'comment': comment}
        return cls._create()

class TCPServiceGroup(SMCElement):
    """ 
    Represents a TCP Service group
    
    Create TCP Services and add to TCPServiceGroup::
    
        tcp1 = TCPService.create('api-tcp1', 5000)
        tcp2 = TCPService.create('api-tcp2', 5001)
        ServiceGroup.create('servicegroup', element=[tcp1.href, tcp2.href])
    """ 
    typeof = 'tcp_service_group'
       
    def __init__(self, name, meta=None):
        SMCElement.__init__(self, name, meta)
        pass
        
    @classmethod
    def create(cls, name, element=None, comment=None):
        """
        Create the TCP Service group
        
        :param str name: name of tcp service group
        :param list element: tcp services by href
        :return: :py:class:`smc.api.web.SMCResult`
        """
        comment = comment if comment else ''
        elements = [] if element is None else element
        cls.json = {'name': name,
                    'element': elements,
                    'comment': comment}
        return cls._create()

class UDPServiceGroup(SMCElement):
    """ 
    UDP Service Group 
    Used for storing UDP Services or UDP Service Groups.
    
    Create two UDP Services and add to UDP service group::
    
        udp1 = UDPService.create('udp-svc1', 5000)
        udp2 = UDPService.create('udp-svc2', 5001)
        UDPServiceGroup.create('udpsvcgroup', element=[udp1.href, udp2.href])
    """
    typeof = 'udp_service_group'
    
    def __init__(self, name, meta=None):
        SMCElement.__init__(self, name, meta)
        pass
        
    @classmethod
    def create(cls, name, element=None, comment=None):
        """
        Create the UDP Service group
        
        :param str name: name of service group
        :param list element: UDP services or service group by reference
        :return: :py:class:`smc.api.web.SMCResult`
        """
        comment = comment if comment else ''
        elements = [] if element is None else element
        cls.json = {'name': name,
                    'element': elements,
                    'comment': comment}
        return cls._create()

class IPServiceGroup(SMCElement):
    """ 
    IP Service Group
    Used for storing IP Services or IP Service Groups
    
    """
    typeof = 'ip_service_group'
    
    def __init__(self, name, meta=None):
        SMCElement.__init__(self, name, meta)
        pass
        
    @classmethod
    def create(cls, name, element=None, comment=None):
        """
        Create the IP Service group element
        
        :param str name: name of service group
        :param list element: IP services or IP service groups by ref
        :return: :py:class:`smc.api.web.SMCResult`
        """
        comment = comment if comment else ''
        elements = [] if element is None else element
        cls.json = {'name': name,
                    'element': elements,
                    'comment': comment}
        return cls._create()

class ApplicationSituation(SMCElement):
    """
    Application Situations are network applications used as rule service
    parameters in policies. Applications examples are 'facebook chat', 
    'facebook plugins', etc. These transcend the layer 7 protocol being
    used (most commonly port 80 and 443) and instead provide visibility 
    into the application itself.
    """
    typeof = 'application_situation'
    
    def __init__(self, name, meta=None):
        SMCElement.__init__(self, name, meta)
        pass
    
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

    def __init__(self, name, meta=None):
        SMCElement.__init__(self, name, meta)
        pass
    
    @classmethod
    def create(cls, name):
        cls.json = {'name': name}
        return cls._create()
        
class SecurityGroup(SMCElement):
    pass

class Country(SMCElement):
    """
    .. note:: Country requires SMC API version >= 6.1
    """
    pass

class URLListApplication(SMCElement):
    """
    URL List Application represents a list of URL's (typically by domain)
    that allow for easy grouping for performing whitelist and blacklisting
    
    Creating a URL List::
    
        URLListApplication.create(name='whitelist',
                                  entry_url=['www.google.com', 'www.cnn.com'])
    
    .. note:: URLListApplication requires SMC API version >= 6.1
    """
    typeof = 'url_list_application'
    
    def __init__(self, name, meta=None):
        SMCElement.__init__(self, name, meta)
        pass
    
    @classmethod
    def create(cls, name, url_entry):
        """
        Create the custom URL list
        
        :param str name: name of url list
        :param list url_entry: list of url's
        :return: :py:class:`smc.qpi.web.SMCResult`
        """
        cls.json = {'name': name,
                    'url_entry': url_entry}
        print cls.json
        return cls._create()

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
    
        IPList.create(name='mylist')
        
    Create an IPList with initial content::
    
        IPList.create(name='mylist', iplist=['1.1.1.1','1.1.1.2', '1.2.3.4'])
        
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
    """
    typeof = 'ip_list'
    
    def __init__(self, name, meta=None):
        SMCElement.__init__(self, name, meta)
        pass

    def download(self, filename=None, as_type='zip'):
        """
        Download the IPList. List format can be either zip, text or
        json. For large lists, it is recommended to use zip encoding.
        Filename is required for zip downloads.
        
        :param str filename: Name of file to save to (required for zip)
        :param str as_type: type of format to download in: |txt|json|zip (default)
        :raises: IOError: if problem writing to destination filename
        :return: :py:class:`smc.api.web.SMCResult`
        """
        if as_type == 'zip':
            if filename is None:
                raise MissingRequiredInput('Filename must be specified when '
                                           'downloading IPList as a zip file.')
            self.headers=None
            filename = '{}'.format(filename)
        elif as_type == 'txt':
            self.headers={'accept':'text/plain'}
        elif as_type == 'json':
            self.headers = {'accept': 'application/json'}
        #Find the entry point link for the IPList
        href=find_link_by_name('ip_address_list', 
                                self.link)
        self.filename = filename
        return self._read(href=href)
    
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
        params=None
        files=None
        if filename:
            files = {'ip_addresses': open(filename, 'rb')}
        if as_type == 'json':
            headers={'accept':'application/json',
                     'content-type':'application/json'}
        elif as_type == 'txt':
            params={'format':'txt'}

        return SMCRequest(
                    href=find_link_by_name('ip_address_list', self.link),
                    headers=headers, files=files, json=json, 
                    params=params).create()

    @classmethod   
    def create(cls, name, iplist=None):
        """
        Create an IP List. It is also possible to add entries by supplying
        a list of IPs/networks, although this is optional. You can also 
        use upload/download to add to the iplist.
        
        :param str name: name of ip list
        :param list iplist: list of ipaddress
        :return: :py:class:`smc.api.web.SMCResult`
        """
        cls.json={'name': name}
        result = cls._create()
        if result.href and iplist is not None:
            #get link to ip_access_list node for this element
            links = search.element_by_href_as_json(result.href) 
            newlist = IPList(name)
            newlist.json = {'ip': iplist}
            return SMCRequest(
                        href=find_link_by_name('ip_address_list', 
                                               links.get('link')),
                        json=newlist.json).create()
        return result

class Expression(SMCElement):
    """
    Expressions are used to build boolean like objects used in policy. For example,
    if you wanted to create an expression that negates a specific set of network
    elements to use in a "NOT" rule, an expression would be the element type.
    
    For example, adding a rule that negates (network A or network B):: 
    
        sub_expression = Expression.build_sub_expression(
                            name='mytestexporession', 
                            ne_ref=['http://172.18.1.150:8082/6.0/elements/host/3999',
                                    'http://172.18.1.150:8082/6.0/elements/host/4325'], 
                            operator='union')
    
        expression = Expression.create(name='apiexpression', 
                                       ne_ref=[],
                                       sub_expression=sub_expression)
                                       
    .. note:: The sub-expression creates the json for the expression 
              (network A or network B) and is then used as an argument to create.
    """
    typeof = 'expression'
    
    def __init__(self, name, meta=None):
        SMCElement.__init__(self, name, meta)
        pass
    
    @staticmethod
    def build_sub_expression(name, ne_ref=None, operator='union'):
        """
        Static method to build and return the proper json for a sub-expression.
        A sub-expression would be the grouping of network elements used as a
        target match. For example, (network A or network B) would be considered
        a sub-expression. This can be used to compound sub-expressions before 
        calling create.
        
        :param str name: name of sub-expression
        :param list ne_ref: network elements references
        :param str operator: |exclusion (negation)|union|intersection (default: union)
        :return: JSON of subexpression. Use in :func:`~create` constructor
        """
        ne_ref = [] if ne_ref is None else ne_ref
        json = {'name': name,
                'ne_ref': ne_ref,
                'operator': operator}
        return json
    
    @classmethod
    def create(cls, name, ne_ref=None, operator='exclusion', sub_expression=None):
        """
        Create the expression
        
        :param str name: name of expression
        :param list ne_ref: network element references for expression
        :param str operator: |exclusion (negation)|union|intersection 
               (default: exclusion)
        :param dict sub_expression: sub expression used
        :return: :py:class:`smc.api.web.SMCResult`
        """
        sub_expression = [] if sub_expression is None else [sub_expression]
        cls.json = {'name':name,
                    'operator': operator,
                    'ne_ref': ne_ref,
                    'sub_expression': sub_expression}
        print cls.json
        return cls._create()
            
class Zone(SMCElement):
    """ 
    Class representing a zone used on physical interfaces and
    used in access control policy rules, typically in source and
    destination fields. Zones can be applied on multiple interfaces
    which would allow logical grouping in policy.
    
    Create a zone::
        
        Zone.create('myzone')
    """
    typeof = 'interface_zone'
    
    def __init__(self, name, meta=None):
        SMCElement.__init__(self, name, meta)
        pass
    
    @classmethod
    def create(cls, name):
        """ 
        Create the zone element
        
        :param str zone: name of zone
        :return: :py:class:`smc.api.web.SMCResult`
        """
        cls.json = {'name': name}
        return cls._create()
        
class LogicalInterface(SMCElement):
    """
    Logical interface is used on either inline or capture interfaces. If an
    engine has both inline and capture interfaces (L2 Firewall or IPS role),
    then you must use a unique Logical Interface on the interface type.

    Create a logical interface::
    
        LogicalInterface.create('mylogical_interface')  
    """
    typeof = 'logical_interface'
    
    def __init__(self, name, meta=None):
        SMCElement.__init__(self, name, meta)
        pass
    
    @classmethod
    def create(cls, name, comment=None):
        """    
        Create the logical interface
        
        :param str name: name of logical interface
        :return: :py:class:`smc.api.web.SMCResult`
        """
        comment = comment if comment else ''
        cls.json = {'name': name,
                    'comment': comment}
        return cls._create()
