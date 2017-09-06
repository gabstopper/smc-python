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

if __name__ == '__main__':
    import logging
    from pprint import pprint
    
    logging.getLogger()
    logging.basicConfig(
        level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s.%(funcName)s: %(message)s')
    
    session.login(url='http://172.18.1.150:8082', api_key='EiGpKD4QxlLJ25dbBEp20001', timeout=30,
                  domain='foo')

    from smc.core.engine import Engine
    
    engine = Engine('foo')
    
    pprint(engine.data)
    #for node in engine.nodes:
    #    print(vars(node.status()))
        
    #query = ConnectionQuery('sg_vm')
    
    #for record in query.fetch_as_element():
    #    print(record)
        
    from datetime import datetime
    
    from smc_monitoring.models.query import Query
    #query = LogQuery(fetch_size=50)
    #query.format.timezone('CST')
    
    
    # TODO:
    # If queries do not return anything, the query never times out
    # If the engine is not initialized, the query sits in select blocking. Should check for a connected engine first?
    
    #from smc.core.engine import Engine
    #engine = Engine('foo')
    #for node in engine.nodes:
    #    pprint(vars(node.status()))
    
    #query = ConnectionQuery('sg_vm')
        
    #pprint(query.resolve_field_ids(query.field_ids))
    
    #query = UserQuery('sg_vm')
    #query = VPNSAQuery('sg_vm')
    #query = SSLVPNQuery('sg_vm')
    #query = RoutingQuery('sg_vm')
    #query.format.timezone('CST')  
    #for record in query.fetch_batch():
    #    print(record)
    
    #query = ActiveAlertQuery('sg_vm') #<---- Doesnt work??
    #query.request = {'fetch': {},
    #                 'format': {'field_format': 'name',
    #                            'type': 'detailed'},
    #                 'query': {'definition': 'ACTIVE_ALERTS', 'target': 'sg_vm'}}
    
    
   
    session.logout()