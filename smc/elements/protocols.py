"""
.. versionadded:: 0.6.2
    Requires SMC version >= 6.4.3

Protocols define elements within the SMC that are specified to Protocol Agents.
Protocol Agents can be attached to specific services by type. If a service inherits
the ProtocolAgentMixin, the service type is eligible to add a protocol agent.

An example of attaching a protocol agent to a generic TCP Service, in this
case used as a custom HTTP service::

    >>> TCPService.create(name='testservice', min_dst_port=8080,
            protocol_agent=ProtocolAgent('HTTP'), comment='foo')
    TCPService(name=testservice)
    
You can optionally also add a protocol agent to an existing service if the
service is already created::

    >>> from smc.elements.protocols import ProtocolAgent
    >>> service.update_protocol_agent(ProtocolAgent('HTTP'))
    >>> service.update()
    ...
    >>> service.protocol_agent
    ProtocolAgent(name=HTTP)

To make modifications on an existing Protocol Agent assigned to a service,
you can iterate the protocol agent values to see the available parameter settings
then call update on the same collection.

For example, to set the above service to redirect to a Proxy Server (CIS redirect),
you can use this logic.

First view the available protocol agent parameters::

    >>> service = TCPService('testservice')
    >>> service.protocol_agent
    ProtocolAgent(name=HTTP)
    ...
    >>> for parameter in service.protocol_agent_values:
    ...    parameter
    ... 
    BooleanValue(name=http_enforce_safe_search,description=Enforce SafeSearch,value=0)
    ProxyServiceValue(name=redir_cis,description=Redirect to Proxy Server,proxy_server=None)
    StringValue(name=http_server_stream_by_user_agent,description=Optimized server stream fingerprinting,value=Yes)
    StringValue(name=http_url_logging,description=Logging of accessed URLs,value=Yes)

The parameters returned all inherit from a base class template :class:`~ProtocolParameterValue`.
Each returned parameter is generated dynamically based on the type of input expected for the given
parameter/field type.

.. note:: The `description` field of the parameter matches what you would see in the SMC UI under
    the Protocol Parameters tab of a service using a ProtocolAgent. The `name` field is the internal
    name that you would use to reference the setting when calling `protocol_agent_values.update`.

We want to add the CIS (ProxyServer) redirect, so update is done on the 'redir_cis' (name) field::

    >>> from smc.elements.servers import ProxyServer
    >>> service.protocol_agent_values.update(name='redir_cis', proxy_server=ProxyServer('generic5'))
    True
    
The update was successful, and we can now validate the parameter repr shows an assigned proxy::

    >>> for parameter in service.protocol_agent_values:
    ...   parameter
    ... 
    BooleanValue(name=http_enforce_safe_search,description=Enforce SafeSearch,value=0)
    ProxyServiceValue(name=redir_cis,description=Redirect to Proxy Server,proxy_server=ProxyServer(name=generic5))
    StringValue(name=http_server_stream_by_user_agent,description=Optimized server stream fingerprinting,value=Yes)
    StringValue(name=http_url_logging,description=Logging of accessed URLs,value=Yes)

Lastly, to commit this change to SMC, you must still call `update` on the service element::

    service.update()


You can unset a ProxyServer by setting the proxy_server field to None and updating::

    service.update_protocol_agent(None)
    service.update()

"""
from smc.base.model import Element, SubElement, ElementCache
from smc.base.decorators import cached_property
from smc.elements.servers import ProxyServer
from smc.base.util import element_resolver
from smc.base.structs import BaseIterable
from smc.api.exceptions import MissingDependency


