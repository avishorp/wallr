import cv2
from target import TrackingTarget
import numpy

TARGET_SIZE = 25
VIDEO_SIZE = (640, 480)
VIDEO_SOURCE = 0
TRACK_WINDOW = (100, 100)
LOCK_RETENTION = 20
LOCK_THRESHOLD = 0

# Tracking states
TRK_STATE_ACQUIRE = 0
TRK_STATE_LOCKED = 1

class Tracker(object):
    def __init__(self, targetCls):
        # Create a target image
        self.target = targetCls(25).getImage()

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
        
    def switchToLocked(self, win):
        self.state = TRK_STATE_LOCKED
        self.window = win

    def run(self):
        while self.running:
            # Capture a frame
            ret, img = self.cap.read()

            if ret:
                # Convert the frame to grayscale
                imggray = cv2.cvtColor(img, cv2.cv.CV_RGB2GRAY)
                self.onFrame(imggray)

    def stop(self):
        self.running = False

    def onFrame(self, img):
        "Default callback for frame display"
        if self.state == TRK_STATE_ACQUIRE:
            # Target aquisition state
            
            # Try to find the target across the whole image
            matches = cv2.matchTemplate(img, self.target, cv2.TM_CCOEFF)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(matches)
            
            # Make sure the detection is not too weak
            if max_val > LOCK_THRESHOLD:
                self.lastDetections.append(max_loc)

                # In order to declare lock, we must have
                # LOCK_RETENTION samples in the buffer
                if len(self.lastDetections) > LOCK_RETENTION:
                    # Remove the oldest sample from the list
                    self.lastDetections.pop(0)

                    # The criterion for switching from ACQUIRE state
                    # to locked state is that the standard deviation of the
                    # detection center is lower than a predefined threshold
                    c = self.stddev(self.lastDetections)
                    print c
        
        self.targetPoint = max_loc

        self.onCoordinates(img, max_loc[0], max_loc[1])

    def onCoordinates(self, img, x, y):
        pass
    
    def stddev(self, points):
        # Is it mathematically correct?
        v = map(numpy.std, zip(*points))
        return numpy.sqrt(v[0]*v[0] + v[1]*v[1] )

##################################

if __name__=='__main__':
    class DebugTracker(Tracker):
        def __init__(self, targetCls):
            super(DebugTracker, self).__init__(targetCls)
            self.t = cv2.getTickCount()
            self.sec = cv2.getTickFrequency()
            self.nFrames = 0

        def onFrame(self, img):
            super(DebugTracker, self).onFrame(img)
            
            imgdisp = cv2.cvtColor(img, cv2.cv.CV_GRAY2RGB)

            if self.state == TRK_STATE_ACQUIRE:
                statetxt = "ACK"
                
                for d in self.lastDetections:
                    self.crosshair(imgdisp, d, color=[0,255,0])
            else:
                statetxt = "LOCK"

            cv2.putText(imgdisp, text=statetxt, org=(8,50), 
                        fontFace=cv2.FONT_HERSHEY_PLAIN, 
                        fontScale=3, 
                        color=[255, 255, 0])
            cv2.imshow('tracker', imgdisp)
            self.nFrames += 1
            
            if (cv2.getTickCount() - self.t) > self.sec:
                print "FPS=%d" % self.nFrames
                self.nFrames = 0
                self.t = cv2.getTickCount()

            ch = 0xFF & cv2.waitKey(1)
            
            if (ch == 'q'):
                self.stop()

        def onCoordinates(self, img, x, y):
            #cv2.circle(img, (x,y), 10, color=[255, 0, 0], thickness=2)
            pass
        
        def crosshair(self, img, center, color):
            x = center[0]
            y = center[1]
            cv2.line(img, (x-5, y), (x+5,y), color = color, thickness=1)
            cv2.line(img, (x, y-5), (x,y+5), color = color, thickness=1)

    trk = DebugTracker(TrackingTarget)
    trk.run()

