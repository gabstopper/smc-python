

from smc_monitoring.models.query import Query


class ActiveAlertQuery(Query):
    location = '/monitoring/session/socket'
    
    def __init__(self, target):
        super(ActiveAlertQuery, self).__init__('ACTIVE_ALERTS', target)
        