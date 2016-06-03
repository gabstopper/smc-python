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
        """ create actions""" 
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
        _parser_fw = subparsers.add_parser('single_fw', parents=[engine_parser])        
        
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
        parser_host.add_argument('--secondary_ip', nargs=1, default=argparse.SUPPRESS)  
        
        parser_iprange = subparsers.add_parser('iprange', parents=[element_parser])
        parser_iprange.add_argument('--addr_range', required=True)
        
        parser_router = subparsers.add_parser('router', parents=[element_parser])
        parser_router.add_argument('--ipaddress', required=True)
        parser_router.add_argument('--secondary_ip', action="append", default=argparse.SUPPRESS) 
        
        parser_network = subparsers.add_parser('network', parents=[element_parser])
        parser_network.add_argument('--ip_network', required=True)
        
        parser_group = subparsers.add_parser('group', parents=[element_parser])
        parser_group.add_argument('--members', required=True, nargs='*')
        
        #interfaces
        parser_l3intf = subparsers.add_parser('l3interface', parents=[element_parser])
        parser_l3intf.add_argument('--ipaddress', required=True)
        parser_l3intf.add_argument('--ip_network', required=True)
        parser_l3intf.add_argument('--interface_id', required=True)
        
        parser_l2intf = subparsers.add_parser('l2interface', parents=[element_parser])
        parser_l2intf.add_argument('--interface_id', required=True)
        parser_l2intf.add_argument('--logical_intf', required=True)
        
        _logical_intf = subparsers.add_parser('logical_interface', parents=[element_parser])
        
        self.document = parser.parse_args(self.unknown)
        self.document.action = 'create'
        self.document = vars(self.document)
        
        
    def remove(self):
        """ remove actions """
        parser = ThrowingArgumentParser(add_help=False)        
        subparsers = parser.add_subparsers(dest='target')
        
        remove_parser = subparsers.add_parser('element')
        remove_parser.add_argument('--name', required=True)
       
        self.document = parser.parse_args(self.unknown)
        self.document.action = 'remove'
        self.document = vars(self.document)
    
    
    def search(self):
        pass

    

if __name__ == "__main__":

    #cli = CLIParser(['create','host', '--name', 'grger', '--ipaddress', 'wefw', '--secondary_ip', '1.1.1.1'])
    #cli = CLIParser(['create','iprange', '--name', 'efewf', '--addr_range', 'rgr'])
    #cli = CLIParser(['create','router', '--name', 'wgwe', '--ipaddress', 'wef', '--secondary_ip', 'rrg'])
    #cli = CLIParser(['create','network', '--name', 'wg', '--ip_network', 'fe'])
    #cli = CLIParser(['create','group', '--name', 'wg','--members'])
    #cli = CLIParser(['remove', 'element', '--name', 'wefwefw'])
    cli = CLIParser(['create', 'l3interface', '--name', 'wef', '--ipaddress', 'wef', '--ip_network', '3f3f', '--interface_id', 'rger'])
        
    #cli = CLIParser(['create','single_ips', '--mgmt_ip', '1.1.1.1', '--mgmt_network', '1.1.1.1', '--name', 'asd', '--logical_interface', 'logicaltest'])
    print cli.document
    