'''
Created on May 28, 2016

@author: davidlepage
'''
import argparse

__version__ = '0.1'

class ArgumentParserError(Exception): pass

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
        
        #TODO: should the exception be caught here or default value provided
        args, self.unknown = parser.parse_known_args(document)
        if not hasattr(self, args.command):
            parser.print_help()

        getattr(self, args.command)()
       
    def create(self):
    
        parser = ThrowingArgumentParser(add_help=False)        
        subparsers = parser.add_subparsers(dest='target')
        
        #common engine settings
        engine_parser = ThrowingArgumentParser(add_help=False)

        engine_parser.add_argument('--name', required=True)
        engine_parser.add_argument("--mgmt_ip", required=True)
        engine_parser.add_argument("--mgmt_network", required=True)
        engine_parser.add_argument("--mgmt_interface", default=argparse.SUPPRESS)
        engine_parser.add_argument("--dns", default=argparse.SUPPRESS)
        engine_parser.add_argument("--fw_license", action="store_true", default=False)
        
        #security engine specific subparsers        
        parser_fw = subparsers.add_parser('single_fw', parents=[engine_parser])        
        
        parser_l2 = subparsers.add_parser('single_layer2', parents=[engine_parser])
        parser_l2.add_argument('--inline_interface', default=argparse.SUPPRESS)
        parser_l2.add_argument('--logical_interface', default=argparse.SUPPRESS)
        
        parser_ips = subparsers.add_parser('single_ips', parents=[engine_parser])
        parser_ips.add_argument('--inline_interface', default=argparse.SUPPRESS)
        parser_ips.add_argument('--logical_interface', default=argparse.SUPPRESS)
        
        #elements
        element_parser = ThrowingArgumentParser(add_help=False)
        element_parser.add_argument('--name', required=True)
        element_parser.add_argument('--comment', default=argparse.SUPPRESS)
        
        parser_host = subparsers.add_parser('host', parents=[element_parser])
        parser_host.add_argument('--ipaddress', required=True)
        parser_host.add_argument('--secondary_ip', action="append", default=argparse.SUPPRESS)  
        
        
        self.document = parser.parse_args(self.unknown)
        self.document.action = 'create'
        self.document = vars(self.document)
        
        
    def remove(self):
        pass
    
    def search(self):
        pass

    

if __name__ == "__main__":

    cli = CLIParser(['create','host', '--name', 'grger', '--ipaddress', 'wefw', '--secondary_ip', '1.1.1.1'])
    #cli = CLIParser(['create','single_ips', '--mgmt_ip', '1.1.1.1', '--mgmt_network', '1.1.1.1', '--name', 'asd', '--logical_interface', 'logicaltest'])
    print cli.document
    