import cv2
from target import TrackingTarget
import numpy

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

class Tracker(object):
    def __init__(self, targetCls):
        # Create a target image
        self.target = targetCls(TARGET_SIZE).getImage()

        # Reset the state
        self.reset = self.switchToAcquire
        self.reset()

        # Initialize the video capture
        self.cap = cv2.VideoCapture(VIDEO_SOURCE)
        self.cap.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, VIDEO_SIZE[0])
        self.cap.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, VIDEO_SIZE[1])

        self.running = True

    def switchToAcquire(self):
        self.state = TRK_STATE_ACQUIRE
        self.lastDetections = []
        self.onAcquire()
        
    def switchToLocked(self, point):
        self.state = TRK_STATE_LOCKED
        self.window = None
        self.onLock()

    def run(self):
        while self.running:
            # Capture a frame
            ret, img = self.cap.read()

            if ret:
                # Convert the frame to grayscale
                imggray = cv2.equalizeHist(cv2.cvtColor(img, cv2.cv.CV_RGB2GRAY))
                self.onFrame(imggray)

    def stop(self):
        self.running = False

    def onFrame(self, img):
        "Default callback for frame display"
        if self.state == TRK_STATE_ACQUIRE:
            # Target aquisition state
            
            # Try to find the target across the whole image
            matches = cv2.matchTemplate(img, self.target, cv2.TM_CCORR_NORMED)
            self.m = matches
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(matches)
            sel_val = max_val
            sel_loc = max_loc
            print sel_val
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


