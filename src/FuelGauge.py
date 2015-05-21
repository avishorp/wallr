import pygame
from WallrResources import RESOURCES
from animation import Animation
import time

class FuelGauge(pygame.sprite.Sprite):
    # Animation Types
    ANIMATION_LINEAR = 0
    ANIMATION_EXPONENTIAL = 1

    def __init__(self, position, bgcolor = (255, 255, 255)):
        pygame.sprite.Sprite.__init__(self)

        self.paused = False

        # Load the fuel gauge and needle images
        #self.gauge = self.image.load(getResFilename("fuel_gauge.png"))
        self.gauge = RESOURCES['fuel_gauge']
        self.needle = RESOURCES['needle']

        self.bgcolor = bgcolor
        
        # The sprite is located at a constant position and its size
        # remains constant as well
        self.rect = pygame.Rect(position, self.gauge.get_rect().size)
        self.image = pygame.Surface(self.gauge.get_rect().size)
        self.image.set_colorkey((255,255,255))
        # Initial draw
        self.image.fill(self.bgcolor)
        self.image.blit(self.gauge.image, (0,0))
        
        self.setFuelLevel(0)
        self.currentAnimation = None
        self.animations = []
        self.defaultAnimation = None
        self.update = self.updatex

    def updatex(self):
        if self.paused:
            return
        now = time.time()

        # Apply animation
        if self.currentAnimation is not None:
            # An animation is in effect, let it dictate the fuel level
            l, finish = self.currentAnimation.nextValue(now)
            if finish:
                self.currentAnimation = None

        else:
            if len(self.animations) > 0:
                self.currentAnimation = self.animations.pop(0)
                self.currentAnimation.start()
            else:
                # No animation in queue
                if self.defaultAnimation is not None:
                    # (re)start default animation
                    self.currentAnimation = self.defaultAnimation
                    self.defaultAnimation.start()

        # Copy the background image to a new surface
        self.image.fill(self.bgcolor)
        self.image.blit(self.gauge.image, (0,0))

        # Rotate the needle
        n = pygame.transform.rotate(self.needle.image, self.angle)
        
        # Put the needle on the background
        c = self.gauge.image.get_rect().center
        self.image.blit(n, (self.gauge.needle_pos[0]-n.get_rect().width,self.gauge.needle_pos[1]-n.get_rect().height))

    def setFuelLevel(self, l):
        if l < 0 or l > 100:
            raise ValueError("Fuel level must be betweeb 0 to 100")
            
        self.angle = -90.0/100.0*l
        self.level = l

    def getFuelLevel(self):
        return self.level

    def animateToFuelLevel(self, l, callback = None, rate = 70.0, type = ANIMATION_LINEAR):
        if l < 0 or l > 100:
            raise ValueError("Fuel level must be betweeb 0 to 100")

        if type == FuelGauge.ANIMATION_LINEAR:
            anim = Animation(self, self.getFuelLevel, self.setFuelLevel, l, 
                             rate, callback = callback)
        else:
            anim = Animation(self, self.getFuelLevel, self.setFuelLevel, l, 
                             rate, -0.5, callback = callback)
        
        self.animations.append(anim)
        
        # If the default animation is running, pause it in favour
        # of the new animation
        if self.currentAnimation == self.defaultAnimation:
            self.currentAnimation = None

    def setConstantRate(self, rate, callback):
        self.defaultAnimationCallback = callback
        self.defaultAnimation = Animation(self, self.getFuelLevel, self.setFuelLevel, 0,
                                          rate, callback=self._constantRateDone)
        if self.currentAnimation is not None:
            self.currentAnimation = self.defaultAnimation
            self.defaultAnimation.start()

    def _constantRateDone(self):
        self.defaultAnimation = None
        self.defaultAnimationCallback()

    def update(self):
        pass

    def pause(self):
        self.paused = True
        if self.currentAnimation is not None:
            self.currentAnimation.pause()

    def resume(self):
        print "resume **************************************"
        self.paused = False
        if self.currentAnimation is not None:
            self.currentAnimation.resume()

    def fillTank(self, cb):
        self.animateToFuelLevel(100, cb, type=FuelGauge.ANIMATION_EXPONENTIAL)

    def addFuel(self, amount, callback = None):
        # Calc the new fuel amount
        d = self.getFuelLevel() + amount
        
        # Clip it
        d = max(min(d, 100), 1)
        print "Addfuel: %d" % d
        if d == 0:
            cb = self.outOfFuelCallback()
        else:
            cb = callback
            
        an = self.animateToFuelLevel(d, cb, type=FuelGauge.ANIMATION_LINEAR,
                                     rate = 100.0)

    def outOfFuelCallback(self):
        print "Out of fuel"
        pass
