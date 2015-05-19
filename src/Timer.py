import pygame, time

class Timer(pygame.sprite.Sprite):
    # This is a pseudo-sprite. It does not have an image
    # nor rect. The sprite base is only used to keep it as
    # a part of a group
    def __init__(self, period, callback, start = False):
        pygame.sprite.Sprite.__init__(self)

        self.paused = True
        self.period = period
        self.callback = callback
        self.elapsed = 0
        
        if start:
            self.resume()

    def pause(self):
        self.paused = True
        
    def resume(self):
        self.paused = False
        self.lastt = time.time()

    def update(self):
        if self.paused:
            return False
            
        now = time.time()
        dt = now - self.lastt
        self.elapsed += dt
        self.lastt = now
        if (self.elapsed > self.period):
            # Timer expired
            self.pause()
            self.callback()
            self.kill()
