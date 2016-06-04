import logging
from smc.actions import search
from smc.cli.options import all_option_names
from smc.api import web as web_api
from pprint import pprint


class ElementContainer(object):
    def __init__(self, name=None):
        self.name = name
        self.type = None #list of available types?
        self.json = None
        
    def showKeys(self):
        return all_option_names()      

    def showByName(self, name):
        t = search.element_info_as_json(name)
        self.name = name
        if t:
            if t.get('type'): self.type = t.get('type', None)
            print "Name: %s, Type: %s" % (self.name, self.type)
            self.json = search.element_as_json(self.name)
            print self.json
                                                    
    def showByType(self, element):
        self.type = element
        self.json = search.all_elements_by_type(element)
        if self.json:
            print "{:<45} {:<15}".format('Name', 'Type')
            for result in self.json:
                print "{:<45} {:<15}".format(result.get('name', None), result.get('type', None))
                
                    
    def __str__(self):
        sb = []
        for key in self.__dict__:
            sb.append("{key}='{value}'".format(key=key, value=self.__dict__[key]))
 
        return ', '.join(sb)
 
    def __repr__(self):
        return self.__str__() 
    
    def test(self):
        d = {1: ["blah", 5]}
        print "{:<8} {:<15} {:<10}".format('Key','Label','Number')
        for k, v in d.iteritems():
            label, num = v
            print "{:<8} {:<15} {:<10}".format(k, label, num)        

    def test2(self):
        teams_list = ["Man Utd", "Man City", "T Hotspur"]
        data = ([[1, 2, 1],
                 [0, 1, 0],
                 [2, 4, 2]])
        row_format ="{:>15}" * (len(teams_list) + 1)
        print row_format.format("", *teams_list)
        for team, row in zip(teams_list, data):
            print row_format.format(team, *row)
    
if __name__ == "__main__":
    import time
    
    web_api.session.login('http://172.18.1.150:8082', 'EiGpKD4QxlLJ25dbBEp20001')
    
    logging.getLogger()
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s')
    
    element = ElementContainer()
    #for option in all_option_names():
    #    print "Looking for host objects: %s" % option
    #    time.sleep(3)
    #    element.showByType(option)
    
    element.showByName('binh')
    
    
    web_api.session.logout()