from WallrResources import RESOURCES
from WallrSettings import settings, get_section
import os.path, time
import pygame


class NotConnectedError(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class CarLink:
    def __init__(self, carfs, joystick_num = 0):
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

if __name__=='__main__':
    pygame.init()
    size = [100, 100]
    screen = pygame.display.set_mode(size)
    carlink = CarLink('/car')
    p = 0

    done = False
    while done == False:
        for event in pygame.event.get(): # User did something
            if event.type == pygame.QUIT: # If user clicked close
                done=True # Flag that we are done so we exit this loop
            if event.type == pygame.JOYAXISMOTION:
                print carlink.joystick.get_axis(0)
                carlink.update_axes()

        if p==30:
            p = 0
            c = carlink.isconnected()
            if c:
                print carlink.isrunning()
                print carlink.getbattery()
            else:
                print "Not connected"

        p += 1
