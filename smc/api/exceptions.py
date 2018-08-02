'''
Exceptions Module
'''
import smc.api.web
from smc.base.util import unicode_to_bytes


class SMCException(Exception):
    """ Base class for exceptions """


class SessionNotFound(SMCException):
    """
    Retrieving a session by name did not succeed because the session did
    not already exist
    """


class SessionManagerNotFound(Exception):
    def __init__(self, message=''):
        msg = 'A session manager was not found for this session. This generally means '\
        'the session was not obtained through the standard session factory or the session '\
        'manager may have been replaced. '
        _msg = message or msg
        super(SessionManagerNotFound, self).__init__(_msg)


class ConfigLoadError(SMCException):
    """
    Thrown when there was a problem reading credential information from
    file. Typically caused by missing settings.
    """


class SMCConnectionError(SMCException):
    """
    Thrown when there are connection related issues with the SMC.
    This could be that the underlying http requests library could not connect
    due to wrong IP address, wrong port, or time out
    """


class SMCOperationFailure(SMCException):
    """ Exception class for storing results from calls to the SMC
    This is thrown for HTTP methods that do not return the expected HTTP
    status code. See each http_* method in :py:mod:`smc.api.web` for
    expected success status

    :param response: response object returned from HTTP method
    :param msg: optional msg to insert

    Instance attributes:

    :ivar response: http request response object
    :ivar code: http status code
    :ivar status: status from SMC API
    :ivar message: message attribute from SMC API
    :ivar details: details list from SMC API (may not always exist)
    :ivar smcresult: :py:class:`smc.api.web.SMCResult` object for consistent returns
    """

    def __init__(self, response=None):
        # Response is type <class 'requests.models.Response'>
        self.response = response
        self.code = None
        self.smcresult = smc.api.web.SMCResult()
        if response is not None:
            self._unpack_response()

    def _unpack_response(self):
        details = None
        self.code = self.response.status_code
        if self.response.headers.get('content-type') == 'application/json':
            try:
                data = self.response.json()
            except ValueError:
                message = 'No valid message returned from SMC server'
            else:
                message = data.get('message', None)
                details = data.get('details', None)
        else:  # it's not json
            if self.response.text:
                message = self.response.text
            else:
                message = "No message returned from SMC server"

        self.smcresult.code = self.code

        if details:
            details = unicode_to_bytes(' '.join(details)) \
                if isinstance(details, list) else unicode_to_bytes(details)
            # Some error messages from SMC include line breaks
            details = details.replace('\n', ' ').rstrip()

        if message:
            message = unicode_to_bytes(message)

        if message and details:
            self.smcresult.msg = '{} {}'.format(message, details)
        elif details:
            self.smcresult.msg = details
        else:
            self.smcresult.msg = message

    def __repr__(self):
        return 'SMCOperationFailure(response=%s)' % (self.response)


class CertificateError(SMCException):
    """
    Related to certificate based operations like requests, signing, or
    creation. For example, engines that are not initialized can not respond
    to certificate creation requests and SMC API will return an error.
    """


class CertificateImportError(CertificateError):
    """
    Failure to import a certificate or private key
    """


class CertificateExportError(CertificateError):
    """
    Failure to export a certificate
    """


class CreateEngineFailed(SMCException):
    """
    Thrown when a POST operation returns with a failed response.
    API based response will be returned as the exception message
    """


class LoadEngineFailed(SMCException):
    """ Thrown when attempting to load an engine that does not
    exist
    """


class PolicyCommandFailed(SMCException):
    """
    Generic policy related command failures such as opening
    or closing a VPN policy.
    """


class CreatePolicyFailed(SMCException):
    """
    Thrown when failures occur when creating specific
    poliies like Firewall Policy, IPS, VPN, etc.
    """


class LoadPolicyFailed(SMCException):
    """
    Failure when trying to load a specific policy type
    """


class LoadElementFailed(SMCException):
    """
    Failure when attempting to obtain the settings for a specific
    element. This is more generic for a broad class of elements.
    """


