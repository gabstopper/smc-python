'''
Created on Aug 26, 2017

@author: davidlepage
'''
from smc_monitoring.monitors.blacklist import BlacklistQuery
from smc_monitoring.models.filters import InFilter
from smc_monitoring.models.constants import LogField
from smc_monitoring.models.values import FieldValue, IPValue, ServiceValue
from smc import session
from smc_monitoring.monitors.connections import ConnectionQuery
from smc_monitoring.monitors.logs import LogQuery
from smc_monitoring.monitors.vpns import VPNSAQuery
from smc_monitoring.monitors.users import UserQuery
from smc_monitoring.monitors.routes import RoutingQuery
from smc_monitoring.monitors.sslvpn import SSLVPNQuery
from smc_monitoring.models.formatters import TableFormat, CSVFormat, RawDictFormat
from smc_monitoring.models.formats import TextFormat
from smc_monitoring.monitors.alerts import ActiveAlertQuery
from smc_monitoring.models.formats import DetailedFormat
from smc_monitoring.wsocket import SMCSocketProtocol, SessionNotFound, websocket
import smc_monitoring
from smc_monitoring.models.calendar import datetime_from_ms
from smc.core.engines import Layer3Firewall
from smc.core.engine import Engine

if __name__ == '__main__':
    import logging
    from pprint import pprint
    
    logging.getLogger()
    logging.basicConfig(
        level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s.%(funcName)s: %(message)s')
    
    #session.login(url='http://172.18.1.26:8082', api_key='kKphtsbQKjjfHR7amodA0001', timeout=45,
    #              beta=True)
    session.login(url='http://172.18.1.150:8082', api_key='EiGpKD4QxlLJ25dbBEp20001', timeout=30,
                  )
    #session.login(url='https://172.18.1.151:8082',
    #              api_key='NdHp2CgzPga7lHwltcPrabew', timeout=30,
    #              verify='/Users/davidlepage/Downloads/cacert.pem', beta=True)
    #from smc.core.engine import Engine
    #engine = Engine('foo')
    
    #if session.session.verify and session.session.verify 

    #import sys
    #sys.exit(1)
    #TODO: BLACKLISTQUERY fails when using format ID's due to CombinedFilter.
    #import websocket
    websocket.enableTrace(True)
  
    #https://stackoverflow.com/questions/38501531/forcing-requests-library-to-use-tlsv1-1-or-tlsv1-2-in-python
    from smc_monitoring.models.query import Query
    #query = ConnectionQuery('lynn', check_hostname=False)
    #query = BlacklistQuery('sg_vm')
    
    engine = Engine('sg_vm')
    for bl in engine.blacklist_show(max_recv=5):
        print(bl)
           
    #query.request = {"query":{"definition":"BLACKLIST","target":"sg_vm"}, "fetch":{}, "format":{"type":"texts", "field_format": "name"}}
    #query = UserQuery('lynn', check_hostname=False)
    #query = VPNSAQuery('sg_vm')
    #query = SSLVPNQuery('lynn', check_hostname=False)
    #query = RoutingQuery('lynn')
    
    #print(Query.resolve_field_ids(BlacklistQuery.field_ids))
    #query.request = {"query":{"definition":"BLACKLIST","target":"lynn"}, "fetch":{}, "format":{"type":"texts"}}
    
    #myfilter = InFilter(FieldValue(LogField.SRC), [IPValue('192.168.4.82'), IPValue('172.18.1.152')])
   
    #query = LogQuery(fetch_size=50)
    #for fields in Query.resolve_field_ids(LogQuery.field_ids):
    #    print(fields)
    #query.update_filter(myfilter)
    #query.time_range.last_five_minutes()
    #query.format.timezone('CST')
    #for record in query.fetch_batch():
    #for record in query.fetch_as_element(check_hostname=False):
    #for record in query.fetch_as_element():
    #for record in query.fetch_batch(RawDictFormat):
    #for record in query.fetch_batch(CSVFormat):
    #for record in query.fetch_live():
    #   print(record),
        #record.delete()
    #print(session.url)
    
    
    from smc_monitoring.pubsub.subscribers import Notification, Event
                    
    #notification = Notification('host')
    
    #for published in notification.notify(as_type=Event):
    #    print(published, published.action, published.element)
    
    
    # TODO:
    # If queries do not return anything, the query never times out
    # If the engine is not initialized, the query sits in select blocking. Should check for a connected engine first?
    
    #query = ConnectionQuery('sg_vm')
        
    #pprint(query.resolve_field_ids(query.field_ids))
    
    #query = UserQuery('sg_vm')
    #query = VPNSAQuery('sg_vm')
    #query = SSLVPNQuery('sg_vm')
    #query = RoutingQuery('sg_vm')
    #query.format.timezone('CST')  
    #for record in query.fetch_batch():
    #    print(record)
    
    query = ActiveAlertQuery('sg_vm') #<---- Doesnt work??
    query.request = {"query": {
                        "definition":"ACTIVE_ALERTS",
                        "target":"Shared Domain",
                        "filter": {
                            "type": "in",
                            "left": {
                                "type": "field",
                                "id": LogField.NODEID},
                            "right":[
                                {"type": "element",
                                 "href": Engine('sg_vm').href}]
                            }
                        }, 
                     "fetch":{},
                     "format":{"type":"texts"}}
    
    #query.request = {'fetch': {},
    #                 'format': {'field_format': 'name',
    #                            'type': 'detailed'},
    #                 'query': {'definition': 'ACTIVE_ALERTS', 'target': 'sg_vm'}}
    #for record in query.fetch_batch(RawDictFormat):
    #    print(record)
    
   
    session.logout()
