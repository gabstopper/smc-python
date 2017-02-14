"""
Class representing basic models for data obtained or retrieved from the SMC

Element is the top level class that exposes methods that are common to all
elements such as viewing the json data, retrieving common attribute data,
exporting the element and modifying.

Element class relationship::
   
        Element (object)
        |-----------------------------------------------|
      href = ElementLocator()                 (Inheriting classes)
      cache = ElementCache()
      meta = Meta(href,name,type)
      name                                    
      delete()                                
      export()
      describe()
      modify_attribute()

If a class is obtained through a top level reference and does not have a direct
entry point, it needs to override the name attribute to obtain the name from 
self.meta. The UnicodeMixin will print the object representation as unicode from
the self._name attribute. 
"""
from collections import namedtuple
import smc.core
import smc.compat as compat
from smc.api.common import SMCRequest
import smc.actions.search as search
from smc.api.exceptions import ElementNotFound, LoadEngineFailed
from .util import bytes_to_unicode, unicode_to_bytes, find_link_by_name
from .mixins import UnicodeMixin
from smc.api.web import SMCResult
    
def prepared_request(**kwargs):
    return SMCRequest(**kwargs)

def ElementCreator(cls):
    return SMCRequest(href=search.element_entry_point(cls.typeof), 
                      json=cls.json).create()

class ElementLocator(object):
    """
    There are two ways to get an elements location, either through the 
    describe_xxx methods which is then stored in the instance meta attribute, 
    or by specifying the resource directly, i.e. Host('myhost'). 

    If the element is going to be loaded directly, it must have a class attribute
    'typeof' to specify the element type. Elements with only 'meta=None' in their 
    constructor do not have valid entry points in the SMC API and will be created 
    through a reference. 
    The typeof class attribute is used in this descriptor as a search filter to find 
    the href location of the element and represents the SMC API entry point for that
    element type.
    """
    def __get__(self, instance, cls=None):
        #Does the instance already have meta data
        if instance.meta:
            return instance.meta.href
        else:
            if hasattr(instance, 'typeof'):
                element = search.element_info_as_json_with_filter(
                                                instance.name, instance.typeof)
                if element:
                    instance.meta = Meta(**element[0])
                    return instance.meta.href
                raise ElementNotFound('Cannot find specified element: {}, type: {}'
                                      .format(unicode_to_bytes(instance.name), 
                                              instance.typeof))
            elif isinstance(instance, smc.core.engine.Engine):
                element = search.element_info_as_json_with_filter(instance.name, 
                                                                 'engine_clusters')
                if element:
                    instance.meta = Meta(**element[0])
                    return instance.meta.href
                raise LoadEngineFailed('Cannot load engine name: {}, ensure the '
                                       'name is correct and that the engine exists.'
                                       .format(instance.name))
            else:
                raise ElementNotFound('This class does not have the required attribute '
                                      'and cannot be referenced directly, type: {}'
                                      .format(instance))

cachehit = 0

class ElementCache(object):
    def __init__(self):
        self._cache = None #tuple (etag, json)
 
    def __get__(self, instance, owner):
        try:
            if instance._cache is not None:
                result = prepared_request(headers={'Etag': instance._cache[0]}, 
                                          href=instance.href).read()
                if result.code == 304:
                    return instance._cache
                else:
                    instance._cache = (result.etag, result.json)
        except AttributeError:
            result = search.element_by_href_as_smcresult(instance.href)
            instance._cache = (result.etag, result.json)
        return instance._cache
                                            
class Element(UnicodeMixin):
    """
    Base element with common methods shared by inheriting classes
    """
    href = ElementLocator()
    cache = ElementCache()

    def __init__(self, name, meta=None):
        self._name = name #<str>
        self.meta = meta

    @classmethod
    def _load(cls, etag, data, meta):
        """
        Alternate class loader. Some elements are referenced only by
        href when retrieving such as rule services/destinations, etc. 
        To return an object type, the raw json is retrieved and then
        mapped to the class type.
        """
        c = cls(meta.name, meta=meta)
        c._cache = (etag, data)
        return c
    
    @property
    def etag(self):
        """
        ETag for this element
        """
        return self.cache[0]
        
    @property
    def name(self):
        """
        Name of element
        """
        if compat.PY3:
            return self._name
        else:
            return bytes_to_unicode(self._name)

    def delete(self):
        """
        Delete the element
        
        :return: :py:class:`smc.api.web.SMCResult`
        """
        return SMCRequest(href=self.href).delete()

    def describe(self):
        """
        Describe the elements as dict, for example::
            
            print engine.internal_gateway.describe()
        """
        return self.cache[1]
    
    def get_attr_by_name(self, attr):
        """
        Retrieve a specific attribute by name
        
        :return: attr value or None if it doesn't exist
        """
        return self.cache[1].get(attr)
  
    def export(self, filename='element.zip', wait_for_finish=False):
        """
        Export this element
        
        :param str filename: filename to store exported element
        :param boolean wait_for_finish: wait for update msgs (default: False)
        :return: generator yielding updates on progress, or [] if element cannot
                 be exported, like for system elements
        """
        from smc.administration.tasks import Task, task_handler
        href = find_link_by_name('export', self.link)
        if href is not None:
            element = SMCRequest(
                        href=href,
                        filename=filename).create()
            task = task_handler(Task(**element.json), 
                                wait_for_finish=wait_for_finish, 
                                filename=filename)
            return task
        else:
            return []

    @property
    def link(self):
        return self.cache[1].get('link')
    
    def modify_attribute(self, **kwargs):
        """
        Modify the attribute / value pair
        
        :param dict kwargs: key=value pair to change
        :raises: :py:class:`smc.api.exceptions.ElementNotFound`   
        :return: :py:class:`smc.api.web.SMCResult`
        """
        etag, element = self.cache
        if element.get('system') == True:
            return SMCResult(msg='Cannot modify system element: %s' % self.name)
        for k, v in kwargs.items():
            target_value = element.get(k)
            if isinstance(target_value, dict): #update dict leaf
                element[k].update(v)
            elif isinstance(target_value, list): #replace list
                element[k] = v
            else: #single key/value
                element.update({k: v}) #replace str
        return SMCRequest(href=self.href, 
                          json=element,
                          etag=etag).update()

    def __unicode__(self):
        return u'{0}(name={1})'.format(self.__class__.__name__, self.name)
    
    def __repr__(self):
        return str(self)

class Meta(namedtuple('Meta', 'name href type')):
    """
    Internal namedtuple used to store top level element information. When 
    doing base level searches, SMC API will return only meta data for the
    element that has name, href and type.
    Meta has the same data structure returned from 
    :py:func:`smc.actions.search.element_info_as_json`
    """
    def __new__(cls, href, name=None, type=None): # @ReservedAssignment
        return super(Meta, cls).__new__(cls, name, href, type)
