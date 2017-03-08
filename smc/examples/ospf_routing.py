"""
Dynamic routing using OSPF is supported on Layer 3 engines or layer 3 
virtual engines.

OSPF must first be enabled at the engine level and an OSPFProfile must be
assigned.

Next, you create an OSPFArea and assign it to an OSPFInterfaceSetting. The
OSPFInterfaceSetting can be a default profile already existing as a system
element or can be one created custom.

Apply this OSPFArea to an interface in the engine routing node.

Lastly, push policy.

A full example is defined below in main.
"""
from smc import session
from smc.elements.collection import describe_ospfv2_interface_settings
from smc.routing.ospf import OSPFArea, OSPFKeyChain, OSPFInterfaceSetting,\
    OSPFDomainSetting, OSPFProfile
from smc.core.engines import Layer3Firewall

def create_ospf_area_with_message_digest_auth():
    """
    If you require message-digest authentication for your OSPFArea, you must
    create an OSPF key chain configuration. 
    """
    OSPFKeyChain.create(name='secure-keychain', 
                        key_chain_entry=[{'key': 'fookey',
                                          'key_id': 10,
                                          'send_key': True}])
    
    """
    An OSPF interface is applied to a physical interface at the engines routing
    node level. This configuration is done by an OSPFInterfaceSetting element. To
    apply the key-chain to this configuration, add the authentication_type of 
    message-digest and reference to the key-chain
    """
    key_chain = OSPFKeyChain('secure-keychain') #obtain resource
    OSPFInterfaceSetting.create(name='authenicated-ospf', 
                                authentication_type='message_digest', 
                                key_chain_ref=key_chain.href)
    
    """
    Create the OSPFArea and assign the above created OSPFInterfaceSetting.
    In this example, use the default system OSPFInterfaceSetting called
    'Default OSPFv2 Interface Settings'
    """
    for profile in describe_ospfv2_interface_settings():
        if profile.name.startswith('Default OSPF'): #Use the system default
            interface_profile = profile.href

    OSPFArea.create(name='area0', 
                    interface_settings_ref=interface_profile, 
                    area_id=0)

def create_ospf_profile():
    """
    An OSPF Profile contains administrative distance and redistribution settings. An
    OSPF Profile is applied at the engine level. 
    When creating an OSPF Profile, you must reference a OSPFDomainSetting. 
    
    An OSPFDomainSetting holds the settings of the area border router (ABR) type, 
    throttle timer settings, and the max metric router link-state advertisement 
    (LSA) settings.
    """
    OSPFDomainSetting.create(name='custom', 
                             abr_type='cisco')

    ospf_domain = OSPFDomainSetting('custom') #obtain resource

    ospf_profile = OSPFProfile.create(name='myospfprofile', 
                                      domain_settings_ref=ospf_domain.href)
    print(ospf_profile)
        
if __name__ == '__main__':
    
    session.login(url='http://172.18.1.150:8082', api_key='EiGpKD4QxlLJ25dbBEp20001', timeout=60)
    
    """
    Create an OSPF area using the default OSPF Interface Setting element, 
    create a layer 3 firewall, enabling OSPF and applying the OSPF Area to
    Interface 0
    """
    for profile in describe_ospfv2_interface_settings():
        if profile.name.startswith('Default OSPF'):
            profile_ref = profile.href

    area = OSPFArea.create(name='area0', 
                           interface_settings_ref=profile_ref, 
                           area_id=0)
    
    area = OSPFArea('area0') #obtain resource
    
    #Create layer 3 firewall and enable OSPF, using the default system 
    #OSPFProfile
    engine = Layer3Firewall.create(name='ospf-fw', 
                                   mgmt_ip='172.18.1.30', 
                                   mgmt_network='172.18.1.0/24', 
                                   domain_server_address=['8.8.8.8'], 
                                   enable_ospf=True)
    #Get routing resources for this newly created engine
    for interface in engine.routing.all(): 
        if interface.name == 'Interface 0': 
            result = interface.add_ospf_area(area) #Apply OSPF 'area0' to interface 0
    if result.href:
        print "Success!"
    else:
        print "Failed with message: %s" % result.msg
    
    session.logout()