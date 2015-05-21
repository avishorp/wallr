from multiprocessing import Process, Pipe
from threading import Thread


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
                print "Parent Received :" + str(msg)
                # Wait for messages on the pipe, and send them to the callback
                self.callback(*msg)

    def terminate(self):
        self.tmsgParent.send(False)
        self.running = False
        self.join()

    def stop(self):
        self.running = False

    def trackerWrapper(self, tmsg, cls, args, kwargs):
        # Create the tracker object
        tracker = cls(lambda msg, params: tmsg.send((msg, params)), *args, **kwargs)
        tracker.start()
        
        self.running = True
        while self.running:
            try:
                msg = tmsg.recv()
                if msg is not None:
                    print "Child terminating"
                    running = false
            except IOError,e:
                if e.errno == 4:
                    # Ignore error caused by handled signal
                    pass
                
        tmsg.close()
