import pygame, os.path
import time, sys, math
from animation import Animation
from WallrResources import RESOURCES

BACKGROUND_COLOR = (255, 255, 255) # White background
SCREEN_SIZE = (640, 480)

class ProgressBar(pygame.sprite.Sprite):
    def __init__(self, width, height, num_divisions = 10, spacing = 3, 
                 inactive_color = (0, 64, 0), active_color = (0, 255, 0),
                 bg_color = (255, 255, 255)):
        self.size = (width, height)
        self.num_divisions = 10
        self.spacing = 3
        self.inactive_color = inactive_color
        self.active_color = active_color
        self.bg_color = bg_color

        self.progress = 0
        self.div = 1.0/self.num_divisions
        self.bar_width = width / num_divisions - spacing 

    def setProgress(self, progress):
        if progress < 0 or progress > 1.0:
            raise ValueError("Progress must be between 0 to 1")
        self.progress = progress
        
    def getProgress(self):
        return self.progress

    def draw(self):
        s = pygame.Surface(self.size)
        s.fill(self.bg_color)
        
        x = 0
        prg = 0
        for d in range(0, self.num_divisions):
            if prg <= self.progress:
                clr = self.active_color
            else:
                clr = self.inactive_color
                
            pygame.draw.rect(s, clr, 
                             pygame.Rect(x, 0, self.bar_width, self.size[1]))
            x += self.bar_width + self.spacing
            prg += self.div

        return s

class FuelGauge(pygame.sprite.Sprite):
    # Animation Types
    ANIMATION_LINEAR = 0
    ANIMATION_EXPONENTIAL = 1

    def __init__(self):
        pygame.sprite.Sprite.__init__(self)
        
        # Load the fuel gauge and needle images
        #self.gauge = self.image.load(getResFilename("fuel_gauge.png"))
        self.gauge = RESOURCES['fuel_gauge']
        self.needle = RESOURCES['needle']
        
        self.setFuelLevel(0)
        self.currentAnimation = None
        self.animations = []
        self.defaultAnimation = None

    def draw(self, now):
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
        r = self.gauge.get_rect()
        self.surface = pygame.Surface(r.size)
        self.surface.set_colorkey((255,255,255))
        self.surface.fill((255,255,255))
        self.surface.blit(self.gauge.image, (0,0))

        # Rotate the needle
        n = pygame.transform.rotate(self.needle.image, self.angle)
        
        # Put the needle on the background
        c = self.gauge.image.get_rect().center
        self.surface.blit(n, (self.gauge.needle_pos[0]-n.get_rect().width,self.gauge.needle_pos[1]-n.get_rect().height))

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
        

class WallrGame(object):
    def __init__(self):
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        pygame.draw.rect(self.screen, BACKGROUND_COLOR, 
                         pygame.Rect(0, 0, SCREEN_SIZE[0], SCREEN_SIZE[1]))
        
        self.fuelGauge = FuelGauge()
        self.fuelGauge.setFuelLevel(0)
        self.fuelGauge.animateToFuelLevel(100, self.s1, type=FuelGauge.ANIMATION_EXPONENTIAL)
        
        self.progressBar = ProgressBar(10*13, 30)
        self.progressBar.setProgress(0)
        self.pa = Animation(self.progressBar, self.progressBar.getProgress,
                                 self.progressBar.setProgress, 1.0, rate=1.0)
        self.pa.start()

        self.sprites = pygame.sprite.RenderPlain((self.fuelGauge))

    def s1(self):
        sys.stdout.write("Animation 1 done\n")
        self.fuelGauge.setConstantRate(5, lambda: sys.stdout.write("Constant rate done"))

    def start(self):
        self.run()
        
    def run(self):
        self.running = True
        t0 = time.time()
        x = 0
        flg = False
        while self.running:
            event = pygame.event.poll()
            if event.type == pygame.QUIT:
                self.running = False

            pygame.draw.rect(self.screen, BACKGROUND_COLOR, 
                         pygame.Rect(0, 0, SCREEN_SIZE[0], SCREEN_SIZE[1]))
            
            now = time.time()
            if (((now - t0) > 8) and (not flg)):
                print "+10"
                self.fuelGauge.animateToFuelLevel(self.fuelGauge.getFuelLevel() + 10,
                                                  lambda: sys.stdout.write("Animation 2 done\n"),
                                                  type=FuelGauge.ANIMATION_LINEAR,
                                                  rate=220)
                flg = True
            self.fuelGauge.draw(now)
            self.screen.blit(self.fuelGauge.surface, (0,0))

            p = self.progressBar.draw()
            self.pa.nextValue(time.time())
            self.screen.blit(p, (100,100))
            #self.sprites.draw(self.screen)
            pygame.display.flip()

if __name__=='__main__':
    game = WallrGame()
    game.start()
