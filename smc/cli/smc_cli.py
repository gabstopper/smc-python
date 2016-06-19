'''
Created on May 28, 2016

@author: davidlepage
'''
from __future__ import unicode_literals

from prompt_toolkit import AbortAction, CommandLineInterface
from prompt_toolkit.filters import Always
from prompt_toolkit.shortcuts import create_eventloop, create_prompt_application
from prompt_toolkit.history import InMemoryHistory
from smc.cli.lexer import CommandLexer
from smc.cli.style import CustomizedStyle
from smc.cli.completer import CommandCompleter
from smc.cli.smc_utils import SMCBroker

class StonesoftCLI(object):

    def __init__(self):
        self.theme = 'friendly'
        self.smc_cli = None
        self._create_cli()

    def _exec_command(self, command):
        results = SMCBroker(command.split()).validate()
        if results:
            print results

    def _create_cli(self):

        application = create_prompt_application(
            message='smc> ',
            wrap_lines=True,
            complete_while_typing=Always(),
            lexer=CommandLexer,
            completer=CommandCompleter(),
            style=CustomizedStyle(self.theme).style,
            history=InMemoryHistory(),
            get_title=AppTitle(),
            mouse_support=True,
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
    def __call__(self):
        return 'SMC Command Line Utility'
