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
    'game_over_font': GameResource.Resource('RPGSystem.ttf'),
    'car_nocomm': GameResource.ImageResource('car_nocomm.png'),
    'car_norun': GameResource.ImageResource('car_norun.png'),
    'car_battery1': GameResource.ImageResource('car_battery1.png'),
    'car_battery2': GameResource.ImageResource('car_battery2.png'),
    'car_battery3': GameResource.ImageResource('car_battery3.png'),
    'car_battery4': GameResource.ImageResource('car_battery4.png'),
    'car_battery5': GameResource.ImageResource('car_battery5.png')

}