class FetchElementFailed(SMCException):
    """
    Failure when fetching results
    """


class CreateElementFailed(SMCException):
    """
    Generic exception when there was a failure calling a
    create method
    """


class DeleteElementFailed(SMCException):
    """
    Used when deletion fails, typically due to dependencies
    for the target element
    """


class UpdateElementFailed(SMCException):
    """
    Failure when updating element. When failure is due to ETag
    being invalid, target was modified before change was
    submitted. A resubmit would be required.
    """


class CreateVPNFailed(SMCException):
    """
    Creating a policy or route based VPN failed.
    """


class ModificationFailed(SMCException):
    """
    Used when making generic modifications to elements.
    """


class ModificationAborted(SMCException):
    """
    A previous requirement was not met which prevented an
    attempted change from being executed.
    """


class MissingDependency(SMCException):
    """
    A dependency is missing for the given operation.
    """
    

class ActionCommandFailed(SMCException):
    """
    Action type commands use this exception
    """


class InvalidRuleValue(SMCException):
    """
    Used within rule creation methods to prevent invalid submissions
    """


class CreateRuleFailed(SMCException):
    """
    Indicates a failed response when creating a rule of any type.
    """


class InvalidSearchFilter(SMCException):
    """
    Thrown by collections when using invalid search sequences.
    """


class ElementNotFound(SMCException):
    """
    Generic exception when an attempt is made to load an element
    that is not found.
    """


class ResourceNotFound(SMCException):
    """
    Used to indicate a resource link is not found on the
    queried node. For example, the :py:class:`smc.core.engine.Engine` class
    will expose available resources but some engines may not have those
    links.
    """


class MissingRequiredInput(SMCException):
    """
    Some functinos will flat out fail if certain fields are not provided.
    This is to ensure that some functions have some protection in case the
    user doesn't read the doc's.
    """


class UnsupportedEntryPoint(SMCException):
    """
    An entry point was specified that was not found in this API
    version. This is likely due to using an older version of the
    SMC API that does not support that feature. The exception is
    thrown specifying the entry point specified.
    """


class UnsupportedEngineFeature(SMCException):
    """
    If an operation is performed on an engine that does not support
    the functionality, this is thrown. For example, only Master Engine
    has virtual resources. IPS and Layer 2 Firewall do not have internal
    gateways (used for VPN).
    """


class UnsupportedInterfaceType(SMCException):
    """
    Some interface types are not supported on certain engines. For example,
    Virtual Engines only have Virtual Physical Interfaces. Layer 3 Firewalls
    do not support Capture or Inline Interfaces. This exception will be thrown
    when an attempt is made to enumerate interfaces for an engine type missing
    a reference to an unsupported interface type
    """
    

class TaskRunFailed(SMCException):
    """
    When running tasks such as policy upload, refresh policy, etc, if the result
    from SMC is a failure, possibly due to an incorrect input (i.e. missing policy),
    then this exception will be thrown
    """
    

class LicenseError(SMCException):
    """
    Thrown when operations to perform Node specific license related operations such as
    bind license, fetch license or cancel license fail.
    For node licensing specific actions, see:
    :py:class: `smc.core.node.Node`
    """
    

class NodeCommandFailed(SMCException):
    """
    Each engine node will have multiple commands that can be executed such as go online,
    go offline, go standby, locking, etc. When these commands fail, this exception will
    be thrown and wrap the SMC API response.
    For all node specific command actions, see:
    :py:class: `smc.core.node.Node`
    """
    

class EngineCommandFailed(SMCException):
    """
    Engines will have some commands that are specifically executed such as adding
    blacklist entries, flushing blacklist or adding routes. This exception will be
    thrown if the SMC API responds with any sort of error and wrap the response
    """
    

class InterfaceNotFound(SMCException):
    """
    Returned when attempting to fetch an interface directly
    """
    
class UserElementNotFound(SMCException):
    """
    Raised when attempting to find a user element that cannot be found in a
    mapped database (internal or external LDAP)
    """
    