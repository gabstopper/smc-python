import time
import re
from smc.base.model import prepared_request
from smc import session
from smc.base.util import find_link_by_name
from smc.api.exceptions import TaskRunFailed, ActionCommandFailed

clean_html = re.compile(r'<.*?>')


def task_history():
    """
    Get all tasks stored by the SMC

    Example of aborting an existing task by follower link::

        for task in task_history():
            if task.follower == task:
                task.abort()

    Abort any in progress tasks::

        for task in task_history():
            if task.in_progress:
                task.abort()

    :return: list :py:class:`~Task`
    """
    tasks = prepared_request(
        href=session.entry_points.get('task_progress')
        ).read().json
    
    return [Task(**prepared_request(href=task['href']).read().json)
            for task in tasks]
  

def task_status(follower):
    """
    Return the task specified.

    Return specific task::

        task = task_status('http://......')

    :param str follower: task follower link
    :return: :py:class:`~Task`
    """
    for task in task_history():
        if task.follower == follower:
            return task


class Task(object):
    """
    Task representation. This is generic and the format is used for
    any calls to SMC that return an asynchronous follower link to
    check the status of the task. Use this as input to the task_handler
    generator to control displaying updates to the user.

    Task has the following attributes:

    :ivar boolean success: True|False
    :ivar str last_message: message returned from SMC
    :ivar boolean in_progress: is task currently running
    :ivar str progress: percentage of completion
    :ivar str follower: href for task, use to query for status
    :ivar str result: result link, used in downloads
    """
    def __init__(self, **kwargs):
        self.name = None
        self.success = False #: 
        self.type = None
        self.last_message = None
        self.in_progress = None
        self.progress = None
        self.follower = None
        self.resource = None

        for k, v in kwargs.items():
            setattr(self, k, v)

    @property
    def result(self):
        """
        ** read only result **
        """
        return find_link_by_name('result', self.link)

    def abort(self):
        """
        Abort existing task

        :raises ActionCommandFailed: aborting task failed with reason
        :return: None
        """
        prepared_request(
            ActionCommandFailed,
            href=find_link_by_name('abort', self.link)
            ).delete()

    def _poll(self):
        _task = prepared_request(
            ActionCommandFailed,
            href=self.follower).read().json

        for k, v in _task.items():
            setattr(self, k, v)

    def __getattr__(self, value):
        """
        Last Message attribute may not be available initially, so
        this catches the missing attribute.
        """
        return None

    def __repr__(self):
        return '{0}(type={1})'.format(self.__class__.__name__, self.type)


class ProgressTask(Task):
    def __init__(self, follower, **kw):
        super(ProgressTask, self).__init__(follower=follower, **kw)
        self.type = 'progress_task'
            
    def wait(self, timeout=5, max_intervals=300):
        """
        Wait for this progress task to complete. Each yielded result
        is the % progress complete. Once the task is complete, you
        can obtain the last message by the ``last_message`` attribute.
        To find success/failure, access ``success`` attribute, and 
        the ``last_message`` to get the final message.
            
        :param int timeout: how long to wait between polling for updates
        :param int max_intervals: maximum number polling intervals before
            returning. Default is 60 iterations (5 min)
        :return: percentage updates as int
        :rtype: int
        """
        i=0
        while i <= max_intervals:
            self._poll()
            if self.progress:
                yield self.progress
            if not self.in_progress:
                break
            i += 1
            time.sleep(timeout) 


class DownloadTask(Task):
    def __init__(self, follower, filename, **kw):
        super(DownloadTask, self).__init__(follower=follower, **kw)
        self.type = 'download_task'
        self.filename = filename
    
    def wait(self, timeout=2):
        try:
            while self.in_progress:
                self._poll()
                time.sleep(timeout)
            prepared_request(
                ActionCommandFailed,
                href=self.result,
                filename=self.filename).read()
            return self
        except IOError as io:
            raise TaskRunFailed(
                'Export task failed with message: {}'.format(io))    
