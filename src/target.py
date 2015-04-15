
# This module defines the tracking target. It defines a class, TrackingTarget
# that generates an image of the tracking target for a desired size. The
# image can be later accessed
#
# The module can also be used for viewing and generating the target as
# an image file from the command line:
#
#   python target.py [--size=<size>] [-d|--draw] [--output-file=<filename>]
#
#     size - The size of the target (in Pixels)
#     draw - Draw the target on screen. If no filename is specified, the
#            target is always drawn
#     output-file - The name of the file to which the image is written

import cv2, numpy
import sys, getopt

class TrackingTarget:
    def __init__(self, size):
        # Create an empty image
        self.img = numpy.ones([size,size], dtype=numpy.uint8)*255
        cv2.randn(self.img, 128, 128)
        
        # Draw the target
        cc = size/2
        r1 = cc - 1
        r2 = cc*2/3
        r3 = cc/3
        center = (cc, cc)
        cv2.circle(self.img, center, r1, 0, cv2.cv.CV_FILLED)
        cv2.circle(self.img, center, r2, 255, cv2.cv.CV_FILLED)
        cv2.circle(self.img, center, r3, 0, cv2.cv.CV_FILLED)
        
    def getImage(self):
        return self.img


if __name__ == "__main__":
    # Parse the command line arguments
    opts, args = getopt.getopt(sys.argv[1:], "d", 
                               ["size=","output-file=","draw"])
    
    opt_draw = False
    opt_filename = None
    opt_size = 30

    for o, a in opts:
        if o == '-d' or o == '--draw':
            opt_draw = True

        if o == '--size':
            opt_size = int(a)
            
        if o == '--output-file':
            opt_filename = a

    # If no output file specified, defult to draw
    if opt_filename is None:
        opt_draw = True

    # Create the target
    target = TrackingTarget(opt_size)
    
    # If required, write an output file
    if opt_filename is not None:
        cv2.imwrite(opt_filename, target.getImage())
        
    # If required, draw the target
    if opt_draw:
        cv2.imshow('capture', target.getImage())
        ch = 0xFF & cv2.waitKey(0)


