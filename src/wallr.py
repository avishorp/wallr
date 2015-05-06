import pygame, os.path
import time, sys, math
from animation import Animation

BACKGROUND_COLOR = (255, 255, 255) # White background
SCREEN_SIZE = (640, 480)
RESOURCE_DIR = "../res"

class Resource(object):
    def __init__(self, path, filename, **kwargs):
        self.filename = os.path.join(path, filename)
        for k in kwargs:
            setattr(self, k, kwargs[k])

class ImageResource(Resource):
    def __init__(self, path, filename, center=None, colorkey=None, **kwargs):
        # Call parent to process generic parameters
        super(ImageResource, self).__init__(path, filename, **kwargs)
        
        # Load the resource
        self.image = pygame.image.load(self.filename)
        if center is not None:
            self.image.get_rect().center = center

        if colorkey is not None:
            self.image.set_colorkey(colorkey)
            
    def get_rect(self):
        return self.image.get_rect()

RESOURCES = {
    'fuel_gauge': ImageResource(RESOURCE_DIR, 'fuel_gauge.png', center=(100, 100),
                                keycolor = (255,255,255),
                                needle_pos = (132, 137)),
    'needle': ImageResource(RESOURCE_DIR, 'needle.png', 
                            center = (105, 4), keycolor = (255, 255, 255))
}


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
        #self.fuelGauge.animateToFuelLevel(0, lambda: sys.stdout.write("Animation 2 done\n"),
        #                                  type=FuelGauge.ANIMATION_EXPONENTIAL)
        #self.fuelGauge.animateToFuelLevel(50, lambda: sys.stdout.write("Animation 3 done\n"),
        #                                  type=FuelGauge.ANIMATION_EXPONENTIAL)
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
            #self.sprites.draw(self.screen)
            pygame.display.flip()

if __name__=='__main__':
    game = WallrGame()
    game.start()