class ProtocolAgentMixin(object):
    """
    ProtocolAgentMixin is used by services that allow a protocol
    agent. 
    """
    @property
    def protocol_agent(self):
        """ Protocol Agent for this service

        :return: Return the protocol agent or None if this service does not
            reference a protocol agent
        :rtype: ProtocolAgent
        """
        if 'protocol_agent_ref' in self.data:
            return Element.from_href(self.protocol_agent_ref)
    
    @property
    def protocol_agent_values(self):
        """
        Protocol agent values are protocol specific settings configurable
        on a service when a protocol agent is assigned to that service.
        This property will return an iterable that represents each protocol
        specific parameter and it's value.
        
        :rtype: BaseIterable(ProtocolAgentValues)
        """ 
        if 'paValues' in self.data:
            return ProtocolAgentValues(self.protocol_agent, self.paValues)
        return []
        
    def update_protocol_agent(self, protocol_agent):
        """
        Update this service to use the specified protocol agent.
        After adding the protocol agent to the service you must call
        `update` on the element to commit.
        
        :param str,ProtocolAgent protocol_agent: protocol agent element or href
        :return: None
        """
        if not protocol_agent:
            for pa in ('paValues', 'protocol_agent_ref'):
                self.data.pop(pa, None)
        else:
            self.data.update(protocol_agent_ref=element_resolver(protocol_agent))


class ProtocolAgent(Element):
    """ 
    Protocol Agents ensure that related connections for a service are properly
    grouped and evaluated by the engine, as well as assisting the engine with
    content filtering or network address translation tasks.
    """
    typeof = 'protocol'
    
    def _get_param_values(self, name):
        """
        Return the parameter by name as stored on the protocol
        agent payload. This loads the data from the local cache
        versus having to query the SMC for each parameter.
        
        :param str name: name of param
        :rtype: dict
        """
        for param in self.data.get('paParameters', []):
            for _pa_parameter, values in param.items():
                if values.get('name') == name:
                    return values
        
    @cached_property
    def parameters(self):
        """
        Protocol agent parameters are settings specific to the protocol agent
        type. Each protocol agent will have parameter settings that are
        configurable when a service uses a given protocol agent. Parameters
        on the protocol agent are templates that define settings exposed in
        the service. These are read-only attributes.
        
        :rtype: list(ProtocolParameter)
        """
        return [type('ProtocolParameter', (SubElement,), {
            'data': ElementCache(data=self._get_param_values(param.get('name')))}
            )(**param)
            for param in self.make_request(resource='pa_parameters')]
        
    
class ProtocolParameterValue(object):
    """
    A ProtocolParameterValue defines a protocol agent parameter setting
    when a protocol agent is assigned to a service. There are multiple
    protocol parameter types and each protocol agent will have specific
    parameters depending on functionality.
    
    Read only attributes are:
    
    :ivar ProtocolAgent protocol_agent: The protocol agent for this parameter value
    :ivar dict protocol_agent_values: The protocol agent values for this setting
    :ivar str description: The read-only description of this setting, used in SMC UI
    :ivar str type: The value type that this parameter is expected, i.e. string, integer, etc
    
    Mutable attributes are:
    
    :ivar str value: The mutable value for this particular setting
    
    """
    @cached_property
    def protocol_parameter(self):
        """
        The protocol parameter defined from the base protocol agent. This is a
        read-only element that provides some additional context to the parameter
        setting.
        
        :rtype: ProtocolParameter
        """
        for parameter in self.protocol_agent.parameters:
            if parameter.href in self.protocol_agent_values.get('parameter_ref', []):
                return parameter
        
    @property
    def description(self):
        """
        Description of this protocol parameter. The description is what will
        be displayed on the service properties under the Protocol Parameters
        tab when a Protocol Agent is assigned to a service
        
        :rtype: str
        """
        return getattr(self.protocol_parameter, 'description', '')
    
    @property
    def name(self):
        """
        Name of this protocol setting
        
        :rtype: str
        """
        return getattr(self.protocol_parameter, 'name', '')
    
    @property
    def type(self):
        """
        The type of this parameter. Can be string value, integer value, etc.
        The type is returned as a string representation.
        
        :rtype: str
        """
        return getattr(self.protocol_parameter, 'type', '')
    
    @property
    def value(self):
        """
        The value for this given protocol parameter. The return type is defined
        by the `type` of parameter
        
        :return: value based on `type` of parameter. Will return None if this parameter
            does not support the `value` key for this parameter
        """
        return self.protocol_agent_values.get('value')
    
    def _update(self, **kwargs):
        """
        Update the mutable field `value`.
        
        :rtype: bool
        """
        if 'value' in kwargs and self.protocol_agent_values.get('value') != \
            kwargs.get('value'):
            self.protocol_agent_values.update(value=kwargs['value'])
            return True
        return False
    
    def __repr__(self):
        return '%s(name=%s,description=%s,value=%s)' % (
            self.__class__.__name__, self.name, self.description, self.value)
    

