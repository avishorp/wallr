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
    'fuel_x1': GameResource.ImageResource('fuel_x1.png'),
    'green': GameResource.ImageResource('tl_green.png'),
    'gameover': GameResource.ImageResource('game-over.jpg'),
    'clock_font': GameResource.Resource('DS-DIGI.TTF'),
    'game_over_image': GameResource.ImageResource('game_over_img.jpg'),
    'game_over_font': GameResource.Resource('RPGSystem.ttf')
}
