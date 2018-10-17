"""
Waiters are convenience classes that use blocking or non-blocking threads to
monitor for a particular state of an engine node.

A waiter can have a callback added that will be executed after either
the state has matched, a number of iterations exceeded or an exception is
caught while monitoring. The callback should be a callable that takes a single
argument.

They provide the ability to perform logical actions such as "wait for the engine to
have status 'Configured', then fire a policy upload task".

Example of waiting for an engine to be ready, then send policy::

    class ContainerPolicyCallback(object):
        def __init__(self, container):
            self.engine = engine

        def __call__(self, status):
            if status == 'Configured':
                self.engine.upload(policy='MyPolicy')

    engine = Engine('myengine')
    callback = ContainerPolicyCallback(engine)

    waiter = ConfigurationStatusWaiter(engine.nodes[0], 'Configured')
    waiter.add_done_callback(callback)

Waiters can also be blocking while waiting for status. Example of using a waiter
to block input while waiting for the engine to reach a specific status::

    waiter = ConfigurationStatusWaiter(node, 'Initial', max_wait=5)
    while not waiter.done():
        print("Status after 5 sec wait: %s" % waiter.result(5))

"""
import time
import threading

#: Configuration status constant values
CFG_STATUS = frozenset(['Initial', 'Declared', 'Configured', 'Installed'])

#: Node status constant values
STATUS = frozenset(['Not Monitored', 'Unknown', 'Online', 'Going Online',
                    'Locked Online', 'Going Locked Online','Offline','Going Offline',
                    'Locked Offline', 'Going Locked Offline','Standby','Going Standby',
                    'No Policy Installed', 'Policy Out Of Date'])

#: Node state constant values
STATE = frozenset(['INITIAL', 'READY', 'ERROR', 'SERVER_ERROR', 'NO_STATUS',
                   'TIMEOUT', 'DELETED', 'DUMMY'])


class NodeWaiter(threading.Thread):
    """
    Node Waiter provides a common threaded interface to monitoring
    a nodes status and wait for a specific response.
    """
    def __init__(self, resource, status, timeout=5,
                 max_wait=36, **kw):
        threading.Thread.__init__(self)
        self._desired_status = status
        self._resource = resource #node resource
        self._status = None
        self._max_wait = max_wait
        self._timeout = timeout
        self.callbacks = []
        self._done = threading.Event()
        self.daemon = True
        self.start()

    def run(self):
        while not self.finished():
            time.sleep(self._timeout)
            try:
                self._status = self._get_status()
                self._max_wait -= 1
            except Exception as e:
                self._status = e
                break

        self._done.set()
        for call in self.callbacks:
            call(self._status)

    def _get_status(self):
        # Raises NodeCommandFailed
        # Modified in 0.6.2 to support SMC 6.5 where the attribute name changed
        status = self._resource.status()
        latest = [getattr(status, attr) for attr in self.value if getattr(status, attr)]
        if self._desired_status in latest:
            return self._desired_status
        else:
            return latest[0] or None

    def finished(self):
        return self._done.is_set() or \
            self._status == self._desired_status or \
            self._max_wait == 0

    def add_done_callback(self, callback):
        """
        Add a callback to run after the task completes.
        The callable must take 1 argument which will be
        the completed Task.

        :param callable callback
        """
        if self._done.is_set():
            raise ValueError('Thread has already terminated, cannot add callback.')
        if callable(callback):
            self.callbacks.append(callback)

    def done(self):
        """
        Is the task still running or considered complete

        :rtype: bool
        """
        return self._done.is_set() or not self.isAlive()

    def result(self, timeout=None):
        """
        Get current status result after waiting timeout
        Result does a join on the thread to get a status update. It
        is possible the first couple of statuses are None if an
        update has not yet been joined.
        """
        self.wait(timeout)
        return self._status

    def wait(self, timeout=None):
        """
        Blocking method to wait for thread
        """
        self.join(timeout)

    def stop(self):
        """
        Stop thread if it's still running
        """
        if self.isAlive():
            self._done.set()


class ConfigurationStatusWaiter(NodeWaiter):
    """
    Configuration status waiter provides a current engine status
    with respects to having a configuration.

    :param Node resource: Engine node to check for status
    :param str status: used defined status to wait for.
    :raises NodeCommandFailed: Failure to obtain a status back
        from the engine. This can be thrown when getting initial
        status. If thrown after the thread has started, it is caught
        and returned in the ``result`` after ending the thread.
    """
    value = ('configuration_status',)

    def __init__(self, resource, status, **kw):
        if status not in CFG_STATUS:
            raise ValueError(
                'Status is invalid. Valid options are: %s' % CFG_STATUS)
        super(ConfigurationStatusWaiter, self).__init__(resource, status, **kw)


class NodeStatusWaiter(NodeWaiter):
    """
    Node Status specifies the current state of the engine such as offline, online,
    locked offline, no policy installed, etc.

    :param Node resource: Engine node to check for status
    :param str status: used defined status to wait for.
    :raises NodeCommandFailed: Failure to obtain a status back
        from the engine. This can be thrown when getting initial
        status. If thrown after the thread has started, it is caught
        and returned in the ``result`` after ending the thread.
    """
    # Node status changed in SMC 6.5 from status to monitoring_status so
    # value was changed to an iterable to check for a status other than
    # None for both attributes 
    value = ('status', 'monitoring_status', 'engine_node_status')

    def __init__(self, resource, status, **kw):
        if status not in STATUS:
            raise ValueError(
                'Status is invalid. Valid options are: %s' % STATUS)
        super(NodeStatusWaiter, self).__init__(resource, status, **kw)


class NodeStateWaiter(NodeWaiter):
    """
    Node State specifies where the engine is within it's lifecycle, such as
    initial state, ready state, error, timeout, etc.

    :param Node resource: Engine node to check for status
    :param str status: used defined status to wait for.
    :raises NodeCommandFailed: Failure to obtain a status back
        from the engine. This can be thrown when getting initial
        status. If thrown after the thread has started, it is caught
        and returned in the ``result`` after ending the thread.
    """
    value = ('state', 'monitoring_state')

    def __init__(self, resource, status, **kw):
        if status not in STATE:
            raise ValueError(
                'Status is invalid. Valid options are: %s' % STATE)
        super(NodeStateWaiter, self).__init__(resource, status, **kw)