class ProxyServiceValue(ProtocolParameterValue):
    """
    This represents a protocol parameter specific to setting a redirect to
    proxy setting on a service with a protocol agent.
    
    Mutable attributes are:
    
    :ivar str proxy_server: The mutable value for this particular setting.
        Represents the ProxyServer element
    """
    @property
    def _inspected_service_ref(self):
        return self.protocol_agent_values.get('inspected_service_ref')
    
    @property
    def proxy_server(self):
        """
        The ProxyServer element referenced in this protocol parameter, if any.
        
        :return: The proxy server element or None if one is not assigned
        :rtype: ProxyServer
        """
        # TODO: Workaround for SMC 6.4.3 which only provides the inspected service
        # reference. We need to find the Proxy Server from this ref.
        if self._inspected_service_ref:
            for proxy in ProxyServer.objects.all():
                if self._inspected_service_ref.startswith(proxy.href+'/'):
                    return proxy
    
    def _update(self, **kwargs):
        """
        Internal method to update the parameter dict stored in attribute
        protocol_agent_values. Allows masking of real attribute names to
        something more sane.
        
        :rtype: bool
        """
        updated = False
        if 'proxy_server' in kwargs:
            proxy_server = kwargs.get('proxy_server')
            if not proxy_server and self._inspected_service_ref:
                self.protocol_agent_values.pop('inspected_service_ref', None)
                updated = True
            elif isinstance(proxy_server, ProxyServer):
                # Need the inspected service reference for the protocol
                enabled_services = {svc.name:svc.href for svc in proxy_server.inspected_services}
                
                if self.protocol_agent.name not in enabled_services:
                    raise MissingDependency('The specified ProxyServer %r does not enable '
                        'the required protocol %s' % (proxy_server.name, self.protocol_agent.name))
                
                if self._inspected_service_ref != enabled_services.get(self.protocol_agent.name):
                    self.protocol_agent_values['inspected_service_ref'] = enabled_services.get(
                        self.protocol_agent.name)
                    updated = True
        return updated
        
    def __repr__(self):
        return '%s(name=%s,description=%s,proxy_server=%s)' % (
            self.__class__.__name__, self.name, self.description, self.proxy_server)


class TlsInspectionPolicyValue(ProtocolParameterValue):
    """
    This represents HTTPS Inspection Exceptions that would be a parameter
    for a HTTPS Protocol Agent service.
    
    Mutable attributes are:
    
    :ivar str tls_policy: The mutable value for this particular setting.
        Represents the HTTPS Inspection Exceptions element
    """
    @property
    def _tls_inspection_policy_ref(self):
        return self.protocol_agent_values.get('tls_inspection_policy_ref')
    
    @property
    def tls_policy(self):
        """
        The HTTPSInspectionExceptions element referenced in this protocol
        agent parameter. Will be None if one is not assigned.
        
        :return: The https inspection exceptions element or None if not
            assigned
        :rtype: HTTPSInspectionExceptions
        """
        if self._tls_inspection_policy_ref:
            return Element.from_href(self._tls_inspection_policy_ref)
    
    def _update(self, **kwargs):
        if 'tls_policy' in kwargs:
            tls_policy = kwargs.get('tls_policy')
            if not tls_policy and self._tls_inspection_policy_ref:
                self.protocol_agent_values.pop('tls_inspection_policy_ref', None)
                return True
            elif tls_policy and tls_policy.href != self._tls_inspection_policy_ref:
                self.protocol_agent_values.update(
                    tls_inspection_policy_ref=tls_policy.href)
                return True
        return False

    def __repr__(self):
        return '%s(name=%s,description=%s,tls_policy=%s)' % (
            self.__class__.__name__, self.name, self.description, self.tls_policy)


