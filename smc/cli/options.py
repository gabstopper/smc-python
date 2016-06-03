'''
Created on May 21, 2016

@author: davidlepage
'''
import re

_IP_ADDR = re.compile("^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
_IP_NETWORK = re.compile("^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\/\d{1,2}")
_IP_RANGE = re.compile("^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\-\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}")
_ID_INTERFACE = re.compile("^[01][0-9][0-9]|2[0-4][0-9]|25[0-5]")

class CommandOption(object):
    def __init__(self, name, meta=None, nargs=None, regex=None):
        self.name = name
        self.meta = meta
        self.nargs = nargs
        self.regex = regex

ARG_NAME = CommandOption(
    name = 'name',
    meta = 'name of element')

ARG_IP_NETWORK = CommandOption(
    name = 'ip_network',
    meta = 'format: x/24 or x/255.255.255.0',
    regex = _IP_NETWORK)

ARG_MGMT_IP = CommandOption(
    name = 'mgmt_ip',
    meta = 'format: x.x.x.x',
    regex = _IP_ADDR)

ARG_IP_RANGE = CommandOption(
    name = 'addr_range',
    meta = 'format: 1.1.1.1-1.1.1.150',
    regex = _IP_RANGE)

ARG_MGMT_NET = CommandOption(
    name = 'mgmt_network',
    meta = 'format: x.x.x.x/y',
    regex = _IP_NETWORK)

ARG_MGMT_INT = CommandOption(
    name = 'mgmt_interface',
    meta = 'interface id for mgmt')

ARG_INT_ID = CommandOption(
    name = 'interface_id',
    meta = 'id of interface',
    regex = _ID_INTERFACE)

ARG_GW = CommandOption(
    name = 'gateway',
    meta = 'next hop gateway')

ARG_LOGICAL_INT = CommandOption(
    name='logical_intf',
    meta = 'name for logical interface')

ARG_IP_ADDR = CommandOption(
    name = 'ipaddress',
    regex = _IP_ADDR)

ARG_MEMBERS = CommandOption(
    name = 'members',
    meta = 'member list, comma separated')

TARGET_SINGLE_IPS = CommandOption(
    name = 'single_ips',
    nargs = [ARG_NAME, ARG_MGMT_IP, ARG_MGMT_NET, ARG_MGMT_INT])

TARGET_SINGLE_L2 = CommandOption(
    name = 'single_layer2',
    nargs = [ARG_NAME, ARG_MGMT_IP, ARG_MGMT_NET, ARG_MGMT_INT])
        
TARGET_SINGLE_FW = CommandOption(
    name = 'single_fw',
    nargs = [ARG_NAME, ARG_MGMT_IP, ARG_MGMT_NET, ARG_MGMT_INT])

TARGET_L3_ROUTE = CommandOption(
    name = 'l3route',
    nargs = [ARG_NAME, ARG_IP_NETWORK, ARG_GW, ARG_INT_ID])

TARGET_L3_INT = CommandOption(
    name = 'l3interface',
    nargs = [ARG_NAME, ARG_IP_ADDR, ARG_IP_NETWORK, ARG_INT_ID])

TARGET_L2_INT = CommandOption(
    name = 'l2interface',
    nargs = [ARG_NAME, ARG_INT_ID, ARG_LOGICAL_INT])
               
TARGET_LOGICAL_INT = CommandOption(
    name = 'logical_interface',
    nargs=[ARG_NAME])
               
TARGET_NETWORK= CommandOption(
    name = 'network',
    nargs = [ARG_NAME, ARG_IP_NETWORK])
               
TARGET_HOST = CommandOption(
    name = 'host',
    nargs = [ARG_NAME, ARG_IP_ADDR])

TARGET_IPRANGE = CommandOption(
    name = 'iprange',
    nargs = [ARG_NAME, ARG_IP_RANGE])

TARGET_ROUTER = CommandOption(
    name = 'router',
    nargs = [ARG_NAME, ARG_IP_ADDR])

TARGET_GROUP = CommandOption(
    name = 'group',
    nargs = [ARG_NAME, ARG_MEMBERS])

TARGET_ELEMENT = CommandOption(
    name = 'element',
    nargs = [ARG_NAME])

COMMAND_OPTIONS = {
    'create': [
               TARGET_SINGLE_FW,
               TARGET_SINGLE_IPS,
               TARGET_SINGLE_L2,
               TARGET_L3_ROUTE,
               TARGET_L3_INT,
               TARGET_L2_INT,
               #TARGET_LOGICAL_INT,
               TARGET_NETWORK,
               TARGET_HOST,
               TARGET_IPRANGE,
               TARGET_ROUTER,
               TARGET_GROUP
               ],
    'remove': [
               TARGET_ELEMENT
               ],
    'search': [
               TARGET_ELEMENT
               ],
    'show':   [
               TARGET_ELEMENT
               ]
    }


def all_option_names():
    """ get all option names 
    :return: sorted list of all options by name 
    """
    opts = set([])
    for command in COMMAND_OPTIONS:
        for opt in COMMAND_OPTIONS[command]:
            opts.add(opt.name)
    return sorted(list(opts))

    
def all_arg_names():
    """ get all argument names 
    :return: sorted list of all arguments by name 
    """
    opts = set([])
    for command in COMMAND_OPTIONS:
        for c in COMMAND_OPTIONS[command]:
            cmd_opt = c.nargs
            for arg in cmd_opt:
                opts.add(arg.name)
    return sorted(list(opts))


def get_cmd():
    """ top level commands
    :return list of top level available commands
    """
    return COMMAND_OPTIONS.keys()


def get_cmd_target(command):
    """ get options based on command [create, remove, etc]
    :param command: top level cmd given, get targets
    :return list of available menu items 
    """
    if command in COMMAND_OPTIONS:
        return list(command_opt.name for command_opt in COMMAND_OPTIONS[command] if command_opt.name)  #CommandOption

    
def sub_menus(command, target):
    """ get submenu's for target
    :param command: top level command (create, remove, etc)
    :param target: second level command (single_fw, host, etc)
    :return: list of tuples (menu,meta) 
    """
    if command in COMMAND_OPTIONS:
        #CommandOption
        cmd_target_nargs = next(command_opt.nargs for command_opt in COMMAND_OPTIONS[command] if command_opt.name == target)
        menu_meta_tuple = list((command_option.name,command_option.meta) for command_option in cmd_target_nargs)
        return menu_meta_tuple


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
 