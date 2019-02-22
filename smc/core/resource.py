import collections
from smc.api.exceptions import EngineCommandFailed
from smc.base.model import SubElement, Element
from smc.base.util import datetime_from_ms
from smc.base.structs import SerializedIterable


class Snapshot(SubElement):
    """
    Policy snapshots currently held on the SMC. You can retrieve all
    snapshots at the engine level and view details of each::

        for snapshot in engine.snapshots:
            print(snapshot)

    Snapshots can be generated manually, but also will be generated
    automatically when a policy is pushed::
    
        engine.generate_snapshot(filename='mysnapshot.zip')
    
    Snapshots can also be downloaded::

        for snapshot in engine.snapshots:
            if snapshot.name == 'blah snapshot':
                snapshot.download()

    Snapshot filename will be <snapshot_name>.zip if not specified.
    """

    def download(self, filename=None):
        """
        Download snapshot to filename

        :param str filename: fully qualified path including filename .zip
        :raises EngineCommandFailed: IOError occurred downloading snapshot
        :return: None
        """
        if not filename:
            filename = '{}{}'.format(self.name, '.zip')
        
        try:
            self.make_request(
                EngineCommandFailed,
                resource='content',
                filename=filename)

        except IOError as e:
            raise EngineCommandFailed("Snapshot download failed: {}"
                                      .format(e))


class PendingChanges(SerializedIterable):
    """
    Pending changes apply to the engine having changes that have not
    yet been committed.
    Retrieve from the engine level::
    
        >>> for changes in engine.pending_changes.all():
        ...   print(changes, changes.resolve_element)
        ... 
        (ChangeRecord(approved_on=u'', changed_on=u'2017-07-12 15:24:40 (GMT)', 
        element=u'http://172.18.1.150:8082/6.2/elements/fw_cluster/116', 
        event_type=u'stonegate.object.update', modifier=u'admin'), 
        FirewallCluster(name=sg_vm))
    
    Approve all changes::
    
        >>> engine.pending_changes.approve_all()
        
    Conversely, reject all pending changes::
    
        >>> engine.pending_changes.disapprove_all()
    
    :raises ActionCommandFailed: failure to retrieve pending changes
    :rtype: ChangeRecord
    """
    
    def __init__(self, engine):
        result = engine.make_request(
            resource='pending_changes')
        self.engine = engine
        super(PendingChanges, self).__init__(result, ChangeRecord)
    
    def approve_all(self):
        """
        Approve all pending changes

        :raises ActionCommandFailed: possible permissions issue
        :return: None
        """
        self.engine.make_request(
            method='create',
            resource='approve_all_changes')

    def disapprove_all(self):
        """
        Disapprove all pending changes

        :raises ActionCommandFailed: possible permissions issue
        :return: None
        """
        self.engine.make_request(
            method='create',
            resource='disapprove_all_changes')


_ChangeRecord = collections.namedtuple('ChangeRecord', 'approved_on changed_on '
        'element element_name event_type modifier')
_ChangeRecord.__new__.__defaults__ = (None,) * len(_ChangeRecord._fields) 


class ChangeRecord(_ChangeRecord):
# class ChangeRecord(collections.namedtuple(
#         'ChangeRecord', 'approved_on changed_on element element_name event_type modifier')):
    """
    Change record details for any pending changes.
    
    :param approved_on: approved on datetime, may be empty if not approved
    :param change_on: changed on datetime
    :param element: element affected
    :param event_type: type of change, update, delete, etc.
    :param modifier: account making the modification
    :param element_name: name of the element (only present in SMC >= 6.5)
    """
    __slots__ = ()
    @property
    def resolve_element(self):
        return Element.from_href(self.element)


_History = collections.namedtuple('History', 'creation_time creator creator_name '
    'is_locked is_obsolete is_trashed last_modification_time modifier modifier_name') 
_History.__new__.__defaults__ = (None,) * len(_History._fields) 


class History(_History):
    """
    History description of this element. This will provide basic information
    about the element such as when it was created, last modified along with
    the accounts making the modifications.
    
    :ivar bool is_locked: is this record currently locked
    :ivar bool is_osbsolete: is this record obsoleted
    :ivar bool is_trashed: is the record in the trash bin
    """
    __slots__ = ()
    
    @property
    def created_by(self):
        """
        The account that created this element. Returned as 
        an Element.
        
        :rtype: Element
        """
        return Element.from_href(self.creator)
    
    @property
    def modified_by(self):
        """
        The account that last modified this element.
        
        :rtype: Element
        """
        return Element.from_href(self.modifier)
    
    @property
    def when_created(self):
        """
        When the element was created as a datetime object
        
        :rtype: datetime
        """
        return datetime_from_ms(self.creation_time)
    
    @property
    def last_modified(self):
        """
        When the element was last modified as a datetime object
        
        :rtype: datetime
        """
        return datetime_from_ms(self.last_modification_time)
    
    def __repr__(self):
        return 'History(is_locked={}, is_obsolete={}, is_trashed={})'.format(
            self.is_locked, self.is_obsolete, self.is_trashed)