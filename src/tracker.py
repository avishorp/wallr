import cv2
from target import TrackingTarget
import numpy, threading, Queue
import trkutil

USE_HD = True
TARGET_SIZE = 40 if USE_HD else 25
VIDEO_SIZE = (1270, 720) if USE_HD else (640, 480)
VIDEO_SOURCE = 0
TRACK_WINDOW = (50, 50)
LOCK_RETENTION = 20
LOCK_THRESHOLD = 0.05
LOCK_SWITCH_STDDEV = 0.2
NUM_MATCHERS = 4
DETECTION_MARGIN = 0.1

# Tracking states
TRK_STATE_ACQUIRE = 0
TRK_STATE_LOCKED = 1

class VideoCaptureThread(threading.Thread):
    def __init__(self, videoSource, destQueue):
        super(VideoCaptureThread, self).__init__()
        self.source = videoSource
        self.queue = destQueue
        self.running = False
        self.nFrame = 0
        
    def run(self):
        self.running = True
        print "VideoCaptureThread running"
        while self.running:
            # Try to capture a frame
            ret, img = self.source.read()
            
            if ret:
                try:
                    # Push it onto the queue
                    self.queue.put((self.nFrame, img), True, 1)
                    self.nFrame += 1

                except Queue.Full:
                    # Should not be thrown normally, used to handle
                    # thread termination
                    pass
                
    def terminate(self):
        self.running = False

class PreProcessThread(threading.Thread):
    def __init__(self, sourceQueue, destQueue):
        super(PreProcessThread, self).__init__()
        self.sourceQ = sourceQueue
        self.destQ = destQueue

    def run(self):
        self.running = True
        print "PreProcessThread running"
        while self.running:
            try:
                # Get an image from the source queue
                nFrame, iimg = self.sourceQ.get(True, 1)
            
                # Do the pre processing
                pimg = cv2.equalizeHist(cv2.cvtColor(iimg, cv2.cv.CV_RGB2GRAY))
            
                # Push the result on the destination queue
                result = (nFrame, iimg, pimg)
                self.destQ.put(result, True, 1)
            
            except (Queue.Full, Queue.Empty):
                # Should not be thrown normally, used to handle
                # thread termination
                pass

    def terminate(self):
        self.running = False

