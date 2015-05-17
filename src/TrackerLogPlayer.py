import time
import threading, sys


# Message types that can be sen to the callback function
#
MSG_SWITCH_TO_ACQ  = 0 # No parameters
MSG_SWITCH_TO_LOCK = 1 # No parameters
MSG_COORDINATES    = 2 # (x,y) of the detection
MSG_LOCK_PROGRESS  = 3 # A number between 0 to 100 designating the acquisition progress

# Reads a log file produced by the tracker and plays it back
# by calling the given callback with appropriate messages at
# appropriate times.
# This class is used for testing the game without an actual
# tracker
class TrackerLogPlayer(threading.Thread):
    def __init__(self, logfile, cb):
        super(TrackerLogPlayer, self).__init__()
        
        self.log = open(logfile, 'r')
        self.cb = cb
        self.running = True

    def terminate(self):
        self.running = False

    def run(self):
        t0 = time.time()
        for l in self.log:
            raw = l.split(',')
            rtime = float(raw[0])
            message = int(raw[1])
            
            # Wait until the appropriate time arrives
            atime = t0 + rtime
            while time.time() < atime:
                if not self.running:
                    return None

            params = None
            if message == MSG_LOCK_PROGRESS:
                params = float(raw[2])
            if message == MSG_COORDINATES:
                params = {'x': float(raw[2]), 'y': float(raw[3])}
            # Call the callback
            self.cb(message, params)

if __name__=='__main__':
    tp = TrackerLogPlayer('tracker.log', 
                          lambda msg: sys.stdout.write("%d\n" % msg))
    tp.start()
