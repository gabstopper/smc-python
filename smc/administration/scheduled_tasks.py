"""
.. versionadded:: 0.5.7
    Requires SMC version >= 6.3.2

Scheduled tasks are administrative processes that can run either immediately
after being defined, or scheduled to run on a regular basis. Scheduled tasks
in the SMC are defined under Administration->Tasks->Definition. 

Some tasks are read-only, meaning they are system elements and cannot be modified
or copied and can therefore only be scheduled (these task related classes will not
have a `create` method). Other tasks can be created and custom settings can be
defined. Check the documentation for each task to determine the capabilities.

All tasks inherit the ScheduledTaskMixin which provides a `start` method and 
access to a TaskSchedule instance through the `task_schedule` property. The 
associated TaskSchedule defines whether to run the task ongoing and details
specifying when the task should be run and how often.

An example follows that shows how to use a refresh policy task. Other tasks use the
same API syntax.

Finding existing tasks for a specific task type::
    
    for task in RefreshPolicyTask.objects.all():
        print(task, task.task_schedule)

Review an existing task and it's task schedule::

    task = RefreshPolicyTask(name='mytask')
    for schedule in task.task_schedule:
        print(schedule.activation_date, schedule.activated)
    
Create a refresh policy refresh task::
    
    task = RefreshPolicyTask.create(
        name='mytask',
        engines=[Engine('engine1'), Engine('engine2')],
        comment='some comment')
    
A created task can always be run at any time without having to set a
schedule for the task by calling `start` on the task::

    task = RefreshPolicyTask('mytask')
    task.start()

A task can also be scheduled for a future time. Adding a scheduled run to
the task requires that we first obtain the task and add the schedule to it.
This can be done when creating the task, or the retrieved after::

    task = RefreshPolicyTask.create(
        name='mytask',
        engines=[Engine('engine1'), Engine('engine2')],
        comment='refresh policy on specified engines')
    
    task.add_schedule(
        name='refresh_policy_on_saturday',
        activation_date=1512325716000,  # 12/04/2017 00:00:00
        day_period='weekly',
        day_mask=128,
        comment='tun this task weekly')

You can also specify tasks that run on a regular interval, such as
monthly::

    task = RefreshPolicyTask(name='mytask')
    task.add_schedule(
        name='run_monthly', 
        activation_date=1512367200000, # Start 12/4/2017 at 00:00:00
        day_period='monthly')
    
Repeat a task for a period of time, then disable task on specified
date::

    task = DeleteLogTask.create(
        name='Delete SMC Server logs',
        servers='all',
        time_range='last_full_month',
        all_logs=True)
        
    task.add_schedule(
        name='Run for 6 months',
        activation_date=1512367200000, # Start 12/04/2017
        day_period='monthly',
        repeat_until_date=1528088400000, # End 06/04/2018
        comment='purge log task')

.. note:: You can use the helper method :func:`smc.base.util.datetime_to_ms`
    for obtaining millisecond times for scheduled tasks.
"""

from smc.base.model import Element, SubElement, ElementCreator
from smc.api.exceptions import ActionCommandFailed
from smc.administration.tasks import Task
from smc.elements.servers import ManagementServer, LogServer
from smc.core.engines import MasterEngine
from smc.elements.other import FilterExpression
from smc.base.util import datetime_from_ms


