import unittest
from smc_monitoring.monitors.logs import LogQuery
from smc_monitoring.models.formats import TextFormat, DetailedFormat, RawFormat,\
    CombinedFormat
from smc_monitoring.models.constants import LogField
from smc_monitoring.models.calendar import datetime_to_ms, datetime_from_ms,\
    TimeFormat


class Test(unittest.TestCase):

    def setUp(self):
        pass


    def tearDown(self):
        pass
    
    def test_log_query_params(self):
        query = LogQuery(fetch_size=50)
        
        # Default format is TextFormat
        self.assertIsInstance(query.format, TextFormat)
        
        orig = {'fetch': {'backwards': True, 'quantity': 50},
                 'format': {'field_format': 'pretty',
                            'resolving': {'senders': True},
                            'type': 'texts'},
                 'query': {'end_ms': 0, 'start_ms': 0, 'type': 'stored'}}
        
        self.assertDictEqual(orig, query.request)
    
        # Add a timezone
        query.format.timezone('CST')
        # Check that 'resolving' was modified on the format
        resolving = {'resolving': {'timezone': 'CST',
                                   'time_show_zone': True,
                                   'senders': True},
                     'type': 'texts',
                     'field_format': 'pretty'}
        
        self.assertDictEqual(resolving, query.format.data)
        
        # Test that set_resolving works properly
        query.format.set_resolving(timezone='PST')
        self.assertEqual(query.format.data['resolving']['timezone'], 'PST')
        
        # Change field format from 'pretty' to 'name'
        query.format.field_format('name')
        self.assertEqual(query.format.data['field_format'], 'name')
        
        # Add field names to the query..
        query.format.field_names(['Src', 'Dst'])
        for name in query.format.data['field_names']:
            self.assertIn(name, ['Src', 'Dst'])
        
        # Add field IDs to the query
        query.format.field_ids([LogField.SRC, LogField.IPSAPPID])
        for _id in query.format.data['field_ids']:
            self.assertIn(_id, [LogField.SRC, LogField.IPSAPPID])
        
        
    def test_custom_formats_for_query(self):
        dt = DetailedFormat(timezone='CST',
                            time_show_zone=True,
                            ip_elements=True,
                            ip_locations=True)
        
        # Add detailed format to a query
        query = LogQuery(format=dt)
        d = {'fetch': {'backwards': True},
             'format': {'field_format': 'pretty',
                        'resolving': {'ip_elements': True,
                                      'ip_locations': True,
                                      'senders': True,
                                      'time_show_zone': True,
                                      'timezone': 'CST'},
                        'type': 'detailed'},
             'query': {'end_ms': 0, 'start_ms': 0, 'type': 'stored'}}
        
        self.assertDictEqual(d, query.request)
        
        # Change the format for a query
        rf = RawFormat(field_format='name')
        rf.field_ids([LogField.SRC, LogField.DST])
        
        query.update_format(rf)
        request = {'fetch': {'backwards': True},
                   'format': {
                       'field_format': 'name',
                       'field_ids': [7, 8],
                       'type': 'raw'},
                   'query': {'end_ms': 0, 'start_ms': 0, 'type': 'stored'}}
        
        self.assertDictEqual(request, query.request)
        
        # Start with fresh Query and add a combined filter. A combined filter
        # mixes individual formats together and when data is returned it's
        # dict key will be the mapping to the format
        
        text = TextFormat() 
        text.field_ids([LogField.TIMESTAMP]) 
         
        detailed = DetailedFormat() 
        detailed.field_ids([LogField.SRC, LogField.DST]) 
         
        combined = CombinedFormat(tformat=text, dformat=detailed)  
        query = LogQuery(fetch_size=1)
        query.update_format(combined)
        
        d = {'fetch': {'backwards': True, 'quantity': 1},
             'format': {'formats': {'dformat': {'field_format': 'pretty',
                                                'field_ids': [7, 8],
                                                'resolving': {'senders': True},
                                                'type': 'detailed'},
                                    'tformat': {'field_format': 'pretty',
                                                'field_ids': [1],
                                                'resolving': {'senders': True},
                                                'type': 'texts'}},
                        'type': 'combined'},
             'query': {'end_ms': 0, 'start_ms': 0, 'type': 'stored'}}
        
        self.assertDictEqual(d, query.request)

    def test_query_time_format(self):
        query = LogQuery()
        self.assertEqual(query.time_range.start_time, 0)
        self.assertEqual(query.time_range.end_time, 0)
        # Make sure time range is changed
        query.time_range.last_five_minutes()
        fivemin_start = query.time_range.start_time
        fivemin_end = query.time_range.end_time
        self.assertNotEqual(fivemin_start, 0)
        self.assertNotEqual(fivemin_end, 0)
        
        # Change again
        query.time_range.last_fifteen_minutes()
        fifteen_min_start = query.time_range.start_time
        fifteen_min_end = query.time_range.end_time
        self.assertNotEqual(fifteen_min_start, fivemin_start)
        self.assertNotEqual(fifteen_min_start, fivemin_end)
        
        from datetime import datetime
        # Time conversions
        dt = datetime(2017, 9, 2, 6, 25, 30, 0)
        ms = datetime_to_ms(dt)
        self.assertTrue(dt == datetime_from_ms(ms))
    
        from pprint import pprint
        
        tf = TimeFormat()
        
        def get_time_diff():
            return datetime_from_ms(tf.data.get('end_ms')) - \
                datetime_from_ms(tf.data.get('start_ms'))
        
        tf.last_five_minutes()
        self.assertEqual(get_time_diff().seconds, 300)  # 300 seconds = 5 min
        
        tf.last_fifteen_minutes()
        self.assertEqual(get_time_diff().seconds, 900)
        
        tf.last_thirty_minutes()
        self.assertEqual(get_time_diff().seconds, 1800)
        
        tf.last_hour()
        self.assertEqual(get_time_diff().seconds, 3600)
        
        tf.last_day()
        self.assertEqual(get_time_diff().days, 1)
        
        tf.last_week()
        self.assertEqual(get_time_diff().days, 7)
    

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()