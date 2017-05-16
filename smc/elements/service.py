"""
Module reprenting service related elements in the SMC
"""
from smc.base.model import Element, ElementCreator


class ProtocolAgentMixin(object):
    """
    ProtocolAgentMixin is used by services that allow a protocol
    agent. 
    """
    @property
    def protocol_agent(self):
        """ Protocol Agent for this service

        :return: :py:class:`smc.elements.service.Protocol` or None
        """
        href = self.data.get('protocol_agent_ref')
        if href:
            return Element.from_href(href)


class TCPService(ProtocolAgentMixin, Element):
    """ 
    Represents a TCP based service in SMC
    TCP Service can use a range of ports or single port. If using
    single port, set only min_dst_port. If using range, set both
    min_dst_port and max_dst_port. 

    Create a TCP Service for port 5000::

        >>> TCPService.create('tcpservice', 5000, comment='my service')
        TCPService(name=tcpservice)
        
    Available attributes:
    
    :ivar int min_dst_port: starting destination port for this service. If the
        service is a single port service, use only this field
    :ivar int max_dst_port: used in conjunction with min_dst_port for creating a
        port range service.
    """
    typeof = 'tcp_service'

    def __init__(self, name, **meta):
        super(TCPService, self).__init__(name, **meta)
        pass

    @classmethod
    def create(cls, name, min_dst_port, max_dst_port=None,
               comment=None):
        """
        Create the TCP service

        :param str name: name of tcp service
        :param int min_dst_port: minimum destination port value
        :param int max_dst_port: maximum destination port value
        :raises CreateElementFailed: failure creating element with reason
        :return: instance with meta
        :rtype: TCPService
        """
        max_dst_port = max_dst_port if max_dst_port is not None else ''
        json = {'name': name,
                'min_dst_port': min_dst_port,
                'max_dst_port': max_dst_port,
                'comment': comment}

        return ElementCreator(cls, json)


class UDPService(ProtocolAgentMixin, Element):
    """ 
    UDP Services can use a range of ports or single port. If using
    single port, set only min_dst_port. If using range, set both
    min_dst_port and max_dst_port. 

    Create a UDP Service for port range 5000-5005::

        >>> UDPService('udpservice', 5000, 5005).create()
        UDPService(name=udpservice)
        
    Available attributes:
    
    :ivar int min_dst_port: starting destination port for this service. If the
        service is a single port service, use only this field
    :ivar int max_dst_port: used in conjunction with min_dst_port for creating a
        port range service.
    """
    typeof = 'udp_service'

    def __init__(self, name, **meta):
        super(UDPService, self).__init__(name, **meta)
        pass

    @classmethod
    def create(cls, name, min_dst_port, max_dst_port=None,
               comment=None):
        """
        Create the UDP Service

        :param str name: name of udp service
        :param int min_dst_port: minimum destination port value
        :param int max_dst_port: maximum destination port value
        :raises CreateElementFailed: failure creating element with reason
        :return: instance with meta
        :rtype: UDPService
        """
        max_dst_port = max_dst_port if max_dst_port is not None else ''
        json = {'name': name,
                'min_dst_port': min_dst_port,
                'max_dst_port': max_dst_port,
                'comment': comment}

        return ElementCreator(cls, json)


class IPService(ProtocolAgentMixin, Element):
    """ 
    Represents an IP-Proto service in SMC
    IP Service is represented by a protocol number. This will display
    in the SMC under Services -> IP-Proto. It may also show up in 
    Services -> With Protocol if the protocol is tied to a Protocol Agent.

    Create an IP Service for protocol 93 (AX.25)::

        >>> IPService('ipservice', 93).create()
        IPService(name=ipservice)
        
    Available attributes:
    
    :ivar str protocol_number: IP protocol number for this service
    """
    typeof = 'ip_service'

    def __init__(self, name, **meta):
        super(IPService, self).__init__(name, **meta)
        pass

    @classmethod
    def create(cls, name, protocol_number, comment=None):
        """
        Create the IP Service

        :param str name: name of ip-service
        :param int protocol_number: ip proto number for this service
        :raises CreateElementFailed: failure creating element with reason
        :return: instance with meta
        :rtype: IPService
        """
        json = {'name': name,
                'protocol_number': protocol_number,
                'comment': comment}

        return ElementCreator(cls, json)


