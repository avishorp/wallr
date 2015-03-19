import cv2
from target import TrackingTarget

TARGET_SIZE = 25
VIDEO_SIZE = (640, 480)
VIDEO_SOURCE = 0

class Tracker:
    def __init__(self, targetCls):
        # Create a target image
        self.target = targetCls(25)
        
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
        pass

    def onCoordinates(self, x, y):
        pass


##################################

if __name__=='__main__':
    class DebugTracker(Tracker):
        def onFrame(self, img):
            cv2.imshow('tracker', img)
            ch = 0xFF & cv2.waitKey(1)
            
            if (ch == 'q'):
                self.stop()

    trk = DebugTracker(TrackingTarget)
    trk.run()

