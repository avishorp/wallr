
class Rectangle:
    def __init__(self, xleft, ytop, xright, ybottom):
        self.xleft = xleft
        self.xright = xright
        self.ytop = ytop
        self.ybottom = ybottom
        
    def __repr__(self):
        return "((%d,%d),(%d,%d))" % (self.xleft, self.ytop, self.xright, self.ybottom)