class EthernetService(Element):
    """ 
    Represents an ethernet based service in SMC
    Ethernet service only supports adding eth2 frame type. 
    Ethertype field should be the ethernet2 ethertype hex code 
    converted into decimal format. 

    Create an ethernet rule for DEC DNS which has an ethernet type
    hex code of 803C, and a decimal conversion value of 32828:

        >>> EthernetService.create(name='myService', ethertype='32828')
        EthernetService(name=myService)

    .. note:: Ethernet Services are only available as of SMC version 6.1.2

    Available attributes:
    
    :ivar str frame_type: ethernet frame; 'eth2','llc','snap'
    :ivar str ethertype: hex string code for protocol
    """
    typeof = 'ethernet_service'

    def __init__(self, name, **meta):
        super(EthernetService, self).__init__(name, **meta)
        pass

    @classmethod
    def create(cls, name, frame_type='eth2', ethertype=None, comment=None):
        """
        Create an ethernet service

        :param str name: name of service
        :param str frame_type: ethernet frame type, eth2\|llc\|snap
        :param str ethertype: hex string code for protocol
        :param str comment: optional comment
        :raises CreateElementFailed: failure creating element with reason
        :return: instance with meta
        :rtype: EthernetService
        """
        json = {'frame_type': frame_type,
                'name': name,
                'value1': ethertype,
                'comment': comment}

        return ElementCreator(cls, json)


class Protocol(Element):
    """ 
    Represents a protocol module in SMC 
    Add is not possible 
    """
    typeof = 'protocol'

    def __init__(self, name, **meta):
        super(Protocol, self).__init__(name, **meta)
        pass


class RPCService(Element):
    """
    Represents an RPC service element
    """
    typeof = 'rpc_service'

    def __init__(self, name, **meta):
        super(RPCService, self).__init__(name, **meta)
        pass


class ICMPService(Element):
    """ 
    Represents an ICMP Service in SMC
    Use the RFC icmp type and code fields to set values. ICMP
    type is required, icmp code is optional but will make the service
    more specific if type codes exist.

    Create an ICMP service using type 3, code 7 (Dest. Unreachable)::

        >>> ICMPService.create(name='api-icmp', icmp_type=3, icmp_code=7)
        ICMPService(name=api-icmp)
        
    Available attributes:
    
    :ivar int icmp_type: icmp type field
    :ivar int icmp_code: icmp type code
    """
    typeof = 'icmp_service'

    def __init__(self, name, **meta):
        super(ICMPService, self).__init__(name, **meta)
        pass

    @classmethod
    def create(cls, name, icmp_type, icmp_code=None, comment=None):
        """
        Create the ICMP service element

        :param str name: name of service
        :param int icmp_type: icmp type field
        :param int icmp_code: icmp type code
        :raises CreateElementFailed: failure creating element with reason
        :return: instance with meta
        :rtype: ICMPService
        """
        icmp_code = icmp_code if icmp_code else ''
        json = {'name': name,
                'icmp_type': icmp_type,
                'icmp_code': icmp_code,
                'comment': comment}

        return ElementCreator(cls, json)


class ICMPIPv6Service(Element):
    """ 
    Represents an ICMPv6 Service type in SMC
    Set the icmp type field at minimum. At time of writing the
    icmp code fields were all 0.

    Create an ICMPv6 service for Neighbor Advertisement Message::

        >>> ICMPIPv6Service.create('api-Neighbor Advertisement Message', 139)
        ICMPIPv6Service(name=api-Neighbor Advertisement Message)
        
    Available attributes:
    
    :ivar int icmp_type: ipv6 icmp type field
    """
    typeof = 'icmp_ipv6_service'

    def __init__(self, name, **meta):
        super(ICMPIPv6Service, self).__init__(name, **meta)
        pass

    @classmethod
    def create(cls, name, icmp_type, comment=None):
        """
        Create the ICMPIPv6 service element

        :param str name: name of service
        :param int icmp_type: ipv6 icmp type field
        :raises CreateElementFailed: failure creating element with reason
        :return: instance with meta
        :rtype: ICMPIPv6Service
        """
        json = {'name': name,
                'icmp_type': icmp_type,
                'comment': comment}

        return ElementCreator(cls, json)


class ApplicationSituation(Element):
    """
    Application Situations are network applications used as rule service
    parameters in policies. Applications examples are 'facebook chat', 
    'facebook plugins', etc. These transcend the layer 7 protocol being
    used (most commonly port 80 and 443) and instead provide visibility 
    into the application itself.
    """
    typeof = 'application_situation'

    def __init__(self, name, **meta):
        super(ApplicationSituation, self).__init__(name, **meta)
        pass
