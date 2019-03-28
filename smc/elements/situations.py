"""
Module that represents inspection and correlated situations.

.. versionadded:: 0.6.3
    Requires SMC version >= 6.5

Situations can be either inspection related or correlated. Both types can be
searched to obtain collections.

Every situation has an associated 'context' which identifies properties of
the situation and how matching or correlation is performed.

A situation context group is a top level structure that encapsulates similar
individual inspection contexts. You can retrieve these as follows::

    >>> from smc.elements.situations import SituationContextGroup
    >>> for group in SituationContextGroup.objects.all():
    ...   group
    ... 
    SituationContextGroup(name=DoS Detection)
    SituationContextGroup(name=FINGER)
    SituationContextGroup(name=SMTP Deprecated)
    SituationContextGroup(name=PPTP)
    SituationContextGroup(name=IPv6)
    SituationContextGroup(name=NETBIOS)
    SituationContextGroup(name=SIP)
    SituationContextGroup(name=SNMP)

You can optionally retrieve situation context groups directly, and iterate
the inspection contexts (sub_elements), which might be additional situation
context groups or inspection contexts::

    >>> group = SituationContextGroup('DoS Detection')
    >>> group.sub_elements
    [InspectionSituationContext(name=TCP synflood detection (SYN-ACK timeout based detection)),
     InspectionSituationContext(name=TCP synflood detection (SYN-timeout method)),
     InspectionSituationContext(name=Non-ratebased DoS attacks),
     InspectionSituationContext(name=TCP DoS events),
     InspectionSituationContext(name=UDP DoS events), InspectionSituationContext(name=UDP DoS detected)]

If you are interested in inspection contexts directly (i.e. groups are
'flattened' out), you can retrieve these as follows::

    >>> from smc.elements.situations import InspectionSituationContext
    >>> for context in InspectionSituationContext.objects.all():
    ...   context
    ... 
    InspectionSituationContext(name=Context for DNS_POLICY_NOTIFY_FAIL)
    InspectionSituationContext(name=Context for FTP AUTH success)
    InspectionSituationContext(name=TCP PPTP Server Stream)
    InspectionSituationContext(name=Context for SMTP_INCONSISTENT_REPLIES)
    InspectionSituationContext(name=Context for TCP Option Too Short)
    InspectionSituationContext(name=RIFF File Stream)
    InspectionSituationContext(name=Context for IP Total Length Error)
    ...
    
You can optionally retrieve an inspection situation context directly. Most
situation contexts are system level elements and will be read only, but you
can fetch them to view configurations if necessary. 

Every situation context will have at least one `situation parameter`, which
is the parameter / value pair used to match the on inspection situations which
are categorized by the situation context. For example, in the case of detecting
a text file stream, a single regular expression type situation parameter is used::

    >>> context = InspectionSituationContext('Text File Stream')
    >>> for parameter in context.situation_parameters:
    ...   parameter
    ... 
    SituationParameter(name=Regular Expression)
    
Inspection Situations are the individual events that are either predefined or
system defined that identify specific events to inspect for. All inspection
situations have an inspection context (see above), and can also be customized
or be duplicated.

Creating an inspection situation is a two step process. You must first create
the situation with a specified context, then add the necessary parameter values.

An example of creating a new situation that uses a regular expression pattern
to match within a Text File Stream::

    >>> from smc.elements.situations import InspectionSituation
    >>> from smc.elements.situations import InspectionSituationContext
    >>> 
    >>> situation = InspectionSituation.create(name='foosituation', situation_context=InspectionSituationContext('Text File Stream'), severity='high')
    >>> situation
    InspectionSituation(name=foosituation)
    >>> situation.create_regular_expression(r'(?x)\\n.*ActiveXObject \\x28 \\x22 WScript\\.Shell(?[s_file_text_script -> sid()])\\n')
    >>>

"""
from smc.base.model import Element, ElementRef, ElementList, SubElement,\
    ElementCache, ElementCreator
from smc.api.exceptions import CreateElementFailed, ElementNotFound
from smc.elements.other import SituationTag


SEVERITY = {10: 'critical', 7: 'high', 4: 'low', 1: 'information'}


