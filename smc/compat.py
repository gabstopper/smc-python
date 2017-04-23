"""
Compatibility for py2 / py3
"""
import sys
import smc

PY3 = sys.version_info > (3,)


def min_smc_version(version):
    """
    Is version at least the minimum provided
    Used for compatibility with selective functions
    """
    return smc.session.api_version >= version
