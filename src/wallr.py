import pygame, os.path
import time, sys, math

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


class NeedleAnimation:
    def __init__(self, final, rate, exponent):
        self.final = final
        self.baserate = rate
        self.rate = self.baserate
        self.exponent = exponent
        
    def setStartingPoint(self, stp, stt):
        self.startPoint = stp
        self.startTime = stt
        self.directionUp = self.final > self.startPoint
        
    def nextValue(self, now):
        dt = now - self.startTime
        r = dt*(self.rate/100.0)
        l = self.startPoint + (self.final - self.startPoint)*r
        print "%f %f %f %f %d" % (now, dt, self.rate, r, l)

        if self.exponent is not None:
            self.rate = math.pow(self.baserate, (r+1)*self.exponent)
        else:
            self.rate = self.baserate

        # Determine end condition
        finish = (self.directionUp and (l >= self.final)) or (not self.directionUp and (l <= self.final))
        if finish:
            l = self.final
        return (l, finish)

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

    def draw(self, now):
        # Apply animation
        if self.currentAnimation is not None:
            # An animation is in effect, let it dictate the fuel level
            l, finish = self.currentAnimation[0].nextValue(now)
            self.setFuelLevel(l)
            if finish:
                cb = self.currentAnimation[1]
                if cb is not None:
                    # Kick the callback
                    cb()
                self.currentAnimation = None

        else:
            if len(self.animations) > 0:
                self.currentAnimation = self.animations.pop(0)
                self.currentAnimation[0].setStartingPoint(self.level, now)


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
        
    def animateToFuelLevel(self, l, callback = None, rate = 20.0, type = ANIMATION_LINEAR):
        if l < 0 or l > 100:
            raise ValueError("Fuel level must be betweeb 0 to 100")

        if type == FuelGauge.ANIMATION_LINEAR:
            anim = NeedleAnimation(l, rate, None)
        else:
            anim = NeedleAnimation(l, rate, 0.995)
        
        self.animations.append((anim, callback))
        
    def update(self):
        pass
        

class WallrGame(object):
    def __init__(self):
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        pygame.draw.rect(self.screen, BACKGROUND_COLOR, 
                         pygame.Rect(0, 0, SCREEN_SIZE[0], SCREEN_SIZE[1]))
        
        self.fuelGauge = FuelGauge()
        self.fuelGauge.setFuelLevel(0)
        self.fuelGauge.animateToFuelLevel(100, lambda: sys.stdout.write("Animation 1 done\n"),
                                          type=FuelGauge.ANIMATION_LINEAR)
        self.fuelGauge.animateToFuelLevel(0, lambda: sys.stdout.write("Animation 2 done\n"),
                                          type=FuelGauge.ANIMATION_EXPONENTIAL)
        self.fuelGauge.animateToFuelLevel(50, lambda: sys.stdout.write("Animation 3 done\n"),
                                          type=FuelGauge.ANIMATION_EXPONENTIAL)
        self.sprites = pygame.sprite.RenderPlain((self.fuelGauge))


    def start(self):
        self.run()
        
    def run(self):
        self.running = True
        x = 0
        while self.running:
            event = pygame.event.poll()
            if event.type == pygame.QUIT:
                self.running = False

            pygame.draw.rect(self.screen, BACKGROUND_COLOR, 
                         pygame.Rect(0, 0, SCREEN_SIZE[0], SCREEN_SIZE[1]))
            
            now = time.time()
            self.fuelGauge.draw(now)
            self.screen.blit(self.fuelGauge.surface, (0,0))
            #self.sprites.draw(self.screen)
            pygame.display.flip()

if __name__=='__main__':
    game = WallrGame()
    game.start()
