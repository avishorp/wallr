import pygame, time
from WallrResources import RESOURCES, SETTINGS

def timeToMMSSTT(t):
    minute = int(t) / 60
    sec = int(t - minute*60)
    tenths = int((t - int(t))*100)
    return "%02d:%02d:%02d" % (minute, sec, tenths)

class Clock(pygame.sprite.Sprite):
    def __init__(self, pos):
        pygame.sprite.Sprite.__init__(self)
        self.reset()
        self.font = pygame.font.Font(RESOURCES['clock_font'].filename, 34)
        
        size = self.font.size("88:88:88")
        self.image = pygame.Surface(size)
        self.rect = pygame.Rect(pos, size)
        self.allsegs = False

        self.pause()

    def reset(self):
        self.elapsed = 0
        self.last = time.time()
        
    def pause(self):
        self.paused = True

    def resume(self):
        self.last = time.time()
        self.paused = False

    def allSegments(self, v):
        self.allsegs = v

    def update(self):
        if not self.paused:
            now = time.time()
            dt = now - self.last
            self.last = now
            self.elapsed += dt

        if self.allsegs:
            ts = "88:88:88"
        else:
            ts = timeToMMSSTT(self.elapsed)

        ci = self.font.render(ts, True, (0,0,0))
        self.image.fill((255,255,255))
        self.image.blit(ci, (0, 0))

    def getTime(self):
        return self.elapsed
