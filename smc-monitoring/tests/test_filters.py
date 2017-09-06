import unittest
from pprint import pprint
from smc_monitoring.monitors.logs import LogQuery
from smc_monitoring.models.values import FieldValue, IPValue, ServiceValue,\
	StringValue, ConstantValue
from smc_monitoring.models.filters import InFilter, AndFilter, DefinedFilter,\
	NotFilter, OrFilter, TranslatedFilter
from smc_monitoring.models.constants import LogField, Actions


class Test(unittest.TestCase):
	pass
	
	def test_infilter(self):
		# Naked INFilter
		infilter = InFilter(FieldValue(LogField.SRC), [IPValue('172.18.1.1', '172.18.1.2')])
		d = {'left': {'id': 7, 'type': 'field'},
			 'right': [{'type': 'ip', 'value': '172.18.1.1'},
			           {'type': 'ip', 'value': '172.18.1.2'}],
			 'type': 'in'}
		self.assertDictEqual(infilter.filter, d)
		
		# Add to query using query method
		query = LogQuery()
		query.add_in_filter(
			FieldValue(LogField.SRC), [IPValue('172.18.1.1', '172.18.1.2')])
		query_filter = query.request['query']['filter']
		self.assertDictEqual(d, query_filter)
		
		# Update the original filter, validate update
		infilter.update_filter(FieldValue('Src'), [IPValue('1.1.1.1')])
		
		d = {'left': {'name': 'Src', 'type': 'field'},
			 'right': [{'type': 'ip', 'value': '1.1.1.1'}],
			 'type': 'in'}
		
		# Update filter on query
		self.assertDictEqual(infilter.filter, d)
		query.update_filter(InFilter(FieldValue('Src'), [IPValue('1.1.1.1')]))
		query_filter = query.request['query']['filter']
		self.assertDictEqual(d, query_filter)
		
	def test_and_filter(self):
		andfilter = AndFilter([
            InFilter(FieldValue(LogField.SRC), [IPValue('192.168.4.84')]),
            InFilter(FieldValue(LogField.SERVICE), [ServiceValue('TCP/80')])])
		
		f = {'type': 'and',
			 'values': [{'left': {'id': 7, 'type': 'field'},
			             'right': [{'type': 'ip', 'value': '192.168.4.84'}],
			             'type': 'in'},
			            {'left': {'id': 27, 'type': 'field'},
			             'right': [{'type': 'service', 'value': 'TCP/80'}],
			             'type': 'in'}]}
	
		self.assertDictEqual(andfilter.filter, f)
		
		query = LogQuery()
		query.add_and_filter([
            InFilter(FieldValue(LogField.SRC), [IPValue('192.168.4.84')]),
            InFilter(FieldValue(LogField.SERVICE), [ServiceValue('TCP/80')])])
		
		query_filter = query.request['query']['filter']
		self.assertDictEqual(f, query_filter)
		
		# Update the original filter
		andfilter.update_filter(
			[InFilter(FieldValue(LogField.DST), [IPValue('1.1.1.1')]),
			 InFilter(FieldValue(LogField.ACTION), [ConstantValue(Actions.DISCARD, Actions.BLOCK)])])
		
		d = {'type': 'and',
			 'values': [{'left': {'id': 8, 'type': 'field'},
			             'right': [{'type': 'ip', 'value': '1.1.1.1'}],
			             'type': 'in'},
			            {'left': {'id': 14, 'type': 'field'},
			             'right': [{'type': 'constant', 'value': 0},
			                       {'type': 'constant', 'value': 13}],
			             'type': 'in'}]}
	
		self.assertDictEqual(andfilter.filter, d)
		
		query.update_filter(
			AndFilter([
            		InFilter(FieldValue(LogField.DST), [IPValue('1.1.1.1')]),
              	InFilter(FieldValue(LogField.ACTION), [ConstantValue(Actions.DISCARD, Actions.BLOCK)])
            ])
		)
			
		query_filter = query.request['query']['filter']
		self.assertDictEqual(d, query_filter)
		
	def test_not_filter(self):
		notfilter = NotFilter([
			InFilter(FieldValue(LogField.SERVICE), [ServiceValue('UDP/53', 'TCP/80')])])    
		
		f = {'type': 'not',
			 'value': {'left': {'id': 27, 'type': 'field'},
			           'right': [{'type': 'service', 'value': 'UDP/53'},
			                     {'type': 'service', 'value': 'TCP/80'}],
			           'type': 'in'}}
		
		self.assertDictEqual(notfilter.filter, f)
		
		query = LogQuery()
		query.add_not_filter([
            InFilter(FieldValue(LogField.SERVICE), [ServiceValue('UDP/53', 'TCP/80')])])
		
		query_filter = query.request['query']['filter']
		self.assertDictEqual(f, query_filter)
		
		notfilter.update_filter([
			 InFilter(FieldValue(LogField.HTTPREQUESTHOST),[StringValue('play.googleapis.com')])])
			
		d = {'type': 'not',
			 'value': {'left': {'id': 1586, 'type': 'field'},
			           'right': [{'type': 'string', 'value': 'play.googleapis.com'}],
			           'type': 'in'}}
		self.assertDictEqual(d, notfilter.filter)
		
		query.update_filter(
			NotFilter([InFilter(FieldValue(LogField.HTTPREQUESTHOST),[StringValue('play.googleapis.com')])])
		)
			
		query_filter = query.request['query']['filter']
		self.assertDictEqual(d, query_filter)
		
	def test_or_filter(self):
		orfilter = OrFilter([
			InFilter(FieldValue(LogField.SRC), [IPValue('192.168.4.84')]),
			InFilter(FieldValue(LogField.SERVICE), [ServiceValue('TCP/80')])])
		
		f = {'type': 'or',
			 'values': [{'left': {'id': 7, 'type': 'field'},
			             'right': [{'type': 'ip', 'value': '192.168.4.84'}],
			             'type': 'in'},
			            {'left': {'id': 27, 'type': 'field'},
			             'right': [{'type': 'service', 'value': 'TCP/80'}],
			             'type': 'in'}]}
		
		self.assertDictEqual(orfilter.filter, f)
		
		query = LogQuery()
		query.add_or_filter([
            InFilter(FieldValue(LogField.SRC), [IPValue('192.168.4.84')]),
			InFilter(FieldValue(LogField.SERVICE), [ServiceValue('TCP/80')])])
		
		query_filter = query.request['query']['filter']
		self.assertDictEqual(f, query_filter)
		
		orfilter.update_filter([
			InFilter(FieldValue(LogField.DST), [IPValue('1.1.1.1')]),
			InFilter(FieldValue(LogField.SERVICE), [ServiceValue('TCP/443')])])
		
		d = {'type': 'or',
			 'values': [{'left': {'id': 8, 'type': 'field'},
			             'right': [{'type': 'ip', 'value': '1.1.1.1'}],
			             'type': 'in'},
			            {'left': {'id': 27, 'type': 'field'},
			             'right': [{'type': 'service', 'value': 'TCP/443'}],
			             'type': 'in'}]}
		
		self.assertDictEqual(d, orfilter.filter)
		
		query.update_filter(
			OrFilter([
			InFilter(FieldValue(LogField.DST), [IPValue('1.1.1.1')]),
			InFilter(FieldValue(LogField.SERVICE), [ServiceValue('TCP/443')])])
		)
			
		query_filter = query.request['query']['filter']
		self.assertDictEqual(d, query_filter)
	
	def test_defined(self):
		query = LogQuery()
		query.add_defined_filter(FieldValue(LogField.ACTION))
		f = {'type': 'defined',
             'value': {'id': 14, 'type': 'field'}}
		
		query_filter = query.request['query']['filter']
		self.assertDictEqual(f, query_filter)
		
	def test_translated(self):
		
		trans_filter = TranslatedFilter()
		trans_filter.within_ipv4_network('$Dst', ['192.168.4.0/24'])
		f = {'type': 'translated', 'value': '$Dst IN union(ipv4_net("192.168.4.0/24"))'}
		self.assertDictEqual(f, trans_filter.filter)
		
		trans_filter.within_ipv4_range('$Src', ['1.1.1.1-192.168.1.254'])
		f = {'type': 'translated',
 			 'value': '$Src IN range(ipv4("1.1.1.1"),ipv4("192.168.1.254"))'}
		self.assertDictEqual(f, trans_filter.filter)
		
		trans_filter.exact_ipv4_match('$Dst', ['1.1.1.1'])
		f = {'type': 'translated', 'value': '$Dst == ipv4("1.1.1.1")'}
		self.assertDictEqual(f, trans_filter.filter)
		
		trans_filter.exact_ipv4_match('$Src', ['172.18.1.152', '192.168.4.84'])
		f = {'type': 'translated',
 			 'value': '$Src IN union(ipv4("172.18.1.152"),ipv4("192.168.4.84"))'}
		self.assertDictEqual(f, trans_filter.filter)
		
		qt = LogQuery()
		tr = qt.add_translated_filter()
		tr.exact_ipv4_match('$Src', ['172.18.1.152', '192.168.4.84'])
		
		query_filter = qt.request['query']['filter']
		self.assertDictEqual(query_filter, f)
		
		
	def name_with_fields(self):
		query = LogQuery(fetch_size=100)
		
		query.add_in_filter(
			FieldValue(LogField.SRC), [IPValue('192.168.4.84')])
		
		query.format.field_format('name')
		
		logquery = {
	        "format": {
	            "type": "texts",
	            "field_format": "name",
	            "resolving": {"senders": True}
	        },
	        "query": {
	            "type":"stored",
	            "end_ms": 0,
	            "start_ms": 0,
	            "filter": {
	                "type":"in",
	                "left": {
	                    "type": "field",
	                    "id": LogField.SRC},
	                "right":[{
	                    "type": "ip",
	                    "value": "192.168.4.84"}]}
	        },
	        "fetch":{"quantity":100, 'backwards': True}
	    	   }
		
		self.assertDictEqual(query.request, logquery)
	
	
	def in_filter_ip_in_source_or_dest(self):
		ip_in_src_or_dst_filter = {
	        "format": {
	            "type": "texts",
	            "field_format": "name"
	        },
	        "query": {
	            "type":"stored",
	            "filter": {
	                "type": "in",
	                "left": {
	                    "type": "ip",
	                    "value": "10.0.0.252"},
	                "right":[
	                    {"type": "field",
	                     "name": LogField.DST},
	                    {"type": "field",
	                     "name": LogField.SRC}]}
	        },
	        "fetch":{"quantity":100}
	    	   }
		
	def in_filter_multiple_sources(self):
		multiple_sources_using_in = {
	        "format": {
	            "type": "texts",
	            "field_format": "name"
	        },
	        "query": {
	            "type":"stored",
	            "filter": {
	                "type": "in",
	                "left": {
	                    "type": "field",
	                    "name": LogField.SRC},
	                "right":[
	                    {"type": "ip",
	                     "value": "10.0.0.252"},
	                    {"type": "ip",
	                     "value": "192.168.4.84"}]}
	        },
	        "fetch":{"quantity":100}
	    	   }
		
	def by_element_filter(self):
		by_element = {
	        "format": {
	            "type": "texts",
	            "field_format": "name"
	        },
	        "query": {
	            "type":"stored",
	            "filter": {
	                "type": "in",
	                "left": {
	                    "type": "field",
	                    "name": "Src"},
	                "right":[
	                    {"type": "element",
	                     "href": Host('kali').href}]
	            }
	        },
	        "fetch":{"quantity":100}
	    	   }
	
	def defined_filter(self):
		
		defined_filter = {
	        "format": {
	            "type": "texts",
	            "field_format": "name"
	        },
	        "query": {
	            "type":"stored",
	            "filter": {
	                "type": "defined",
	                "value": {"type": "field",
	                          "id": LogField.IPSAPPID}
	                }
	        },
	        "fetch":{"quantity":100}
	    	   }
	
	def and_in_not_filter(self):
		not_filter = {
        "format": {
            "type": "texts",
            "field_format": "name"
        },
        "query": {
            "type":"stored",
            "start_ms": 0,
            "end_ms": 0,
            "filter": {
                "type": "and",
                "values": [
                    {"type": "in",
                     "left": {
                         "type": "field",
                         "name": "Src"},
                     "right":[
                         {"type": "ip",
                          "value": "172.18.1.20"}]
                    },
                    {"type": "not",
                     "value":
                        {"type": "in",
                         "left": {
                             "type": "field",
                             "id": LogField.SERVICE},
                         "right":[
                             {"type": "service",
                              "value": "UDP/53"}]
                         }
                    },       
                    ]
            }
        },
        "fetch":{"quantity":100}
    	   }
	
	def cs_ci_like_filter(self):
		cs_like_filter = {
        "format": {
            "type": "texts",
            "field_format": "name"
        },
        "query": {
            "type":"stored",
            "filter": {
                "type": "ci_like",
                "left": {
                    "type": "field",
                    "id": LogField.INFOMSG},
                "right": {
                    "type": "string", 
                    "value":"Connection was reset by client" }
                }
        },
        "fetch":{"quantity":100}
    	   }
	
	def resolving(self):
		resolved = {
			{'fetch': {'backwards': True, 'quantity': 50},
			 'format': {'field_format': 'name',
			            'resolving': {'senders': True,
			                          'time_show_zone': True,
			                          'timezone': 'CST'},
			            'type': 'texts'
			            },
			 'query': {'end_ms': 0,
			           'filter': {'left': {'id': 7, 'type': 'field'},
			                      'right': [{'type': 'ip', 'value': '192.168.4.84'}],
			                      'type': 'in'},
			           'start_ms': 0,
			           'type': 'stored'}
			}
		}
	
	def combined(self):
		combined = {
        'fetch': {'quantity': 50},
        'format': {
            'type': 'combined',
            'formats': {
                "format": {
                    "type": "texts",
                    "field_format": "name",
                    "field_ids" : [LogField.TIMESTAMP, LogField.PROTOCOL]
                },
                "format2": {
                    "type": "detailed",
                    "field_ids": [LogField.SRC, LogField.DST]
                }
            },
        },
        'query': {}
    	   }
    
