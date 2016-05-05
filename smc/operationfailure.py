class OperationFailure(Exception):
    def __init__(self, error):
        self.msg = error