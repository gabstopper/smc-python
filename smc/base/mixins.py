from smc.api.exceptions import FetchElementFailed, ActionCommandFailed
from smc.api.common import SMCRequest


class SMCCommand(object):
    """
    Mixin class to simplify using REST operations to SMC. This is inherited by
    ElementBase so all sub classes have access to these methods. This mixin
    represents GET,POST,PUT,DELETE operations that are not direct updates to
    an elements attributes (use .update() and delete()), but rather generic calls
    to execute some operation related to the element. For example, Node commands
    such as 'Go Online', etc require PUT be called. Since the element itself is
    not modified, update calls do not require the ETag attribute.
    
    If the 'resource' kwarg is provided, this should contain the name of the resource
    'rel' link and it will resolve the link automatically. Otherwise provide 'href'
    kwarg to identify the destination for the operation. In addition, you can provide
    a custom exception class as the first arg otherwise a default will be chosen based
    on the operation type.
    
    :param str resource: name of resource as found in elements links cache
    :param str raw_result: provide raw_result to return as SMCResult versus json
    :raises ResourceNotFound: only raised in the case where a 'resource' kwarg
        link is provided where that link does not exist.
    """
    
    def read_cmd(self, *exception, **kwargs):
        exc = FetchElementFailed
        if exception:
            exc = exception[0]
        
        raw_result = kwargs.pop('raw_result', None)
        request = self._request(exc, **kwargs)
        if raw_result:
            return request.read()
        return request.read().json

    def send_cmd(self, *exception, **kwargs):
        exc = ActionCommandFailed
        if exception:
            exc = exception[0]
        
        raw_result = kwargs.pop('raw_result', None)
        request = self._request(exc, **kwargs)
        if raw_result:
            return request.create()
        return request.create().json
    
    def del_cmd(self, *exception, **kwargs):
        exc = ActionCommandFailed
        if exception:
            exc = exception[0]
        
        request = self._request(exc, **kwargs)
        return request.delete().json
    
    def upd_cmd(self, *exception, **kwargs):
        exc = ActionCommandFailed
        if exception:
            exc = exception[0]
        
        request = self._request(exc, **kwargs)
        return request.update()
        
    def _request(self, exception, **kwargs):
        link = kwargs.pop('resource', None)
        if link is not None:
            kwargs.update(href=self.data.get_link(link))
        
        request = SMCRequest(**kwargs)
        request.exception = exception
        return request


class UnicodeMixin(object):
    """
    Mixin used to stage for supporting python 3. After py2 support is dropped
    then this can be removed. Py2 requires that __str__ returns bytes whereas
    py3 should return unicode. Each py2 supported class will have a __unicode__
    method.

    Consider migrating to future module and use their class decorator
    from future.utils import python_2_unicode_compatible
    \@python_2_unicode_compatible
    From: http://python-future.org/what_else.html
    """
    import sys
    if sys.version_info > (3, 0):
        def __str__(x): return x.__unicode__()
    else:
        def __str__(x): return unicode(x).encode('utf-8')
