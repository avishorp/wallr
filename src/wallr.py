import pygame, os.path

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


class FuelGauge(pygame.sprite.Sprite):
    def __init__(self):
        pygame.sprite.Sprite.__init__(self)
        
        # Load the fuel gauge and needle images
        #self.gauge = self.image.load(getResFilename("fuel_gauge.png"))
        self.gauge = RESOURCES['fuel_gauge']
        self.needle = RESOURCES['needle']
        
        self.setFuelLevel(0)

    def draw(self):
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
        
    def update(self):
        pass
        

class WallrGame(object):
    def __init__(self):
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        pygame.draw.rect(self.screen, BACKGROUND_COLOR, 
                         pygame.Rect(0, 0, SCREEN_SIZE[0], SCREEN_SIZE[1]))
        
        self.fuelGauge = FuelGauge()
        self.fuelGauge.setFuelLevel(100)
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
            
            self.fuelGauge.draw()
            self.screen.blit(self.fuelGauge.surface, (0,0))
            #self.sprites.draw(self.screen)
            pygame.display.flip()

if __name__=='__main__':
    game = WallrGame()
    game.start()
