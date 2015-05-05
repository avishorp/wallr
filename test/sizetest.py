#!/usr/bin/env python

# This is a small script to test the effect of target size on the detection quality.
# It captures a single frame, and then runs the template matching algorithm for a set
# of target sizes, printing the matching value (closer to 1 - better)

import sys
sys.path.append('../src')

import cv2, target

VIDEO_SIZE = (1920, 1080)
TARGET_SIZE = range(12, 60)


def graph_point(v, width):
    s = [' ']*width
    s[int(v*width)] = '*'
    return ''.join(s)


cap = cv2.VideoCapture(0)
cap.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, VIDEO_SIZE[0])
cap.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, VIDEO_SIZE[1])
ret, img = cap.read()

winname = "Size Test"
cv2.namedWindow(winname)
cv2.startWindowThread()

imggray = cv2.equalizeHist( cv2.cvtColor(img, cv2.cv.CV_RGB2GRAY))
#imggray = cv2.cvtColor(img, cv2.cv.CV_RGB2GRAY)


r = []
max_val = 0
max_loc = 0
max_target = 0

for s in TARGET_SIZE:
    t = target.TrackingTarget(s).getImage()
    mv,xv,ml,xl=cv2.minMaxLoc(cv2.matchTemplate(imggray, t, cv2.TM_CCORR_NORMED))
    loc = xl
    if xv > max_val:
        max_val = xv
        max_loc = loc
        max_target = t
    r.append(xv)
    #print "size=%d  value=%f" % (s, xv)
    print "%d  %f (%f,%f)" % (s, xv, loc[0], loc[1])

    imgcomb = imggray.copy()
    imgcomb = cv2.cvtColor(imgcomb, cv2.cv.CV_GRAY2RGB)
    cv2.rectangle(imgcomb, loc, (loc[0]+s,loc[1]+s), color=[0,0,255])

    cv2.imshow(winname, imgcomb)
    #ch = 0xFF & cv2.waitKey(1)



for s in range(len(TARGET_SIZE)):
    print "%5d|%s" % (TARGET_SIZE[s], graph_point(r[s], 40))

print "\nMaximal value: %f at target size %d" % (max_val, max_target)
