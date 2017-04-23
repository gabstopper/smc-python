from .util import unicode_to_bytes


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
        #__str__ = lambda x: unicode_to_bytes(unicode(x))
