'''
Created on Aug 14, 2016

@author: davidlepage
'''
import os
from ConfigParser import SafeConfigParser, NoOptionError, NoSectionError
from smc.api.exceptions import ConfigLoadError

def load_from_file(alt_filepath=None):
    """ Attempt to read the SMC configuration from a 
    dot(.) file in the users home directory. The order in
    which credentials are parsed is:
    
    - Passing credentials as parameters to the session login
    - Shared credential file (~/.smcrc)
    
    Configuration file should look like::
    
        [smc]
        smc_address=172.18.1.150
        smc_apikey=xxxxxxxxxxxxxxxxxxx
        smc_port=8082
    
    Address is the IP of the SMC Server
    apikey is obtained from creating an API Client in SMC
    port to use for SMC, (default: 8082)
    
    FQDN will be constructed from the information above.
    
    :param alt_filepath: Specify a different file name for the
    configuration file. This should be fully qualified and include
    the name of the configuration file to read.
    """
    path = '~/.smcrc'
    config = {}
    option_names = ['smc_address', 'smc_port', 'smc_apikey', 'smc_api']
    parser = SafeConfigParser(defaults={'smc_port':'8082',
                                        'smc_api': None},
                              allow_no_value=True)
    
    if alt_filepath is not None:
        path = alt_filepath
    else:
        path = os.path.expandvars(path)
        path = os.path.expanduser(path)
    
    try:
        parser.read(path)
        for option in option_names:
            val = parser.get('smc', option)
            config[option] = val
    except NoOptionError as e:
        raise ConfigLoadError('Failed loading credentials from configuration '
                              'file: {}; {}'.format(path,e))
    except NoSectionError as e:
        raise ConfigLoadError('Failed loading credential file from: {}, check the '
                              'path and verify contents are correct.'.format(path, e))
    
    for flag in ['ssl_on']:
        use_ssl = parser.has_option('smc', flag)
            
    if use_ssl:
        scheme = 'https'
    else:
        scheme = 'http'
    
    data = {}    
    url = '{}://{}:{}'.format(scheme, config.get('smc_address'), config.get('smc_port'))
    data.update(url=url,
                api_key=config.get('smc_apikey'),
                api_version=config.get('smc_api'))
    return data

