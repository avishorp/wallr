from WallrResources import RESOURCES
from WallrSettings import settings, get_section
import os.path, time
import pygame

CAR_QUERY_RATE = 0.3
BATTERY_THRSH = [ 145, 141, 137, 133 ]

class NotConnectedError(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class CarLink:
    def __init__(self, carfs, joystick_num = 0):
        self.last_update_time = 0
        self.status = 'nocomm'
        
        # Check the exsitance of all the required files in carfs
        self.fcontrol = file(os.path.join(carfs, 'control'), 'w')
        self.fnbattery = os.path.join(carfs, 'battery')
        self.fnconnected = os.path.join(carfs, 'connected')
        self.fnrunning = os.path.join(carfs, 'running')

        # Initialize the Joystick
        pygame.joystick.init()
        self.joystick = pygame.joystick.Joystick(0)
        self.joystick.init()

        # Get the Joystick settings
        jname = self.joystick.get_name()
        print "Using joystick: " + jname
        s = get_section('joystick:' + jname)
        if s is None:
            raise Exception('Cannot find joystick mapping in INI file for "%s"' % jname)
        
        self.axis_speed = int(s['speed'])
        self.axis_rotation = int(s['rotation'])
        self.button_start = int(s['start'])
        self.button_forceacq = int(s['force acq'])
        self.deadzone = float(s['deadzone'])
        #self.speedinv = 

    def update(self):

        if (time.time()-self.last_update_time) > CAR_QUERY_RATE:
            self.last_update_time = time.time()
            conn = self.isconnected()
            if conn:
                try:
                    run = self.isrunning()
                    if run:
                        bat = self.getbattery()
                        if bat > BATTERY_THRSH[0]:
                            self.status = 'battery5'
                        elif bat > BATTERY_THRSH[1]:
                            self.status = 'battery4'
                        elif bat > BATTERY_THRSH[2]:
                            self.status = 'battery3'
                        elif bat > BATTERY_THRSH[3]:
                            self.status = 'battery2'
                        else:
                            self.status = 'battery1'
                    else:
                        self.status = 'norun'

                except NotConnectedError:
                    self.status = 'nocomm'
            else:
                self.status = 'nocomm'

            print "Status: " + self.status
            return True
        else:
            # No update was done
            return False

    def isconnected(self):
        fconnected = file(self.fnconnected, 'r')
        data = fconnected.read().strip()
        fconnected.close()

        if data == '0':
            return False
        elif data == '1':
            return True
        else:
            raise Exception("Unknown value")


    def isrunning(self):
        frunning = file(self.fnrunning, 'r')
        data = frunning.read().strip()
        frunning.close()

        if data == '0':
            return False
        elif data == '1':
            return True
        elif data == 'not_connected':
            raise NotConnectedError
        else:
            raise Exception("Unknown value")

    def getbattery(self):
        fbattery = file(self.fnbattery, 'r')
        data = fbattery.read().strip()
        fbattery.close()

        if data == 'not_connected':
            raise NotConnectedError
        else:
            return int(data)

    def getstatus(self):
        return self.status

    def getsprite(self, pos):
        return CarStatusSprite(pos, self)

    def move(self, speed = 0, rotation = 0):
        self.fcontrol.write("@%d,%d\n" % (speed, rotation))
        self.fcontrol.flush()
        
    def update_axes(self):
        speed = self.joystick.get_axis(self.axis_speed)
        if abs(speed) < self.deadzone:
            speed = 0
        rotation = self.joystick.get_axis(self.axis_rotation)
        if abs(rotation) < self.deadzone:
            rotation = 0
        self.move(int(speed*32), int(rotation*32))

class CarStatusSprite(pygame.sprite.Sprite):
    def __init__(self, pos, carlink):
        pygame.sprite.Sprite.__init__(self)
        self.carlink = carlink
        
        self.icons = {
            'nocomm': RESOURCES['car_nocomm'].image,
            'norun': RESOURCES['car_norun'].image,
            'battery1': RESOURCES['car_battery1'].image,
            'battery2': RESOURCES['car_battery1'].image,
            'battery3': RESOURCES['car_battery1'].image,
            'battery4': RESOURCES['car_battery1'].image,
            'battery5': RESOURCES['car_battery1'].image }
        self.image = self.icons['nocomm']
        self.rect = pygame.Rect(pos, self.icons['nocomm'].get_size())

    def pause(self):
        pass

    def resume(self):
        pass

    def update(self):
        if self.carlink.update():
            st = self.carlink.getstatus()
            if st!='nocomm':
                print "bat %d %d" % (time.time(), self.carlink.getbattery())
            self.image = self.icons[st]


if __name__=='__main__':
    pygame.init()
    size = [100, 100]
    screen = pygame.display.set_mode(size)
    background = pygame.Surface(size)
    background.fill((255,255,255))

    carlink = CarLink('/car')
    p = 0

    g = pygame.sprite.RenderUpdates([ carlink.getsprite((5,5)) ])

    done = False
    while done == False:
        for event in pygame.event.get(): # User did something
            if event.type == pygame.QUIT: # If user clicked close
                done=True # Flag that we are done so we exit this loop
            if event.type == pygame.JOYAXISMOTION:
                print carlink.joystick.get_axis(0)
                carlink.update_axes()

        g.update()
        g.clear(screen, background)
        updates = g.draw(screen)
        pygame.display.update(updates)


