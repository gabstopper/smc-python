from smc.actions.search import element_by_href_as_json,\
    element_by_href_as_smcresult
from smc.api.exceptions import EngineCommandFailed
from smc.api.common import SMCRequest
from smc.elements.util import find_link_by_name

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

    @property
    def data(self):
        return element_by_href_as_json(self.href)
    
    @property
    def href(self):
        return self.meta.href
    
    def all(self):
        """
        Get all interfaces that can act as routing nodes
        
        :return: list :py:class:`~RoutingNode`
        """
        node=[]
        for interface in self.data.get('routing_node'):
            node.append(RoutingNode(meta=self.meta,
                                    data=interface))
        return node

    def __repr__(self):
        return '{0}(name={1})'.format(self.__class__.__name__, 
                                      self.meta)  
   
class RoutingNode(object):
    """
    Routing Node is the interface bound to a routing configuration.
    The routing node will also have at least one network associated 
    with it. This will be returned when calling engine.routing.all().
    
    To find all routing node interfaces on an engine::
    
        for routing_node in engine.routing.all():
            print routing_node.name, routing_node.network

    :ivar: str name: name of routing node
    :ivar: list network: list of networks on this interface
    """
    def __init__(self, meta=None, data=None):
        self.meta = meta
        self.data = data #routing node json

    @property
    def name(self):
        return self.data.get('name')

    @property
    def href(self):
        return self.meta.href

    @property
    def network(self):
        """
        Network/s associated with this routing node
        
        :return: list networks associated with this routing node
        """
        networks=[]
        for node in self.data.get('routing_node'):
            networks.append(node.get('ip'))
        return networks
    
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
        
        for network in self.data.get('routing_node'):
            network.get('routing_node').append(data)     
        #Re-retrieve top level routing engine json. The etag must be 
        #sent from the top routing node since the SMC API doesn't 
        #allow updates on sub-elements directly
        node = element_by_href_as_smcresult(self.href)
        json = node.json
        routing_node = json.get('routing_node') #Get routing node
        for interface in routing_node:
            if interface.get('key') == self.data.get('key'):
                interface.update(self.data)  #match on key index and update

        return SMCRequest(href=self.href,
                          json=json, 
                          etag=node.etag).update()

    def __repr__(self):
        return '{0}(name={1})'.format(self.__class__.__name__, 
                                      self.name)  

class Alias(object):
    """
    Aliases are specific to an engine instance and are typically 
    used as rule elements. They are intended to have a different value
    based on the engine that the alias is applied to. 
    
    :ivar name: name of alias
    """
    def __init__(self, resolved_value=None, alias_ref=None,
                 cluster_ref=None):
        self.name = None
        self.resolved_value = resolved_value
        self.alias_ref = alias_ref
        self.cluster_ref = cluster_ref

    def describe(self):
        return element_by_href_as_json(self.alias_ref)
        
    def __repr__(self):
        self.name = self.describe().get('name')
        return '{0}(name={1})'.format(self.__class__.__name__, 
                                      self.name)

class Snapshot(object):
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
    def href(self):
        return self.meta.href
    
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
        snapshot = self.describe()
        href = find_link_by_name('content', snapshot.get('link'))
        try:
            return SMCRequest(href=href, filename=filename).read()
        except IOError as e:
            raise EngineCommandFailed("Snapshot download failed: {}"
                                      .format(e))
    def describe(self):
        """
        Retrieve full json for this snapshot
        
        :return: json text
        """
        return element_by_href_as_json(self.href)  
    
    def __repr__(self):
        return '{0}(name={1})'.format(self.__class__.__name__, self.name)
