import GameResource

# TODO: Make this more robust
RESOURCE_DIR = "../res"

GameResource.setResourceBaseDir(RESOURCE_DIR)

RESOURCES = {
    'logo': GameResource.ImageResource('logo.png', keycolor = (255, 255, 255)),
    'fuel_gauge': GameResource.ImageResource('fuel_gauge.png', center=(100, 100),
                                keycolor = (255,255,255),
                                needle_pos = (132, 137)),
    'needle': GameResource.ImageResource('needle.png', 
                            center = (105, 4), keycolor = (255, 255, 255)),
    'red': GameResource.ImageResource('tl_red.png'),
    'red_yellow': GameResource.ImageResource('tl_red_yellow.png'),
    'green': GameResource.ImageResource('tl_green.png'),
    'clock_font': GameResource.Resource('DS-DIGI.TTF')
}

SETTINGS = {
    'screen_size': (640, 480),
    'background_color': (255, 255, 255),
    'lock_rect': (640/2-50, 60, 100, 100),
}

