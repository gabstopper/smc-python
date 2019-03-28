from smc.base.model import Element

class ApplianceSwitchModule(Element):
    """
    Read only class specifying hardware switch modules used in smaller
    appliance form factors. This is referenced when creating switch
    interfaces
    """
    typeof = 'appliance_switch_module'
    