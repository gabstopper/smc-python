"""
Module providing service configuration and creation.

Some services may be generic services while others might provide more
in depth functionality using protocol agents. A protocol agent provides
layer 7 configuration capabilities specific to the protocol it defines.
If a given service inherits the ProtocolAgentMixin, this service type is
eligible to have a protocol agent attached.

.. seealso:: :py:mod:`smc.elements.protocols`

"""
from smc.base.model import Element, ElementCreator
from smc.elements.protocols import ProtocolAgentMixin
from smc.base.util import element_resolver


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

    @classmethod
    def create(cls, name, min_dst_port, max_dst_port=None, min_src_port=None,
               max_src_port=None, protocol_agent=None, comment=None):
        """
        Create the TCP service

        :param str name: name of tcp service
        :param int min_dst_port: minimum destination port value
        :param int max_dst_port: maximum destination port value
        :param int min_src_port: minimum source port value
        :param int max_src_port: maximum source port value
        :param str,ProtocolAgent protocol_agent: optional protocol agent for
            this service
        :param str comment: optional comment for service
        :raises CreateElementFailed: failure creating element with reason
        :return: instance with meta
        :rtype: TCPService
        """
        max_dst_port = max_dst_port if max_dst_port is not None else ''
        json = {'name': name,
                'min_dst_port': min_dst_port,
                'max_dst_port': max_dst_port,
                'min_src_port': min_src_port,
                'max_src_port': max_src_port,
                'protocol_agent_ref': element_resolver(protocol_agent) or None,
                'comment': comment}

        return ElementCreator(cls, json)


class UDPService(ProtocolAgentMixin, Element):
    """ 
    UDP Services can use a range of ports or single port. If using
    single port, set only min_dst_port. If using range, set both
    min_dst_port and max_dst_port. 

    Create a UDP Service for port range 5000-5005::

        >>> UDPService.create('udpservice', 5000, 5005)
        UDPService(name=udpservice)
        
    Available attributes:
    
    :ivar int min_dst_port: starting destination port for this service. If the
        service is a single port service, use only this field
    :ivar int max_dst_port: used in conjunction with min_dst_port for creating a
        port range service
    """
    typeof = 'udp_service'

    @classmethod
    def create(cls, name, min_dst_port, max_dst_port=None, min_src_port=None,
               max_src_port=None, protocol_agent=None, comment=None):
        """
        Create the UDP Service

        :param str name: name of udp service
        :param int min_dst_port: minimum destination port value
        :param int max_dst_port: maximum destination port value
        :param int min_src_port: minimum source port value
        :param int max_src_port: maximum source port value
        :param str,ProtocolAgent protocol_agent: optional protocol agent for
            this service
        :param str comment: optional comment
        :raises CreateElementFailed: failure creating element with reason
        :return: instance with meta
        :rtype: UDPService
        """
        max_dst_port = max_dst_port if max_dst_port is not None else ''
        json = {'name': name,
                'min_dst_port': min_dst_port,
                'max_dst_port': max_dst_port,
                'min_src_port': min_src_port,
                'max_src_port': max_src_port,
                'protocol_agent_ref': element_resolver(protocol_agent) or None,
                'comment': comment}

        return ElementCreator(cls, json)


class IPService(ProtocolAgentMixin, Element):
    """ 
    Represents an IP-Proto service in SMC
    IP Service is represented by a protocol number. This will display
    in the SMC under Services -> IP-Proto. It may also show up in 
    Services -> With Protocol if the protocol is tied to a Protocol Agent.

    Create an IP Service for protocol 93 (AX.25)::

        >>> IPService.create('ipservice', 93)
        IPService(name=ipservice)
        
    Available attributes:
    
    :ivar str protocol_number: IP protocol number for this service
    """
    typeof = 'ip_service'

    @classmethod
    def create(cls, name, protocol_number, protocol_agent=None, comment=None):
        """
        Create the IP Service

        :param str name: name of ip-service
        :param int protocol_number: ip proto number for this service
        :param str,ProtocolAgent protocol_agent: optional protocol agent for
            this service
        :param str comment: optional comment
        :raises CreateElementFailed: failure creating element with reason
        :return: instance with meta
        :rtype: IPService
        """
        json = {'name': name,
                'protocol_number': protocol_number,
                'protocol_agent_ref': element_resolver(protocol_agent) or None,
                'comment': comment}

        return ElementCreator(cls, json)
    
    @property
    def protocol_number(self):
        """
        Protocol number for this IP Service
        
        :rtype: int
        """
        return int(self.data.get('protocol_number'))
    

class EthernetService(Element):
    """ 
    Represents an ethernet based service in SMC
    Ethernet service only supports adding Ethernet II frame type. 
    
    The value1 field should be the ethernet2 ethertype hex code
    which will be converted to decimal format.

    Create an ethernet rule representing the presence of an IEEE
    802.1Q tag::

        >>> EthernetService.create(name='8021q frame', value1='0x8100')
        EthernetService(name=8021q frame)

    .. note:: Ethernet Services are only available as of SMC version 6.1.2

    """
    typeof = 'ethernet_service'

    @classmethod
    def create(cls, name, frame_type='eth2', value1=None, comment=None):
        """
        Create an ethernet service

        :param str name: name of service
        :param str frame_type: ethernet frame type, eth2
        :param str value1: hex code representing ethertype field
        :param str comment: optional comment
        :raises CreateElementFailed: failure creating element with reason
        :return: instance with meta
        :rtype: EthernetService
        """
        json = {'frame_type': frame_type,
                'name': name,
                'value1': int(value1, 16),
                'comment': comment}

        return ElementCreator(cls, json)
    
    @property
    def value1(self):
        if 'value1' in self.data:
            return hex(int(self.data.get('value1')))
    
    @value1.setter
    def value1(self, value):
        if 'value1' in self.data:
            self.data['value1'] = int(value, 16)


class RPCService(Element):
    """
    Represents an RPC service element
    """
    typeof = 'rpc_service'


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


class URLCategory(Element):
    """
    Represents a URL Category for policy. URL Categories are read only.
    To make whitelist or blacklists, use :class:`smc.elements.network.IPList`.
    """
    typeof = 'url_category'
