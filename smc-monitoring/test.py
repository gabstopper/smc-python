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


def print_fields(number):
    ids = Query.resolve_field_ids(list(range(number)))
    for x in ids:
        pprint(x)
    for x in reversed(ids):
        print('{}={} #: {}'.format(
            x.get('name').upper(),
            x.get('id'),
            x.get('comment')))

       
if __name__ == '__main__':
    import logging
    from pprint import pprint
    
    logging.getLogger()
    logging.basicConfig(
        level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s.%(funcName)s: %(message)s')
    
    #session.login(url='http://172.18.1.26:8082', api_key='kKphtsbQKjjfHR7amodA0001', timeout=45,
    #              beta=True)
    session.login(url='http://172.18.1.150:8082', api_key='EiGpKD4QxlLJ25dbBEp20001', timeout=30)
    
    #session.login(url='http://172.18.1.151:8082',
    #              api_key='hBC38alwmpsXkQaoRMyLvAUk', timeout=30,
    #              beta=True)
    

    #pprint(session._get_log_schema())
    #if session.session.verify and session.session.verify 

    #TODO: BLACKLISTQUERY fails when using format ID's due to CombinedFilter.
    #import websocket
    websocket.enableTrace(True)
  
    #https://stackoverflow.com/questions/38501531/forcing-requests-library-to-use-tlsv1-1-or-tlsv1-2-in-python
    from smc_monitoring.models.query import Query
    #query = ConnectionQuery('lynn')
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
    #query = VPNSAQuery('sg_vm')
    #query = SSLVPNQuery('lynn', check_hostname=False)
    #query = RoutingQuery('lynn')
    
    #print(Query.resolve_field_ids(BlacklistQuery.field_ids))
    #query.request = {"query":{"definition":"BLACKLIST","target":"lynn"}, "fetch":{}, "format":{"type":"texts"}}
    
    #myfilter = InFilter(FieldValue(LogField.SRC), [IPValue('192.168.4.82'), IPValue('172.18.1.152')])
   
    query = LogQuery(fetch_size=1)
    #pprint(query.get_field_schema())
        #if 'fields' in fields:
        #    return fields['fields']
    
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
    
    #query = SSLVPNQuery('sg_vm')
    #query = RoutingQuery('sg_vm')
    query = BlacklistQuery('sg_vm', timezone='CST')
    #pprint(query._get_field_schema())
    #query.format.timezone('CST')  
    #pprint(query.get_field_schema())
    #query.get_field_schema()
    #for record in query.fetch_batch():
    #    print(record)
    
    #query = ActiveAlertQuery('Shared Domain')
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
    
    
    
    #query.add_in_filter(FieldValue(LogField.NODEID), [IPValue('172.18.1.254')]) <-- Works!
    #query.add_in_filter(FieldValue(LogField.COMPID), [ElementValue(node, node2)]) <-- Doesnt work!
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
    query.request = request2
    #for record in query.fetch_as_element():
    #    print(record, record.vulnerability_refs)
    #for record in query.fetch_raw(max_recv=3):
    for record in query.fetch_batch():
    #for record in query.fetch_live():
        print(record)
    
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
    
    #print_fields(100000)
    #[{u'GtiFileReputation': 5, u'SenderType': 0, u'VpnId': 17, u'Service': 375, u'NatSrc': u'172.18.1.152', u'Dst': u'172.18.1.251', u'FileMd5Hash': u'ff7da1d4c3569a42452677700d7f8720', u'Action': 9, u'AlertSeverity': 8, u'TlsHandshakeDowngraded': False, u'SenderDomain': 1, u'Type': 6, u'TagInfo': u'QeGARgoM', u'NatDport': 443, u'Srczone': 96, u'LogId': 6551, u'TlsDetected': None, u'SitCategory': 40000001, u'TlsDecrypted': None, u'HttpResponseCode': 200, u'RuleId': 8619297190, u'IpAttacker': u'172.18.1.251', u'HttpRequestMethod': u'GET', u'Srcif': 0, u'Alert': 900, u'IpVersion': 4, u'Url': u'https://debian.lepages.local/virussign.com_ff7da1d4c3569a42452677700d7f8720.vir', u'VulnerabilityReferences': [], u'TcpMissingDataSeen': False, u'NatSport': 8132, u'AtdReputation': 100, u'EventId': 1069998600287183300, u'Src': u'172.18.1.152', u'Timestamp': 1517581153876, u'HttpRequestHost': u'debian.lepages.local', u'CompId': 118, u'FileType': 2555912, u'PeerEndPoint': 46, u'NodeId': 118, u'Situation': 76508, u'PortSource': 443, u'IpSource': u'172.18.1.251', u'EndPoint': 26, u'IpTarget': u'172.18.1.152', u'IpDest': u'172.18.1.152', u'Dport': 443, u'ReceptionTime': 1517581153756, u'FileTransferDir': 2, u'ClientApplication': 78016, u'PortDest': 8132, u'ScannerId': 0, u'Protocol': 6, u'Scanner': 0, u'Facility': 51, u'DataType': 3, u'Dstzone': 96, u'VirusId': u'Malicious', u'IpsAppid': 786434, u'DataTags': [1, 100000000, 202000000, 202010000, 205000000, 300000000], u'FileName': u'virussign.com_ff7da1d4c3569a42452677700d7f8720.vir', u'RelatedConnectionRef': u'1517581153429/118/6365196701526978564', u'SenderModuleId': 60200029, u'SrvhelperId': 60200009, u'NatDst': u'192.168.3.101', u'Dstif': 0, u'EthType': 2048, u'SrcIpAddrs': u'172.18.1.152', u'DstIpAddrs': u'172.18.1.251', u'Sport': 8132, u'FileLength': 51712, u'TcpHandshakeSeen': True}]

    session.logout()
