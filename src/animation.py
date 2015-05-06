
import time
import traceback

# Generalized animation class
class Animation:
    def __init__(self, obj, getter, setter, final, rate, exponent=0.0, callback=None):
        self.final = final
        self.baseRate = rate
        self.rate = self.baseRate
        self.exponent = exponent
        self.destObject = obj
        self.destGetter = getter
        self.destSetter = setter
        self.callback = callback
        
    def start(self):
        self.startPoint = self.destGetter()
        self.startTime = time.time()
        self.directionUp = self.final > self.startPoint
        self.range = abs(self.final - self.startPoint)
        #print "Starting: from %d to %d" % (self.startPoint, self.final)
        #for line in traceback.format_stack():
        #    print line.strip()

    def nextValue(self, now):
        dt = now - self.startTime
        r = dt*(self.rate/100.0)
        l = self.startPoint + (self.final - self.startPoint)*r
        rel = l/self.range
        if not self.directionUp:
            rel = 1 - rel
        self.rate = self.baseRate*(1 +rel*self.exponent)

        #print "%f %f %f %f %f %d" % (now, dt, self.rate, r, rel, l)
  
        # Determine end condition
        finish = (self.directionUp and (l >= self.final)) or (not self.directionUp and (l <= self.final))
        if finish:
            l = self.final
            if self.callback is not None:
                self.callback()
            
        # Set the destination attribute
        self.destSetter(l)

        return (l, finish)