def _severity_by_name(name):
    """
    Return the severity integer value by it's name. If not found,
    return 'information'.
    
    :rtype: int
    """
    for intvalue, sevname in SEVERITY.items():
        if name.lower() == sevname:
            return intvalue
    return 1


class SituationParameter(SubElement):
    """
    A situation parameter defines the parameter type used to define
    the inspection situation context. For example, Regular Expression
    would be a situation parameter.
    """
    @property
    def type(self):
        """
        The type of this situation parameter in textual format. For
        example, integer, regexp, etc.
        
        :rtype: str
        """
        return self.data.get('type')
    
    @property
    def display_name(self):
        """
        The display name as shown in the SMC
        
        :rtype: str
        """
        return self.data.get('display_name')
    
    @property
    def order(self):
        """
        The order placement for this parameter. This is only relevant when
        there are multiple parameters in an inspection context definition.
        
        :rtype: int
        """
        return self.data.get('order', 0)


class SituationParameterValue(SubElement):
    """
    The situation parameter value is associated with a situation parameter
    and as the name implies, provides the value payload for the given
    parameter.
    """
 

class SituationContextGroup(Element):
    """
    A situation context group is simply a top level group for organizing
    individual situation contexts. This is a top level element that can
    be retrieved directly::
    
        >>> from smc.elements.situations import SituationContextGroup
        >>> for group in SituationContextGroup.objects.all():
        ...   group
        ... 
        SituationContextGroup(name=DoS Detection)
        SituationContextGroup(name=FINGER)
        SituationContextGroup(name=SMTP Deprecated)
        SituationContextGroup(name=PPTP)
        SituationContextGroup(name=IPv6)
        SituationContextGroup(name=NETBIOS)
        SituationContextGroup(name=SIP)
        SituationContextGroup(name=SNMP)
        ...
    
    :ivar list(InspectionContext, InspectionContextGroup) sub_elements: the
        members of this inspection context group
    """
    typeof = 'situation_context_group'
    sub_elements = ElementList('sub_elements')


class SituationContext(Element):
    """
    A situation context can be used by an inspection situation or by a
    correlated situation. The context defines the situation parameters
    used to define a pattern match and how that match is made.
    
    :ivar str name: name of this situation context
    :ivar str comment: comment for the context
    """
    @property
    def description(self):
        """
        Description for this context
        
        :rtype: str
        """
        return self.data.get('description', '')
    
    @property
    def situation_parameters(self):
        """
        Situation parameters defining detection logic for the context.
        This will return a list of SituationParameter indicating how
        the detection is made, i.e. regular expression, integer value,
        etc.
        
        :rtype: list(SituationParameter)
        """
        for param in self.data.get('situation_parameters', []):
            cache = ElementCache(data=self.make_request(href=param))
            yield type('SituationParameter', (SituationParameter,), {
                'data': cache})(name=cache.name, type=cache.type, href=param)
                

class InspectionSituationContext(SituationContext):
    """
    Represents groups of situation contexts that can be characterized by
    a common technique used for identifying the situation. Contexts also
    typically have in common the type of situation they apply to, i.e.
    `File Text Stream` would be an inspection context, and encapsulates
    inspection situations such as ActiveX in text file stream detection,
    etc.
    """
    typeof = 'inspection_situation_context'


class CorrelationSituationContext(SituationContext):
    """
    Correlation Contexts define the patterns for matching groups of related
    events in traffic. Examples of correlation contexts are Count, Compress,
    Group, Match and Sequence. See SMC documentation for more details on
    each context type and meaning.
    """
    typeof = 'correlation_situation_context'
    
    
