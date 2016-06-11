import logging
from pprint import pprint
from smc.actions import search
from smc.api import web as web_api

logger = logging.getLogger(__name__)

class Element(object):
    """ Element container for retrieved json show events
    Based on the 'target' (single_fw, single_ips, host, etc) there are
    multiple show methods that return different display options for the 
    returned data. 
    :param target: single_fw, single_ips, single_layer2, host, etc
    :param kwargs: name: show is based on specific element by name (default:None)
    :param kwargs: details: specified when user wants generic output of all elements by type (default:False)
    :param kwargs: interfaces: for engines, if specified, show interface information (default:False)
    :param kwargs: routes: for engines, if specified show route information (default:False)
    """
    def __init__(self, target, **kwargs):
        self.target = target #type: single_fw, host, network, etc
        self.headers = []  #headers for table output
        self.rows = [] #data for formatted output
        self.kwargs = kwargs
    
    def show(self):
        if self.kwargs.get('details') is True: #all entries for target
            print self.showByType(self.target)
        elif self.kwargs.get('name') is not None:
            name = self.kwargs.get('name')
            if self.kwargs.get('interfaces') is True:
                print self.showInterfaces(name)
            elif self.kwargs.get('routes') is True:
                print self.showRoutes(name)
            else:
                pprint(self.showAsJson(name))
    
    def showByName(self, name):
        sb = []
        ignore = ['key','link']
        json = search.element_as_json(name)
        if json:
            for entry, value in json.iteritems():
                if entry not in ignore:
                    sb.append(entry + ": " + str(value))
            return '\n'.join(sb)
    
    def showByType(self, target):
        self.headers.extend(['Name', 'Type'])
        t = search.all_elements_by_type(target)
        if t:
            for result in t:
                self.rows.append([result.get('name', None), result.get('type', None)])
            return self.showAsTable()
    
    def showAsJson(self, name):
        json = search.element_as_json(name)
        return json
                
    def showAsTable(self):
        sb = []
        col_width = [max(len(x) for x in col) for col in zip(*self.rows)]
        #print "column max width: %s" % col_width
        sb.append("".join("{:{}}".format(x, col_width[i] + 6)
                                    for i, x in enumerate(self.headers)))
        for entry in self.rows:
            sb.append("".join("{:{}}".format(x, col_width[i] + 6)
                                    for i, x in enumerate(entry)))
                
        return '\n'.join(sb)
    
    def showInterfaces(self, name):
        self.headers = ['IntId', 'Type', 'Interface', 'NicId', 'Address', 'Network', 'Mgmt']
        json = search.element_as_json(name) 
        phys_int = json.get('physicalInterfaces', None)
        #pprint(phys_int)
        for interface in phys_int:
            for intf_type, intf_data in interface.iteritems():
                interfaces = intf_data.get('interfaces', None)
                for x in interfaces:
                    for y,z in x.iteritems():
                        mgmt = 'True' if z.get('primary_mgt') is True else 'False'
                        self.rows.append([intf_data.get('interface_id', ''),
                                              intf_type,
                                              y,
                                              z.get('nicid',''),
                                              z.get('address',''),
                                              z.get('network_value',''),
                                              mgmt
                                              ])
        if self.rows:
            return self.showAsTable()
        
    def showRoutes(self, name):
        self.headers = ['NicId', 'Name', 'Network', 'Gateway', 'Destination']
        json = search.get_routing_node(name)
        routes = json.get('routing_node') #return list
        #pprint(routes)
        for route in routes:
            tmp = []
            if route.get('level') == 'interface': #top level interface
                tmp.append(route.get('nic_id'))
                tmp.append(route.get('name',''))
                intf_node = route.get('routing_node')[0]
                if intf_node.get('level') == 'network': #local interface network
                    tmp.append(intf_node.get('ip',''))
                    gateway = intf_node.get('routing_node') #gateway node
                    if len(gateway) > 0: 
                        tmp.append(gateway[0].get('ip') if gateway[0].get('level') == 'gateway' else '')
                        dest = gateway[0].get('routing_node')
                        if len(dest) > 0:   #destination node
                            tmp.append(dest[0].get('ip') if dest[0].get('level') == 'any' else '')   
                    else:
                        tmp.append('None') #keep rows aligned in case of empty fields
                        tmp.append('')
                    
            self.rows.append(tmp)
        if self.rows:
            return self.showAsTable()
               
    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__) 
    
    
if __name__ == "__main__":
    
    web_api.session.login('http://172.18.1.150:8082', 'EiGpKD4QxlLJ25dbBEp20001')
    
    logging.getLogger()
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s')

    
    element = Element('single_fw', name=None, interfaces=False, routes=False, details=True)
    print element.show()
    
    element = Element('single_fw', name='mylayer2', interfaces=True, routes=False, details=False)
    print element.show()
    
    element = Element('host', name='sg_vm', interfaces=False, routes=True, details=False)
    assert element.show() is None
        
    web_api.session.logout()