class MatchTemplateThread(threading.Thread):
    def __init__(self, sourceQueue, destQueue, template):
        super(MatchTemplateThread, self).__init__()
        self.sourceQ = sourceQueue
        self.destQ = destQueue
        self.template = template
        self.roi = None
        
    def setMatchingROI(self, roi):
        self.roi = roi

    def run(self):
        self.running = True
        print "MatchTemplateThread running"
        while self.running:
            try:
                # Get an image from the source queue
                nFrame, iimg, pimg = self.sourceQ.get(True, 1)
                
                roi = pimg[self.roi.xleft:self.roi.xright,
                           self.roi.ytop,self.roi.ybottom] if self.roi is not None else pimg
            
                # Run template matching
                matches = cv2.matchTemplate(pimg, self.template, cv2.TM_CCORR_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(matches)
                sel_val = max_val
                sel_loc = max_loc

                # Push the result on the destination queue
                result = (nFrame, iimg, pimg, sel_loc, sel_val)
                self.destQ.put(result, True, 1)

            except (Queue.Full, Queue.Empty):
                # Should not be thrown normally, used to handle
                # thread termination
                pass

    def terminate(self):
        self.running = False


class QueueDistributor(object):
    # A QueueDistributor class is an adaptor between one producer
    # and multiple queues. It reflects the Queue's put interface,
    # distributing the actual put between multiple queues, in round
    # robin fashion
    def __init__(self, queueList):
        self.n = 0
        self.queues = queueList
        
    def put(self, *args):
        self.queues[self.n].put(*args)
        self.n = (self.n + 1) % len(self.queues)

class Tracker(threading.Thread):
    def __init__(self, targetCls):
        super(Tracker, self).__init__()

        # Create a target image
        self.target = targetCls(TARGET_SIZE).getImage()

        # Reset the state
        self.currentFrame = 0
        self.reset = self.switchToAcquire
        self.reset()

        # Create the worker threads and queues
        self.rawVideoQueue = Queue.Queue(1)
        self.videoSourceThread = VideoCaptureThread(self.getVideoSource(),
                                                    self.rawVideoQueue)
        
        self.preProcQueues = [ Queue.Queue(1) for k in range(0, NUM_MATCHERS) ]
        self.preProcThread = PreProcessThread(self.rawVideoQueue,
                                              QueueDistributor(self.preProcQueues))

        self.matchQueue = Queue.Queue(1)
        self.matchTemplateThreads = [ MatchTemplateThread(
            self.preProcQueues[k], self.matchQueue, self.target)
                                      for k in range(0, NUM_MATCHERS) ]


    def start(self):
        # Start all the working threads
        for tr in self.matchTemplateThreads:
            tr.start()
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
        
    def switchToLocked(self, point, value):
        self.state = TRK_STATE_LOCKED

        self.detectionPoint = point
        self.detectionThreshold = value*(1-DETECTION_MARGIN)
        self.window = self.calcWindow(point, TRACK_WINDOW, VIDEO_SIZE)
        self.onLock()
        
    def calcWindow(self, point, size, screen):
        #     | size_x |
        #     +----------------+--
        #     |                | ^
        #     |                | size_y
        #     |                | v
        #     |        O       |--
        #     |                |
        #     |                |
        #     |                |
        #     +----------------+
        win = trkutil.Rectangle(
            self.clip(point[0]-size[0], screen[0]), # xleft
            self.clip(point[0]+size[0], screen[0]), # xright
            self.clip(point[1]-size[1], screen[1]), # ytop
            self.clip(point[1]+size[1], screen[1])) # ybottom

        return win
            
    def clip(self, value, maxvalue):
        return max(0, int(min(maxvalue, value)))

    def terminate(self):
        self.running = False
        
        all_threads = [
            (self.videoSourceThread, "SourceVideoThread"),
            (self.preProcThread, "PreProcThread") ]
        for tr in range(len(self.matchTemplateThreads)):
            all_threads.append((self.matchTemplateThreads[tr],
                                "MatchTemplateThread %d" % tr))
            
        for tr in all_threads:
            tr[0].terminate()
            
        for tr in all_threads:
            tr[0].join()
            print "%s terminated" % tr[1]

        self.join()
        print "Tracker terminated"

    def run(self):
        self.running = True
        print "Tracker thread running"
        while self.running:
            try:
                # Wait on the match queue
                nFrame, iimg, pimg, sel_loc, sel_val = self.matchQueue.get()
            
                # New match result
                print "%d X=%d Y=%d %f" % (nFrame, sel_loc[0], sel_loc[1], sel_val) 
                self.onFrame(nFrame, iimg, pimg, sel_loc, sel_val)

            except Queue.Empty:
                pass

    def onFrame(self, nFrame, iimg, pimg, sel_loc, sel_val):
        "Default callback for frame display"
        
        # Update the frame counter
        self.currentFrame = nFrame
        
        if self.state == TRK_STATE_ACQUIRE:
            # Target aquisition state
            #########################

            # Make sure the detection is not too weak
            if sel_val > LOCK_THRESHOLD:
                self.lastDetections.append((sel_loc, sel_val))

                # In order to declare lock, we must have
                # LOCK_RETENTION samples in the buffer
                if len(self.lastDetections) > LOCK_RETENTION:
                    # Remove the oldest sample from the list
                    self.lastDetections.pop(0)

                    # The criterion for switching from ACQUIRE state
                    # to locked state is that the standard deviation of the
                    # detection center is lower than a predefined threshold
                    c = self.stddev(zip(*self.lastDetections)[0])
                    
                    if c < LOCK_SWITCH_STDDEV:
                        # There are enough "good" samples, the standard deviation
                        # is small enough - switch to locked state

                        # The detection point is the average of all the detection
                        # points in the last detections
                        p = zip(*self.lastDetections)[0]
                        v = zip(*self.lastDetections)[1]
                        point = map(lambda n: int(round(numpy.average(n))),
                                    zip(*p))
                        value = numpy.average(v)
                        self.switchToLocked(point, value)

        else:
            # Locked state
            ##############
            pass

        # Frame processing finished successfully
        return True
        
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
    
