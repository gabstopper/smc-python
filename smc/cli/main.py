'''
Created on May 28, 2016

@author: davidlepage
'''

import os
import sys
import traceback
from functools import wraps
import ConfigParser
from logging.config import fileConfig
import logging

from smc.api.web import session as smc, SMCConnectionError
from smc.cli.smc_cli import StonesoftCLI

from smc.cli import __version__
from ConfigParser import NoSectionError

print u'\033[94;1mSMC CLI Version: %s\033[0m' % __version__

def cli():
    """
    Main CLI entry point.
    First start by attempting to log in to SMC using the URL and
    the apikey (optional apiversion). Once a valid session has been obtained
    it is stored in global smc.api.web.session. Then launch the CLI. If login is
    unsuccessful, CLI will still launch but attempts to perform any operations
    will produce a traceback due to a missing SMC session
    """
    try:
        login()
        smc_cli = StonesoftCLI()
        smc_cli.run_cli()
    except (EOFError, KeyboardInterrupt):
        pass
    except (IOError), io:
        logging.exception(io)
    except (SMCConnectionError), err:
        logging.error(err)
    finally:
        smc.logout()

def login_cfg(func):
    """ collect configuration decorator """
    @wraps(func)
    def cfg_function(*args, **kwargs):
        if kwargs:
            pass
        else:
            config = ConfigParser.SafeConfigParser()
            location = config.read(os.path.expanduser('~/.smcrc'))
            logging.debug("Configuration read from location: %s" % location)

            arguments = {}
            for section in ['smc']:
                for candidate in ['url', 'apikey']: #required
                    if config.has_option(section, candidate):
                        logging.debug("%s -> %s" % \
                                      (candidate, config.get(section, candidate)))
                        arguments[candidate] = config.get(section, candidate)
                    else:
                        arguments.clear()
                        break
                if config.has_option(section, 'apiversion'): #optional
                    arguments['apiversion'] = config.get(section, 'apiversion')    
        return func(*args, **arguments)
    return cfg_function

@login_cfg
def login(*args, **kwargs):
    """
    Login to SMC using crendential information. API User should be created
    in the SMC Administration->API Users. Each user will have a corresponding
    API key used for authentication.
    By default, user and apikey information in stored in ~/.smcrc
    :param args: not used
    :param kwargs: url, apikey, apiversion 
    """
    if not kwargs:
        print("Cannot find SMC api credentials. Not logged in. "
              "Is the ~/.smcrc configuration file missing?")
    else:
        smc.login(kwargs.get('url'),
                  kwargs.get('apikey'),
                  kwargs.get('apiversion'))


if __name__ == '__main__':

    config = '~/.smcrc'   
    try:
        fileConfig(os.path.expanduser(config), disable_existing_loggers=False)
        
    except NoSectionError:
        print "Unable to find config file: %s, logging disabled" % os.path.expanduser(config)
    
    logger = logging.getLogger()
    
    for dep in ['requests', 'urllib3']:
        if logger.getEffectiveLevel() == 10:
            logging.getLogger(dep).setLevel(logging.DEBUG)
        else:
            logging.getLogger(dep).setLevel(logging.WARNING)

    cli()
