'''
Created on Sep 24, 2017

@author: davidlepage
'''
from urlparse import urlparse
from smc import session
from smc.base.model import Element
from smc_monitoring.wsocket import SMCSocketProtocol

   
EVENT_ACTIONS = set(['create', 'update', 'delete', 'trashed', 'untrashed', 'validating', 'validated'])

    
class Notification(object):
    """
    Subscribe to notifications for a specific SMC element type.
    
    To successfully establish a connection to the notification socket, you
    must first obtain a session from the SMC. The session information
    (including any SSL parameters) will be obtained from the current session. 
    
        session.login(.....)
        ...
    
    Subscribe types are defined by the available `entry points` from the SMC
    API. Retrieve entry points from the session::
    
        for ep in session.entry_points.all():
            print(ep)
    
    Subscribing to all events can be done by providing an empty string or the
    'splat' operator to the notification::
    
        notification = Notification('')     # <-- represents all elements
        notification = Notification('*')    # <-- also represents all elements
    
    Once you have the entry point/s that are of interest, you
    can request notifications for changes to that element type. An
    example of retrieving notifications when there are changes
    to layer2 policies::
    
        notification = Notification('layer2_policy')
        for published in notification.notify():
            print(published)
        
    You can also set up notifications to multiple entry points
    in a single session with a comma separated string:
    
        notification = Notification('host,network')
    
    Each notification will also carry a `subscription_id` that uniquely
    identifies a mapping for the event. This enables multiple event types be
    registered individually with a way to map to event by subscription_id::
    
        notification = Notification('network')    # <-- Event type #1
        notification.subscribe('host')            # <-- Event type #2
        notification.subscribe('layer2_policy')   # <-- Event type #3
    
    Notifications can be returned in raw dict format or as :class:`Event`
    by providing 'as_type=Event' to the notify call::
    
        notification = Notification('network')
        
        for published in notification.notify(as_type=Event):
            print(published.subscription_id, published.action, published.element)
    
    You can also override some socket protocol details such as timeout and SSL
    parameters by passing them as kwargs to the Notification constructor. These
    are passed through the the websocket. See
    :class:`smc_monitoring.wsocket.SMCSocketProtocol` for more details::
    
        notification = Notification('network', sock_timeout=10)
    
    """
    location = '/notification/socket'
     
    def __init__(self, request, **kw):
        self.request = {
            'context': request
        }
        self.subscriptions = []
        self.subscription_map = {}
        self.sockopt = kw
    
    def subscribe(self, entry_point):
        self.subscriptions.append(Notification(entry_point))
                
    def run_forever(self):
        with SMCSocketProtocol(self, **self.sockopt) as sock:
            for subscription in self.subscriptions:
                sock.send_message(subscription)
            for result in sock.receive():
                yield result  
        
    def notify(self, as_type=None):
        for result in self.run_forever():
            #print("Result: %s" % result)
            if 'success' in result:
                self.subscription_map.update(
                    context=result.get('context'),
                    subscription_id=result.get('subscription_id'))
            if 'events' in result:
                if as_type is not None:
                    for event in result['events']:
                        event.update(subscription_id=result.get('subscription_id'))
                        yield as_type(**event)
                else:
                    yield result
                    
     
class Event(object):
    """
    An Event represents a container used for changes published from the
    SMC notification socket. An event has the following attributes:
    
    :ivar str action: type of action for event
    :ivar Element element: resolved element type as instance
    :ivar subscription_id: id mapping this event
    """
    def __init__(self, type, element, **kw):
        self.action = type
        self._element = element
        self.subscription_id = kw.pop('subscription_id', 0)
        
    @property
    def element(self):
        smc_url = urlparse(session.url).netloc
        event_url = urlparse(self._element).netloc
        return Element.from_href(self._element.replace(event_url, smc_url))
    
    def __repr__(self):
        return '%s(subscription_id=%s,action=%s,element=%s)' % \
            (self.__class__.__name__, self.subscription_id, self.action,
             self._element)
                