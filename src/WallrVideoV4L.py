 # WallrVideo.py
#
# Defines the video source used by wallr

import ast, cv2


class WallrVideo(object):
    def __init__(self, settings):
        self.width = int(settings.width)
        self.height = int(settings.height)
        self.fps = int(settings.fps)

        self.cap = cv2.VideoCapture(0)


    def next_frame(self):
        ret, img = self.cap.read()
        if ret:
            imggray = cv2.cvtColor(img, cv2.cv.CV_RGB2GRAY)
            return imggray
        else:
            return None

    def next_frame_block(self):
        while True:
            f = self.next_frame()
            if f is not None:
                return (f,)

    def setup(self):
        self.cap.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, self.height)