def policy_validation_settings(**kwargs):
    """
    Set policy validation settings. This is used when policy based
    tasks are created and `validate_policy` is set to True. The
    following kwargs can be overridden in the create constructor.
    
    :param bool configuration_validation_for_alert_chain: default False
    :param bool duplicate_rule_check_settings: default False
    :param bool empty_rule_check_settings: default True
    :param bool emtpy_rule_check_settings_for_alert: default False
    :param bool general_check_settings: default True
    :param bool nat_modification_check_settings: default True
    :param bool non_supported_feature: default True
    :param bool routing_modification_check: default False
    :param bool unreachable_rule_check_settings: default False
    :param bool vpn_validation_check_settings: default True
    :return: dict of validation settings
    """
    validation_settings = {
        'configuration_validation_for_alert_chain': False,
        'duplicate_rule_check_settings': False,
        'empty_rule_check_settings': True,
        'empty_rule_check_settings_for_alert': False,
        'general_check_settings': True,
        'nat_modification_check_settings': True,
        'non_supported_feature': True,
        'routing_modification_check': False,
        'unreachable_rule_check_settings': False,
        'vpn_validation_check_settings': True}
    
    for key, value in kwargs.items():
        validation_settings[key] = value
    
    return {'validation_settings': validation_settings}


def log_target_types(all_logs=False, **kwargs):
    """
    Log targets for log tasks. A log target defines the log types
    that will be affected by the operation. For example, when creating
    a DeleteLogTask, you can specify which log types are deleted.
    
    :param bool for_alert_event_log: alert events traces (default: False)
    :param bool for_alert_log: alerts (default: False)
    :param bool for_fw_log: FW logs (default: False)
    :param bool for_ips_log: IPS logs (default: False)
    :param bool for_ips_recording: any IPS pcaps (default: False)
    :param bool for_l2fw_log: layer 2 FW logs (default: False)
    :param bool for_third_party_log: any 3rd party logs (default: False)
    :return: dict of log targets
    """
    log_types = {
        'for_alert_event_log': False,
        'for_alert_log': False,
        'for_audit_log': False,
        'for_fw_log': False,
        'for_ips_log': False,
        'for_ips_recording_log': False,
        'for_l2fw_log': False,
        'for_third_party_log': False}
    
    if all_logs:
        for key in log_types.keys():
            log_types[key] = True
    else:
        for key, value in kwargs.items():
            log_types[key] = value
    
    return log_types

    
class TaskSchedule(SubElement):
    """
    A task schedule is associated with a given task type that defines
    when the scheduled task should run.
    
    :ivar str day_period: how often to run the task
    :var str final_action: what to do when the task is complete
    :ivar str minute_period: if day_period is set to hourly, when to run
        within the hour.
    """
    
    @property
    def activated(self):
        """
        Whether this schedule is active for this task.
        
        :rtype: bool
        """
        return self.data.get('activated', False)
    
    @property
    def activation_date(self):
        """
        Return the UTC time when the task is set to first run.
        The activation date is returned as a python datetime
        object.
            
        :return: datetime object in format '%Y-%m-%d %H:%M:%S.%f'
        :rtype: datetime
        """
        return datetime_from_ms(self.data.get('activation_date'))

    def activate(self):
        """
        If a task is suspended, this will re-activate the task.
        Usually it's best to check for activated before running
        this::
        
            task = RefreshPolicyTask('mytask')
            for scheduler in task.task_schedule:
                if scheduler.activated:
                    scheduler.suspend()
                else:
                    scheduler.activate()
        """
        if 'activate' in self.data.links:
            self.make_request(
                ActionCommandFailed,
                method='update',
                etag=self.etag,
                resource='activate')
            self._del_cache()
        else:
            raise ActionCommandFailed('Task is already activated. To '
                'suspend, call suspend() on this task schedule')
            
    def suspend(self):
        """
        Suspend this scheduled task.
        
        :raises ActionCommandFailed: failed to suspend, already suspended. Call
            activate on this task to reactivate.
        :return: None
        """
        if 'suspend' in self.data.links:
            self.make_request(
                ActionCommandFailed,
                method='update',
                etag=self.etag,
                resource='suspend')
            self._del_cache()
        else:
            raise ActionCommandFailed('Task is already suspended. Call activate '
                'to reactivate.')
            
