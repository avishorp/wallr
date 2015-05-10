import pygame, os.path
import time, sys, math
from animation import Animation
from WallrResources import RESOURCES
from ProgressBar import ProgressBar
from FuelGauge import FuelGauge

BACKGROUND_COLOR = (255, 255, 255) # White background
SCREEN_SIZE = (640, 480)
        

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
                                 self.progressBar.setProgress, 1.0, rate=10.0,
                                 callback=lambda: sys.stdout.write('ProgressBar animation done\n'))
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
