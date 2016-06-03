'''
Created on May 28, 2016

@author: davidlepage
'''
from __future__ import unicode_literals

from prompt_toolkit import AbortAction, CommandLineInterface
from prompt_toolkit.filters import Always
from prompt_toolkit.shortcuts import create_eventloop, create_prompt_application
from prompt_toolkit.history import InMemoryHistory
from lexer import CommandLexer
from style import CustomizedStyle
from completer import CommandCompleter
from smc_utils import SMCBroker


__version__ = '0.1'
    
class StonesoftCLI(object):
    
    def __init__(self):
        self.theme = 'friendly'       
        self.smc_cli = None
        self._create_cli()
        
        self.PYGMENTS_CMD = ' | pygmentize -l json'

    def _exec_command(self, command):
        results = SMCBroker(command.split()).validate()
        if results:
            print '\033[91m' + results
            #print '\033[1m' + results
    
            
    def _create_cli(self):
        
        application = create_prompt_application(
            message = 'smc> ', 
            wrap_lines = True, 
            complete_while_typing=Always(), 
            enable_history_search = True,
            lexer = CommandLexer,
            completer = CommandCompleter(), 
            style = CustomizedStyle(self.theme).style,
            history = InMemoryHistory(),
            get_title=AppTitle(), 
            mouse_support = True, 
            on_abort=AbortAction.RETRY)
           
        eventloop = create_eventloop()
        self.smc_cli = CommandLineInterface(
            application=application,
            eventloop=eventloop)
        
        
    def run_cli(self):
        while True:
            document = self.smc_cli.run(reset_current_buffer=True)
            self._exec_command(document.text)
         
           
class AppTitle(object):
    def get_title(self):
        return 'SMC Command Line Utility'
    __call__ = get_title 