class ScheduledTaskMixin(object):
    """
    Actions common to all scheduled tasks.
    """
    def start(self):
        """
        Start the scheduled task now. Task can then be tracked by
        using common Task methods.
        
        :raises ActionCommandFailed: failed starting task
        :return: return as a generic Task
        :rtype: Task
        """
        return Task(self.make_request(
            ActionCommandFailed,
            method='create',
            resource='start'))
    
    @property
    def task_schedule(self):
        """
        Return any task schedules associated with this
        scheduled task.
        
        :raises ActionCommandFailed: failure to retrieve task schedule
        :return: list of task schedules
        :rtype: TaskSchedule
        """
        return [TaskSchedule(**sched)
                for sched in self.make_request(
                resource='task_schedule')]
    
    def add_schedule(self, name, activation_date, day_period='one_time',
                     final_action='ALERT_FAILURE', activated=True,
                     minute_period='one_time', day_mask=None,
                     repeat_until_date=None, comment=None):
        """
        Add a schedule to an existing task.
        
        :param str name: name for this schedule
        :param int activation_date: when to start this task. Activation date
            should be a UTC time represented in milliseconds.
        :param str day_period: when this task should be run. Valid options:
            'one_time', 'daily', 'weekly', 'monthly', 'yearly'. If 'daily' is
            selected, you can also provide a value for 'minute_period'.
            (default: 'one_time')
        :param str minute_period: only required if day_period is set to 'daily'.
            Valid options: 'each_quarter' (15 min), 'each_half' (30 minutes), or
            'hourly', 'one_time' (default: 'one_time')
        :param int day_mask: If the task day_period=weekly, then specify the day
            or days for repeating. Day masks are: sun=1, mon=2, tue=4, wed=8,
            thu=16, fri=32, sat=64. To repeat for instance every Monday, Wednesday
            and Friday, the value must be 2 + 8 + 32 = 42
        :param str final_action: what type of action to perform after the
            scheduled task runs. Options are: 'ALERT_FAILURE', 'ALERT', or
            'NO_ACTION' (default: ALERT_FAILURE)
        :param bool activated: whether to activate the schedule (default: True)
        :param str repeat_until_date: if this is anything but a one time task run,
            you can specify the date when this task should end. The format is the
            same as the `activation_date` param.
        :param str comment: optional comment
        :raises ActionCommandFailed: failed adding schedule
        :return: None
        """
        json = {
            'name': name,
            'activation_date': activation_date,
            'day_period': day_period,
            'day_mask': day_mask,
            'activated': activated,
            'final_action': final_action,
            'minute_period': minute_period,
            'repeat_until_date': repeat_until_date if repeat_until_date else None,
            'comment': comment}
        
        if 'daily' in day_period:
            minute_period = minute_period if minute_period != 'one_time' else 'hourly'
            json['minute_period'] = minute_period
        
        return self.make_request(
            ActionCommandFailed,
            method='create',
            resource='task_schedule',
            json=json)

    @property
    def resources(self):
        """
        Resources associated with this task. Depending on the task, this
        may be engines, policies, servers, etc.
        
        :return: list of Elements
        :rtype: list
        """
        return [Element.from_href(href)
                for href in self.data.get('resources')]
    

class RefreshPolicyTask(ScheduledTaskMixin, Element):
    """
    A scheduled task associated with refreshing policy on engine/s.
    A refresh will push an existing policy that is already mapped to
    the engine/s. Use :class:`~UploadPolicyTask` to create a task
    that will assign a policy to an engine/s and upload.
    
    .. note:: Any engine can force a policy refresh on the engine
        node directly by calling engine.refresh(), or from the engines
        assigned policy by calling policy.refresh(engine) also.
    """
    typeof = 'refresh_policy_task'
    
    @classmethod
    def create(cls, name, engines, comment=None,
               validate_policy=True, **kwargs):
        """
        Create a refresh policy task associated with specific
        engines. A policy refresh task does not require a policy
        be specified. The policy used in the refresh will be the
        policy already assigned to the engine.
        
        :param str name: name of this task
        :param engines: list of Engines for the task
        :type engines: list(Engine)
        :param str comment: optional comment
        :param bool validate_policy: validate the policy before upload.
            If set to true, validation kwargs can also be provided
            if customization is required, otherwise default validation settings
            are used.
        :param kwargs: see :func:`~policy_validation_settings` for keyword
            arguments and default values.
        :raises ElementNotFound: engine specified does not exist
        :raises CreateElementFailed: failure to create the task
        :return: the task
        :rtype: RefreshPolicyTask
        """
        json = {
            'resources': [engine.href for engine in engines],
            'name': name,
            'comment': comment}
        
        if validate_policy:
            json.update(policy_validation_settings(**kwargs))
        
        return ElementCreator(cls, json)


