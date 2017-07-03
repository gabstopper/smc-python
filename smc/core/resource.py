from collections import namedtuple
from smc.api.exceptions import EngineCommandFailed, ActionCommandFailed
from smc.base.model import SubElement, prepared_request


class Snapshot(SubElement):
    """
    Policy snapshots currently held on the SMC. You can retrieve all
    snapshots at the engine level and view details of each::

        for snapshot in engine.snapshots:
            print snapshot.describe()

    Snapshots can also be downloaded::

        for snapshot in engine.snapshots:
            if snapshot.name == 'blah snapshot':
                snapshot.download()

    Snapshot filename will be <snapshot_name>.zip if not specified.
    """

    def __init__(self, **meta):
        super(Snapshot, self).__init__(**meta)
        pass

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
            prepared_request(EngineCommandFailed,
                             href=self.data.get_link('content'),
                             filename=filename
                             ).read()
        except IOError as e:
            raise EngineCommandFailed("Snapshot download failed: {}"
                                      .format(e))


class PendingChanges(object):
    """
    Pending changes apply to the engine having changes that have not
    yet been committed.
    """

    def __init__(self, engine):
        self._engine = engine  # Engine resource reference

    def pending_changes(self):
        """
        List of pending changes and details of the change

        :return: :py:class:`smc.core.resource.ChangeRecord`
        """
        records = []
        for record in prepared_request(
                        href=self._engine.data.get_link('pending_changes')
                        ).read().json:
            records.append(ChangeRecord(**record))
        return records

    def approve_all_changes(self):
        """
        Approve all pending changes

        :raises ActionCommandFailed: possible permissions issue
        :return: None
        """
        prepared_request(
            ActionCommandFailed,
            href=self._engine.data.get_link('approve_all_changes')
        ).create()

    def disapprove_all_changes(self):
        """
        Disapprove all pending changes

        :raises ActionCommandFailed: possible permissions issue
        :return: None
        """
        prepared_request(
            ActionCommandFailed,
            href=self._engine.data.get_link('disapprove_all_changes')
        ).create()

    @property
    def has_changes(self):
        """
        Does the policy have pending changes

        :rtype: bool
        """
        return bool(self.pending_changes())


ChangeRecord = namedtuple(
    'ChangeRecord',
    'approved_on changed_on element event_type modifier')
