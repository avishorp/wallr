import GameResource

# TODO: Make this more robust
RESOURCE_DIR = "../res"

GameResource.setResourceBaseDir(RESOURCE_DIR)

RESOURCES = {
    'fuel_gauge': GameResource.ImageResource('fuel_gauge.png', center=(100, 100),
                                keycolor = (255,255,255),
                                needle_pos = (132, 137)),
    'needle': GameResource.ImageResource('needle.png', 
                            center = (105, 4), keycolor = (255, 255, 255))
}

