"""
Route module encapsulates functions related to static routing and 
related configurations on NGFW
"""
from collections import namedtuple
from smc.base.model import Element, prepared_request, SubElement
from smc.base.util import find_link_by_name
from smc.api.exceptions import CreateElementFailed

class Routing(SubElement):
    """
    Routing represents the Engine routing configuration and provides the
    ability to view and add features to routing nodes such as OSPF.
    
    Routing nodes are nested, starting with the engine level. You will
    want to iterate from the top level to obtain nested routes. Most routes
    will be nested on the interface level::
    
        engine = Engine('sg_vm')
        for routing_node in engine.routing.all():
            print(routing_node, list(routing_node))
    """
    def __init__(self, data, **meta):
        super(Routing, self).__init__(**meta)
        self.add_cache(data)
    
    def __iter__(self):
        for node in self.data['routing_node']:
            yield(Routing(href=find_link_by_name('self', node.get('link')),
                          data=node))
            
    @property
    def name(self):
        """
        Interface name / ID for routing level
        
        :return: str name: name of routing node
        """
        return self.data.get('name')
            
    @property
    def ip(self):
        """
        IP network / host for this route
        
        :return: str ip: of this routing level
        """
        return self.data.get('ip')
            
    @property
    def level(self):
        """
        Routing nodes have multiple 'levels' where routes can
        be nested. Most routes are placed at the interface level.
        This setting can mostly be ignored, but provides an 
        informative view of how the route is nested.
        
        :return: str level: engine\|interface
        """
        return self.data.get('level')
        
    def add_ospf_area(self, ospf_area, 
                      communication_mode='NOT_FORCED',
                      unicast_ref=None,
                      network=None):
        """
        Add OSPF Area to this routing node.
                
        Communication mode specifies how the interface will interact with the
        adjacent OSPF environment. Please see SMC API documentation for more
        in depth information on each option.
                
        If the interface has multiple networks nested below, all networks
        will receive the OSPF area by default. OSPF cannot be applied to
        IPv6 networks.
                
        Example of adding an area to interface routing node::
                
            area = OSPFArea('area0') #obtain area resource
            
            #Get routing resources
            for interface in engine.routing.all(): 
                if interface.name == 'Interface 0':
                    interface.add_ospf_area(area)
                    
        .. note:: If UNICAST is specified, you must also provide a unicast_ref
                  to identify the remote host
                
        :param OSPFArea ospf_area: OSPF area instance or href
        :param str communication_mode: NOT_FORCED|POINT_TO_POINT|PASSIVE|UNICAST
        :param str unicast_ref: location ref of host (required for UNICAST)
        :param str network: if network specified, only add OSPF to this network on interface
        :raises: :py:class:`smc.api.exceptions.EngineCommandFailed`
        :raises: :py:class:`smc.api.exceptions.ElementNotFound`
        :return: None
        """
        if isinstance(ospf_area, Element):
            ospf_area = ospf_area.href
            
        communication_mode = communication_mode.upper()
        node = {'href': ospf_area, 
                'communication_mode': communication_mode,
                'level': 'gateway'}
        if communication_mode == 'UNICAST':
            #Need a destination ref, add to sub routing_node
            node.update(routing_node=[{'href': unicast_ref,
                                       'level': 'any'}])
            
        for networks in iter(self):
            if len(networks.ip.split(':')) == 1: #Skip IPv6
                if network is not None: #Only place on specific network
                    if networks.ip == network:
                        networks.data['routing_node'].append(node)
                else:
                    networks.data['routing_node'].append(node)
        
        prepared_request(CreateElementFailed,
                         href=self.href,
                         json=self.data,
                         etag=self.etag).update()
        
    def all(self):
        """
        Return all routes for this engine.
        
        :return: list list of route entries
        """
        return [node for node in iter(self)]
            
    def __str__(self):
        return '{0}(name={1},level={2})'.format(self.__class__.__name__, 
                                                self.name,
                                                self.level)
    def __repr__(self):
        return str(self)

def routetuple(d):
    d.pop('cluster_ref', None)
    routes = namedtuple('Route', d.keys())
    return routes(**d)
    
class Routes(object):
    """
    Routes are represented by a query to the SMC for the
    specified engine. This represents the current routing
    table.
    Route are obtained through the following method::
        
        for routes in engine.routing_monitoring.all():
            print(routes)
    
    Routes have the following attributes:
        
    :ivar int src_if: The source IF of the routing entry
    :ivar int dst_if: The destination IF of the routing entry
    :ivar str route_type: Route type specifies status (Static, Connected, etc)
    :ivar str route_network: The route network address
    :ivar int route_netmask: Network mask
    :ivar str route_gateway: The route gateway address
        
    .. note:: Not all attributes may be present.
    """
    def __init__(self, data):
        self._data = data
            
    def __iter__(self):
        for route in self._data['routing_monitoring_entry']:
            yield routetuple(route)
                
    def all(self):
        return [r for r in iter(self)]
 
class Antispoofing(SubElement):
    """
    Anti-spoofing is configured by default based on
    interface networks directly attached. It is possible
    to override these settings by adding additional
    networks as valid source networks on a given
    interface.
    
    Antispoofing is nested similar to routes. Iterate the
    antispoofing configuration::
    
        for entry in engine.antispoofing.all():
            print(entry)
    """
    def __init__(self, data, **meta):
        super(Antispoofing, self).__init__(**meta)
        self.add_cache(data)
        
    def __iter__(self):
        for node in self.data['antispoofing_node']:
            yield(Antispoofing(href=find_link_by_name('self', node.get('link')), 
                               data=node))    

    @property
    def name(self):
        """
        Name on this node level
        """
        return self.data.get('name')
        
    @property
    def ip(self):
        """
        IP network / address / host of this antispoofing entry
        
        :return: str ip: ip of this antispoofing node
        """
        return self.data.get('ip')
        
    @property
    def level(self):
        """
        Routing nodes have multiple 'levels' where routes can
        be nested. Most routes are placed at the interface level.
        This setting can mostly be ignored, but provides an 
        informative view of how the route is nested.
        
        :return: str level: engine\|interface
        """
        return self.data.get('level')
        
    @property
    def validity(self):
        """
        Enabled or disabled antispoofing entry
        
        :return: str validity: enable\|disable\|absolute
        """
        return self.data.get('validity')
        
    def add(self, entry):
        """
        Add an entry to this antispoofing node level. 
        Entry can be either href or network elements specified
        in :py:class:`smc.elements.network`
            
        ::

            for entry in engine.antispoofing.all():
                if entry.name == 'Interface 0':
                    entry.add(Network('network-10.1.2.0/24'))

        :param entry: entry to add
        :return: None
        :raises: :py:class:`smc.api.exceptions.CreateElementFailed`
        :raises: :py:class:`smc.api.exceptions.ElementNotFound`
        """
        if isinstance(entry, Element):
            entry = entry.href
            
        node = {'antispoofing_node': [],
                'auto_generated': 'false',
                'href': entry,
                'level': self.level,
                'validity': 'enable'}
        
        self.data['antispoofing_node'].append(node)
        prepared_request(CreateElementFailed,
                         href=self.href,
                         json=self.data,
                         etag=self.etag).update()
    
    def all(self):
        return [node for node in iter(self)]
        
    def __str__(self):
        return '{0}(name={1},level={2})'.format(self.__class__.__name__, 
                                                self.name,
                                                self.level)
    def __repr__(self):
        return str(self)
        