class ProtocolAgentValues(BaseIterable):
    """
    Protocol Agent Values define settings that can be set for specific
    protocols when a protocol agent is referenced in a service.
    
    This is a collection of parameters that are relevant based on the
    protocol agent type. This is called from the service itself when a
    service has a protocol agent attached. An example of iterating a 
    given service with an HTTP protocol agent attached::
    
        >>> from smc.elements.service import TCPService
        >>> service = TCPService('mynewservice')
        >>> service.protocol_agent
        ProtocolAgent(name=HTTP)
        >>> for parameter in service.protocol_agent_values:
        ...   parameter
        ... 
        BooleanValue(name=http_enforce_safe_search,description=Enforce SafeSearch,value=0)
        ProxyServiceValue(name=redir_cis,description=Redirect to Proxy Server,proxy_server=None)
        StringValue(name=http_server_stream_by_user_agent,description=Optimized server stream fingerprinting,value=Yes)
        StringValue(name=http_url_logging,description=Logging of accessed URLs,value=Yes)
        
    Each protocol agent parameter has a name value and description.
    The name is an internal name representation but the description is
    the value you would see within the SMC UI for the given field.
    
    Each parameter class is dynamically generated based on the class template
    ProtocolParameterValue. The class name indicates the type of parameter
    value that is expected for the given field.
        
    :rtype: ProtocolParameterValue
    """
    _class_map = {'proxy_service_value': ProxyServiceValue,
                  'tls_inspection_policy_value': TlsInspectionPolicyValue}
    
    def __init__(self, protocol_agent, values):
        items = []
        for parameter_value in values:
            for value_type, val in parameter_value.items():
                items.append(
                    type(str(value_type.title().replace('_', '')),
                         (self._class_map.get(value_type, ProtocolParameterValue),), {
                             'protocol_agent': protocol_agent,
                             'protocol_agent_values': val})()
                )
        super(ProtocolAgentValues, self).__init__(items)
    
    def update(self, name, **kwargs):
        """
        Update protocol agent parameters based on the parameter name.
        Provide the relevant keyword pairs based on the parameter type.
        When update is called, a boolean is returned indicating whether
        the field was successfully updated or not. You should check the
        return value and call `update` on the service to commit to SMC.
        
        Example of updating a TCP Service using the HTTPS Protocol Agent
        to set an HTTPS Inspection Exception::
        
            >>> service = TCPService('httpsservice')
            >>> service.protocol_agent
            ProtocolAgent(name=HTTPS)
            >>> for parameter in service.protocol_agent_values:
            ...   parameter
            ... 
            ProxyServiceValue(name=redir_cis,description=Redirect connections to Proxy Server,proxy_server=None)
            BooleanValue(name=http_enforce_safe_search,description=Enforce SafeSearch,value=0)
            StringValue(name=http_server_stream_by_user_agent,description=Optimized server stream fingerprinting,value=Yes)
            StringValue(name=http_url_logging,description=Logging of accessed URLs,value=Yes)
            TlsInspectionPolicyValue(name=tls_policy,description=HTTPS Inspection Exceptions,tls_policy=None)
            StringValue(name=tls_inspection,description=HTTPS decryption and inspection,value=No)
            ...
            >>> service.protocol_agent_values.update(name='tls_policy', tls_policy=HTTPSInspectionExceptions('myexceptions'))
            True
            
        :param str name: The name of the parameter to update
        :param dict kwargs: The keyword args to perform the update
        :raises ElementNotFound: Can be thrown when an element reference
            was passed but the element does not exist
        :raises MissingDependency: A dependency was missing preventing the
            update. This can happen when adding a ProxyServer for a protocol
            that isn't enabled
        """
        for value in self.items:
            if value.name == name:
                return value._update(**kwargs)
        return False
    
    def get(self, parameter_name):
        """
        Get the parameter by it's name. This is a convenience for fetching.
        For example, fetch the proxy server (redir_cis) parameter from a
        HTTP or HTTPS protocol agent::
        
            pv = newservice.protocol_agent_values.get('redir_cis')
        
        :return: Return the parameter value if it exists, otherwise None
        :rtype: ProtocolParameterValue
        """
        return super(ProtocolAgentValues, self).get(name=parameter_name)
