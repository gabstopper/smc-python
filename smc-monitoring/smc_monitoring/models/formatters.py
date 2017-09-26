"""
Custom formats used to return data in different formats.
These are used from the query itself when calling the fetch_as_format()
method.
For example, returning a LogQuery as a table::

    query = LogQuery(fetch_size=200)
    for log in query.fetch_batch(): # Default is TableFormat
        print(log)
        
As CSV::
    
    query = LogQuery(fetch_size=200)
    for log in query.fetch_batch(CSVFormat):
        print(log)
    
Each format also allows the ability to customize the fields that should be
in the output. By default, each query type in :py:mod:`smc_monitoring.monitors`
will have a class attribute ``field_ids`` which specify the default fields. 
These can be customized by modifying the query.format.field_ids([....])
parameter.

For example, modifying a routing query to return only destination interface
and the route network::

    query = RoutingQuery('sg_vm')
    query.format.field_ids([LogField.DSTIF, LogField.ROUTENETWORK])
    for log in query.fetch_batch():
        ...
 
The same field_id customization applies to all query types. 

A simple way to view results is to use a RawDictFormat::

    query = LogQuery(fetch_size=3)
    query.format.field_names(['Src', 'Dst'])
    for record in query.fetch_batch(RawDictFormat):
        ...

It is also possible to provide your own formatter. At a minimum you must
provide a method called ``formatted`` in your class. The custom class should
extend :class:`._Header` to support custom field_ids within the query.


.. note:: Constants are defined in :py:mod:`smc_monitoring.models.constants`. 
    Although there are many field values, not all field values will return
    results for every query. It is sometimes useful to log in to the SMC to 
    verify available fields.

"""
from smc_monitoring.models.constants import LogField


class InvalidFieldFormat(Exception):
    """
    If using a complex format type such as combined, formatters
    are not supported. These specialized formats must be returned
    in raw dict format as they've been customized to return the data
    in a specific way.
    """
    pass


class _Header(object):
    def __init__(self, query):
        self.query = query
        
        # Allow custom field_ids to be used
        field_ids = query.format.data.get('field_ids')
        # Format specified by the query for id to name mapping
        field_format = query.format.data.get('field_format')
         # If a combined filter is specified, field_format will be None
        if not field_format:
            raise InvalidFieldFormat('Field format specified is not a supported '
                'type for formatters and must be returned as a raw dict.')
        
        if not field_ids:
            field_ids = query.field_ids
         
        # Ask for the field parameters so we can create the
        # headers based on the field_format (pretty, name, id)
        fields = query.resolve_field_ids(field_ids, **query.sockopt)
        
        if not fields:
            raise ValueError(
                'Unable to resolve field IDs. Call query.format.field_ids() '
                'and set valid fields.')
        
        self.headers = []
        for ids in field_ids:
            for mapping in fields:
                if mapping.get('id') == ids:
                    self.headers.append(mapping.get(field_format))
                    break
        
        self.header_set = False
    

class CSVFormat(_Header):
    """
    Return the results in CSV format. The first line will be a comma
    separated string with the field header. This is an iterable that
    will return results in batches of 200 (max) per iteration.
    """
    def __init__(self, query):
        super(CSVFormat, self).__init__(query)
    
    def formatted(self, alist):
        format = ('%s\n')  # @ReservedAssignment
        formatted_data = ''
        if not self.header_set:
            formatted_data += format % ','.join(self.headers)
            self.header_set = True
        for element in alist:
            data_to_format = []
            for pair in self.headers:
                value = element.get(pair, '')
                if ',' in value:
                    value = value.replace(',', ' ')
                data_to_format.append(value)
            formatted_data += format % ','.join(data_to_format)
        formatted_data.rstrip()[-1]
        return formatted_data 
    
    
class TableFormat(_Header):
    """
    Return the data in a table format. The field_id values will be
    used for the table header. Spacing will be calculated for each
    batch of results to align the table. The base spacing is determined 
    by the header width, but adjusted wider if the data returned is wider.
    Anytime there is an adjustment to the width, a new table header will also
    be printed to visually realign. The query will return a max of 200 batch
    results per iteration.
    
    .. note:: Table alignment will likely not be exact between batches
        as width is calculated per batch.
    """
    def __init__(self, query):
        super(TableFormat, self).__init__(query)
        # Calculate starting column width
        self.column_width = [(header, len(header)) for header in self.headers]

    def formatted(self, alist):
        column_widths = []
        for header in self.headers:
            column_widths.append(max(len(str(column.get(header, ''))) for column in alist))
        # Create a tuple pair of key and the associated column width for data
        key_width_pair = list(zip(self.headers, column_widths))
        
        data_longest_item = dict(key_width_pair)
        current_column_width = dict(self.column_width)
        
        for col, width in current_column_width.items():
            if data_longest_item.get(col, 0) > width:
                self.header_set = False # Add header again to realign
                current_column_width[col] = data_longest_item.get(col)
        
        self.column_width = [(key, current_column_width[key]) for key in self.headers]
        
        if not self.header_set:
            header_divider = []
            #for key in key_width_pair:
            for key in self.column_width:
                header_divider.append('-' * key[1])
            # Create a list of dictionary from the keys and the header and
            # insert it at the beginning of the list. Do the same for the
            # divider and insert below the header.
            header_divider = dict(zip(self.headers, header_divider))
            alist.insert(0, header_divider)
            header = dict(zip(self.headers, self.headers))
            alist.insert(0, header)
            self.header_set = True      
    
        format = ('%-*s ' * len(self.headers)).strip() + '\n'  # @ReservedAssignment
        formatted_data = ''
        for element in alist:
            data_to_format = []
            # Create a tuple that will be used for the formatting in
            # width, value format
            #for pair in key_width_pair:
            for pair in self.column_width:
                data_to_format.append(pair[1])
                data_to_format.append(element.get(pair[0],'-'))
            formatted_data += format % tuple(data_to_format)
        formatted_data.rstrip()[-1]
        return formatted_data
    

class RawDictFormat(object):
    """
    Return the data as a list in raw dict format. The results are not
    filtered with exception of the returned fields based on field_id
    filters. This is a convenience format for consistency, although you
    can also call the :py:class:`smc_monitoring.models.query.Query.fetch_raw`
    method to get the same data.
    """
    def __init__(self, query):
        pass
    
    def formatted(self, alist):
        return alist

    