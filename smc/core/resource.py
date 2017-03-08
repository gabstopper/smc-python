from smc.api.exceptions import EngineCommandFailed
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
    def __init__(self, meta=None):
        super(Snapshot, self).__init__(meta)
        pass

    def download(self, filename=None):
        """
        Download snapshot to filename
        
        :param str filename: fully qualified path including filename .zip
        :raises: :py:class:`smc.api.exceptions.EngineCommandFailed`
        :return: None
        """
        if not filename:
            filename = '{}{}'.format(self.name, '.zip')
        try:
            prepared_request(EngineCommandFailed,
                             href=self._link('content'), 
                             filename=filename).read()
        except IOError as e:
            raise EngineCommandFailed("Snapshot download failed: {}"
                                      .format(e))