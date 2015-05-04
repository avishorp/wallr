import cv2
from target import TrackingTarget
import numpy, threading, Queue
import trkutil
import raspicap

TARGET_SIZE = 20
VIDEO_SIZE = (1920, 1080)
VIDEO_SOURCE = 0
TRACK_WINDOW = (100, 100)
LOCK_RETENTION = 20
LOCK_THRESHOLD = 0.05
LOCK_SWITCH_STDDEV = 0.2
NUM_MATCHERS = 4
DETECTION_MARGIN = 0.1
LOCK_FAIL_RETENTION = 5
INITIAL_SEARCH_WINDOW = trkutil.Rectangle(640-200, 640+200, 360-200, 360+200)

# Tracking states
TRK_STATE_ACQUIRE = 0
TRK_STATE_LOCKED = 1

class Tracker(threading.Thread):
    def __init__(self, targetCls):
        super(Tracker, self).__init__()
        
        self.running = False

        # Create a target image
        self.target = targetCls(TARGET_SIZE).getImage()

        # Reset the state
        self.nFrame = 0
        self.reset = self.switchToAcquire
        self.reset()

        # Initialize the camera
        raspicap.setup()

    def switchToAcquire(self):
        self.state = TRK_STATE_ACQUIRE
        self.lastDetections = []
        self.window = INITIAL_SEARCH_WINDOW
        self.onAcquire()
        
    def switchToLocked(self, point, value):
        self.state = TRK_STATE_LOCKED

        self.detectionPoint = point
        self.detectionThreshold = value*(1-DETECTION_MARGIN)
        self.failCount = LOCK_FAIL_RETENTION
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

        # Correct the center point so that the target is in the middle
        # of the window
        pp = (point[0] + TARGET_SIZE/2, point[1]+TARGET_SIZE/2)
        win = trkutil.Rectangle(
            self.clip(pp[0]-size[0], screen[0]), # xleft
            self.clip(pp[0]+size[0], screen[0]), # xright
            self.clip(pp[1]-size[1], screen[1]), # ytop
            self.clip(pp[1]+size[1], screen[1])) # ybottom

        return win
            
    def clip(self, value, maxvalue):
        return max(0, int(min(maxvalue, value)))

    def terminate(self):
        self.running = False
        self.join()
        print "Tracker terminated"

    def run(self):
        self.running = True
        print "Tracker thread running"
        while self.running:
            # Wait on the match queue
            rawFrame = raspicap.next_frame_block()
            self.nFrame += 1
            
            iimg = rawFrame[0] # Only the Y component
            pimg = cv2.equalizeHist(iimg)
            self.onFrame(self.nFrame, iimg, pimg)

    def onFrame(self, nFrame, iimg, pimg):
        "Default callback for frame display"
        
        # Run template matching
        roi = pimg[self.window.ytop:self.window.ybottom,
                   self.window.xleft:self.window.xright]
        self.rroi = roi
                   

        self.matches = cv2.matchTemplate(roi, self.target, cv2.TM_SQDIFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(self.matches)
        sel_val = min_val
        sel_loc = (min_loc[0] + self.window.xleft, min_loc[1] + self.window.ytop)
        
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
            if sel_val > self.detectionThreshold:
                # Successful detection
                self.detectionPoint = sel_loc
                self.window = self.calcWindow(self.detectionPoint, TRACK_WINDOW, VIDEO_SIZE)
                self.failCount = LOCK_FAIL_RETENTION

            else:
                # Failed detection
                self.failCount -= 1
                
                if self.failCount == 0:
                    # Too many failures, switch back to acquisition
                    self.switchToAcquire()


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
    