class Situation(Element):
    """
    Situation defines a common interface for inspection and correlated
    situations.
    """
    typeof = 'situations'
    situation_context = ElementRef('situation_context_ref')
    
    @property
    def severity(self):
        """
        The severity of this inspection situation, critical, high,
        low, information
        
        :rtype: int
        """
        return SEVERITY.get(self.data.get('severity'))

    @property
    def description(self):
        """
        The description for this situation
        
        :rtype: str
        """
        return self.data.get('description', '')
    
    @property
    def attacker(self):
        """
        How the Attacker is determined when the Situation matches. This
        information is used for blacklisting and in log entries and may
        be None
        
        :rtype: str or None
        """
        return self.data.get('attacker')
    
    @property
    def target(self):
        """
        How the Target is determined when the Situation matches. This
        information is used for blacklisting and in log entries and may
        be None
        
        :rtype: str or None
        """
        return self.data.get('target')

    @property
    def parameter_values(self):
        """
        Parameter values for this inspection situation. This correlate to
        the the situation_context.
        
        :rtype: list(SituationParameterValue)
        """
        for param in self.data.get('parameter_values', []):
            cache = ElementCache(data=self.make_request(href=param))
            name = '{}'.format(cache.type.title()).replace('_', '')
            yield type(name, (SituationParameterValue,), {
                'data': cache})(name=cache.name, type=cache.type, href=param)
    

class InspectionSituation(Situation):
    """
    It is an element that identifies and describes detected events in the
    traffic or in the operation of the system. Situations contain the
    Context information, i.e., a pattern that the system is to look for in
    the inspected traffic.
    """
    typeof = 'inspection_situation'
    
    @classmethod
    def create(cls, name, situation_context, attacker=None, target=None,
               severity='information', situation_type=None, description=None,
               comment=None):
        """
        Create an inspection situation.
        
        :param str name: name of the situation
        :param InspectionSituationContext situation_context: The situation
            context type used to define this situation. Identifies the proper
            parameter that identifies how the situation is defined (i.e. regex, etc).
        :param str attacker: Attacker information, used to identify last packet
            the triggers attack and is only used for blacklisting. Values can
            be packet_source, packet_destination, connection_source, or
            connection_destination
        :param str target: Target information, used to identify the last packet
            that triggers the attack and is only used for blacklisting. Values
            can be packet_source, packet_destination, connection_source, or
            connection_destination
        :param str severity: severity for this situation. Valid values are
            critical, high, low, information
        :param str description: optional description
        :param str comment: optional comment
        """
        try:
            json = {
                'name': name, 'comment': comment,
                'description': description,
                'situation_context_ref': situation_context.href,
                'attacker': attacker, 'victim': target,
                'severity': _severity_by_name(severity)}
            
            element = ElementCreator(cls, json)
            tag = situation_type or SituationTag('User Defined Situations')
            tag.add_element(element)
            return element
            
        except ElementNotFound as e:
            raise CreateElementFailed('{}. Inspection Situation Contexts require SMC '
                'version 6.5 and above.'.format(str(e)))
        
    def create_regular_expression(self, regexp):
        """
        Create a regular expression for this inspection situation
        context. The inspection situation must be using an inspection
        context that supports regex.
        
        :param str regexp: regular expression string
        :raises CreateElementFailed: failed to modify the situation
        """
        for parameter in self.situation_context.situation_parameters:
            if parameter.type == 'regexp':
                return self.add_parameter_value(
                    'reg_exp_situation_parameter_values',
                    **{'parameter_ref': parameter.href,
                       'reg_exp': regexp}) # Treat as raw string

        raise CreateElementFailed('The situation does not support a regular '
            'expression as a context value.')

    def add_parameter_value(self, resource, **value):
        return self.make_request(
            CreateElementFailed,
            method='create', 
            resource=resource,
            json=value)
    
    def find_vulnerabilities(self):
        pass # Not yet implemented
        
    @property
    def vulnerability_references(self):
        """
        If this inspection situation has associated CVE, OSVDB, BID,
        etc references, this will return those reference IDs
        
        :rtype: list(str)
        """
        return self.data.get('vulnerability_references', [])
    

class CorrelationSituation(Situation):
    """
    Correlation Situations are used by NGFW Engines and Log Servers to
    conduct further analysis of detected events. Correlation Situations do
    not handle traffic directly. Instead they analyze the events generated by
    matches to Situations found in traffic. Correlation Situations use Event
    Binding elements to define the log events that bind together different
    types of events in traffic. 
    """
    typeof = 'correlation_situation'
    
#     @classmethod
#     def create(cls, **kw):
#         return ElementCreator(json=kw)
    

