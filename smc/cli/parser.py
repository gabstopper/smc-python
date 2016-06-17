'''
Created on May 28, 2016

@author: davidlepage
'''

import argparse
import logging
from options import format_arguments

class ArgumentParserError(Exception):
    pass

class ThrowingArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ArgumentParserError(message)

class CLIParser(object):
    def __init__(self, document):
        self.document = document
        self.unknown = None
        
        parser = ThrowingArgumentParser(add_help=False,
            usage='''<command> <target> [<args>]''')
        parser.add_argument('command')

        args, self.unknown = parser.parse_known_args(document)
        if not hasattr(self, args.command):
            pass #don't display help at the top level

        getattr(self, args.command)()

    def create(self):
        """ create actions """   
        self._parser_parse('create')

    def remove(self):
        """ remove actions """
        self._parser_parse('remove')

    def show(self):
        """ show actions """
        self._parser_parse('show')

    def search(self):
        pass

    def _parser_parse(self, action):
        parser = ThrowingArgumentParser(add_help=False)
        subparsers = parser.add_subparsers(dest='target')

        for target, actions in format_arguments(action):
            logging.debug("Subparser: %s, args: %s" % (target, actions))

            _target = subparsers.add_parser(target)
            for name, action_val in actions:
                if action_val:
                    _target.add_argument("--"+name, **action_val)
                else:
                    _target.add_argument("--"+name)
       
        self.document = parser.parse_args(self.unknown)
        self.document.action = action
        self.document = vars(self.document)
