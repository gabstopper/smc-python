"""
Time formats are optionally used in a LogQuery to specify custom ranges for
which to search 'stored' log events. 

When adding a time format to a query, the ``start_time`` and ``end_time`` values
need to be in milliseconds. The engine logs are stored in UTC time but in order
to display the client side dates properly, you should set a timezone on the
query.

There are helper methods to simplify retrieving for last_XXX period of time as
well as custom range formats.

Set up a query with a time format::

    query = LogQuery(fetch_size=50)
    query.format.timezone('Europe/Helsinki')
    query.time_range.last_five_minutes()

.. seealso:: :func:`~TimeFormat.custom_range` for more examples on creating
    custom time range formats.
    
"""
import time
from datetime import datetime, timedelta


def datetime_to_ms(dt):
    """
    Convert an unaware datetime object to milliseconds.
    This datetime should be the time you would expect to see
    on the client side. The SMC will do the timestamp conversion
    based on the query timezone.
    
    :return: value representing the datetime in milliseconds
    :rtype: int
    """
    return int(time.mktime(dt.timetuple()) * 1000)


def datetime_from_ms(ms):
    """
    Convenience to return datetime from milliseconds
    
    :return: datetime from ms
    :rtype: datetime
    """
    return datetime.fromtimestamp(ms/1000.0)


def subtract_from_now(td):
    """
    Subtract timedelta from current time
    """
    now = datetime.now()
    return int((now - td).strftime('%s'))*1000


current_millis = lambda: int(round(time.time() * 1000))

    
class TimeFormat(object):
    """
    Construct a time format to control the start and end times
    for a query. If unspecified, results will be limited by the
    fetch size quantity only. Helper methods are provided to simplify
    adding time based filters once the instance is constructed.
    
    :param int start_ms: datetime object in milliseconds. Where to
        start the query in time. If your search should go backwards
        in time, specify the oldest time/date in start_time.
    :param int end_ms: datetime object in milliseconds. Where to
        end the query in time. 
    """
    def __init__(self, start_ms=0, end_ms=0):
        """
        Create new time format instance.
        """
        self.data = {
            'start_ms': start_ms,
            'end_ms': end_ms
        }
    
    @property
    def start_time(self):
        """
        Return the start time in datetime format. Will return
        0 if start time is not specified.
        
        :rtype: datetime
        """
        return datetime_from_ms(self.data.get('start_ms')) if \
            self.data.get('start_ms') != 0 else 0
    
    @property
    def end_time(self):
        """
        Return the end time in datetime format. Will return
        0 if end time is not specified.
        
        :rtype: datetime
        """
        return datetime_from_ms(self.data.get('end_ms')) if \
            self.data.get('start_ms') != 0 else 0
        
    def last_five_minutes(self):
        """
        Add time from current time back 5 minutes
        """
        return self.custom_range(subtract_from_now(
            timedelta(minutes=5)))

    def last_fifteen_minutes(self):
        """
        Add time from current time back 15 minutes
        """
        return self.custom_range(subtract_from_now(
            timedelta(minutes=15)))
        
    def last_thirty_minutes(self):
        """
        Add time from current time back 30 minutes
        """
        return self.custom_range(subtract_from_now(
            timedelta(minutes=30)))
    
    def last_hour(self):
        """
        Add time from current time back 1 hour
        """
        return self.custom_range(subtract_from_now(
            timedelta(minutes=60)))
    
    def last_day(self):
        """
        Add time filter from current time back 1 day
        """
        return self.custom_range(subtract_from_now(
            timedelta(days=1)))
    
    def last_week(self):
        """
        Add time filter from current time back 7 days.
        """
        return self.custom_range(subtract_from_now(
            timedelta(days=7)))
    
    def custom_range(self, start_time, end_time=None):
        """
        Provide a custom range for the search query. Start time and end
        time are expected to be naive ``datetime`` objects converted to 
        milliseconds. When submitting the query, it is strongly recommended
        to set the timezone matching the local client making the query.
        
        Example of finding all records on 9/2/2017 from 06:25:30 to 06:26:30
        in the local time zone CST::
        
            dt_start = datetime(2017, 9, 2, 6, 25, 30, 0)
            dt_end = datetime(2017, 9, 2, 6, 26, 30, 0)
    
            query = LogQuery()
            query.format.timezone('CST')
            query.time_range.custom_range(
                datetime_to_ms(dt_start),
                datetime_to_ms(dt_end))
            
            for record in query.fetch_batch():
                print(record)
                
        Last two minutes from current (py2)::
        
            now = datetime.now()
            start_time = int((now - timedelta(minutes=2)).strftime('%s'))*1000
        
        Specific start time (py2)::
        
            p2time = datetime.strptime("1.8.2017 08:26:42,76", "%d.%m.%Y %H:%M:%S,%f").strftime('%s')
            p2time = int(s)*1000
            
        Specific start time (py3)::
        
            p3time = datetime.strptime("1.8.2017 08:40:42,76", "%d.%m.%Y %H:%M:%S,%f")
            p3time.timestamp() * 1000
        
        :param int start_time: search start time in milliseconds. Start time
            represents the oldest timestamp.
        :param int end_time: search end time in milliseconds. End time
            represents the newest timestamp.
        """
        if end_time is None:
            end_time = current_millis()
        
        self.data.update(
            start_ms=start_time,
            end_ms=end_time)
        return self

    