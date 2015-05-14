import sys, time, os
import TrackerLogPlayer as tracker
import pygame, Queue
from WallrResources import RESOURCES, SETTINGS
from ProgressBar import ProgressBar
from FuelGauge import FuelGauge


class WallrLockMode(object):
    def __init__(self, screen, background):
        self.screen = screen
        self.background = background
        self.progress = ProgressBar(130, 30,
                                    (255, 250))
        self.widgets = pygame.sprite.RenderUpdates([self.progress])

    def create(self):
        self.image = pygame.Surface(self.screen.get_size())

        # Clear the screen
        self.image.blit(self.background, (0,0))
        # Draw the "lock rectangle"
        pygame.draw.rect(self.image, (255,0,0),
                         pygame.Rect(SETTINGS['lock_rect']), 10)
        # Draw the text
        fontname = pygame.font.match_font('sans')
        font = pygame.font.Font(fontname, 34)
        text = "Please place the tank in the rectangle"
        st = font.render(text, True, (0,0,0))
        self.image.blit(st, (self.screen.get_width()/2-st.get_width()/2, 200))
        # Logo
        logo = RESOURCES['logo']
        self.image.blit(logo.image, (self.screen.get_width()/2-logo.get_rect().width/2, 320))

    def resume(self):
        # Clear the progress bar
        self.progress.setProgress(0)

        # Draw the initial screen
        self.screen.blit(self.image, (0,0))
        pygame.display.update()
        self.active = True
        
    def pause(self):
        pass

    def trackerMessage(self, msg, params):
        if msg == tracker.MSG_LOCK_PROGRESS:
            self.progress.setProgress(params)
        if msg == tracker.MSG_SWITCH_TO_LOCK:
            print "Deactivating lock"
            self.active = False

    def loop(self):
        if not self.active:
            return False
            
        # Update and draw the progress bar
        self.widgets.update()
        self.widgets.clear(self.screen, self.background)
        updates = self.widgets.draw(self.screen)
        pygame.display.update(updates)
        
        return True

class WallrGameMode(object):
    MODE_RED = 0
    MODE_YELLOW = 1
    MODE_GREEN = 2
    MODE_PLAY = 3

    def __init__(self, screen, background):
        self.screen = screen
        self.background = background
        self.mode = WallrGameMode.MODE_RED
        self.clear = []

    def create(self):
        self.fuelGauge = FuelGauge((0,0))
        self.widgets = pygame.sprite.RenderUpdates([self.fuelGauge])
        self.location = None
        self.prevLocation = None
          
    def pause(self):
        pass

    def resume(self):
        print "Resume game"
        self.screen.blit(self.background, (0,0))
        pygame.display.update()

        self.active = True

    def trackerMessage(self, msg, param):
        print "WallrGame trackerMessage"
        if msg == tracker.MSG_SWITCH_TO_ACQ:
            print "Switch back"
            self.active = False
        if msg == tracker.MSG_COORDINATES:
            self.prevLocation = self.location
            self.location = (int(param['x'])/2, int(param['y'])/2)
        
    def loop(self):
        if not self.active:
            return False

        updates = []
        while len(self.clear) > 0:
            r = self.clear.pop()
            pygame.draw.rect(self.screen, (255,255,255), r, 0)
            updates.append(r)
            
        if self.location is not None:
            r = pygame.draw.circle(self.screen, (0,0,255), self.location, 20, 2)
            updates.append(r)
            self.clear.append(r)

        pygame.display.update(updates)
        return True


# This is the main game class for Wallr.
# The main class implements the two major modes:
#   - LOCK mode - In which the user is requested to put the car
#                 in a specific place so the tracker can lock
#                 onto it.
#   - GAME mode - The game itself.
class WallrMain(object):
    MODE_LOCK = 0
    MODE_GAME = 1

    def __init__(self):
        self.mode = WallrMain.MODE_LOCK

        # Instantiate a tracker and connect it to the
        # local callback
        self.trkMessages = Queue.Queue()
        self.trk = tracker.TrackerLogPlayer('tracker.log', self.trackerCallback)
        self.trk.start()


        # Initialize PyGame and create a screen and a background
        pygame.init()
        self.init_display()
        self.screen = pygame.display.set_mode(SETTINGS['screen_size'])
        self.background = pygame.Surface(SETTINGS['screen_size'])
        self.background.fill(SETTINGS['background_color'])
        
        self.modeLock = WallrLockMode(self.screen, self.background)
        self.modeGame = WallrGameMode(self.screen, self.background)

        self.create()

    def init_display(self):
        "Ininitializes a new pygame screen using the framebuffer"
        # Based on "Python GUI in Linux frame buffer"
        # http://www.karoltomala.com/blog/?p=679
        disp_no = os.getenv("DISPLAY")
        if disp_no:
            print "I'm running under X display = {0}".format(disp_no)
        else:
            # Check which frame buffer drivers are available
            # Start with fbcon since directfb hangs with composite output
            drivers = ['fbcon', 'directfb', 'svgalib']
            found = False
            for driver in drivers:
                # Make sure that SDL_VIDEODRIVER is set
                if not os.getenv('SDL_VIDEODRIVER'):
                    os.putenv('SDL_VIDEODRIVER', driver)
                    try:
                        pygame.display.init()
                    except pygame.error:
                        print 'Driver: {0} failed.'.format(driver)
                        continue
                    found = True
                    break

    def trackerCallback(self, msg, params):
        # Synchronize the tracker messages through a queue
        self.trkMessages.put((msg, params))

    def create(self):
        self.modeLock.create()
        self.modeGame.create()

    def start(self):
        self.running = True
        self.modeLock.resume()

        while self.running:
            event = pygame.event.poll()
            if event.type == pygame.QUIT:
                self.running = False

            if self.mode == WallrMain.MODE_LOCK:
                cm = self.modeLock
            else:
                cm = self.modeGame

            # Check if a message is available on the queue
            # from the tracker
            if not self.trkMessages.empty():
                m = self.trkMessages.get()
                cm.trackerMessage(*m)

            if not cm.loop():
                print "Switch mode"
                # Switch mode
                cm.pause()

                if self.mode == WallrMain.MODE_LOCK:
                    print "Switch to game"
                    self.mode = WallrMain.MODE_GAME
                    self.modeGame.resume()
                else:
                    print "Switch to lock"
                    self.mode = WallrMain.MODE_LOCK
                    self.modeLock.resume()

game = WallrMain()
game.start()

