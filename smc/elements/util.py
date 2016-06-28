'''
Created on Jun 26, 2016

@author: davidlepage
'''
import os
import pkg_resources
import json

import logging
logger = logging.getLogger(__name__)

def get_json_template(template_name):
    """ Get the json template file specified as template name
    Used for element templates
    :param template_name: name of template
    :return json of template, None if error
    """
    resource_package = __name__  ## this is so files can be retrieved when in egg
    resource_path = os.path.join('/templates', template_name)
    template = pkg_resources.resource_string(resource_package, resource_path)
   
    v = None
    try:
        v = json.loads(template)
    except ValueError, e:
        logger.error("Exception occurred when loading json template: %s. ValueError was: %s" % (template, e))
    return v
