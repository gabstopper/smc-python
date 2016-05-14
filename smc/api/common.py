'''
Created on May 13, 2016

@author: davidlepage
'''

import logging
import smc.api.web as web_api
from smc.api.web import SMCOperationFailure

logger = logging.getLogger(__name__)

def _create(element):
    logger.debug("Creating element: %s, href: %s, json: %s" % (element.name, element.href, element.json))
    try:
        smc_result = web_api.session.http_post(element.href, element.json)
        element.href = smc_result #new href          
        logger.info("Success creating single element: %s, type: %s, href: %s" % (element.name, element.type, smc_result))
       
    except SMCOperationFailure, e:
            logger.error("Failed creating element type: %s, name: %s, %s" % (element.type, element.name, e.msg))

def _update(element):
    logger.debug("Updating element: %s, href: %s, json: %s" % (element.name, element.href, element.json))
    try: 
        web_api.session.http_put(element.href, element.json, element.etag)
        logger.info("Success updating element: %s, type: %s" % (element.name,element.type))
        
    except SMCOperationFailure, e:
        logger.error("Failed updating element type: %s, name: %s, msg: %s" % (element.type, element.name, e.msg))
        
def _remove(element):
    logger.debug("Removing element: %s, href: %s" % (element.name, element.href))
    try:
        web_api.session.http_delete(element.href) #delete to href
        logger.info("Successfully removed element: %s, type: %s" % (element.name, element.type))
            
    except SMCOperationFailure, e:
        logger.error("Failed removing element: %s, type: %s, msg: %s" % (element.name, element.type, e.msg))