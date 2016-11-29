"""
Compatibility for py2 / py3
"""
import sys

PY3 = sys.version_info > (3,)

'''
try:
    import simplejson as json
except (ImportError, SyntaxError):
    # simplejson does not support Python 3.2, it throws a SyntaxError
    # because of u'...' Unicode literals.
    import json
'''