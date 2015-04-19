import cv2
from target import TrackingTarget
import numpy, threading, Queue

USE_HD = True
TARGET_SIZE = 40 if USE_HD else 25
VIDEO_SIZE = (1270, 720) if USE_HD else (640, 480)
VIDEO_SOURCE = 0
TRACK_WINDOW = (100, 100)
LOCK_RETENTION = 20
LOCK_THRESHOLD = 0.05
LOCK_SWITCH_STDDEV = 0.2

# Tracking states
TRK_STATE_ACQUIRE = 0
TRK_STATE_LOCKED = 1

class VideoCaptureThread(threading.Thread):
    def __init__(self, videoSource):
        super(VideoCaptureThread, self).__init__()
        self.source = videoSource
        self.queue = Queue.Queue(1)
        self.running = False
        self.nFrame = 0
        
    def getEndpointQueue(self):
        return self.queue

    def run(self):
        self.running = True
        print "VideoCaptureThread running"
        while self.running:
            # Try to capture a frame
            ret, img = self.source.read()
            
            if ret:
                # Push it onto the queue
                self.queue.put((self.nFrame, img))
                self.nFrame += 1
                
    def terminate(self):
        self.running = False
        self.join()

class PreProcessThread(threading.Thread):
    def __init__(self, sourceQueue):
        super(PreProcessThread, self).__init__()
        self.sourceQ = sourceQueue
        self.destQ = Queue.Queue(2)

    def getEndpointQueue(self):
        return self.destQ
    
    def run(self):
        self.running = True
        print "PreProcessThread running"
        while self.running:
            # Get an image from the source queue
            nFrame, iimg = self.sourceQ.get()
            
            # Do the pre processing
            pimg = cv2.equalizeHist(cv2.cvtColor(iimg, cv2.cv.CV_RGB2GRAY))
            
            # Push the result on the destination queue
            result = (nFrame, iimg, pimg)
            self.destQ.put(result)

class MatchTemplateThread(threading.Thread):
    def __init__(self, sourceQueue, template):
        super(MatchTemplateThread, self).__init__()
        self.sourceQ = sourceQueue
        self.destQ = Queue.Queue(2)
        self.template = template

    def getEndpointQueue(self):
        return self.destQ
    
    def run(self):
        self.running = True
        print "MatchTemplateThread running"
        while self.running:
            # Get an image from the source queue
            nFrame, iimg, pimg = self.sourceQ.get()
            
            # Run template matching
            matches = cv2.matchTemplate(pimg, self.template, cv2.TM_CCORR_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(matches)
            sel_val = max_val
            sel_loc = max_loc

            # Push the result on the destination queue
            result = (nFrame, iimg, pimg, sel_loc, sel_val)
            self.destQ.put(result)


class Tracker(threading.Thread):
    def __init__(self, targetCls):
        super(Tracker, self).__init__()

        # Create a target image
        self.target = targetCls(TARGET_SIZE).getImage()

        # Reset the state
        self.reset = self.switchToAcquire
        self.reset()

        # Create the worker threads
        self.videoSourceThread = VideoCaptureThread(self.getVideoSource())
        self.preProcThread = PreProcessThread(
            self.videoSourceThread.getEndpointQueue())
        self.matchTemplateThread = MatchTemplateThread(
            self.preProcThread.getEndpointQueue(), self.target)
        self.matchQueue = self.matchTemplateThread.getEndpointQueue()

    def start(self):
        # Start all the working threads
        self.matchTemplateThread.start()
        self.preProcThread.start()
        self.videoSourceThread.start()
        super(Tracker, self).start()

    def getVideoSource(self):
        # Initialize the video capture
        cap = cv2.VideoCapture(VIDEO_SOURCE)
        cap.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, VIDEO_SIZE[0])
        cap.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, VIDEO_SIZE[1])
        return cap

    def switchToAcquire(self):
        self.state = TRK_STATE_ACQUIRE
        self.lastDetections = []
        self.onAcquire()
        
    def switchToLocked(self, point):
        self.state = TRK_STATE_LOCKED
        self.window = None
        self.onLock()

    def run(self):
        self.running = True
        print "Tracker thread running"
        while self.running:
            # Wait on the match queue
            nFrame, iimg, pimg, sel_loc, sel_val = self.matchQueue.get()
            
            # New match result
            print "%d X=%d Y=%d %f" % (nFrame, sel_loc[0], sel_loc[1], sel_val) 
            self.onFrame(nFrame, iimg, pimg, sel_loc, sel_val)

    def onFrame(self, nFrame, iimg, pimg, sel_loc, sel_val):
        "Default callback for frame display"
        if self.state == TRK_STATE_ACQUIRE:
            # Target aquisition state

            # Make sure the detection is not too weak
            if sel_val > LOCK_THRESHOLD:
                self.lastDetections.append(sel_loc)

                # In order to declare lock, we must have
                # LOCK_RETENTION samples in the buffer
                if len(self.lastDetections) > LOCK_RETENTION:
                    # Remove the oldest sample from the list
                    self.lastDetections.pop(0)

                    # The criterion for switching from ACQUIRE state
                    # to locked state is that the standard deviation of the
                    # detection center is lower than a predefined threshold
                    c = self.stddev(self.lastDetections)
                    
                    if c < LOCK_SWITCH_STDDEV:
                        # There are enough "good" samples, the standard deviation
                        # is small enough - switch to locked state

                        # The detection point is the average of all the detection
                        # points in the last detections
                        dp = map(numpy.average, zip(*self.lastDetections))
                        self.switchToLocked(dp)
        
    def onCoordinates(self, img, x, y):
        pass

    def onLock(self):
        pass
        
    def onAcquire(self):
        pass
    
    def stddev(self, points):
        # Is it mathematically correct?
        v = map(numpy.std, zip(*points))
        return numpy.sqrt(v[0]*v[0] + v[1]*v[1] )


