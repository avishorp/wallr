from multiprocessing import Process, Pipe
from threading import Thread
import traceback

class TrackerProxy(Thread):

    def __init__(self, cls, callback, *args, **kwargs):
        super(TrackerProxy, self).__init__()

        self.callback = callback
        
        # Create the tracker in a new process
        self.tmsgParent, self.tmsgChild = Pipe(duplex = True)
        self.proc = Process(target=self.trackerWrapper, args=(self.tmsgChild, cls, args, kwargs))

    def start(self):
        self.running = True

        # Start the process
        self.proc.start()

        # Start this thread
        print "Starting local thread"
        super(TrackerProxy, self).start()

    def run(self):
        while self.running:
            msg = self.tmsgParent.recv()
            if msg is not None:
                # Wait for messages on the pipe, and send them to the callback
                self.callback(*msg)

    def terminate(self):
        self.tmsgParent.send(('terminate', None))
        self.running = False
        self.join()

    def forceSwitch(self):
        #for line in traceback.format_stack():
        #    print line.strip()
        print "TrackerProxy: forceSwitch"
        self.tmsgParent.send(('forceSwitch', ()))

    def stop(self):
        self.running = False

    def trackerWrapper(self, tmsg, cls, args, kwargs):
        # Create the tracker object
        tracker = cls(lambda msg, params: tmsg.send((msg, params)), *args, **kwargs)
        self.tracker = tracker
        tracker.start()
        
        self.running = True
        while self.running:
            try:
                msg = tmsg.recv()
                if msg is not None:
                    fn, params = msg
                    print "TrackerProxy(RX): " + fn
                    if (fn == 'terminate'):
                        print "Child terminating"
                        running = False
                    else:
                        getattr(tracker, fn)(*params)

            except IOError,e:
                if e.errno == 4:
                    # Ignore error caused by handled signal
                    pass
                
        tmsg.close()
