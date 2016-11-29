"""
Configuration Loader
"""
import os
import io
from smc.api.exceptions import ConfigLoadError

try:
    import configparser
except ImportError:
    import ConfigParser as configparser  # @UnusedImport

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
        api_version=6.1
        smc_port=8082
        smc_ssl=True
        verify_ssl=True
        ssl_cert_file='/Users/davidlepage/home/mycacert.pem'

    :param str smc_address: IP of the SMC Server
    :param str smc_apikey: obtained from creating an API Client in SMC
    :param str api_version: Which version to use (default: latest)
    :param int smc_port: port to use for SMC, (default: 8082)
    :param boolean smc_ssl: Whether to use SSL (default: False)
    :param boolean verify_ssl: Verify client cert (default: False)
    :param str ssl_cert_file: Full path to client pem (default: None)
    
    The only settings that are required are smc_address and smc_apikey.
    
    Setting verify_ssl to True (default) validates the client cert for
    SSL connections and requires the ssl_cert_file path to the cacert.pem. 
    If not given, verify will default back to False.
    
    FQDN will be constructed from the information above.

    """
    required = ['smc_address', 'smc_apikey']
    bool_type = ['smc_ssl', 'verify_ssl'] #boolean option flag
    option_names = ['smc_port', 
                    'api_version', 
                    'smc_ssl', 
                    'verify_ssl', 
                    'ssl_cert_file',
                    'timeout']
    
    parser = configparser.SafeConfigParser(defaults={
                                        'smc_port':'8082',
                                        'smc_api': None,
                                        'smc_ssl': 'false',
                                        'verify_ssl': 'false',
                                        'smc_cert_file': None,
                                        'timeout': None},
                              allow_no_value=True)
    path = '~/.smcrc'
    
    if alt_filepath is not None:
        full_path = alt_filepath
    else:
        ex_path = os.path.expandvars(path)
        full_path = os.path.expanduser(ex_path)

    section = 'smc'
    config_dict = {}
    try:
        
        with io.open(full_path, 'rt', encoding='UTF-8') as f:
            parser.readfp(f)

        #Get required settings, if not found it will raise err
        for name in required:
            config_dict[name] = parser.get(section, name)

        for name in option_names:
            if parser.has_option(section, name):
                if name in bool_type:
                    config_dict[name] = parser.getboolean(section, name)
                else: #str
                    config_dict[name] = parser.get(section, name)

    except configparser.NoOptionError as e:
        raise ConfigLoadError('Failed loading credentials from configuration '
                              'file: {}; {}'.format(path,e))
    except configparser.NoSectionError as e:
        raise ConfigLoadError('Failed loading credential file from: {}, check the '
                              'path and verify contents are correct.'.format(path, e))
    except IOError as e:
        raise ConfigLoadError('Failed loading configuration file: {}'.format(e))

    return transform_login(config_dict)
       
def transform_login(config):
    """
    Parse login data as dict. Called from load_from_file and
    also can be used when collecting information from other
    sources as well.
    
    :param dict data: data representing the valid key/value pairs
           from smcrc
    :return: dict dict of settings that can be sent into session.login
    """
    verify = True
    if config.get('smc_ssl'):
        scheme = 'https'
        
        if config.get('verify_ssl'):
            # Get cert path to verify
            verify = config.get('ssl_cert_file')
            if not verify: # Setting omitted
                verify = False
        else:
            verify = False
    else:
        scheme = 'http'
    
    transformed = {}    
    url = '{}://{}:{}'.format(scheme, 
                              config.get('smc_address'), 
                              config.get('smc_port'))
    
    timeout = config.get('timeout')
    try:
        if timeout:
            int_timeout = int(timeout)
        else:
            int_timeout = None
    except ValueError:
        int_timeout = None
    
    transformed.update(url=url,
                       api_key=config.get('smc_apikey'),
                       api_version=config.get('api_version'),
                       verify=verify,
                       timeout=int_timeout)
    return transformed

