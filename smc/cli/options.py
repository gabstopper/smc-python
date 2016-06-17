'''
Created on May 21, 2016

@author: davidlepage
'''


'''
import re

_IP_ADDR = re.compile("^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
_IP_NETWORK = re.compile("^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\/\d{1,2}")
_IP_RANGE = re.compile("^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\-\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}")
_ID_INTERFACE = re.compile("^[01][0-9][0-9]|2[0-4][0-9]|25[0-5]")
'''

import argparse

class ArgCommand(object):
    def __init__(self, name, meta=None, actions=None):
        self.name = name
        self.meta = meta
        self.actions = actions

    def __repr__(self, *args, **kwargs):
        return "%s(%r)" % (self.__class__, self.__dict__)


class ArgIterator(object):
    def __init__(self, ArgCommand, include_actions=False):
        self.command = iter(ArgCommand)
        self.include_actions = include_actions

    def next(self):
        option = self.command.next()
        self.last = option
        if self.include_actions:
            return (option.name, option.actions)
        else:
            return (option.name, option.meta)

    def __iter__(self):
        return self


ARG_NAME = ArgCommand(
    name='name',
    meta='name of element',
    actions=dict(required=True))

ARG_IP_NETWORK = ArgCommand(
    name='ip_network',
    meta='format: x/24 or x/255.255.255.0',
    actions=dict(required=True))

ARG_IP_RANGE = ArgCommand(
    name='addr_range',
    meta='format: 1.1.1.1-1.1.1.150',
    actions=dict(required=True))

ARG_MGMT_IP = ArgCommand(
    name='mgmt_ip',
    meta='format: x.x.x.x',
    actions=dict(required=True))

ARG_MGMT_NET = ArgCommand(
    name='mgmt_network',
    meta='format: x.x.x.x/y',
    actions=dict(required=True))

ARG_MGMT_INT = ArgCommand(
    name='mgmt_interface',
    meta='interface id for mgmt',
    actions=dict(default=argparse.SUPPRESS))

ARG_INT_ID = ArgCommand(
    name='interface_id',
    meta='id of interface')

ARG_GW = ArgCommand(
    name='gateway',
    meta='next hop gateway',
    actions=dict(required=True))

ARG_LOGICAL_INT = ArgCommand(
    name='logical_interface',
    meta='name for logical interface',
    actions=dict(default=argparse.SUPPRESS))

ARG_IP_ADDR = ArgCommand(
    name='ipaddress',
    meta='ip address for element',
    actions=dict(required=True))

ARG_MEMBERS = ArgCommand(
    name='members',
    meta='member list, comma separated',
    actions=dict(required=True, nargs="*"))

OPT_NAME = ArgCommand(
    name='name',
    meta='name of element')

OPT_DNS = ArgCommand(
    name='dns',
    meta='add dns servers',
    actions=dict(default=argparse.SUPPRESS))

OPT_FW_LICENSE = ArgCommand(
    name='fw_license',
    meta='attempt to license fw',
    actions=dict(action="store_true", default=False))

OPT_DETAILS = ArgCommand(
    name='details',
    actions=dict(action="store_true"))

OPT_INTERFACES = ArgCommand(
    name='interfaces',
    actions=dict(action="store_true"))

OPT_ROUTES = ArgCommand(
    name='routes',
    actions=dict(action="store_true"))


COMMAND_OPTIONS = {
    'create': {
        'host': (ARG_NAME,
                 ARG_IP_ADDR),
        'group': (ARG_NAME,
                  ARG_MEMBERS),
        'router': (ARG_NAME,
                   ARG_IP_ADDR),
        'network': (ARG_NAME,
                    ARG_IP_NETWORK),
        'l3route': (ARG_NAME,
                    ARG_IP_NETWORK,
                    ARG_GW,
                    ARG_INT_ID),
        'iprange': (ARG_NAME,
                    ARG_IP_RANGE),
        'single_fw': (ARG_NAME,
                      ARG_MGMT_IP,
                      ARG_MGMT_NET,
                      ARG_MGMT_INT,
                      OPT_DNS,
                      OPT_FW_LICENSE),
        'single_ips': (ARG_NAME,
                       ARG_MGMT_IP,
                       ARG_MGMT_NET,
                       ARG_MGMT_INT,
                       OPT_DNS,
                       OPT_FW_LICENSE),
        'l3interface': (ARG_NAME,
                        ARG_IP_ADDR,
                        ARG_IP_NETWORK,
                        ARG_INT_ID),
        'l2interface': (ARG_NAME,
                        ARG_INT_ID,
                        ARG_LOGICAL_INT),
        'single_layer2': (ARG_NAME,
                          ARG_MGMT_IP,
                          ARG_MGMT_NET,
                          ARG_MGMT_INT,
                          OPT_DNS,
                          OPT_FW_LICENSE),
        'logical_interface': (ARG_NAME,),
        },
    'remove': {
        'element': (ARG_NAME,
                    )
        },
    'show': {
        'host': (OPT_NAME,
                 OPT_DETAILS),
        'element' : (ARG_NAME,
                     OPT_DETAILS),
        'single_fw': (OPT_NAME,
                      OPT_INTERFACES,
                      OPT_ROUTES,
                      OPT_DETAILS),
        'single_ips': (OPT_NAME,
                       OPT_INTERFACES,
                       OPT_ROUTES,
                       OPT_DETAILS),
        'single_layer2': (OPT_NAME,
                          OPT_INTERFACES,
                          OPT_ROUTES,
                          OPT_DETAILS),
        }
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
    opts = set([])
    for command in COMMAND_OPTIONS:
        for target in COMMAND_OPTIONS[command]:
            opts.add(target)
    return sorted(list(opts))

def all_arg_names():
    """ get all argument names
    :return: sorted list of all arguments by name
    """
    opts = []
    for command in COMMAND_OPTIONS:
        opts.extend(list(values.name for args in COMMAND_OPTIONS[command].itervalues() 
                         for values in args))
    return sorted(set(opts))

def get_cmd_target(command):
    """ get targets for top level command given
    :param command: name of command (create/remove/show)
    :return list of available next level commands
    """
    if command in COMMAND_OPTIONS:
        return list(target for target in COMMAND_OPTIONS[command])

def all_sub_menus(command, target):
    """ get the menu's available based on the top and sub level cmd
    :param command: command given (create/remove/show)
    :param target: target given (i.e. host, single_fw, single_ips, etc)
    :return list of tuples (ArgCommand.name, ArgCommand.meta) to display by completer
    """
    menus = ArgIterator(COMMAND_OPTIONS[command][target])
    return list(items for items in menus)

def format_arguments(command):
    """ format arguments for argparse
    :param command: command given, (create/remove/show)
    :return generator object with target name and actions list
    """
    for target, args in COMMAND_OPTIONS[command].iteritems():
        arg = ArgIterator(args, include_actions=True)
        args = list(items for items in arg)
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
