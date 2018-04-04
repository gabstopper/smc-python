'''
Created on Aug 26, 2017

@author: davidlepage
'''
from smc_monitoring.monitors.blacklist import BlacklistQuery
from smc_monitoring.models.filters import InFilter
from smc_monitoring.models.constants import LogField, Actions, Alerts
from smc_monitoring.models.values import FieldValue, IPValue, ServiceValue,\
    ElementValue, StringValue, ConstantValue
from smc import session
from smc_monitoring.monitors.connections import ConnectionQuery
from smc_monitoring.monitors.logs import LogQuery
from smc_monitoring.monitors.vpns import VPNSAQuery
from smc_monitoring.monitors.users import UserQuery
from smc_monitoring.monitors.routes import RoutingQuery
from smc_monitoring.monitors.sslvpn import SSLVPNQuery
from smc_monitoring.models.formatters import TableFormat, CSVFormat, RawDictFormat
from smc_monitoring.models.formats import TextFormat, CombinedFormat
from smc_monitoring.monitors.alerts import ActiveAlertQuery
from smc_monitoring.models.formats import DetailedFormat
from smc_monitoring.wsocket import SMCSocketProtocol, SessionNotFound, websocket
import smc_monitoring
from smc_monitoring.models.calendar import datetime_from_ms
from smc.core.engines import Layer3Firewall
from smc.core.engine import Engine
from smc_monitoring.models.query import Query

def print_fields(number):
    ids = Query.resolve_field_ids(list(range(number)))
    for x in ids:
        pprint(x)
    #for x in reversed(ids):
    #    print('{}={} #: {}'.format(
    #        x.get('name').upper(),
    #        x.get('id'),
    #        x.get('comment')))

def get_field_schema_by_name(fields, max_ids=2000):
    # List of fields, expecting the value to match 'pretty' (what is shown in SMC UI)
    ids = Query.resolve_field_ids(list(range(max_ids)))
    for id in ids:
        yield id


