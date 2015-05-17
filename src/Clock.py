import pygame, time
from WallrResources import RESOURCES, SETTINGS

class Clock(pygame.sprite.Sprite):
    def __init__(self, pos):
        pygame.sprite.Sprite.__init__(self)
        self.reset()
        self.font = pygame.font.Font(RESOURCES['clock_font'].filename, 34)
        
        size = self.font.size("88:88:88")
        self.image = pygame.Surface(size)
        self.rect = pygame.Rect(pos, size)

        self.pause()

    def reset(self):
        self.elapsed = 0
        self.last = time.time()
        
    def pause(self):
        self.paused = True

    def resume(self):
        self.last = time.time()
        self.paused = False

    def update(self):
        if not self.paused:
            now = time.time()
            dt = now - self.last
            self.last = now
            self.elapsed += dt

        t = self.elapsed
        minute = int(t) / 60
        sec = int(t - minute*60)
        tenths = int((t - int(t))*100)
        ts = "%02d:%02d:%02d" % (minute, sec, tenths)
        ci = self.font.render(ts, True, (0,0,0))
        self.image.fill((255,255,255))
        self.image.blit(ci, (0, 0))
