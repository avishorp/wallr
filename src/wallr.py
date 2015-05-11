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
        pygame.init()
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        
        self.background = pygame.Surface(SCREEN_SIZE)
        self.background.fill(BACKGROUND_COLOR)
        #pygame.draw.rect(self.background, BACKGROUND_COLOR, 
        #                 pygame.Rect(0, 0, SCREEN_SIZE[0], SCREEN_SIZE[1]))

        self.fuelGauge = FuelGauge((0,0))
        self.fuelGauge.setFuelLevel(0)
        self.fuelGauge.animateToFuelLevel(100, self.s1, type=FuelGauge.ANIMATION_EXPONENTIAL)
        
        self.progressBar = ProgressBar(10*13, 30, (200, 280))
        self.progressBar.setProgress(0)
        self.pa = Animation(self.progressBar, self.progressBar.getProgress,
                                 self.progressBar.setProgress, 1.0, rate=10.0,
                                 callback=lambda: sys.stdout.write('ProgressBar animation done\n'))
        self.pa.start()

        self.sprites = pygame.sprite.RenderUpdates()
        self.sprites.add(self.fuelGauge)
        self.sprites.add(self.progressBar)

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

        self.screen.blit(self.background, (0,0))
        pygame.display.update()

        while self.running:
            event = pygame.event.poll()
            if event.type == pygame.QUIT:
                self.running = False

            now = time.time()
            if (((now - t0) > 8) and (not flg)):
                print "+10"
                self.fuelGauge.animateToFuelLevel(self.fuelGauge.getFuelLevel() + 10,
                                                  lambda: sys.stdout.write("Animation 2 done\n"),
                                                  type=FuelGauge.ANIMATION_LINEAR,
                                                  rate=220)
                flg = True


            self.pa.nextValue(time.time())
            
            self.sprites.update()
            self.sprites.clear(self.screen, self.background)
            updates = self.sprites.draw(self.screen)
            pygame.display.update(updates)

if __name__=='__main__':
    game = WallrGame()
    game.start()
