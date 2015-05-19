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

    def __init__(self, targetCls, show_image, input_file, output_file, force_lock):
        self.t0 = time.time()
        self.log_file = open('tracker.log', 'wb')

        super(DebugTracker, self).__init__(self.cblog, targetCls, force_lock)
        self.t = time.time()
        self.sec = 5
        self.nFrames = 0
        self.tproc_total = 0
        self.show_image = show_image
        self.input_file = input_file
        self.output_file = output_file


    def cblog(self, msg, param):
        d = time.time() - self.t0
        log_format = [("%f",d),("%d",msg)]

        s = "Tracker Message: %s" % self.messages[msg]
        if (msg == tracker.MSG_LOCK_PROGRESS):
            s += " (progress: %f)" % param
            log_format.append(("%f", param))
        if (msg == tracker.MSG_COORDINATES):
            s += " (x=%d, y=%d)" % (param['x'], param['y'])
            log_format.append(("%f", param['x']))
            log_format.append(("%f", param['y']))

        print s
        self.log_file.write((','.join([s[0] for s in log_format])+'\n') %
                            tuple([s[1] for s in log_format]))

    def onFrame(self, nFrame, iimg, pimg):
        tf0 = time.time()
        super(DebugTracker, self).onFrame(nFrame, iimg, pimg)
        tproc = time.time() - tf0
        self.tproc_total += tproc

        if self.show_image:
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
                    cv2.rectangle(imgdisp, (0,0), (self.target_size,self.target_size), color=[255,0,0])

            cv2.imshow('tracker', imgdisp)
            cv2.imshow('matches', self.matches)
        self.nFrames += 1
        
        now = time.time()
        dt = now - self.t
        if (now - self.t) > self.sec:
            print "FPS=%f Processing Time=%f" % ((self.nFrames*1.0/dt), self.tproc_total*1.0/self.nFrames)
            self.nFrames = 0
            self.t = now
            self.tproc_total = 0
            
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
                           ["noimage","output-file=","input-file=","force-lock"])

input_file = None
output_file = None
show_image = True
force_lock = False

for o, a in opts:
    if o == '--noimage':
        show_image = False

    if o == '--input-file':
        input_file = a

    if o == '--output-file':
        output_file = a

    if o == '--force-lock':
        force_lock = True

trk = DebugTracker(target.TrackingTarget, show_image, input_file, output_file, force_lock=force_lock)
signal.signal(signal.SIGINT, lambda sig,frm: trk.stop())

trk.start()

for k in range(10):
    time.sleep(10)
    trk.switchToAcquire()
    time.sleep(10)
    trk.switchToLocked((200,200), 0.5)
while not trk.running:
    pass

while trk.running:
    time.sleep(1)

