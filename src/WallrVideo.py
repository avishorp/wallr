# WallrVideo.py
#
# Defines the video source used by wallr

import raspicap, ast

SENSOR_SIZE = (2592, 1944)

class WallrVideo(object):
    def __init__(self, settings):
        self.width = int(settings.width)
        self.height = int(settings.height)
        self.fps = int(settings.fps)
        
        xd = 1.0/SENSOR_SIZE[0]
        yd = 1.0/SENSOR_SIZE[1]
        origin = ast.literal_eval(settings.origin)
        self.roi = (origin[0]*xd, origin[1]*xd, 
                    (origin[0]+SENSOR_SIZE[0])*xd,
                    (origin[1]+SENSOR_SIZE[1])*yd)

        self.next_frame = raspicap.next_frame
        self.next_frame_block = raspicap.next_frame_block

    def setup(self):
        raspicap.setup(width=self.width, height=self.height, fps=self.fps)
        #raspicap.set_param(roi=self.roi)

