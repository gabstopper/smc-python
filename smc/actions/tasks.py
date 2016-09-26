import time
import re    
import smc.actions.search as search
from smc.api.common import fetch_content_as_file
from smc.elements.util import find_link_by_name
from smc.api.exceptions import TaskRunFailed
from smc.elements.element import SMCElement

clean_html = re.compile(r'<.*?>')

class Task(object):
    """
    Task representation. This is generic and the format is used for 
    any calls to SMC that return an asynchronous follower link to
    check the status of the task. Use this as input to the task_handler
    generator to control displaying updates to the user.
    
    :ivar boolean success: True|False
    :ivar str last_message: message returned from SMC
    :ivar boolean in_progress: is task currently running
    :ivar str progress: percentage of completion
    :ivar str follower: href for task, use to query for status
    :ivar str result: result link, used in downloads
    """
    def __init__(self, **kwargs):
        self.success = False
        self.last_message = None
        self.in_progress = None
        self.progress = None
        self.follower = None

        for k, v in kwargs.iteritems():
            setattr(self, k, v)

    @property
    def result(self):
        return find_link_by_name('result', self.link)
    
    @property
    def abort(self):
        return SMCElement(
                    href=find_link_by_name('abort', self.link)).delete()

    def __getattr__(self, value):
        """
        Last Message attribute may not be available initially, so 
        this catches the missing attribute.
        """ 
        return None

class TaskMonitor(object):
    """
    Provides the ability to monitor an asynchronous task based on the 
    follower href returned from the SMC. In case of longer running 
    operations, you may want to call this later for status. Call the
    task monitor simply by::
    
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
                            sleep = self.sleep)

class TaskDownload(object):
    """
    A task that downloads a file from the SMC. When doing operations such
    as export, SMC will package the data into a zip file and provide the 
    result link for download. This task is used to retrieve the result link
    and save to specified filename.
    
    :param str result: follower result link
    :param str filename: filename provided
    :return: SMCResult
    :raises: :py:class:`smc.api.exceptions.TaskRunFailed`
    """
    def __init__(self, result, filename):
        self.result = result
        self.filename = filename
    
    def run(self):
        try:
            return fetch_content_as_file(self.result, 
                                         self.filename)
        except IOError, io:
            raise TaskRunFailed("Export task failed with message: {}"
                                .format(io))
        
def task_handler(task, wait_for_finish=False,  
                 display_msg=True, sleep=3, filename=None):
    """ Handles asynchronous operations called on engine or node levels
    
    :method: POST
    :param Task task: py:class:`smc.actions.tasks.Task`
    :param boolean wait_for_finish: whether to wait for it to finish or not
    :param boolean display_msg: whether to return display messages or not
    :param int sleep: sleep interval
    :param str filename: name of file for TaskDownload. Only for operations that
           would allow for content to be downloaded from the SMC
    
    If wait_for_finish is False, the generator will yield the follower 
    href only. If true, will return messages as they arrive and location 
    to the result after complete.
    To obtain messages as they arrive, call generator::
    
        engine = Engine('myfw').load()
        for msg in engine.upload('mypolicy', wait_for_finish=True)
            print msg
    """
    if wait_for_finish:
        #first task will not have a last_message attribute
        last_msg = ''
        while True:
            task = Task(**search.element_by_href_as_json(task.follower))
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
    else:
        yield task.follower

