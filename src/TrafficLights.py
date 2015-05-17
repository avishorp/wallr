import pygame, time
from WallrResources import RESOURCES


class TrafficLights(pygame.sprite.Sprite):
    def __init__(self, position, dt = [1.5, 1.5, 0.5]):
        pygame.sprite.Sprite.__init__(self)
        self.img = [
            RESOURCES['red'].image,
            RESOURCES['red_yellow'].image,
            RESOURCES['green'].image
            ]
        self.rect = pygame.Rect(position, self.img[0].get_size())
        self.dt = dt
        self.state = 0
    
    def start(self):
        self.t0 = time.time()
        self.image = self.img[0]
        self.active = True
        self.state = 0

    def update(self):
        if not self.active:
            return None

        t = time.time()
        t0 = self.t0

        if ((t - t0) > self.dt[self.state]):
            # Next state
            self.t0 = t
            self.state += 1

            if self.state > 2:
                self.active = False
                self.kill()
            else:
                self.image = self.img[self.state]
