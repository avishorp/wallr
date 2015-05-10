import pygame

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
