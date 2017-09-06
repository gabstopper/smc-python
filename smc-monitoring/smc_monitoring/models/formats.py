"""
Field formats represent a way to control the format of the returned data.
By modifying a field format, you can control field level settings such as 
wther to resolve IP's via DNS, how to display field names and values and
which fields to return in the query.

Each log format will return a different view type The most common and default
for all queries is the :class:`~TextFormat` using a 'pretty' field format
which is what you will see from the column data and values if using the SMC
Log Viewer.

Return only a specific set of fields by id's::

    query = LogQuery(fetch_size=5)
    query.format.field_ids([
        LogField.TIMESTAMP, LogField.NODEID, LogField.SRC,
        LogField.DST, LogField.PROTOCOL, LogField.ACTION])

Return only a specific set of fields by name::

    query = LogQuery(fetch_size=5)
    query.format.field_names(['Src', 'Dst'])
    
.. note:: If both field_ids and field_names are provided, they will be merged.
  
"""

class FormatFieldMixin(object):
    """
    Format field methods for modifying behavior of a query.
    """
    def field_ids(self, ids):
        """
        Add filter to show only fields with given field ID's. Field ID's
        can be mapped to the LogField constants in
        :class:`smc_monitoring.models.constants.LogField`

        .. note:: Set the return display mode for the Log field name by
            using :meth:`field_format`. The display value ``name`` will
            match the name of the LogField constant.   
        """
        self.data['field_ids'] = ids
    
    def field_names(self, names):
        """
        Show only fields with given name. The ``name`` is the internal SMC
        name for the log field. The simplest way to obtain the name for a
        log field is from the SMC Log Viewer. Use the Log Viewer filter
        window to drag a column filter and select "Show Filter Expression".

        ..note:: The log field name is case sensitive and is typically
            using camelcase notation.
        """
        self.data['field_names'] = names
    
    def field_format(self, name):
        """
        Specify how the field name are printed in the response. 
        
        :param str id: as integer IDs from constants found in 
            :class:`smc_monitoring.models.constants.LogField`
        :param str name: as internal SMC names
        :param str pretty: pretty printed as you would see in the SMC UI
        """
        if name in ['id', 'name', 'pretty']:
            self.data['field_format'] = name


class TextFormat(FormatFieldMixin):
    """
    Text format with 'pretty' field formatting uses the same
    display to what you would see from the native SMC Log Viewer.
    
    Keyword arguments can optionally be provided to set 'resolving'
    fields during instance creation, or they can be set on the instance
    afterwards by calling :py:meth:`set_resolving`.
    """
    def __init__(self, field_format='pretty', **kw):
        self.data = {
            'type': 'texts',
            'field_format': field_format,
            'resolving': {
                'senders': True}
        }
        for setting, value in kw.items():
            self.data['resolving'][setting] = value
    
    def timezone(self, tz):
        """
        Set timezone on the audit records. Timezone can be in formats:
        'US/Eastern', 'PST', 'Europe/Helsinki'
        
        See SMC Log Viewer settings for more examples.
        
        :param str tz: timezone, i.e. CST
        """
        self.data['resolving'].update(
            timezone=tz,
            time_show_zone=True)
    
    def set_resolving(self, **kw):
        """
        Certain log fields can be individually resolved. Use this
        method to set these fields. Valid keyword arguments:
        
        :param str timezone: string value to set timezone for audits
        :param bool time_show_zone: show the time zone in the audit.
        :param bool time_show_millis: show timezone in milliseconds
        :param bool keys: resolve log field keys
        :param bool ip_elements: resolve IP's to SMC elements
        :param bool ip_dns: resolve IP addresses using DNS
        :param bool ip_locations: resolve locations 
        """
        if 'timezone' in kw and 'time_show_zone' not in kw:
            kw.update(time_show_zone=True)
        self.data['resolving'].update(**kw)


class DetailedFormat(TextFormat):
    """
    Detailed format does not do a Log value conversion as the TextFormat
    would, however does provide a field map in the first payload with
    characteristics of the fields in the return data. This might be a
    useful format to obtain conversion ID's for specific fields or
    debugging.
    """
    def __init__(self, field_format='pretty', **kw):
        super(DetailedFormat, self).__init__(field_format, **kw)
        self.data['type'] = 'detailed'

               
class RawFormat(FormatFieldMixin):
    """
    Raw format is an abbreviated version of the detailed format.
    Fewer fields are provided and resolution of field values is
    not done.
    """
    def __init__(self, field_format='pretty'):
        self.data = {
            'type': 'raw',
            'field_format': field_format
        }


class CombinedFormat(object):
    """    
    CombinedFormat provides a way to specify different field resolvers
    based on field name or ID. Keyword arguments provided will define a
    unique key that represents the format object and value is the format
    object itself.
    
    For example, using a combined filter to resolve the TIMESTMAP field
    in text format, but source and destination fields in detailed format::
    
        text = TextFormat()
        text.field_ids([LogField.TIMESTAMP])
        
        detailed = DetailedFormat()
        detailed.field_ids([LogField.SRC, LogField.DST])
        
        combined = CombinedFormat(tformat=text, dformat=detailed)
        
        query = LogQuery(fetch_size=1, format=combined)
        
    After executing the query, the raw record results will be formatted as
    a list of dict's, which each record having a dict key equal to keyword
    argument input provided::
    
        [{'dformat': {'Src Addr': '10.0.0.1', 'Dst Addr': '224.0.0.1'},
          'tformat': {'Creation Time': '2017-08-05 14:12:44'}},
         {'dformat': {'Src Addr': '10.0.0.1', 'Dst Addr': '224.0.0.1'},
          'tformat': {'Creation Time': '2017-08-05 14:12:44'}}]
          ...
    
    The results can then be parsed and used to provide custom views as
    necessary.
    
    :param kw: key word arguments should use an identifier key that will
        be present in the results, and a value which is a format object
        type in :py:mod:`smc.monitoring.formats`.
    """
    def __init__(self, **kw):
        self.data = {
            'type': 'combined',
            'formats': {}
        }
        for format_key, format in kw.items():  # @ReservedAssignment
            self.data['formats'].update(
                {format_key:format.data})
        
