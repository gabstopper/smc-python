'''
Created on May 28, 2016

@author: davidlepage
'''

import os, sys
import ConfigParser
from smc_cli import StonesoftCLI
import smc

from __init__ import __version__

#@click.command()
def cli():
    print "\033[95mVersion: %s" % __version__
    init = InitLogin()
    try:
        init.login()
        smc_cli = StonesoftCLI()
        smc_cli.run_cli()
    except (EOFError, KeyboardInterrupt):
        init.logout()
        
    print('GoodBye!')

class InitLogin(object):
    def __init__(self, url=None, apikey=None, api_version=None):
        self.url = url
        self.apikey = apikey
        self.api_version = api_version
        self.creds = '~/.smcrc'
        self.load_cfg()
        
    def load_cfg(self):
        if self.url or self.apikey is None:
            cfg_path = os.path.join(
                            os.path.dirname(__file__), self.creds) 
            parser = DotConfigParser()
            parser.read(os.path.expanduser(cfg_path))
            d=parser._sections.copy()
            if d:
                self.url = d.get('main', None).get('url', None)
                self.apikey = d.get('main', None).get('apikey', None)
                self.api_version = d.get('main', None).get('api_version', None)
                
    def login(self):
        if not self.apikey or not self.url:
            print "Cannot find SMC api credentials. Missing .smcrc in home directory? Not logged in."
        else:
            smc.session.login(self.url, self.apikey, self.api_version)
    
    def logout(self):
        smc.session.logout()   


class DotConfigParser(ConfigParser.ConfigParser):
    
    def as_dict(self):
        d = dict(self._sections)
        for k in d:
            d[k] = dict(self._defaults, **d[k])
            d[k].pop('__name__', None)
        return d     

        
if __name__ == '__main__':
    import logging
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("smc").setLevel(logging.ERROR)
    
    logging.basicConfig(filename=os.path.expanduser('~/smc.log'), format='%(asctime)s %(levelname)s: %(message)s')
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(message)s')
    ch.setFormatter(formatter)
    logging.getLogger("smc").addHandler(ch)

    cli()    