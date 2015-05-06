import os.path
import pygame

RESOURCE_DIR='.'

def setResourceBaseDir(rd):
    globals()['RESOURCE_DIR'] = rd

class Resource(object):
    def __init__(self, filename, **kwargs):
        self.filename = os.path.join(RESOURCE_DIR, filename)
        for k in kwargs:
            setattr(self, k, kwargs[k])

class ImageResource(Resource):
    def __init__(self, filename, center=None, colorkey=None, **kwargs):
        # Call parent to process generic parameters
        super(ImageResource, self).__init__(filename, **kwargs)
        
        # Load the resource
        self.image = pygame.image.load(self.filename)
        if center is not None:
            self.image.get_rect().center = center

        if colorkey is not None:
            self.image.set_colorkey(colorkey)
            
    def get_rect(self):
        return self.image.get_rect()
