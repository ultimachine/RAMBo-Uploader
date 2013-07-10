import time

class WatchPuppy():
    """A simple class for timing out simple calls"""
    def __init__(self):
        self.timeout = 0
        self.startTime = 0
        
    def startWatching(self, timeout = 2):
        self.timeout = timeout
        self.startTime = time.time()
        #print "watch Puppy started at " + str(self.startTime)
        
    def timedOut(self):
        return (time.time() > self.startTime + self.timeout)