class UploadPolicyTask(ScheduledTaskMixin, Element):
    """
    An upload policy task will assign a specified policy to an
    engine or group of engines and upload. If an engine specified
    has an existing policy assigned, the engine will be reassigned
    the specified policy. If the intent is to create a policy task
    to push an existing assigned policy, use :class:`~RefreshPolicyTask`
    instead.
    
    .. note:: Policy upload on an engine can be done from the engine
        node itself by calling engine.upload('policy_name') or from a policy directly
        by policy.upload('engine_name').
    """
    typeof = 'upload_policy_task'
        
    @classmethod
    def create(cls, name, engines, policy, comment=None,
               validate_policy=False, **kwargs):
        """
        Create an upload policy task associated with specific
        engines. A policy reassigns any policies that might be
        assigned to a specified engine. 
        
        :param str name: name of this task
        :param engines: list of Engines for the task
        :type engines: list(Engine)
        :param Policy policy: Policy to assign to the engine/s
        :param str comment: optional comment
        :param bool validate_policy: validate the policy before upload.
            If set to true, validation kwargs can also be provided
            if customization is required, otherwise default validation settings
            are used.
        :param kwargs: see :func:`~policy_validation_settings` for keyword
            arguments and default values.
        :raises ElementNotFound: engine or policy specified does not exist
        :raises CreateElementFailed: failure to create the task
        :return: the task
        :rtype: UploadPolicyTask
        """
        json = {
            'name': name,
            'policy': policy.href,
            'resources': [eng.href for eng in engines],
            'comment': comment}
        
        if validate_policy:
            json.update(policy_validation_settings(**kwargs))
            
        return ElementCreator(cls, json)


class ValidatePolicyTask(ScheduledTaskMixin, Element):
    """
    Run a policy validation task. This does not perform a policy push.
    This may be useful if you want to validate any pending changes before
    a future policy push.
    """
    typeof = 'validate_policy_task'
    
    @classmethod
    def create(cls, name, engines, policy=None, comment=None, **kwargs):
        """
        Create a new validate policy task.
        If a policy is not specified, the engines existing policy will
        be validated. Override default validation settings as kwargs.
        
        :param str name: name of task
        :param engines: list of engines to validate
        :type engines: list(Engine)
        :param Policy policy: policy to validate. Uses the engines assigned
            policy if none specified.
        :param kwargs: see :func:`~policy_validation_settings` for keyword
            arguments and default values.
        :raises ElementNotFound: engine or policy specified does not exist
        :raises CreateElementFailed: failure to create the task
        :return: the task
        :rtype: ValidatePolicyTask
        """
        json = {
            'name': name,
            'resources': [eng.href for eng in engines],
            'policy': policy.href if policy is not None else policy,
            'comment': comment}
        
        if kwargs:
            json.update(policy_validation_settings(**kwargs))
        
        return ElementCreator(cls, json)
    
    @property
    def policy(self):
        """
        Policy associated with this task
        
        :return: Policy as element
        :rtype: Element
        """
        return Element.from_href(self.data.get('policy'))
    

