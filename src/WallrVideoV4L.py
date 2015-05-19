 # WallrVideo.py
#
# Defines the video source used by wallr

import ast, cv2, threading, Queue
import time

class WallrVideo(threading.Thread):

    def __init__(self, settings):
        super(WallrVideo, self).__init__()
        
        self.width = int(settings.width)
        self.height = int(settings.height)
        self.fps = int(settings.fps)

        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            raise Exception("Failed opening video capture device")

        self.queue = Queue.Queue(1)
        self.running = True

    def terminate(self):
        self.running = False
        self.join()

    def run(self):
        n = 0
        while self.running:
            ret, img = self.cap.read()
            if ret and (self.queue.qsize() == 0):
                n = n + 1
                imggray = cv2.cvtColor(img, cv2.cv.CV_RGB2GRAY)
                self.queue.put(imggray)
            else:
                time.sleep(0.002)
            

    def next_frame(self):
        pass

    def next_frame_block(self):
        frm = self.queue.get()
        if frm is not None:
            return (frm, )


    def setup(self):
        self.cap.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.cv.CV_CAP_PROP_FPS, 30)

