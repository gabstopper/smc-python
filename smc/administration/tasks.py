import time
import re
from smc.base.model import prepared_request
import smc.actions.search as search
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
        
    :return: :py:class:`~Task`
    """
    task_href = search.element_entry_point('task_progress')
    return [Task(**search.element_by_href_as_json(task.get('href'))) 
            for task in search.element_by_href_as_json(task_href)]

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
        self.success = False
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
        
        :raises: :py:class:`smc.api.exceptions.ActionCommandFailed`
        :return: None
        """
        prepared_request(ActionCommandFailed,
                         href=find_link_by_name('abort', self.link)).delete()
    
    def __call__(self):
        _task = search.element_by_href_as_json(self.follower)
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
    
class TaskMonitor(object):
    """
    Provides the ability to monitor an asynchronous task based on the 
    follower href returned from the SMC. In case of longer running 
    operations, you may want to call this later for status. Call the
    task monitor by::
    
        task = TaskMonitor(follower_href).watch()
        for message in task:
            print message
    
    :param str follower: follower href returned from asynchronous operation
    :return: generator receiving messages from task
    """
    def __init__(self, follower, sleep=10):
        self.follower = follower
        self.sleep = sleep
    
    def watch(self):
        return task_handler(Task(follower=self.follower),
                            wait_for_finish=True,
                            sleep=self.sleep)

class TaskDownload(object):
    """
    A task that downloads a file from the SMC. When doing operations such
    as export, SMC will package the data into a zip file and provide the 
    result link for download. This task is used to retrieve the result link
    and save to specified filename.
    
    :param str result: follower result link
    :param str filename: filename provided
    :raises: :py:class:`smc.api.exceptions.TaskRunFailed`
    :raises: :py:class:`smc.api.exceptions.ActionCommandFailed`
    :return: None
    """
    def __init__(self, result, filename):
        self.result = result
        self.filename = filename
    
    def run(self):
        try:
            prepared_request(ActionCommandFailed,
                             href=self.result,
                             filename=self.filename).read()
        except IOError as io:
            raise TaskRunFailed("Export task failed with message: {}"
                                .format(io))
       
def task_handler(task, wait_for_finish=False,  
                 display_msg=True, sleep=3, filename=None):
    """ Handles asynchronous operations called on engine or node levels
    
    :method: POST
    :param Task task: py:class:`smc.administration.tasks.Task`
    :param boolean wait_for_finish: whether to wait for it to finish or not
    :param boolean display_msg: whether to return display messages or not
    :param int sleep: sleep interval
    :param str filename: name of file for TaskDownload. Only for operations that
           would allow for content to be downloaded from the SMC
    
    If wait_for_finish is False, the generator will yield the follower 
    href only. If true, will return messages as they arrive and location 
    to the result after complete.
    To obtain messages as they arrive, call generator::
    
        engine = Engine('myfw')
        for msg in engine.upload('mypolicy', wait_for_finish=True)
            print msg
    """
    if wait_for_finish:
        #first task will not have a last_message attribute
        last_msg = ''
        while True:
            if display_msg:
                if task.last_message != last_msg and \
                    task.last_message is not None:
                    yield re.sub(clean_html,'', task.last_message)
                    last_msg = task.last_message
            if task.success:
                if filename: #download file
                    yield TaskDownload(task.result, filename).run()
                break
            elif not task.in_progress and not task.success:
                break
            time.sleep(sleep)
            task()
    else:
        yield task.follower
