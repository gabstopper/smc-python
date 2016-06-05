import logging
from smc.actions import search
from smc.api import web as web_api
from pprint import pprint

logger = logging.getLogger(__name__)

class ElementContainer(object):
    def __init__(self, name=None):
        self.name = name
        self.type = None #list of available types?
        self.json = []
        self.headers = []
        self.elements = []
        
    def showKeys(self): 
        pass

    def single_fw(self, name=None, all=False):
        self._engine('single_fw', name, all)
        
    def single_ips(self, name=None, all=False):
        self._engine('single_ips', name, all)
    
    def single_layer2(self, name=None, all=False):
        self._engine('single_layer2', name, all)
                
    def _engine(self, engine_type, name=None, all=False):
        if all:
            self.showByType(engine_type)
        elif name:
            self.showByName(name)
            t = search.element_as_json(name)
            if t: pprint(t)
                                                
    def showByName(self, name):
        sb = []
        ignore = ['key','link']
        t = search.element_as_json(name)
        if t:
            for entry, value in t.iteritems():
                if entry not in ignore:
                    sb.append(entry + ": " + str(value))
            print '\n'.join(sb)
                                                               
    def showByType(self, element):
        self.headers.extend(['Name', 'Type'])
        t = search.all_elements_by_type(element)
        if t:
            for result in t:
                self.elements.append([result.get('name', None), result.get('type', None)])
            print self.__str__()
    
    def showAsJson(self, j):
        pass
                
    def __str__(self):
        sb = []
        col_width = [max(len(x) for x in col) for col in zip(*self.elements)]
        #print "column max width: %s" % col_width
        sb.append("".join("{:{}}".format(x, col_width[i] + 5)
                                    for i, x in enumerate(self.headers)))
        for entry in self.elements:
            sb.append("".join("{:{}}".format(x, col_width[i] + 5)
                                    for i, x in enumerate(entry)))
                
        return '\n'.join(sb)
       
    def __repr__(self):
        return self.__str__() 
    
    
if __name__ == "__main__":
    import time
    
    web_api.session.login('http://172.18.1.150:8082', 'EiGpKD4QxlLJ25dbBEp20001')
    
    logging.getLogger()
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s')
    
    element = ElementContainer()
    
    #element.single_fw(name='ewf')
    element.showByType('single_fw')
    #element.showByType('router')
    #element.showByType('network')
    #element.showByName('sg_vm')
    #element.single_fw('all')
    #element.single_ips('all')
    #element.single_layer2('all')
    #element.display()
    #print element
    #print element.table()
    
    web_api.session.logout()