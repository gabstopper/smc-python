"""
Tasks will be fired when executing specific actions such as a policy
upload, refresh, or making backups.

This module provides that ability to access task specific attributes
and optionally poll for status of an operation.

An example of using a task poller when uploading an engine policy
(use 'wait_for_finish=True')::

    engine = Engine('myfirewall')
    poller = engine.upload(policy=fwpolicy, wait_for_finish=True)
    while not poller.done():
        poller.wait(5)
        print("Task Progress {}%".format(poller.task.progress))
    print(poller.last_message())

"""
import re
import time
import threading
from smc.base.mixins import SMCCommand
from smc.base.model import SimpleElement, Element
from smc.api.exceptions import TaskRunFailed, ActionCommandFailed,\
    ResourceNotFound
from smc.base.collection import Search
from smc.base.util import millis_to_utc


clean_html = re.compile(r'<.*?>')


def TaskHistory():
    """
    Task history retrieves a list of tasks in an event queue.
    
    :return: list of task events
    :rtype: Task
    """
    events = Search.objects.entry_point('task_progress')
    return [event.task for event in events]
        

class TaskProgress(Element):
    """
    Task Progress represents a task event queue. These
    tasks may be completed or still running. The task event
    queue events can be retrieved by calling `~TaskHistory`.
    """
    typeof = 'task_progress'
    
    def __init__(self, name, **meta):
        super(TaskProgress, self).__init__(name, **meta)
    
    @property
    def task(self):
        """
        Return the task associated with this event
        
        :rtype: Task
        """
        return Task(self.data)
        

class Task(SMCCommand):
    """
    Task representation. This is generic and the format is used for
    any calls to SMC that return an asynchronous follower link to
    check the status of the task. Use this as input to the task_handler
    generator to control displaying updates to the user.

    :param dict task: task json after task process started
    """
    def __init__(self, task):
        self.data = SimpleElement(**task)

    @property
    def resource(self):
        """
        The resource/s associated with this task

        :rtype: list(Element)
        """
        return [Element.from_href(resource)
                for resource in self.data['resource']]

    @property
    def href(self):
        return self.data['follower']

    @property
    def last_message(self):
        """
        Return the last message logged by SMC

        :rtype: str
        """
        return self.data['last_message']

    @property
    def progress(self):
        """
        Percentage of completion

        :rtype: int
        """
        return self.data.get('progress', 0)

    @property
    def in_progress(self):
        """
        Is this task in progress or complete

        :rtype: bool
        """
        return self.data['in_progress']

    @property
    def success(self):
        """
        Was the task completion considered successful

        :rtype: bool
        """
        return self.data['success']

    @property
    def start_time(self):
        """
        Task start time in UTC datetime format

        :rtype: datetime
        """
        start_time = self.data.get('start_time')
        if start_time:
            return millis_to_utc(start_time)

    @property
    def end_time(self):
        """
        Task end time in UTC datetime format

        :rtype: datetime
        """
        end_time = self.data.get('end_time')
        if end_time:
            return millis_to_utc(end_time)

    def abort(self):
        """
        Abort existing task.

        :raises ActionCommandFailed: aborting task failed with reason
        :return: None
        """
        try:
            self.del_cmd(
                resource='abort')
    
        except ResourceNotFound:
            pass
        except ActionCommandFailed:
            pass

    @property
    def result_url(self):
        """
        Link to result (this task)

        :rtype: str
        """
        return self.data.get_link('result')

    def update_status(self):
        """
        Gets the current status of this task and returns a
        new task object.

        :raises TaskRunFailed: fail to update task status
        """
        task = self.read_cmd(
            TaskRunFailed,
            href=self.href)

        return Task(task)

    def __getattr__(self, key):
        try:
            return self.data[key]
        except KeyError:
            pass

    def __repr__(self):
        return '{0}(type={1})'.format(
            self.__class__.__name__, self.type)


class TaskOperationPoller(object):
    """
    Task Operation Poller provides a way to poll the SMC
    for the status of the task operation.
    """
    def __init__(self, task, timeout=5, max_tries=36,
                 wait_for_finish=False):
        self._task = Task(task)
        self._thread = None
        self._done = None
        self._exception = None
        self.callbacks = [] # Call after operation completes
        if wait_for_finish:
            self._max_tries = max_tries
            self._timeout = timeout
            self._done = threading.Event()
            self._thread = threading.Thread(
                target=self._start)
            self._thread.daemon = True
            self._thread.start()

    def _start(self):
        while not self.finished():
            try:
                time.sleep(self._timeout)
                self._task = self._task.update_status()
                self._max_tries -= 1
            except Exception as e:
                self._exception = e
                break

        self._done.set()
        for call in self.callbacks:
            call(self.task)

    def finished(self):
        return self._done.is_set() or not self._task.in_progress or \
            self._max_tries == 0

    def add_done_callback(self, callback):
        """
        Add a callback to run after the task completes.
        The callable must take 1 argument which will be
        the completed Task.

        :param callable callback
        """
        if self._done is None or self._done.is_set():
            raise ValueError('Task has already finished')
        if callable(callback):
            self.callbacks.append(callback)

    def result(self, timeout=None):
        """
        Return the current Task after waiting for timeout

        :rtype: Task
        """
        self.wait(timeout)
        return self._task

    def wait(self, timeout=None):
        """
        Blocking wait for task status.
        """
        if self._thread is None:
            return
        self._thread.join(timeout=timeout)

    def last_message(self, timeout=5):
        """
        Wait a specified amount of time and return
        the last message from the task

        :rtype: str
        """
        if self._thread is not None:
            self._thread.join(timeout=timeout)
        return self._task.last_message

    def done(self):
        """
        Is the task done yet

        :rtype: bool
        """
        return self._thread is None or not self._thread.isAlive()

    @property
    def task(self):
        """
        Access to task

        :rtype: Task
        """
        return self._task

    def stop(self):
        """
        Stop the running task
        """
        if self._thread is not None and self._thread.isAlive():
            self._done.set()


class DownloadTask(TaskOperationPoller):
    """
    A download task handles tasks that have files associated, for example
    exporting an element to a specified file.
    """
    def __init__(self, filename, task, **kw):
        super(DownloadTask, self).__init__(task, wait_for_finish=True, **kw)
        self.type = 'download_task'
        self.filename = filename

        self.download(None)

    def download(self, timeout):
        self.wait(timeout)
        if not self.task.in_progress and not self.task.success:
            raise TaskRunFailed(self.task.last_message)
        try:
            result = self.task._request(
                TaskRunFailed,
                href=self.task.result_url,
                filename=self.filename).read()
            self.filename = result.content
    
        except IOError as io:
            raise TaskRunFailed(
                'Export task failed with message: {}'.format(io))