if __name__ == '__main__':
    import logging
    from pprint import pprint
    
    logging.getLogger()
    logging.basicConfig(
        level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s.%(funcName)s: %(message)s')
    
    #session.login(url='http://172.18.1.26:8082', api_key='kKphtsbQKjjfHR7amodA0001', timeout=45,
    #              beta=True)
    #session.login(url='http://172.18.1.150:8082', api_key='EiGpKD4QxlLJ25dbBEp20001', timeout=30)
    
    session.login(url='https://smc-standby:8082',
                  api_key='AF7Rggmn6XgmrZMCKKpgiYhp', timeout=30,
                  verify='/Users/davidlepage/Downloads/smc_api.crt', beta=True)
    
    
    #session.login(url='http://172.18.1.36:8082', api_key='kN8CYwTrxB9UNLPyTcnX0001',
    #              api_version='5.10')
    #pprint(session._get_log_schema())
    #if session.session.verify and session.session.verify 


    #TODO: BLACKLISTQUERY fails when using format ID's due to CombinedFilter.
    #import websocket
    websocket.enableTrace(True)
  
    #https://stackoverflow.com/questions/38501531/forcing-requests-library-to-use-tlsv1-1-or-tlsv1-2-in-python
    #from smc_monitoring.models.query import Query
    #query = ConnectionQuery('sg_vm')
    #for log in query.fetch_live():
    #    print(log)
    
    #pprint(query.request)
    #query = BlacklistQuery('sg_vm')
    #query.add_in_filter(
    #    FieldValue(LogField.BLACKLISTENTRYSOURCEIP), [IPValue('2.2.2.2')])
    
    #query.request = {"query": 
    #    {
    #    "definition":"BLACKLIST","target":"sg_vm"},
    #    "fetch":{},
    #    "format":{
    #        "type": "texts",
    #        "field_format": "pretty",
    #        "resolving": {"senders": True}}
    #    }
        
    engine = Engine('sg_vm')
    #for bl in engine.blacklist_show(max_recv=5):
    #    print(bl)
           
    #query.request = {"query":{"definition":"BLACKLIST","target":"sg_vm"}, "fetch":{}, "format":{"type":"texts", "field_format": "name"}}
    #query = UserQuery('lynn', check_hostname=False)
    
    #query = SSLVPNQuery('lynn', check_hostname=False)
    #query = RoutingQuery('lynn')
    
    #print(Query.resolve_field_ids(BlacklistQuery.field_ids))
    #query.request = {"query":{"definition":"BLACKLIST","target":"lynn"}, "fetch":{}, "format":{"type":"texts"}}
    
    #myfilter = InFilter(FieldValue(LogField.SRC), [IPValue('192.168.4.82'), IPValue('172.18.1.152')])
    
    
    
    
    #Use case to pull specific filter logs from Audit
    query = LogQuery()
    query.format.timezone('CET')        
    default_audit_fields_ids = [LogField.TIMESTAMP, LogField.DATATYPE, LogField.USERORIGINATOR, LogField.TYPEDESCRIPTION, LogField.RESULT, LogField.OBJECTNAME, LogField.OBJECTID, LogField.OBJECTTYPE, LogField.INFOMSG]
    query.format.field_ids(default_audit_fields_ids)
    # Show only Audit log entries
    query.add_in_filter( FieldValue(LogField.DATATYPE), [ConstantValue(9)]) #HINT: it could be nice to have the Audit Data Type as constant in the LogField
    
    
    #OBJECTNAME
    #for log in query.fetch_live():
    #    print(log)
    
    #pprint(query._get_field_schema())
        #if 'fields' in fields:
        #    return fields['fields']
    #from smc_monitoring.models.query import Query
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
    
    #pprint(print_fields(200))
    #for field in get_field_schema_by_name(['Sender', 'Operation Type', 'Element'], max_ids=1000):
    #    print("Printing field...")
    #    pprint(field)
    
    
    #print_fields(1536)
    
    from smc_monitoring.pubsub.subscribers import Notification, Event
                    
    #notification = Notification('host')
    
    #for published in notification.notify(as_type=Event):
    #    print(vars(published))
    #    print(published, published.action, published.element)
    
    
    # TODO:
    # If queries do not return anything, the query never times out
    # If the engine is not initialized, the query sits in select blocking. Should check for a connected engine first?
    
    #query = ConnectionQuery('sg_vm')
    #pprint(query.resolve_field_ids(query.field_ids))
    
    #query = UserQuery('sg_vm')
    
    #query = VPNSAQuery('sg_vm')
    #pprint(query.get_field_schema())    
    
    #query = VPNSAQuery('sg_vm')
    #query = ActiveAlertQuery('Shared Domain')
    #query = SSLVPNQuery('sg_vm')
    #query = RoutingQuery('sg_vm')
    #query = BlacklistQuery('sg_vm', timezone='CST')
    #pprint(query._get_field_schema())
    #query.format.timezone('CST')  
    #pprint(query.get_field_schema())
    #query.get_field_schema()
    #for record in query.fetch_raw():
    #    for individual in record:
    #        print(individual)
    
    #query = ActiveAlertQuery('Shared Domain', timezone='America/Chicago')
    #pprint(vars(query))
    #pprint(query.get_field_schema())
    '''
    query.request = {'fetch': {},
                     'format': {
                         'type': 'detailed',
                         'field_ids': list(range(1000))},
                     'query': {
                         'definition': 'ACTIVE_ALERTS',
                         'target': 'Shared Domain'}
                     }
    '''
    
    
    from smc.elements.network import Host
    #query.add_in_filter(FieldValue(LogField.NODEID), [IPValue('172.18.1.252')]) #<-- Works!
    #query.add_in_filter(FieldValue(LogField.NODEID), [ElementValue(Host('Sidewinder v8'))]) #<-- Doesnt work!
    
    request = {'format': {'formats': {'bldata': {'field_format': 'name',
                                                 'resolving': {'senders': True,
                                                               'time_show_zone': True,
                                                               'timezone': 'CST'},
                                                 'type': 'texts'},
                                        'blid': {'field_format': 'pretty',
                                                 'field_ids': [117],
                                                 'resolving': {'senders': True},
                                                 'type': 'texts'}},
                                        'type': 'combined'},
                'query': {'definition': 'BLACKLIST', 'target': 'sg_vm'}}
    
    request2 = {'fetch': {},
                'format': {'field_format': 'pretty',
                           'resolving': {'senders': True,
                                          'time_show_zone': True,
                                          'timezone': 'CST'},
                           'type': 'texts'},
                'query': {'definition': 'BLACKLIST', 'target': 'sg_vm'}}
    
    #pprint(vars(query))
    #query.request = request2
    #for record in query.fetch_as_element():
    #    print(record, record.vulnerability_refs)
    #for record in query.fetch_raw(max_recv=3):
    #for record in query.fetch_batch():
    #    print(record)
    
    #pprint(query.resolve_field_ids(query.field_ids))
    #query.request = {"query": {
    #                    "definition":"ACTIVE_ALERTS",
    #                    "target":"Shared Domain",
    #                    "filter": {
    #                        "type": "in",
    #                        "left": {
    #                            "type": "field",
    #                            "id": LogField.NODEID},
    #                        "right":[
    #                            {"type": "element",
    #                             "href": Engine('sg_vm').href}]
    #                        }
    #                    }, 
    #                     "fetch":{},
    #                     "format":{"type":"texts"}}
    
    #query.request = {'fetch': {},
    #                 'format': {
    #                     'type': 'detailed',
    #                     'field_format': 'pretty'},
    #                 'query': {
    #                     'definition': 'ACTIVE_ALERTS',
    #                     'target': 'Shared Domain'}
    #                 }
    
    #for record in query.fetch_raw(max_recv=3):
    #for record in query.fetch_live():
    #    pprint(record)
    
    
    session.logout()
