#!/usr/bin/env python

# This is a small script to test the effect of target size on the detection quality.
# It captures a single frame, and then runs the template matching algorithm for a set
# of target sizes, printing the matching value (closer to 1 - better)

import sys
sys.path.append('../src')

import cv2, target, os

VIDEO_SIZE = (1920, 1080)
TARGET_SIZE = range(12, 50)
show = True
WHITE_SCREEN = False

def graph_point(v, width):
    s = [' ']*width
    s[int(v*width)] = '*'
    return ''.join(s)


cap = cv2.VideoCapture(0)
cap.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, VIDEO_SIZE[0])
cap.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, VIDEO_SIZE[1])
ret, img = cap.read()
if not ret:
    raise ValueError("Image capture failed")

if show:
    winname = "Size Test"
    cv2.namedWindow(winname)
    cv2.startWindowThread()

if WHITE_SCREEN:
    import pygame

    # Check which frame buffer drivers are available
    # Start with fbcon since directfb hangs with composite output
    drivers = ['fbcon', 'directfb', 'svgalib']
    found = False
    for driver in drivers:
        # Make sure that SDL_VIDEODRIVER is set
        if not os.getenv('SDL_VIDEODRIVER'):
            os.putenv('SDL_VIDEODRIVER', driver)
            try:
                pygame.display.init()
            except pygame.error:
                print 'Driver: {0} failed.'.format(driver)
                continue
            found = True
            break
        if not found:
            raise Exception('No suitable video driver found!')
    size = (pygame.display.Info().current_w, pygame.display.Info().current_h)
    print "Framebuffer size: %d x %d" % (size[0], size[1])
    self.screen = pygame.display.set_mode(size, pygame.FULLSCREEN)
    # Clear the screen to start
    self.screen.fill((255, 255, 255))
    # Initialise font support
    pygame.font.init()
    # Render the screen
    pygame.display.update()
    pygame.mouse.set_visible(False)

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
        max_target = s
    r.append(xv)
    #print "size=%d  value=%f" % (s, xv)
    print "%d  %f (%f,%f)" % (s, xv, loc[0], loc[1])

    if show:
        imgcomb = imggray.copy()
        imgcomb = cv2.cvtColor(imgcomb, cv2.cv.CV_GRAY2RGB)
        cv2.rectangle(imgcomb, loc, (loc[0]+s,loc[1]+s), color=[0,0,255])
        imgcombs = cv2.resize(imgcomb, (VIDEO_SIZE[0]/2,VIDEO_SIZE[1]/2), interpolation = cv2.INTER_AREA)
        cv2.imshow(winname, imgcombs)
    #ch = 0xFF & cv2.waitKey(1)



for s in range(len(TARGET_SIZE)):
    print "%5d|%s" % (TARGET_SIZE[s], graph_point(r[s], 40))

print "\nMaximal value: %f at target size %d" % (max_val, max_target)
