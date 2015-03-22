import cv2
from target import TrackingTarget

TARGET_SIZE = 25
VIDEO_SIZE = (640, 480)
VIDEO_SOURCE = 0

class Tracker(object):
    def __init__(self, targetCls):
        # Create a target image
        self.target = targetCls(25).getImage()
        
        # Initialize the video capture
        self.cap = cv2.VideoCapture(VIDEO_SOURCE)
        self.cap.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, VIDEO_SIZE[0])
        self.cap.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, VIDEO_SIZE[1])

        self.running = True

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
        matches = cv2.matchTemplate(img, self.target, cv2.TM_CCOEFF)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(matches)
        
        self.targetPoint = max_loc

        self.onCoordinates(img, max_loc[0], max_loc[1])

    def onCoordinates(self, img, x, y):
        pass


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
            
            cv2.imshow('tracker', img)
            self.nFrames += 1
            
            if (cv2.getTickCount() - self.t) > self.sec:
                print "FPS=%d" % self.nFrames
                self.nFrames = 0
                self.t = cv2.getTickCount()

            ch = 0xFF & cv2.waitKey(1)
            
            if (ch == 'q'):
                self.stop()

        def onCoordinates(self, img, x, y):
            cv2.circle(img, (x,y), 10, color=255, thickness=2)

    trk = DebugTracker(TrackingTarget)
    trk.run()

