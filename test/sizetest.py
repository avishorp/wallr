#!/usr/bin/env python

# This is a small script to test the effect of target size on the detection quality.
# It captures a single frame, and then runs the template matching algorithm for a set
# of target sizes, printing the matching value (closer to 1 - better)

import sys
sys.path.append('../src')

import cv2, target

VIDEO_SIZE = (640, 480)
TARGET_SIZE = range(15, 60)


def graph_point(v, width):
    s = [' ']*width
    s[int(v*width)] = '*'
    return ''.join(s)


cap = cv2.VideoCapture(0)
cap.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, VIDEO_SIZE[0])
cap.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, VIDEO_SIZE[1])
ret, img = cap.read()

imggray = cv2.equalizeHist( cv2.cvtColor(img, cv2.cv.CV_RGB2GRAY))
#imggray = cv2.cvtColor(img, cv2.cv.CV_RGB2GRAY)


r = []

for s in TARGET_SIZE:
    t = target.TrackingTarget(s).getImage()
    mv,xv,ml,xl=cv2.minMaxLoc(cv2.matchTemplate(imggray, t, cv2.TM_CCORR_NORMED))
    r.append(xv)
    #print "size=%d  value=%f" % (s, xv)
    print "%d  %f" % (s, xv)

for s in range(len(TARGET_SIZE)):
    print "%5d|%s" % (TARGET_SIZE[s], graph_point(r[s], 40))
