'''
Created on May 28, 2016

@author: davidlepage
'''
from __future__ import unicode_literals

from smc_cli import StonesoftCLI
import smc

__version__ = '0.1'

#@click.command()
def cli():
    try:
        print "Version: %s" % __version__ 
        smc.session.login('http://172.18.1.150:8082', 'EiGpKD4QxlLJ25dbBEp20001')
        smc_cli = StonesoftCLI()
        smc_cli.run_cli()
    except (EOFError, KeyboardInterrupt):
        smc.session.logout()
        

    print('GoodBye!')

if __name__ == '__main__':
    import logging
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("smc").setLevel(logging.DEBUG)
    cli()    