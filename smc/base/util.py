"""
Utility functions used in different areas of smc-python
"""
import time
import base64
import datetime
import smc.compat as compat
import smc.api.exceptions


def datetime_to_ms(dt):
    """
    Convert an unaware datetime object to milliseconds. This will
    be a UTC time. The SMC stores all times in UTC and will do the
    time conversions based on the local timezone.
    Example of converting a datetime to milliseconds::
    
        utc_time = datetime.strptime("2018-06-04T00:00:00", "%Y-%m-%dT%H:%M:%S")
        datetime_to_ms(utc_time)
    
    :param dt datetime: pass in python datetime object.
    :return: value representing the datetime in milliseconds
    :rtype: int
    """
    return int(time.mktime(dt.timetuple()) * 1000)
    

def datetime_from_ms(ms):
    """
    Convenience to return datetime from milliseconds. Return in
    UTC time.
    
    :param int ms: milliseconds to convert into datetime object
    :return: datetime from ms
    :rtype: datetime
    """
    try:
        return datetime.datetime.fromtimestamp(ms/1000.0)
    except TypeError: # SMC version 6.2 returns in invalid format (2018-01-09T00:58:41Z)
        return ms


def millis_to_utc(millis):
    """
    Given milliseconds, convert to datetime object in UTC. This will
    also use the systems local timezone when displaying.
    
    :param int millis: milliseconds
    :return datetime using local system time conversion
    :rtype: datetime
    """
    return datetime.datetime(1970, 1, 1) + datetime.timedelta(milliseconds=millis) 


def save_to_file(filename, content):
    """
    Save content to file. Used by node initial contact but
    can be used anywhere.

    :param str filename: name of file to save to
    :param str content: content to save
    :return: None
    :raises IOError: permissions issue saving, invalid directory, etc
    """
    import os.path
    path = os.path.abspath(filename)
    with open(path, "w") as text_file:
        text_file.write("{}".format(content))


def element_resolver(elements, do_raise=True):
    """
    Element resolver takes either a single class instance
    or a list of elements to resolve the href. It does
    not assume a specific interface, instead if it's
    a class, it just needs an 'href' attribute that should
    hold the http url for the resource. If a list is
    provided, a list is returned. If you want to suppress
    raising an exception and just return None or [] instead,
    set do_raise=False.

    :raises ElementNotFound: if this is of type Element,
        ElementLocator will attempt to retrieve meta if it
        doesn't already exist but the element was not found.
    """
    if isinstance(elements, list):
        e = []
        for element in elements:
            try:
                e.append(element.href)
            except AttributeError:
                e.append(element)
            except smc.api.exceptions.ElementNotFound:
                if do_raise:
                    raise
        return e
    try:
        return elements.href
    except AttributeError:
        return elements
    except smc.api.exceptions.ElementNotFound:
        if do_raise:
            raise


def element_default(clazz, default_name, exact_match=False):
    """
    Some element defaults are provided by SMC. Where they are not provided,
    supply a simple mechanism to retrieve the default first match by
    class and name
    
    :param Element clazz: must be of type Element
    :param str default_name: name to search
    :param bool exact_match: whether match can be fuzzy or exact
    :return: the href of the element or None
    """ 
    return getattr(clazz.objects.filter(default_name, exact_match=exact_match)\
        .first(), 'href', None)
        

def merge_dicts(dict1, dict2, append_lists=False):
    """
    Merge the second dict into the first
    Not intended to merge list of dicts.

    :param append_lists: If true, instead of clobbering a list with the
        new value, append all of the new values onto the original list.
    """
    for key in dict2:
        if isinstance(dict2[key], dict):
            if key in dict1 and key in dict2:
                merge_dicts(dict1[key], dict2[key], append_lists)
            else:
                dict1[key] = dict2[key]
        # If the value is a list and the ``append_lists`` flag is set,
        # append the new values onto the original list
        elif isinstance(dict2[key], list) and append_lists:
            # The value in dict1 must be a list in order to append new
            # values onto it. Don't add duplicates.
            if key in dict1 and isinstance(dict1[key], list):
                dict1[key].extend(
                    [k for k in dict2[key] if k not in dict1[key]])
            else:
                dict1[key] = dict2[key]
        else:
            dict1[key] = dict2[key]  # Overwrite list or scalar


def is_subdict(small, big):
    """
    Check if one dict is a subset of another with matching keys and values.
    Used for 'flat' dictionary comparisons such as in comparing interface
    settings. This should work on both python 2 and 3.
    
    See: https://docs.python.org/2/reference/expressions.html#value-comparisons
    
    :rtype: bool
    """
    return dict(big, **small) == big
    
    
def unicode_to_bytes(s, encoding='utf-8', errors='replace'):
    """
    Helper to convert unicode strings to bytes for data that needs to be
    written to on output stream (i.e. terminal)
    For Python 3 this should be called str_to_bytes

    :param str s: string to encode
    :param str encoding: utf-8 by default
    :param str errors: what to do when encoding fails
    :return: byte string utf-8 encoded
    """
    return s if isinstance(s, str) else s.encode(encoding, errors)


def b64encode(source):
    """
    Base64 encoding for python 2 and 3
    
    :rtype: base64 content
    """
    if compat.PY3:
        source = source.encode('utf-8')
    return base64.b64encode(source).decode('utf-8')


def bytes_to_unicode(s, encoding='utf-8', errors='replace'):
    """
    Helper to convert byte string to unicode string for user based input

    :param str s: string to decode
    :param str encoding: utf-8 by default
    :param str errors: what to do when decoding fails
    :return: unicode utf-8 string
    """
    if compat.PY3:
        return str(s, 'utf-8') if isinstance(s, bytes) else s
    return s if isinstance(s, unicode) else s.decode(encoding, errors)
        

def import_submodules(package, recursive=True):
    """
    Import all submodules of a module, recursively,
    including subpackages.

    From http://stackoverflow.com/questions/3365740/how-to-import-all-submodules

    :param package: package (name or actual module)
    :type package: str | module
    :rtype: dict[str, types.ModuleType]
    """
    import importlib
    import pkgutil
    if isinstance(package, str):
        package = importlib.import_module(package)
    results = {}
    for _loader, name, is_pkg in pkgutil.walk_packages(package.__path__):
        full_name = package.__name__ + '.' + name
        results[full_name] = importlib.import_module(full_name)
        if recursive and is_pkg:
            results.update(import_submodules(full_name))
    return results
