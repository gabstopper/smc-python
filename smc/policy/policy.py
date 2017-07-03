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
from smc.api.exceptions import TaskRunFailed, PolicyCommandFailed,\
    ResourceNotFound
from smc.administration.tasks import TaskOperationPoller
from smc.base.model import Element, prepared_request, lookup_class


class Policy(Element):
    """
    Policy is the base class for all policy types managed by the SMC.
    This base class is not intended to be instantiated directly.

    Subclasses should implement create(....) individually as each subclass will likely
    have different input requirements.

    All generic methods that are policy level, such as 'open', 'save', 'force_unlock',
    'export', and 'upload' are encapsulated into this base class.
    """

    def __init__(self, name, **meta):
        super(Policy, self).__init__(name, **meta)
        pass

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
        task = prepared_request(
            TaskRunFailed,
            href=self.data.get_link('upload'),
            params={'filter': engine}
            ).create().json

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
        try:
            prepared_request(
                PolicyCommandFailed,
                href=self.data.get_link('open')
            ).create()
        except ResourceNotFound:
            pass

    def save(self):
        """ Save policy that was modified
        This is only used in SMC API v6.0 and below.

        :return: None
        """
        try:
            prepared_request(
                PolicyCommandFailed,
                href=self.data.get_link('save')
            ).create()
        except ResourceNotFound:
            pass

    def force_unlock(self):
        """ Forcibly unlock a locked policy

        :return: None
        """
        prepared_request(
            PolicyCommandFailed,
            href=self.data.get_link('force_unlock')
        ).create()

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
        result = prepared_request(
            href=self.data.get_link('search_rule'),
            params={'filter': search}
        ).read()
        if result.json:
            results = []
            for data in result.json:
                if data.get('type') == 'ips_ethernet_rule':
                    klazz = lookup_class('ethernet_rule')
                elif data.get('type') == 'ips_ipv4_access_rule':
                    klazz = lookup_class('layer2_ipv4_access_rule')
                else:
                    klazz = lookup_class(data.get('type'))
                results.append(klazz(**data))
            return results
        return []

    def search_category_tags_from_element(self):
        pass

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


class InspectionPolicy(Policy):
    """
    The Inspection Policy references a specific inspection policy that is a property
    (reference) to either a FirewallPolicy, IPSPolicy or Layer2Policy. This policy
    defines specific characteristics for threat based prevention.
    In addition, exceptions can be made at this policy level to bypass scanning based
    on the rule properties.
    """
    typeof = 'inspection_template_policy'

    def __init__(self, name, **meta):
        super(InspectionPolicy, self).__init__(name, **meta)
        pass

    def export(self): pass  # Not valid for inspection policy

    def upload(self): pass  # Not valid for inspection policy
