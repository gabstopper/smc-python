'''
Created on May 29, 2016

@author: davidlepage
'''
import sys, traceback
from parser import CLIParser, ArgumentParserError
from options import all_arg_names
import smc.actions.create

class SMCBroker(object):
    def __init__(self, document):
        self.document = document #str from cli       
        mangle_args = all_arg_names()
        self.document = ['--'+cmd if cmd in mangle_args else cmd for cmd in self.document]

    def validate(self):
        """ wrapper around argparse so it doesn't kill the shell """
        if self.document:           
            try:
                parser = CLIParser(self.document)
                self.document = parser.document
                if self.document.get('action') == 'create':
                    self.document.pop("action", None) #remove not needed attrs
                    target = self.document.get('target') and self.document.pop('target', None)
                    
                    try:
                        getattr(smc.actions.create, target)(**self.document) #dispatch
                    except Exception, e:
                        traceback.print_exc(file=sys.stdout)
                        
            except ArgumentParserError, e: #missing arguments
                return "Incorrect syntax, %s" % e
            except AttributeError, e: #incorrect argument given
                return "Attribute error: %s" % e
            except SystemExit: #argparse does a sys.exit after running -h
                print "Stopping exit"
                pass
        

if __name__ == "__main__":
    #TODO: Make ssure the CLI catches exception at end
    try:
        executor = SMCBroker(['create', 'host', 'name', 'dasf', 'ipaddress', 'wefew'])
        #executor = SMCBroker(['create', 'single_fw', 'name', 'dasf', 'mgmt_ip', 'wefew', 'mgmt_network', '23g'])
        
        executor.validate()
    except Exception, e:
        print "Exception: %s" % e 
        