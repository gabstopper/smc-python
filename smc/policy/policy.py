"""
Policy module represents the classes required to obtaining and manipulating
policies within the SMC.

Policy is the top level base class for all policy subclasses such as
:py:class:`smc.policy.layer3.FirewallPolicy`,
:py:class:`smc.policy.layer2.Layer2Policy`,
:py:class:`smc.policy.ips.IPSPolicy`,
:py:class:`smc.policy.inspection.InspectionPolicy`,
:py:class:`smc.policy.file_filtering.FileFilteringPolicy`

Policy represents actions that are common to all policy types, however for
options that are not possible in a policy type, the method is overridden to
return None. For example, 'upload' is not called on a template policy, but
instead on the policy referencing that template. Therefore 'upload' is
overidden.

.. note:: It is not required to call open() and save() on SMC API >= 6.1. It is
          also optional on earlier versions but if longer running operations are
          needed, calling open() will lock the policy from test_external modifications
          until save() is called.
"""
from smc.api.exceptions import TaskRunFailed, PolicyCommandFailed
from smc.administration.tasks import TaskOperationPoller
from smc.base.model import Element, lookup_class
from collections import namedtuple


class Policy(Element):
    """
    Policy is the base class for all policy types managed by the SMC.
    This base class is not intended to be instantiated directly.

    Subclasses should implement create(....) individually as each subclass will likely
    have different input requirements.

    All generic methods that are policy level, such as 'open', 'save', 'force_unlock',
    'export', and 'upload' are encapsulated into this base class.
    """

    def upload(self, engine, timeout=5, wait_for_finish=False, **kw):
        """
        Upload policy to specific device. Using wait for finish
        returns a poller thread for monitoring progress::

            policy = FirewallPolicy('_NSX_Master_Default')
            poller = policy.upload('myfirewall', wait_for_finish=True)
            while not poller.done():
                poller.wait(3)
                print(poller.task.progress)
            print("Task finished: %s" % poller.message())

        :param str engine: name of device to upload policy to
        :raises: TaskRunFailed
        :return: TaskOperationPoller
        """
        task = self.make_request(
            TaskRunFailed,
            method='create',
            resource='upload',
            params={'filter': engine})
            #json={"resource":[engine.href]})
    
        return TaskOperationPoller(
            task=task,
            timeout=timeout,
            wait_for_finish=wait_for_finish,
            **kw)

    def open(self):
        """
        Open policy locks the current policy, Use when making multiple
        edits that may require more time. Simple create or deleting elements
        generally can be done without locking via open.
        This is only used in SMC API 6.0 and below

        :raises PolicyCommandFailed: Cannot open policy
        :return: None
        """
        self.make_request(
            PolicyCommandFailed,
            method='create',
            resource='open')

    def save(self):
        """ Save policy that was modified
        This is only used in SMC API v6.0 and below.

        :return: None
        """
        self.make_request(
            PolicyCommandFailed,
            method='create',
            resource='save')

    def force_unlock(self):
        """
        Forcibly unlock a locked policy

        :return: None
        """
        self.make_request(
            PolicyCommandFailed,
            method='create',
            resource='force_unlock')

    def search_rule(self, search):
        """
        Search a rule for a rule tag or name value
        Result will be the meta data for rule (name, href, type)

        Searching for a rule in specific policy::

            f = FirewallPolicy(policy)
            search = f.search_rule(searchable)

        :param str search: search string
        :return: rule elements matching criteria
        :rtype: list(Element)
        """
        result = self.make_request(
            resource='search_rule',
            params={'filter': search})
        
        if result:
            results = []
            for data in result:
                if 'ethernet' in data.get('type'):
                    klazz = lookup_class('ethernet_rule')
                elif data.get('type') in [
                    'ips_ipv4_access_rule', 'l2_interface_ipv4_access_rule']:
                    klazz = lookup_class('layer2_ipv4_access_rule')
                else:
                    klazz = lookup_class(data.get('type'))
                results.append(klazz(**data))
            return results
        return []

    @property
    def template(self):
        """
        Each policy is based on a system level template policy that will
        be inherited.

        :return: Template policy based on policy type
        """
        return Element.from_href(self.data.get('template'))

    @property
    def inspection_policy(self):
        """
        Each policy is required to have a reference to an InspectionPolicy.
        The policy may be "No Inspection" but will still exist as a
        reference.

        :return: :py:class:`smc.policy.inspection_policy.InspectionPolicy`
        """
        return Element.from_href(self.data.get('inspection_policy'))

    @property
    def file_filtering_policy(self):
        """
        Each policy is required to have a reference to a File Filtering
        Policy. To use you will need a rule in the policy that has an
        action with file filtering turned on.
        
        :return :class:`smc.policy.file_filtering.FileFilteringPolicy`
        """
        if 'file_filtering_policy' in self.data: # Workaround for SMC 6.3
            return Element.from_href(self.data['file_filtering_policy'])
    
    def rule_counters(self, engine, duration_type='one_week',
            duration=0, start_time=0):
        """
        .. versionadded:: 0.5.6
            Obtain rule counters for this policy. Requires SMC >= 6.2
        
        Rule counters can be obtained for a given policy and duration for
        those counters can be provided in duration_type. A custom start
        range can also be provided.

        :param Engine engine: the target engine to obtain rule counters from
        :param str duration_type: duration for obtaining rule counters. Valid
            options are: one_day, one_week, one_month, six_months, one_year,
            custom, since_last_upload
        :param int duration: if custom set for duration type, specify the
            duration in seconds (Default: 0)
        :param int start_time: start time in milliseconds (Default: 0)
        :raises: ActionCommandFailed
        :return: list of rule counter objects
        :rtype: RuleCounter
        """
        json = {'target_ref': engine.href, 'duration_type': duration_type}
        return [RuleCounter(**rule)
                for rule in self.make_request(
                    method='create',
                    resource='rule_counter',
                    json=json)]


class InspectionPolicy(Policy):
    """
    The Inspection Policy references a specific inspection policy that is a property
    (reference) to either a FirewallPolicy, IPSPolicy or Layer2Policy. This policy
    defines specific characteristics for threat based prevention.
    In addition, exceptions can be made at this policy level to bypass scanning based
    on the rule properties.
    """
    typeof = 'inspection_template_policy'

    def export(self): pass  # Not valid for inspection policy

    def upload(self): pass  # Not valid for inspection policy
    

class RuleCounter(namedtuple(
        'RuleCounter', 'hits rule_ref total_hits')):
    """
    Rule counter representing hits for a specific rule.
    
    :param int hits: hits for this given rule
    :param rule_ref: rule reference to obtain the rule
    :param total_hits: total number of hits over the duration
    """
    __slots__ = ()
    
    def __new__(cls, rule_ref, hits=0, total_hits=0):  # @ReservedAssignment
        return super(RuleCounter, cls).__new__(cls, hits, rule_ref, total_hits)
    
    @property
    def rule(self):
        return Element.from_href(self.rule_ref)