class RefreshMasterEnginePolicyTask(ScheduledTaskMixin, Element):
    """
    Refresh a Master Engine and virtual policy task. 
    
    .. note:: This task is only relevant for engines that are
        Master Engines. This does not apply to standard single FW
        or clustered FW's.
    """
    typeof = 'refresh_master_and_virtual_policy_task'
    
    @classmethod
    def create(cls, name, master_engines, comment=None):
        """
        Create a refresh task for master engines. 
        
        :param str name: name of task
        :param master_engines: list of master engines for this task
        :type master_engines: list(MasterEngine)
        :param str comment: optional comment
        :raises CreateElementFailed: failed to create the task
        :return: the task
        :rtype: RefreshMasterEnginePolicyTask
        """
        json = {
            'name': name,
            'comment': comment,
            'resources': [eng.href for eng in master_engines
                          if isinstance(eng, MasterEngine)]}
        
        return ElementCreator(cls, json)


class DeleteLogTask(ScheduledTaskMixin, Element):
    """
    A delete log task defines a way to purge log data from the SMC.
    When defining the task, you specify which servers to delete from
    (typically management AND log server/s), and which log types to
    delete.
    
    .. note:: Log tasks currently support pre-defined time ranges such
        as 'yesterday', 'last_week', etc. If creating custom time ranges
        for tasks, use the SMC UI.
    """
    typeof = 'delete_log_task'
        
    @classmethod
    def create(cls, name, servers, time_range='yesterday', all_logs=False,
               filter_for_delete=None, comment=None, **kwargs):
        """
        Create a new delete log task. Provide True to all_logs to delete
        all log types. Otherwise provide kwargs to specify each log by
        type of interest.
        
        :param str name: name for this task
        :param servers: servers to back up. Servers must be instances of
            management servers or log servers. To backup all, provide 'all'
            as value.
        :type servers: list(ManagementServer or LogServer)
        :param str time_range: specify a time range for the deletion. Valid
            options are 'yesterday', 'last_full_week_sun_sat',
            'last_full_week_mon_sun', 'last_full_month' (default 'yesterday')
        :param FilterExpression filter_for_delete: optional filter for deleting.
            (default: FilterExpression('Match All')
        :param bool all_logs: if True, all log types will be deleted. If this
            is True, kwargs are ignored (default: False)
        :param kwargs: see :func:`~log_target_types` for keyword
            arguments and default values.
        :raises ElementNotFound: specified servers were not found
        :raises CreateElementFailed: failure to create the task
        :return: the task
        :rtype: DeleteLogTask
        """
        if 'all' in servers:
            servers = [svr.href for svr in ManagementServer.objects.all()]
            servers.extend([svr.href for svr in LogServer.objects.all()])
        else:
            servers = [svr.href for svr in servers]
        
        filter_for_delete = filter_for_delete.href if filter_for_delete else \
            FilterExpression('Match All').href
        
        json = {
            'name': name,
            'resources': servers,
            'time_limit_type': time_range,
            'start_time': 0,
            'end_time': 0,
            'file_format': 'unknown',
            'filter_for_delete': filter_for_delete,
            'comment': comment}  
        
        json.update(**log_target_types(all_logs, **kwargs))
        
        return ElementCreator(cls, json)

                                  
class ServerBackupTask(ScheduledTaskMixin, Element):
    """
    A task that will back up the Management Server/s, Log Server/s and
    optionally the Log Server data.
    
    :ivar bool log_data_must_be_saved: whether to back up logs
    """
    typeof = 'backup_task'
    
    @classmethod
    def create(cls, name, servers, backup_log_data=False,
               encrypt_password=None, comment=None):
        """
        Create a new server backup task. This task provides the ability
        to backup individual or all management and log servers under
        SMC management.
        
        :param str name: name of task
        :param servers: servers to back up. Servers must be instances of
            management servers or log servers. To backup all, provide 'all'
            as value.
        :type servers: list(ManagementServer or LogServer)
        :param bool backup_log_data: Should the log files be backed up. This
            field is only relevant if a Log Server is backed up.
        :param str encrypt_password: Provide an encrypt password if you want
            this backup to be encrypted.
        :param str comment: optional comment
        :raises ElementNotFound: specified servers were not found
        :raises CreateElementFailed: failure to create the task
        :return: the task
        :rtype: ServerBackupTask
        """
        if 'all' in servers:
            servers = [svr.href for svr in ManagementServer.objects.all()]
            servers.extend([svr.href for svr in LogServer.objects.all()])
        else:
            servers = [svr.href for svr in servers]
            
        json = {
            'resources': servers,
            'name': name,
            'password': encrypt_password if encrypt_password else None,
            'log_data_must_be_saved': backup_log_data,
            'comment': comment}
        
        return ElementCreator(cls, json)


