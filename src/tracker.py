import cv2
from target import TrackingTarget
import numpy, threading, Queue, ast
import time
import trkutil
import WallrSettings
import WallrVideo
#import WallrVideoV4L as WallrVideo

# Tracking states
TRK_STATE_ACQUIRE = 0
TRK_STATE_LOCKED = 1

# Message types that can be sen to the callback function
#
MSG_SWITCH_TO_ACQ  = 0 # No parameters
MSG_SWITCH_TO_LOCK = 1 # No parameters
MSG_COORDINATES    = 2 # (x,y) of the detection
MSG_LOCK_PROGRESS  = 3 # A number between 0 to 100 designating the acquisition progress

class Tracker(threading.Thread):

    def __init__(self, targetCls, callback, force_lock = False):
        super(Tracker, self).__init__()
        
        self.running = False
        self.callback = callback
        self.force_lock = force_lock
        
        # Get tracker settings from settings file
        st = WallrSettings.settings.tracker
        self.target_size = int(st['target size'])
        self.search_win = trkutil.Rectangle(*ast.literal_eval(st['initial search window']))
        self.lock_retention = int(st['lock retention'])
        self.lock_threshold = float(st['lock threshold'])
        self.lock_stddev = float(st['lock stddev'])
        self.track_window = ast.literal_eval(st['track window'])
        self.track_margin = float(st['track margin'])
        self.track_retention = int(st['track retention'])
        self.screen_size = (WallrSettings.settings.video.width,
                            WallrSettings.settings.video.height)

        # Create a target image
        self.target = targetCls(self.target_size).getImage()

        # Reset the state
        self.nFrame = 0
        self.reset = self.switchToAcquire
        self.reset()
        if self.force_lock:
            self.switchToLocked((400, 400), 0.5)
        
        # Initialize the camera
        self.vsource = WallrVideo.WallrVideo(WallrSettings.settings.video)
        self.vsource.setup()
        self.vsource.start()

    def setAcquireRectangle(self, top_left, bottom_right):
        print 'set search rect'
        tl = (min(top_left[0], bottom_right[0]),min(top_left[1], bottom_right[1]))
        br = (max(top_left[0], bottom_right[0]),max(top_left[1], bottom_right[1]))
        print tl
        print br

        self.search_win = trkutil.Rectangle(tl[0], tl[1],
                                            br[0], br[1])
        
    def switchToAcquire(self):
        self.state = TRK_STATE_ACQUIRE
        self.lastDetections = []
        self.window = self.search_win

        self.callback(MSG_SWITCH_TO_ACQ, None);
        
    def switchToLocked(self, point, value):
        self.state = TRK_STATE_LOCKED

        self.detectionPoint = point
        self.detectionThreshold = value*(1-self.track_margin)
        self.failCount = self.track_retention
        self.window = self.calcWindow(point, self.track_window, self.screen_size)

        self.callback(MSG_SWITCH_TO_LOCK, None);
        
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
        pp = (point[0] + size[0]/2, point[1]+size[1]/2)
        win = trkutil.Rectangle(
            self.clip(pp[0]-size[0], screen[0]), # xleft
            self.clip(pp[1]-size[1], screen[1]), # ytop
            self.clip(pp[0]+size[0], screen[0]), # xright
            self.clip(pp[1]+size[1], screen[1])) # ybottom

        return win
            
    def clip(self, value, maxvalue):
        return max(0, int(min(maxvalue, value)))

    def terminate(self):
        self.running = False
        self.join()
        self.vsource.terminate()
        print "Tracker terminated"

    def run(self):
        self.running = True
        print "Tracker thread running"
        while self.running:
            # Wait on the match queue
            rawFrame = self.vsource.next_frame_block()
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
                   
        self.matches = cv2.matchTemplate(roi, self.target, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(self.matches)
        sel_val = max_val
        sel_loc = max_loc
        sel_loc = (sel_loc[0] + self.window.xleft, sel_loc[1] + self.window.ytop)
        
        if self.state == TRK_STATE_ACQUIRE:
            # Target aquisition state
            #########################

            # Make sure the detection is not too weak
            if sel_val > self.lock_threshold:
                self.lastDetections.append((sel_loc, sel_val))

                # In order to declare lock, we must have
                # LOCK_RETENTION samples in the buffer
                if len(self.lastDetections) > self.lock_retention:
                    # Remove the oldest sample from the list
                    self.lastDetections.pop(0)

                    # The criterion for switching from ACQUIRE state
                    # to locked state is that the standard deviation of the
                    # detection center is lower than a predefined threshold
                    # Moreover, in order to trace the progress of the acuisition
                    # process, we calculate the stddev for every n points starting
                    # from the less recent one.
                    sdv = [ self.stddev(zip(*self.lastDetections[:i])[0])
                                        for i in range(1,len(self.lastDetections)) ]
                    try:
                        first_fail = [ll < self.lock_stddev for ll in sdv].index(False)
                        progress = 1.0-first_fail*1.0/len(sdv)
                    except ValueError:
                        progress = 1.0

                    self.callback(MSG_LOCK_PROGRESS, progress)

                    c = sdv[-1]
                    
                    if c < self.lock_stddev:
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
                self.window = self.calcWindow(self.detectionPoint, self.track_window, self.screen_size)
                self.failCount = self.lock_retention

                # Generate a message
                self.callback(MSG_COORDINATES, 
                              {'x': self.detectionPoint[0], 'y': self.detectionPoint[1]})

            else:
                # Failed detection
                self.failCount -= 1
                
                if self.failCount == 0:
                    # Too many failures, switch back to acquisition
                    if not self.force_lock:
                        self.switchToAcquire()

    
    def stddev(self, points):
        # Is it mathematically correct?
        v = map(numpy.std, zip(*points))
        return numpy.sqrt(v[0]*v[0] + v[1]*v[1] )
    
