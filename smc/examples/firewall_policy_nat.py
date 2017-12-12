'''
Create a policy with nat rules
'''
from smc import session
from smc.policy.layer3 import FirewallPolicy
from smc.elements.network import Host, Alias

import json
import logging
logging.getLogger()
logging.basicConfig(level=logging.INFO)

if __name__ == '__main__':
    # edit ~/.smcrc
    # [smc]
    # smc_address=192.168.100.7
    # smc_apikey=xxxxxxxxxxx
    # smc_port=8082
    # smc_ssl=False
    # verify_ssl=False
    session.login()

    policy = FirewallPolicy.get('mynatpolicy1', raise_exc=False)
    if policy: policy.delete()

    policy = FirewallPolicy.create(name='mynatpolicy1',
                                   template='Firewall Inspection Template')


    kali_host = Host.get_or_create(name = 'kali', address='1.1.1.1')
    host3 = Host.get_or_create(name='host-3.3.3.3', address='3.3.3.3')


    # Example of creating a dynamic source NAT for host 'kali':
    policy.fw_ipv4_nat_rules.create(name='mynatrule-srcdyn',
                                    sources=[Host('kali')],
                                    destinations='any',
                                    services='any',
                                    dynamic_src_nat='1.1.1.1',
                                    dynamic_src_nat_ports=(1024,65535))


    # Example of creating a static source NAT for host 'kali':
    policy.fw_ipv4_nat_rules.create(name='mynatrule-srcstat',
                                    sources=[kali_host],
                                    destinations='any',
                                    services='any',
                                    static_src_nat='1.1.1.1')

    # Example of creating a destination NAT rule for destination host
    # '3.3.3.3' with destination translation address of '1.1.1.1':
    policy.fw_ipv4_nat_rules.create(name='mynatrule-desthost',
                                    sources='any',
                                    destinations=[host3],
                                    services='any',
                                    static_dst_nat='1.1.1.1')


    # Destination NAT with destination port translation:
    policy.fw_ipv4_nat_rules.create(name='mynatrule-destport',
                                    sources='any',
                                    destinations=[Alias('$$ Interface ID 0.ip')],
                                    services='any',
                                    static_dst_nat='1.1.1.1',
                                    static_dst_nat_ports=(2222, 22))


    nat_rules = policy.fw_ipv4_nat_rules
    print (nat_rules) # smc.base.collection.IPv4NATRule
    for r in nat_rules.all():
        print("==================================")
        print(r) # IPv4NATRule
        print(r.name) # IPv4NATRule
        print(r.destinations)
        print(r.sources)
        print(r.services)
        print(json.dumps(r.data["options"].get("dynamic_src_nat")))
        print(json.dumps(r.data["options"].get("static_src_nat")))
        print(json.dumps(r.data["options"].get("static_dst_nat")))

        dynamic_src_nat = r.dynamic_src_nat # mbr of NATRule
        print(r.dynamic_src_nat) # smc.policy.rule_nat.DynamicSourceNAT
        print(r.dynamic_src_nat.translated_value)
        print(r.static_src_nat)  # smc.policy.rule_nat.StaticSourceNAT
        print(r.static_dst_nat)  # smc.policy.rule_nat.StaticDestNAT

    session.logout()
