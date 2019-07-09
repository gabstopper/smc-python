'''
Created on Dec 14, 2018

Example of using policy rule counters to perform potential cleanup based
on whether rules have hit counts associating them with activity. This also
shows a variety of options that can be used to do finer tune searches and
disable, update or print rule configurations.

@author: davidlepage
'''

from smc.policy.layer3 import FirewallPolicy
from smc.core.engine import Engine


def get_firewall_policy(name=None):
    """
    Get a firewall policy by it's name. If name is not provided, return
    a list of all firewall policies
    
    :param str name: name of policy; If None, return all policies
    :raises ElementNotFound: raised if policy was specified and it
        didn't exist
    :rtype: list(FirewallPolicy) or FirewallPolicy
    """
    if name:
        return FirewallPolicy.get(name)
    return [fp for fp in FirewallPolicy.objects.all()]


if __name__ == '__main__':
    
    from smc import session
    session.login(url='http://172.18.1.150:8082', api_key='EiGpKD4QxlLJ25dbBEp20001', timeout=30,
                  verify=False, retry_on_busy=True)
    
    """
    Obtain the policy based on it's type. This example uses a FirewallPolicy
    type but all policy types are supported, i.e: IPSPolicy or Layer2Policy; as
    well as templates, i.e: IPSTemplatePolicy, FirewallTemplatePolicy, Layer2TemplatePolicy
    
    .. note:: NAT rules and IPv6 rules are included in the output and do not need
        to be handled separately.
    """
    
    policy = FirewallPolicy.get('Standard Firewall Policy with Inspection')
    #policy = get_firewall_policy('Standard*') # <-- Wildcard will only return first match
    
    """
    Rule counters on a given policy can be obtained for all engines using
    the specified policy. This is equivalent to running the rule counters in the
    SMC without a "Target" specified.
      
    :rtype: list(smc.policy.policy.RuleCounter)
    """
    print("Rule counters by policy only\n------------------------")
    for counter in policy.rule_counters(engine=None):
        print(counter)
      
    """
    Get rule counters by specific engine
      
    :param Engine engine: the engine specified as element
    :rtype: list(smc.policy.policy.RuleCounter)
    """
    print("Rule counters by engine\n------------------------")
    for counter in policy.rule_counters(engine=Engine('sg_vm')):
        print(counter)
          
    """
    Durations can be used to specify how far back to retrieve the rule
    counters. 
      
    :param str duration_type: duration for obtaining rule counters. Valid
        options are: one_day, one_week, one_month, six_months, one_year,
        custom, since_last_upload; If custom is provided, set the `duration`
        attribute as well
    :rtype: list(smc.policy.policy.RuleCounter)
    """
    print("Rule counters for last month\n------------------------")
    for counter in policy.rule_counters(duration_type='one_month'):
        print(counter)
      
    """
    Rule counters using custom duration, in seconds from current time
      
    :rtype: list(smc.policy.policy.RuleCounter)
    """
    print("Rule counters for last 3600 seconds\n------------------------")
    for counter in policy.rule_counters(duration_type='custom', duration=3600):
        print(counter)
      
    """
    Rule counters for last week on specific engine
      
    :rtype: list(smc.policy.policy.RuleCounter)
    """
    for counter in policy.rule_counters(engine=Engine('sg_vm'), duration_type='one_week'):
        print(counter)
          
    """
    Rule counters are namedtuples that have the following attributes, allowing you to
    retrieve the given rule from the RuleCounter object
    """
    for counter in policy.rule_counters(engine=Engine('sg_vm'), duration_type='one_week'):
        print(counter, counter.rule)
      
    """
    Obtain the rule reference for each counter and access the History
    of the rule
    """
    for counter in policy.rule_counters(engine=Engine('sg_vm'), duration_type='one_week'):
        rule = counter.rule    # smc.policy.rule.Rule
        history = rule.history # smc.core.resource.History
        print("Rule: %s -> Last modified: %s" % (rule, history.last_modified))
         
    """
    Disable all rules that have not been hit 6 months.
    For this example, simply print the rule object and the parent policy it's associated with
    
    """
    for counter in policy.rule_counters(engine=Engine('sg_vm'), duration_type='six_months'):
        if counter.hits == 0:
            print("Disable: %s from policy: %s" % (counter.rule, counter.rule.parent_policy))
            # counter.rule.update(is_disabled=True, comment='Disabled due to 90 days of no usage') # <-- Disable the rule
  
    """
    View rule details for rules that have not been hit in 6 months.
    Output would be::
     
        Rule object: IPv4Rule(name=Rule @2100159.25)
        Rule type: fw_ipv4_access_rule
        Name: Rule @2100159.25
        Rank: 61.0
        Sources: [Network(name=network-172.18.1.0/24)]
        Destinations: [Network(name=network-192.168.6.0/25)]
        Services: Any
        Action: enforce_vpn
        Log Options: 
            log_payload_additionnal = False
            log_level = undefined
            log_closing_mode = True
            log_payload_record = False
            log_payload_excerpt = False
            log_accounting_info_mode = False
            log_severity = -1
        Comment: None
    """
    for counter in policy.rule_counters(engine=Engine('sg_vm'), duration_type='six_months'):
        if counter.hits == 0:
            rule = counter.rule
            print('Rule object: %s\nRule type: %s\nName: %s\nRank: %s\n' % 
                (rule, rule.typeof, rule.name, rule.rank))
            for values in ('sources', 'destinations', 'services'):
                value = getattr(rule, values)
                cased_value = values.title()
                if value.is_any:
                    print('%s: Any' % cased_value)
                elif value.is_none:
                    print('%s: None' % cased_value)
                else:
                    print('%s: %s' % (cased_value, value.all()))
            # NAT rules can be returned here and do not have an action field
            if rule.action:
                print('Action: %s' % rule.action.action)
             
            log_options = rule.options
            print('Log Options: ')
            for option, value in log_options.data.items():
                print('\t%s = %s' % (option, value))
            print('Comment: %s' % rule.comment)
            print("--------------------------------------")

