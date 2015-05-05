#!/usr/bin/env python

# This program tests the tracker.

import sys
sys.path.append('../src')

import cv2, target, tracker
import getopt, time, signal

class DebugTracker(tracker.Tracker):

    messages = {
        tracker.MSG_SWITCH_TO_ACQ: 'SWITCH_TO_ACQ',
        tracker.MSG_SWITCH_TO_LOCK: 'SWITCH_TO_LOCK',
        tracker.MSG_COORDINATES: 'COORDINATES',
        tracker.MSG_LOCK_PROGRESS: 'LOCK_PROGRESS'
        }

    def __init__(self, targetCls, show_image, input_file, output_file):
        super(DebugTracker, self).__init__(targetCls, self.cblog)
        self.t = cv2.getTickCount()
        self.sec = cv2.getTickFrequency()
        self.nFrames = 0
        self.show_image = show_image
        self.input_file = input_file
        self.output_file = output_file

    def cblog(self, msg, param):
        s = "Tracker Message: %s" % self.messages[msg]
        if (msg == tracker.MSG_LOCK_PROGRESS):
            s += " (progress: %f)" % param
        if (msg == tracker.MSG_COORDINATES):
            s += " (x=%d, y=%d)" % (param['x'], param['y'])

        print s

    def onFrame(self, nFrame, iimg, pimg):
        super(DebugTracker, self).onFrame(nFrame, iimg, pimg)
            
        imgdisp = cv2.cvtColor(pimg, cv2.cv.CV_GRAY2RGB)
        #imgdisp = cv2.cvtColor(self.m, cv2.cv.CV_GRAY2RGB)

        # Draw the tracking window
        cv2.rectangle(imgdisp, (self.window.xleft, self.window.ytop),
                      (self.window.xright, self.window.ybottom), color=[0,0,255])

        if self.state == tracker.TRK_STATE_ACQUIRE:
            statetxt = "ACK"
                
            for d in self.lastDetections:
                self.crosshair(imgdisp, d[0], color=[0,255,0])
        else:
            statetxt = "LOCK"
            self.crosshair(imgdisp, self.detectionPoint, color=[0,0,255])
            

        cv2.putText(imgdisp, text=statetxt, org=(8,50), 
                    fontFace=cv2.FONT_HERSHEY_PLAIN, 
                    fontScale=3, 
                    color=[255, 255, 0])
        cv2.rectangle(imgdisp, (0,0), (tracker.TARGET_SIZE,tracker.TARGET_SIZE), color=[255,0,0])

        if self.show_image:
            cv2.imshow('tracker', imgdisp)
            cv2.imshow('matches', self.matches)
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

    def onLock(self):
        print "Switching to LOCK (time from acquire: %ds)" % (time.time()-self.acqTime)
        
    def onAcquire(self):
        print "Switching to ACQUIRE"
        self.acqTime = time.time()

    def stop(self):
        print "Stop signal received, terminating tracker"
        self.terminate()

        
    def crosshair(self, img, center, color):
        x = center[0]
        y = center[1]
        cv2.line(img, (x-5, y), (x+5,y), color = color, thickness=1)
        cv2.line(img, (x, y-5), (x,y+5), color = color, thickness=1)


##############################################################
##############################################################

# Parse the command line arguments
opts, args = getopt.getopt(sys.argv[1:], "d", 
                           ["noimage","output-file=","input-file="])

input_file = None
output_file = None
show_image = True

for o, a in opts:
    if o == '--noimage':
        show_image = False

    if o == '--input-file':
        input_file = a

    if o == '--output-file':
        output_file = a


trk = DebugTracker(target.TrackingTarget, show_image, input_file, output_file)
signal.signal(signal.SIGINT, lambda sig,frm: trk.stop())

trk.start()
while not trk.running:
    pass

while trk.running:
    time.sleep(1)

