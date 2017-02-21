from smc.actions.search import element_by_href_as_json,\
    element_by_href_as_smcresult
from smc.api.exceptions import EngineCommandFailed
from smc.base.util import find_link_by_name
from smc.base.model import Element, prepared_request

class Routing(object):
    """
    Routing represents the top level routing node from the engine. This
    is the full routing json for the engine node. This is obtained from
    an engine reference::
    
        for routing in engine.routing.all():
            ....
    """
    def __init__(self, meta=None):
        self.meta = meta

    def all(self):
        """
        Get all interfaces that can act as routing nodes
        
        :return: list :py:class:`~RoutingNode`
        """
        return [RoutingNode(meta=self.meta, data=interface)
                for interface in element_by_href_as_json(self.meta.href)
                .get('routing_node')]

class RoutingNode(Element):
    """
    Routing Node is the interface bound to a routing configuration.
    The routing node will also have at least one network associated 
    with it. This will be returned when calling engine.routing.all().
    
    To find all routing node interfaces on an engine::
    
        for routing_node in engine.routing.all():
            print routing_node.name, routing_node.network

    :ivar str name: interface name of routing node
    :ivar list network: list of networks on this interface
    """
    def __init__(self, meta=None, data=None):
        self.meta = meta
        self._data = data #routing node json

    @property
    def name(self):
        return self._data.get('name')

    def describe(self):
        return self._data

    @property
    def network(self):
        """
        Network/s associated with this routing node
        
        :return: list networks associated with this routing node
        """
        return [node.get('ip') for node in self._data.get('routing_node')]

    def add_ospf_area(self, ospf_area, communication_mode='NOT_FORCED',
                      unicast_ref=None):
        """
        Add OSPF Area to this routing node.
        
        Communication mode specifies how the interface will interact with the
        adjacent OSPF environment. Please see SMC API documentation for more
        in depth information on each option. 
        
        Example of adding an area to interface routing node::
        
            area = OSPFArea('area0') #obtain area resource
    
            #Get routing resources
            for interface in engine.routing.all(): 
                if interface.name == 'Interface 0':
                    interface.add_ospf_area(area)
            
        .. note:: If UNICAST is specified, you must also provide a unicast_ref
                  to identify the remote host
        
        :param OSPFArea ospf_area: OSPF area instance
        :param str communication_mode: NOT_FORCED|POINT_TO_POINT|PASSIVE|UNICAST
        :param str unicast_ref: location ref of host (required for UNICAST)
        :return: :py:class:`smc.api.exceptions.SMCResult`
        """
        communication_mode = communication_mode.upper()
        data = {'href': ospf_area.href, 
                'communication_mode': communication_mode,
                'level': 'gateway'}
        if communication_mode == 'UNICAST':
            #Need a destination ref, add to sub routing_node
            data.update(routing_node=[{'href': unicast_ref,
                                       'level': 'any'}])
        
        for network in self._data.get('routing_node'):
            network.get('routing_node').append(data)     
        #Re-retrieve top level routing engine json. The etag must be 
        #sent from the top routing node since the SMC API doesn't 
        #allow updates on sub-elements directly
        node = element_by_href_as_smcresult(self.href)
        json = node.json
        routing_node = json.get('routing_node') #Get routing node
        for interface in routing_node:
            if interface.get('key') == self._data.get('key'):
                interface.update(self._data)  #replace based on key index

        return prepared_request(href=self.href,
                                json=json, 
                                etag=node.etag).update()

class RouteTable(object):
    """
    RouteTable returns a raw view of the engines routing table.
    It is referenced by::
    
        engine = Engine('myengine')
        for route in engine.routing_monitoring.all():
            print route
    """
    def __init__(self, routes):
        self.routes = routes

    def all(self):
        """
        Return all routes
        
        :return: list dict of route entries
        """
        return [Route(**route) 
                for route in self.routes.get('routing_monitoring_entry')]

class Route(object):
    """ 
    Represents a route found in the route table. 
    
    :ivar gateway: gateway for this route
    :ivar network: network/cidr for this route
    :ivar type: type of route, (static, connected, dynamic)
    :ivar src_if: source interface id
    :ivar dst_if: destination interface id
    """
    def __init__(self, route_gateway=None, route_netmask=None, 
                 route_network=None, route_type=None, dst_if=None, 
                 src_if=None, **kwargs):
        self._route_gateway = route_gateway
        self._route_netmask = route_netmask
        self._route_network = route_network
        self._route_type = route_type
        self._dst_if = dst_if
        self._src_if = src_if
    
    @property
    def gateway(self):
        return self._route_gateway
    
    @property
    def network(self):
        return '{}/{}'.format(self._route_network, self._route_netmask)

    @property
    def type(self):
        return self._route_type
    
    @property
    def src_if(self):
        return self._src_if
    
    @property
    def dst_if(self):
        return self._dst_if

    def __str__(self):
        return '{0}(network={1})'.format(self.__class__.__name__, self.network)
    
class Snapshot(Element):
    """
    Policy snapshots currently held on the SMC. You can retrieve all
    snapshots at the engine level and view details of each::
    
        for snapshot in engine.snapshots:
            print snapshot.describe()
    
    Snapshots can also be downloaded::
    
        for snapshot in engine.snapshots:
            if snapshot.name == 'blah snapshot':
                snapshot.download()
                
    Snapshot filename will be <snapshot_name>.zip if not specified.
    
    :ivar name: name of snapshot
    """
    def __init__(self, meta=None):
        self.meta = meta
    
    @property
    def name(self):
        return self.meta.name

    def download(self, filename=None):
        """
        Download snapshot to filename
        
        :param str filename: fully qualified path including filename .zip
        :return: :py:class:`smc.api.web.SMCResult`
        :raises: :py:class:`smc.api.exceptions.EngineCommandFailed`
        """
        if not filename:
            filename = '{}{}'.format(self.name, '.zip')
        href = find_link_by_name('content', self.link)
        try:
            return prepared_request(href=href, filename=filename).read()
        except IOError as e:
            raise EngineCommandFailed("Snapshot download failed: {}"
                                      .format(e))

class Alias(Element):
    """
    An Alias is an element that is shared by multiple engines but has a
    unique value depending on the engine it is applied on. 
    Show the engine aliases and their resolved values::
    
        engine = Engine('sg_vm')
        for alias in engine.alias_resolving():
            print alias.name, alias.resolved_value
    
    """
    def __init__(self, resolved_value=None, alias_ref=None,
                 cluster_ref=None):
        self._resolved_value = resolved_value #: list of resolved values
        self.alias_ref = alias_ref            #: alias href
        self.cluster_ref = cluster_ref        #: engine href
    
    @property
    def name(self):
        """
        Return name of alias
        
        :return: str name of alias
        """
        return element_by_href_as_json(self.href).get('name')

    @property
    def href(self):
        return self.alias_ref
    
    @property
    def resolved_value(self):
        """
        Resolved value of alias
        
        :return: list resolved values for this alias
        """
        return self._resolved_value

    def resolve(self):
        href = find_link_by_name('resolve', self.link)
        # SMC API seems to have an issue with this
        return href