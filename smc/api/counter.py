
cache_hit = 0
    
class countcalls(object):
    """test"""
    __instances = {}
    
    def __init__(self, f):
        self.__f = f
        self.__numcalls = 0
        countcalls.__instances[f] = self
    
    def __call__(self, *args, **kwargs):
        self.__numcalls += 1
        return self.__f(*args, **kwargs)
    
    def count(self):
        return countcalls.__instances[self.__f].__numcalls
    
    @staticmethod
    def counts():
        return dict([(f.__name__, countcalls.__instances[f].__numcalls) for f in countcalls.__instances])