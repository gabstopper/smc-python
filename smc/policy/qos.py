'''
QoS Policy that would be applied to a rule set or physical / tunnel interface.
QoS can also be applied at the VLAN level of an interface.
'''

from smc.base.model import Element

class QoSPolicy(Element):   
    typeof = 'qos_policy'