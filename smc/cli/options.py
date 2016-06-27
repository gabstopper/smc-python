'''
Created on May 21, 2016

@author: davidlepage
'''

import re
import argparse
import collections

_IP_ADDR = re.compile("^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
_IP_NETWORK = re.compile("^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\/\d{1,2}")
_IP_RANGE = re.compile("^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\-\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}")
_ID_INTERFACE = re.compile("^[01][0-9][0-9]|2[0-4][0-9]|25[0-5]")


ArgTuple = collections.namedtuple('ArgTuple', 'name meta regex actions')

dns = ArgTuple('--dns',
               'add dns servers',
               None,
               dict(default=argparse.SUPPRESS))

name = ArgTuple('name',
                'name of element',
                None,
                dict(required=True))

routes = ArgTuple('routes',
                  None,
                  None,
                  dict(action="store_true"))

mgmt_ip = ArgTuple('mgmt_ip',
                   'format: x.x.x.x',
                   _IP_ADDR,
                   dict(required=True))

mgmt_net = ArgTuple('mgmt_network',
                    'ex: 1.1.1.0/24',
                    _IP_NETWORK,
                    dict(required=True))

ip_addr = ArgTuple('ipaddress',
                   'ip address of element',
                   _IP_ADDR,
                   dict(required=True))

network = ArgTuple('ip_network',
                   'format: x/24 or x/255.255.255.0',
                   None,
                   dict(required=True))

members = ArgTuple('members',
                   'member list, comma separated',
                   None,
                   dict(required=True, nargs="*"))

gateway = ArgTuple('gateway',
                   'next hop gateway',
                   None,
                   dict(required=True))

by_name = ArgTuple('by_name',
                   None,
                   None,
                   dict(default=argparse.SUPPRESS))

by_type = ArgTuple('by_type',
                   None,
                   None,
                   dict(default=argparse.SUPPRESS))

mgmt_int = ArgTuple('mgmt_interface',
                    'interface id: 0',
                    _ID_INTERFACE,
                    dict(default=argparse.SUPPRESS))

interfaces = ArgTuple('interfaces',
                     None,
                     None,
                     dict(action="store_true", default=argparse.SUPPRESS))

addr_range = ArgTuple('addr_range',
                      'format: 1.1.1.1-1.1.1.150',
                      _IP_RANGE,
                      dict(required=True))

fw_license = ArgTuple('--fw_license',
                      'attempt to license fw',
                      None,
                      dict(action="store_true", default=False))

logical_int = ArgTuple('logical_interface',
                       'name for logical interface',
                       None,
                       dict(default=argparse.SUPPRESS))

interface_id = ArgTuple('interface_id',
                        'id of interface',
                        _ID_INTERFACE,
                        None)


COMMAND_OPTIONS = {
        'create': [
                   {'single_fw': [name, mgmt_ip, mgmt_net, mgmt_int, fw_license, dns]},
                   {'single_ips': [name, mgmt_ip, mgmt_net, mgmt_int, fw_license, dns]},
                   {'single_layer2': [name, mgmt_ip, mgmt_net, fw_license, dns]},
                   {'host': [name, ip_addr]},
                   {'group': [name, members]},
                   {'router': [name, ip_addr]},
                   {'network': [name, network]},
                   {'iprange': [name, addr_range]},
                   {'l3route': [name, network, gateway, interface_id]},
                   {'l3interface': [name, ip_addr, network, interface_id]},
                   {'l2interface': [name, interface_id, logical_int]},
                   {'logical_interface': [name]}
                   ],
        'remove': [
                   {'element': [name]}
                   ],
        'show'  : [
                   {'single_fw': [name, interfaces, routes]},
                   {'single_ips': [name, interfaces, routes]},
                   {'single_layer2': [name, interfaces, routes]},
                   {'element': [by_name, by_type]},
                   {'host': [name]},
                   {'group': [name]},
                   {'router': [name]},
                   {'network': [name]},
                   {'iprange': [name]},
                   {'logical_interface': [name]}
                   ],
        }


def get_cmd():
    """ top level commands
    :return list of top level available commands
    """
    return COMMAND_OPTIONS.keys()

def all_target_names():
    """ get all target names
    :return: sorted list of all options by name
    """
    mylst = [name
             for command in COMMAND_OPTIONS
             for target in COMMAND_OPTIONS[command]
             for name in target
             ]
    return sorted(set(mylst))

def all_arg_names():
    """ get all argument names
    :return: sorted list of all arguments by name
    """
    opts = set([])
    for command in COMMAND_OPTIONS:
        for cmd_target in COMMAND_OPTIONS[command]:
            for args in cmd_target.itervalues():
                for arg in args:
                    opts.add(arg.name)
    return sorted(opts)

def all_arg_tuples():
    """ get all argument tuples as list
    :return list of all arg tuples
    """
    return [ (arg_name,arg_tuple)
            for command in COMMAND_OPTIONS
            for target in COMMAND_OPTIONS[command]
            for arg_name,arg_tuple in target.iteritems()
            ]

def get_cmd_target(command):
    """ get targets for top level command given
    :param command: name of command (create/remove/show)
    :return list of available next level commands
    """
    return [target 
            for lst in COMMAND_OPTIONS[command] 
            for target in lst.keys()]

def all_sub_menus(command, target):
    """ get the menu's available based on the top and sub level cmd
    :param command: command given (create/remove/show)
    :param target: target given (i.e. host, single_fw, single_ips, etc)
    :return list of tuples (ArgCommand.name, ArgCommand.meta) to display by completer
    """
    menus = [ (arg.name,arg.meta)      
            for command in COMMAND_OPTIONS[command]
            if target in command     
            for arg in command[target]
            ]
       
    return menus

def has_sub_menu(prev):
    if prev == "by_type":
        return all_target_names()
    
def reduce_lst(lst):
    return [x for x in all_target_names() if x not in lst]
            
def format_arguments(command):
    """ format arguments for argparse
    :param command: command given, (create/remove/show)
    :return generator object with target name and actions list tuple
    """
    for option in COMMAND_OPTIONS[command]:
        for target in option:
            args = [(arg.name, arg.actions)    
                    for arg in option[target]
                    ]
            yield (target, args)

def split_command_and_args(tokens):
    """ split out [command target] from args
    :param tokens: words fed from completer
    :return: list of command[0] and args[1]
    """
    command, args = None, None
    if tokens:
        if len(tokens) > 1 and tokens[0] in get_cmd():
            command = ' '.join(tokens[:2])
            args = tokens[2:] if len(tokens) > 2 else None
        else:
            command = tokens[0] if tokens[0] in get_cmd() else command
    return command, args   