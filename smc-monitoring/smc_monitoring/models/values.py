"""
Values are used to provide searchable input for filters.
Each value format is specific to the data type added to the filter. For example,
an IPValue specifies IP's or network values that can be added to a filter from
:py:mod:`smc_monitoring.models.filters`.

Each constructor can be initialized in the following ways:

Single value::

    IPValue('1.1.1.1')

Multiple values::

    IPValue('1.1.1.1', '2.2.2.2')
    
As a list of values::

    i = ['1.1.1.1', '3.3.3.3']
    IPValue(*i)
    
The ``value`` attribute of each :class:`~Value` stores the query string as a list
that is absorbed by the filter.
"""

class Value(object):
    """
    Value is the topmost parent for all value types.
    
    :ivar value: stores value formatted into dict
    """
    def __init__(self, values):
        self.value = values 

            
class ServiceValue(Value):
    """
    Service Values allow searches on the service field. When specifying
    the service value, specify as <protocol/port>. For example, 'TCP/80',
    'UDP/53'. For ICMP, specify as ICMP/Type/Code (Code is optional).

    Search for any services with TCP port 80 and UDP port 53::
    
        query = LogQuery(fetch_size=50)
        query.add_in_filter(
            FieldValue(LogField.SERVICE), [ServiceValue('TCP/80', 'UDP/53')])
    
    :param services: service definitions
    :type services: list or str
    """
    def __init__(self, *services):
        value = [
            {'type': 'service', 'value': service} for service in services]
        super(ServiceValue, self).__init__(value)


class ConstantValue(Value):
    """
    Constant values can be used for log field values. For example,
    specifying a filter by Action can be simplified by specifying
    the constant for the action value. Constant values are not used
    for log field names (use FieldValue instead).
    
    Searching for all actions of discard and block::
    
        query = LogQuery(fetch_size=50)
        query.add_in_filter(
            FieldValue(LogField.ACTION), [ConstantValue(Actions.DISCARD, Actions.BLOCK)])
    
    :param constants: constant values
    :type constants: list or str
    """
    def __init__(self, *constants):
        value = [
            {'type': 'constant', 'value': cnst} for cnst in constants]
        super(ConstantValue, self).__init__(value)


class FieldValue(Value):
    """
    FieldValue specifies a log field filter by either constant ID or name.
    The field name field is the internal name representation for the SMC.
    To find a given field name, within SMC go to Log Viewer and drag a 
    field into the filter window, right click and select "Show Filter
    Expression". 
    
    Using field value as filter for InFilter type::
    
        query = LogQuery(fetch_size=50)
        query.add_in_filter(
            FieldValue(LogField.SRC), [IPValue('192.168.4.84')])
        
    :param fields: fields definitions by name or int ID
    :type fields: list or str
    
    .. note:: If using constant values, consult
        :py:mod:`smc.monitoring.constants.LogField` for valid attributes.
    """
    def __init__(self, *fields):
        value = []
        for field in fields:
            if isinstance(field, int):
                value.append({'type': 'field', 'id': field})
            else:
                value.append({'type': 'field', 'name': field})
        super(FieldValue, self).__init__(value)


class ElementValue(Value):
    """
    Element Values are used when creating a filter for an element already
    defined in the SMC. The element can be referenced by it's type.
    
    Search for a host element 'kali' in the 'source' log field::
    
        query = LogQuery(fetch_size=50)
        query.add_in_filter(
            FieldValue(LogField.SRC), [ElementValue(Host('kali'))])
    
    :param elements: element definitions
    :type elements: list or str
    
    .. note:: Using elements expands the search to potentially include a
        broader range of data. For example, a host can have multiple IP
        addresses, both ipv4 and ipv6.
    """
    def __init__(self, *elements):
        value = [
            {'type': 'element', 'href': element.href} for element in elements]
        super(ElementValue, self).__init__(value)

        
class IPValue(Value):
    """
    IP Values specify IP addresses used for searching.
    
    Search for IP address in source and dest fields::
    
        query = LogQuery(fetch_size=50)
        query.add_in_filter(
            IPValue('192.168.4.84'), [FieldValue(LogField.SRC, LogField.DST)])
    
    :param addresses: address definitions
    :type addresses: list or str    
    """
    def __init__(self, *addresses):
        value = [
            {'type': 'ip', 'value': addr} for addr in addresses]
        super(IPValue, self).__init__(value)


class StringValue(Value):
    """
    String value match. Note that string matching can only be done on
    log fields that are of type string (no type conversions are done
    on non-string types). String matches are also exact.
    
    Find all audits accessing URL play.googleapis.com::
    
        query = LogQuery(fetch_size=50)
        query.add_in_filter(
            FieldValue(LogField.HTTPREQUESTHOST),[StringValue('play.googleapis.com')])
    
    :param value: string to match
    :type value: list    
    """
    def __init__(self, *values):
        value = [
            {'type': 'string', 'value': value} for value in values]
        super(StringValue, self).__init__(value)
        
           
class NumberValue(object):
    pass


class TranslatedValue(object):
    def __init__(self, value):
        pass
    
    