class SGInfoTask(ScheduledTaskMixin, Element):
    """
    An SGInfo task is used for obtaining support data from the engine/s. 
    
    .. note:: An sginfo can be executed directly on an engine node by calling
        the node.sginfo() method directly.
    
    :ivar bool include_core_files: whether to include core files in output
    :ivar bool include_slapcat_output: include slapcat in output
        
    .. warning:: For an sginfo to be readable, the engine must not have the 
        'encrypt_configuration' field enabled on the engine or the data will
        be unreadable. 
    """
    typeof = 'sginfo_task'
    
    @classmethod
    def create(cls, name, engines, include_core_files=False,
               include_slapcat_output=False, comment=None):
        """
        Create an sginfo task. 
        
        :param str name: name of task
        :param engines: list of engines to apply the sginfo task
        :type engines: list(Engine)
        :param bool include_core_files: include core files in the
            sginfo backup (default: False)
        :param bool include_slapcat_output: include output from a
            slapcat command in output (default: False)
        :raises ElementNotFound: engine not found
        :raises CreateElementFailed: create the task failed
        :return: the task
        :rtype: SGInfoTask
        """
        json = {
            'name': name,
            'comment': comment,
            'resources': [engine.href for engine in engines],
            'include_core_files': include_core_files,
            'include_slapcat_output': include_slapcat_output}
        
        return ElementCreator(cls, json)


class SystemSnapsotTask(ScheduledTaskMixin, Element):
    """
    A read-only task that will make a snapshot of all system
    elements after a updating a dynamic package on SMC.
    """
    typeof = 'create_system_snapshot_task'
    
    
class DeleteOldRunTask(ScheduledTaskMixin, Element):
    """
    A read-only task to delete the task history from already run
    tasks. This is generally a recommended task to run on a monthly
    basis to purge the old task data.
    """
    typeof = 'delete_old_executed_task'


class DisableUnusedAdminTask(ScheduledTaskMixin, Element):
    """
    A read-only task to disable any administrator account that has not been
    used within the time set in the Administrator password policy.
    """
    typeof = 'disable_unused_admin_task'
    

class DeleteOldSnapshotsTask(ScheduledTaskMixin, Element):
    """
    A read-only management server task to delete snapshots since the last
    scheduled run. For example, if this task is configured to run once per
    month, snapshots older than 1 month will be deleted.
    """
    typeof = 'delete_old_snapshots_task'


class RenewInternalCertificatesTask(ScheduledTaskMixin, Element):
    """
    A read-only management server task that renews certificates used in
    systems communications and send alerts about expiring certificates.
    """
    typeof = 'renew_internal_certificates_task'


class RenewGatewayCertificatesTask(ScheduledTaskMixin, Element):
    """
    A read-only management server task that renews certificates on internal
    gateways which have automatic certificate renewal enabled.
    """
    typeof = 'renew_gw_certificates_task'


class RenewInternalCATask(ScheduledTaskMixin, Element):
    """
    A read-only management server task that renews certificate authorities
    used in system communications and send alerts about expiring certificate
    authorities.
    """
    typeof = 'renew_internal_ca_task'


class FetchCertificateRevocationTask(ScheduledTaskMixin, Element):
    """
    A read-only management server task to download updated certificate
    revocation lists.
    """
    typeof = 'fetch_certificate_revocation_task'
