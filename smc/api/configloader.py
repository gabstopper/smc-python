"""
Configuration Loader
"""
import os
from ConfigParser import SafeConfigParser, NoOptionError, NoSectionError
from smc.api.exceptions import ConfigLoadError

def load_from_file(alt_filepath=None):
    """ Attempt to read the SMC configuration from a 
    dot(.) file in the users home directory. The order in
    which credentials are parsed is:
    
    - Passing credentials as parameters to the session login
    - Shared credential file (~/.smcrc)
    
    :param alt_filepath: Specify a different file name for the
           configuration file. This should be fully qualified and include
           the name of the configuration file to read.
           
    Configuration file should look like::
    
        [smc]
        smc_address=172.18.1.150
        smc_apikey=xxxxxxxxxxxxxxxxxxx
        smc_port=8082
        smc_cert='/Users/davidlepage/home/mycacert.pem'
        ssl_on
    
    :param str smc_address: IP of the SMC Server
    :param str apikey: obtained from creating an API Client in SMC
    :param int port: port to use for SMC, (default: 8082)
    :param str|boolean smc_cert: True|False|path_to_cacert.pem
    :param ssl_on: flag to enable / disable SSL
    
    Setting smc_cert to True (default) validates the client cert if using
    SSL. False will disable HTTPS cert checking (not recommended), and 
    using a full path to the cacert.pem will use that to validate.
    
    FQDN will be constructed from the information above.

    """
    path = '~/.smcrc'
    config = {}
    option_names = ['smc_address', 'smc_port', 'smc_apikey', 'smc_api',
                    'smc_cert']
    parser = SafeConfigParser(defaults={'smc_port':'8082',
                                        'smc_api': None,
                                        'smc_cert': None},
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
    
    verify = True        
    if use_ssl:
        scheme = 'https'
        if config.get('smc_cert'):
            cert = config.get('smc_cert')
            if cert.startswith('True'):
                verify = True
            elif cert.startswith('False'):
                verify = False
            else:
                verify = cert
    else:
        scheme = 'http'
        
    data = {}    
    url = '{}://{}:{}'.format(scheme, config.get('smc_address'), config.get('smc_port'))
    data.update(url=url,
                api_key=config.get('smc_apikey'),
                api_version=config.get('smc_api'),
                verify=verify)
    return data

