from WallrResources import RESOURCES
from WallrSettings import settings
import os.path, time

class NotConnectedError(Exception):
    def __init__(*args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class CarLink:
    def __init__(self, carfs):
        # Check the exsitance of all the required files in carfs
        self.fcontrol = file(os.path.join(carfs, 'control'))
        self.fnbattery = os.path.join(carfs, 'battery')
        self.fnconnected = os.path.join(carfs, 'connected')
        self.fnrunning = os.path.join(carfs, 'running')

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


if __name__=='__main__':
    carlink = CarLink('/car')
    while(True):
        c = carlink.isconnected()
        if c:
            print carlink.isrunning()
            print carlink.getbattery()
        else:
            print "Not connected"
        time.sleep(1)
