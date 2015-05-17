import pygame, time
from WallrResources import RESOURCES

class StaticSprite(pygame.sprite.Sprite):
    def __init__(self, image, position):
        pygame.sprite.Sprite.__init__(self)

        self.image = image
        self.setPosition(position)

    def setPosition(self, pos):
        self.rect = pygame.Rect(pos, self.image.get_size())
