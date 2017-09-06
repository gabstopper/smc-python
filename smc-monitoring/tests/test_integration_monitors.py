'''
Created on Sep 4, 2017

@author: davidlepage
'''
import mock
import unittest
from smc import session
from smc.api.exceptions import SMCConnectionError
from smc_monitoring.wsocket import SMCSocketProtocol, websocket
from smc_monitoring.monitors.connections import ConnectionQuery
from smc_monitoring.models.formatters import RawDictFormat
from smc_monitoring.models.constants import LogField
from smc_monitoring.monitors.logs import LogQuery
from smc_monitoring.monitors.users import UserQuery
from smc_monitoring.monitors.vpns import VPNSAQuery
from smc_monitoring.monitors.routes import RoutingQuery
from smc_monitoring.monitors.sslvpn import SSLVPNQuery
from smc_monitoring.monitors.blacklist import BlacklistQuery

url = 'http://172.18.1.26:8082'
api_key = 'kKphtsbQKjjfHR7amodA0001'

import logging
logging.getLogger()
logging.basicConfig(level=logging.DEBUG)

class Test(unittest.TestCase):
    
    def setUp(self):
        session.login(
            url=url, api_key=api_key, verify=False,
            timeout=40)

    def tearDown(self):
        try:
            session.logout()
        except (SystemExit, SMCConnectionError):
            pass
    
    @mock.patch('smc_monitoring.models.query.SMCSocketProtocol', autospec=True)
    def test_fetch_raw_with_bounded_limit(self, patch):
        # Set a limit on the number of returned results, forces call of abort()
        records = {'records': {'added': [{u'delta_key': u'AcCoBEMBNM4rQgIGA4mkAlAAAAAA', u'116': u'TCP time wait', u'134': u'HTTP', u'24': u'2017-09-04 14:26:10', u'27': u'Dumb HTTP', u'46': u'Internal', u'47': u'External', u'1': u'2017-09-04 14:25:52', u'3': u'ngf-1065', u'4': u'ngf-1065', u'7': u'192.168.4.67', u'9': u'35236', u'8': u'52.206.43.66', u'302': u'2', u'20007': u'192.168.4.67', u'485': u'INFO: Connection Monitoring', u'20008': u'52.206.43.66', u'11': u'TCP', u'10': u'80', u'38': u'Shared Domain', u'15': u'10.0.0.254', u'17': u'28284', u'1028': u'2017-09-04 14:25:52', u'34': u'6'}]}}
        mock_client = mock.MagicMock(spec=SMCSocketProtocol)
        mock_client.get_from_id = mock.Mock()
        mock_client.receive.return_value = [records] 
        mock_client.__enter__.return_value = mock_client
        patch.return_value = mock_client
        
        query = ConnectionQuery('foo')
        gen = query.fetch_raw(max_recv=1)
        self.assertTrue(next(gen))
        with self.assertRaises(StopIteration):
            next(gen) # Fails because generator should be closed after 1 iteration
    
    @mock.patch('smc_monitoring.models.query.SMCSocketProtocol', autospec=True)
    def test_fetch_batch_with_fields(self, patch):
        fields = {u'fields': [{u'comment': u'Time of creating the event record.', u'name': u'Timestamp', u'filterable': False, u'raw_type': u'time_ms', u'visible': True, u'pretty': u'Creation Time', u'id': 1}, {u'comment': u'Connection destination IP address', u'name': u'Dst', u'filterable': True, u'raw_type': u'ip', u'resolving': u'IP', u'visible': True, u'pretty': u'Dst Addr', u'id': 8}, {u'comment': u'Connection source IP address', u'name': u'Src', u'filterable': True, u'raw_type': u'ip', u'resolving': u'IP', u'visible': True, u'pretty': u'Src Addr', u'id': 7}], u'fetch': 845, u'success': u'Fetch started'}
        records = {u'records': {u'updated': [], u'added': [{u'Dst Addr': u'172.217.9.46', u'Src Addr': u'172.18.1.70', u'Creation Time': u'2017-09-04 19:38:38', u'delta_key': u'AawSAUYBrNkJLgIGA+Z8AwG7AAAAAA=='}]}}
        mock_client = mock.MagicMock(spec=SMCSocketProtocol)
        mock_client.get_from_id = mock.Mock()
        mock_client.receive.return_value = [fields, records] 
        mock_client.__enter__.return_value = mock_client
        patch.return_value = mock_client
        
        query = ConnectionQuery('foo')
        #query.format.field_ids([LogField.TIMESTAMP, LogField.SRC, LogField.DST])
        for record in query.fetch_batch(RawDictFormat, max_recv=1):
            for data in record:
                self.assertEqual(data.get('Dst Addr'), '172.217.9.46')
                self.assertEqual(data.get('Src Addr'), '172.18.1.70')
                self.assertEqual(data.get('Creation Time'), '2017-09-04 19:38:38')
    
    def test_abort_on_query(self):
        # Abort the query right away, calls FetchAborted but does not raise
        query = LogQuery()
        with SMCSocketProtocol(query) as protocol:
            protocol.abort()
    
    @mock.patch('smc_monitoring.models.query.SMCSocketProtocol', autospec=True)
    def test_query_live(self, patch):
        fields = {u'fields': [{u'comment': u'Time of creating the event record.', u'name': u'Timestamp', u'filterable': False, u'raw_type': u'time_ms', u'visible': True, u'pretty': u'Creation Time', u'id': 1}, {u'comment': u'Connection destination IP address', u'name': u'Dst', u'filterable': True, u'raw_type': u'ip', u'resolving': u'IP', u'visible': True, u'pretty': u'Dst Addr', u'id': 8}, {u'comment': u'Connection source IP address', u'name': u'Src', u'filterable': True, u'raw_type': u'ip', u'resolving': u'IP', u'visible': True, u'pretty': u'Src Addr', u'id': 7}], u'fetch': 845, u'success': u'Fetch started'}
        records = {u'records': {u'updated': [], u'added': [{u'Dst Addr': u'172.217.9.46', u'Src Addr': u'172.18.1.70', u'Creation Time': u'2017-09-04 19:38:38'}]}}
        
        mock_client = mock.MagicMock(spec=SMCSocketProtocol)
        mock_client.get_from_id = mock.Mock()
        mock_client.receive.return_value = [fields, records] 
        mock_client.__enter__.return_value = mock_client
        patch.return_value = mock_client
        
        query = ConnectionQuery('foo')
        query.format.field_ids([LogField.TIMESTAMP, LogField.SRC, LogField.DST])
        for record in query.fetch_live(RawDictFormat):
            for d in record:
                for key in d.keys():
                    self.assertIn(key, ['Dst Addr', 'Src Addr', 'Creation Time'])
   
    def test_select_and_socket(self):
        # Since the queries are mocked out, this verifies the select on socket and read
        # from a query.
        import json
        from smc_monitoring.wsocket import select
        records = {u'records': {u'updated': [], u'added': [{u'Dst Addr': u'172.217.9.46', u'Src Addr': u'172.18.1.70', u'Creation Time': u'2017-09-04 19:38:38'}]}}
        mock_socket = mock.Mock()
        with mock.patch('select.select'), mock.patch('smc_monitoring.wsocket.websocket.WebSocket.recv'):
            select.select.return_value = (mock_socket,1,1)
            websocket.WebSocket.recv.return_value = json.dumps(records)
            
            query = ConnectionQuery('foo')
            for result in query.fetch_raw(max_recv=1):
                self.assertDictEqual(result[0],
                    {u'Dst Addr': u'172.217.9.46', u'Src Addr': u'172.18.1.70', u'Creation Time': u'2017-09-04 19:38:38'})
    
    @mock.patch('smc_monitoring.models.query.SMCSocketProtocol', autospec=True)
    def test_connection_query(self, patch):
        fetch = {u'fetch': 1292367744, u'success': u'Fetch started'}
        records = {'records': {'added': [{u'delta_key': u'AcCoBEMBNM4rQgIGA4mkAlAAAAAA', u'116': u'TCP time wait', u'134': u'HTTP', u'24': u'2017-09-04 14:26:10', u'27': u'Dumb HTTP', u'46': u'Internal', u'47': u'External', u'1': u'2017-09-04 14:25:52', u'3': u'ngf-1065', u'4': u'ngf-1065', u'7': u'192.168.4.67', u'9': u'35236', u'8': u'52.206.43.66', u'302': u'2', u'20007': u'192.168.4.67', u'485': u'INFO: Connection Monitoring', u'20008': u'52.206.43.66', u'11': u'TCP', u'10': u'80', u'38': u'Shared Domain', u'15': u'10.0.0.254', u'17': u'28284', u'1028': u'2017-09-04 14:25:52', u'34': u'6'}]}}
        
        mock_client = mock.MagicMock(spec=SMCSocketProtocol)
        mock_client.get_from_id = mock.Mock()
        mock_client.receive.return_value = [fetch, records] 
        mock_client.__enter__.return_value = mock_client
        patch.return_value = mock_client
        
        query = ConnectionQuery('foo')
        # Add custom fields to the query, these should be removed when
        # the query is executed through a cloned query.
        query.format.field_ids([LogField.SRC])
        for record in query.fetch_as_element():
            self.assertEqual(record.timestamp, '2017-09-04 14:25:52')
            self.assertEqual(record.engine, 'ngf-1065')
            self.assertEqual(record.source_addr, '192.168.4.67')
            self.assertEqual(record.dest_addr, '52.206.43.66')
            self.assertEqual(record.service, 'Dumb HTTP')
            self.assertEqual(record.protocol, 'TCP')
            self.assertEqual(record.source_port, 35236)
            self.assertEqual(record.dest_port, 80)
            self.assertEqual(record.state, 'TCP time wait')
    
    @mock.patch('smc_monitoring.models.query.SMCSocketProtocol', autospec=True)
    def test_user_query(self, patch):
        fetch = {u'fetch': 1292367744, u'success': u'Fetch started'}
        records = {'records': {'added': [{u'24': u'2017-09-05 16:55:28', u'20007': u'172.18.1.36', u'38': u'Shared Domain', u'302': u'1', u'delta_key': u'AW1sY2FkbWluQGxlcGFnZXMubG9jYWwgZG9tYWluAawSASQ=', u'1': u'2017-09-05 15:57:10', u'3': u'ngf-1065', u'534': u'2017-09-05 23:57:10', u'3001': u'mlcadmin@lepages.local domain', u'4': u'ngf-1065', u'7': u'172.18.1.36', u'485': u'INFO: User Monitoring', u'34': u'33'}]}}
        
        mock_client = mock.MagicMock(spec=SMCSocketProtocol)
        mock_client.get_from_id = mock.Mock()
        mock_client.receive.return_value = [fetch, records] 
        mock_client.__enter__.return_value = mock_client
        patch.return_value = mock_client
        
        query = UserQuery('foo')
        # Add custom fields to the query, these should be removed when
        # the query is executed through a cloned query.
        query.format.field_names(['Src'])
        for record in query.fetch_as_element():
            self.assertEqual(record.timestamp, '2017-09-05 15:57:10')
            self.assertEqual(record.engine, 'ngf-1065')
            self.assertEqual(record.username, 'mlcadmin@lepages.local domain')
            self.assertEqual(record.ipaddress, '172.18.1.36')
            self.assertEqual(record.domain, 'Shared Domain')
            self.assertEqual(record.expiration, '2017-09-05 23:57:10')
    
    @mock.patch('smc_monitoring.models.query.SMCSocketProtocol', autospec=True)        
    def test_vpn_query(self, patch):
        fetch = {u'fetch': 1292367744, u'success': u'Fetch started'}
        records = {'records': {'added': [{u'delta_key': u'AAVUIc34', u'3000': u'39617297 af0c703d 3181a9b0 04aadde8', u'24': u'2017-09-05 17:09:15', u'27': u'ESP', u'525': u'172.18.1.255', u'526': u'192.168.3.255', u'1': u'2017-09-05 17:09:15', u'543': u'Enabled', u'3': u'ngf-1065', u'546': u'Disabled', u'4': u'ngf-1065', u'544': u'Disabled', u'545': u'Disabled', u'506': u'ciscoasa-5505 (10.0.0.160)', u'8': u'192.168.3.0', u'504': u'10.0.0.254', u'505': u'cisco_asa_5505', u'502': u'sg_vm_vpn', u'501': u'sg_vm_vpn', u'7': u'172.18.1.0', u'302': u'1', u'20007': u'172.18.1.0 - 172.18.1.255', u'1757': u'2017-09-05 17:09:15', u'38': u'Shared Domain', u'103': u'5421cdf8', u'485': u'INFO: VPN SA Monitoring', u'548': u'0', u'20008': u'192.168.3.0 - 192.168.3.255', u'11': u'ESP', u'549': u'0', u'547': u'Disabled', u'34': u'20', u'537': u'hmac-sha1-96/160', u'536': u'aes256-cbc', u'535': u'IPsec', u'534': u'2017-09-06 00:29:15', u'533': u'ed072ab4', u'12202': u'Enabled', u'12204': u'1500', u'12200': u'0', u'12201': u'0', u'539': u'Initiator'}]}}
        
        mock_client = mock.MagicMock(spec=SMCSocketProtocol)
        mock_client.get_from_id = mock.Mock()
        mock_client.receive.return_value = [fetch, records] 
        mock_client.__enter__.return_value = mock_client
        patch.return_value = mock_client
        
        query = VPNSAQuery('foo')
        # Add custom fields to the query, these should be removed when
        # the query is executed through a cloned query.
        query.format.field_names(['Src'])
        for record in query.fetch_as_element():
            self.assertEqual(record.timestamp, '2017-09-05 17:09:15')
            self.assertEqual(record.engine, 'ngf-1065')
            self.assertEqual(record.local_gateway, 'sg_vm_vpn')
            self.assertEqual(record.peer_gateway, 'cisco_asa_5505')
            self.assertEqual(record.local_endpoint, '10.0.0.254')
            self.assertEqual(record.peer_endpoint, 'ciscoasa-5505 (10.0.0.160)')
            self.assertEqual(record.local_networks, '172.18.1.0 - 172.18.1.255')
            self.assertEqual(record.peer_networks, '192.168.3.0 - 192.168.3.255')
            self.assertEqual(record.vpn_id, 'sg_vm_vpn')
            self.assertEqual(record.sa_type, 'IPsec')
            self.assertEqual(record.protocol, 'ESP')
            self.assertEqual(record.negotiation_role, 'Initiator')
            self.assertEqual(record.bytes_sent, 0)
            self.assertEqual(record.bytes_received, 0)
            self.assertEqual(record.expiration, '2017-09-06 00:29:15')
    
    @mock.patch('smc_monitoring.models.query.SMCSocketProtocol', autospec=True)        
    def test_route_query(self, patch):
        fetch = {u'fetch': 1292367744, u'success': u'Fetch started'}
        records = {'records': {'added': [{u'24': u'2017-09-05 17:30:13', u'13': u'Interface #1', u'38': u'Shared Domain', u'302': u'1', u'34': u'34', u'3': u'ngf-1065', u'4': u'ngf-1065', u'165': u'Connected', u'485': u'INFO: Routing Monitoring', u'delta_key': u'AAEKAhg=', u'160': u'10.0.0.0', u'161': u'24', u'163': u'0'}]}}
        
        mock_client = mock.MagicMock(spec=SMCSocketProtocol)
        mock_client.get_from_id = mock.Mock()
        mock_client.receive.return_value = [fetch, records] 
        mock_client.__enter__.return_value = mock_client
        patch.return_value = mock_client
        
        query = RoutingQuery('foo')
        # Add custom fields to the query, these should be removed when
        # the query is executed through a cloned query.
        query.format.field_ids([LogField.SRC])
        for record in query.fetch_as_element():
            self.assertEqual(record.timestamp, '2017-09-05 17:30:13')
            self.assertEqual(record.engine, 'ngf-1065')
            self.assertEqual(record.dest_if, 'Interface #1')
            self.assertEqual(record.dest_vlan, None)
            self.assertEqual(record.dest_zone, None)
            self.assertEqual(record.route_gw, None)
            self.assertEqual(record.route_network, '10.0.0.0')
            self.assertEqual(record.route_type, 'Connected')
            self.assertEqual(record.route_metric, 0)
    
    @mock.patch('smc_monitoring.models.query.SMCSocketProtocol', autospec=True)        
    def test_sslvpn_query(self, patch):
        fetch = {u'fetch': 1292367744, u'success': u'Fetch started'}
        records = {'records': {'added': [{u'24': u'2017-09-05 18:07:03', u'38': u'Shared Domain', u'302': u'1', u'3': u'ngf-1065', u'delta_key': u'ATAwMDAwMDAxb2doTElBQ2FuazZjTDJ6ckhRZ053ZnkzY0pDZXdLeEg2SUR1cFBJRkU3em1BdGlMQkkyd19pYXhuAnU=', u'20007': u'172.18.1.52', u'809': u'2017-09-05 18:07:03', u'808': u'Tunnel', u'3001': u'dlepage@InternalDomain', u'4': u'ngf-1065', u'7': u'172.18.1.52', u'810': u'2017-09-05 20:07:03', u'811': u'{SHA256}ecb381bb0fe1317f3ee63f2703b323451113edb6cbd47847ed5a49bcdc20dd57', u'485': u'INFO: SSL VPN Monitoring', u'34': u'SSL VPN Session Monitoring'}]}}
        
        mock_client = mock.MagicMock(spec=SMCSocketProtocol)
        mock_client.get_from_id = mock.Mock()
        mock_client.receive.return_value = [fetch, records] 
        mock_client.__enter__.return_value = mock_client
        patch.return_value = mock_client
        
        query = SSLVPNQuery('foo')
        for record in query.fetch_as_element():
            self.assertEqual(record.session_start, '2017-09-05 18:07:03')
            self.assertEqual(record.session_expiration, '2017-09-05 20:07:03')
            self.assertEqual(record.username, 'dlepage@InternalDomain')
            self.assertEqual(record.source_addr, '172.18.1.52')
            self.assertEqual(record.engine, 'ngf-1065')
    
    @mock.patch('smc_monitoring.models.query.SMCSocketProtocol', autospec=True)        
    def test_blacklist_query(self, patch):
        fetch = {u'fetch': 1292367744, u'success': u'Fetch started'}
        records = {'records': {'added': [{u'bldata': {u'SessionEvent': u'1', u'blacklist_href': u'http://172.18.1.150:8082/6.2/elements/fw_cluster/116/blacklist/MTA3MjA5Njg3MDU=', u'DataType': u'7', u'BlacklistEntryDuration': u'222222220', u'DataTags': u'INFO: Blacklist Monitoring', u'ReceptionTime': u'2017-09-05 18:20:40', u'NodeId': u'ngf-1065', u'BlacklistEntryId': u'TVRBM01qQTVOamczTURVPQ==', u'CompId': u'ngf-1065', u'Blacklister': u'Management Server', u'BlacklistEntrySourceIp': u'2.2.2.5', u'Timestamp': u'2017-08-26 15:52:43', u'BlacklistEntryDestinationIp': u'0.0.0.0', u'SenderDomain': u'Shared Domain', u'BlacklistEntrySourceIpPrefixlen': u'32', u'BlacklistEntryDestinationIpPrefixlen': u'32'}, u'blid': {u'Blacklist Entry ID': u'10720968705'}, u'delta_key': u'BgJ/BQAB'}]}}
        
        mock_client = mock.MagicMock(spec=SMCSocketProtocol)
        mock_client.get_from_id = mock.Mock()
        mock_client.receive.return_value = [fetch, records] 
        mock_client.__enter__.return_value = mock_client
        patch.return_value = mock_client
        
        query = BlacklistQuery('foo')
        for record in query.fetch_as_element():
            from pprint import pprint
            pprint(vars(record))
            self.assertEqual(record.blacklist_id, '10720968705')
            self.assertEqual(record.timestamp, '2017-08-26 15:52:43')
            self.assertEqual(record.engine, 'ngf-1065')
            self.assertEqual(record.href, 'http://172.18.1.150:8082/6.2/elements/fw_cluster/116/blacklist/MTA3MjA5Njg3MDU=')
            self.assertEqual(record.source, '2.2.2.5/32')
            self.assertEqual(record.destination, '0.0.0.0/32')
            self.assertEqual(record.protocol, 'ANY')
            self.assertEqual(record.source_ports, 'ANY')
            self.assertEqual(record.dest_ports, 'ANY')
            self.assertEqual(record.duration, 222222220)
            

   
            
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()