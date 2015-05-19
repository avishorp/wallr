import sys, time, os, signal
import TrackerLogPlayer as tracker
import pygame, Queue
from WallrResources import RESOURCES, SETTINGS
from ProgressBar import ProgressBar
from FuelGauge import FuelGauge
from TrafficLights import TrafficLights
from StaticSprite import StaticSprite
from Clock import Clock

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

    def loop(self, ev):
        if not self.active:
            return False
            
        # Update and draw the progress bar
        self.widgets.update()
        self.widgets.clear(self.screen, self.background)
        updates = self.widgets.draw(self.screen)
        pygame.display.update(updates)
        
        return True

class WallrGameMode(object):
    STATE_START = 0 
    STATE_WAIT = 1
    STATE_PLAY = 2
    STATE_OVER = 3

    def __init__(self, screen, background):
        self.screen = screen
        self.background = background
        self.state = WallrGameMode.STATE_START
        self.clear = []

    def create(self):
        # Start Screen
        ##############
        # "Press START to begin"
        fontname = pygame.font.match_font('sans')
        font = pygame.font.Font(fontname, 50)
        text = "Press START to begin"
        textimg = font.render(text, True, (0,0,0))
        textspr = StaticSprite(textimg, center(textimg, 200))
        # Logo
        logo = RESOURCES['logo']
        logospr = StaticSprite(logo.image, center(logo.image, 320))
        self.startScreenSprites = pygame.sprite.RenderUpdates(
            [ textspr, logospr ])

        # Game Screen
        #############
        self.fuelGauge = FuelGauge((0,0))
        self.traffic_light = TrafficLights((500,30),
                                           callback = self.resume_play)
        self.traffic_light.start()
        self.clock = Clock((10, 150))
        self.gameScreenSprites = pygame.sprite.RenderUpdates([
            self.fuelGauge,
            self.traffic_light,
            self.clock])
        self.location = None
        self.prevLocation = None
          
    def pause(self):
        self.clock.pause()
        self.fuelGauge.pause()

    def resume(self):
        print "Resume game"
        self.gameScreenSprites.add(self.traffic_light)
        self.traffic_light.start()
        self.screen.blit(self.background, (0,0))
        pygame.display.update()

        self.active = True

    def resume_play(self):
        self.clock.resume()
        self.fuelGauge.resume()

    def trackerMessage(self, msg, param):
        if msg == tracker.MSG_SWITCH_TO_ACQ:
            print "Switch back"
            self.active = False
        if msg == tracker.MSG_COORDINATES:
            self.prevLocation = self.location
            self.location = (int(param['x'])/2, int(param['y'])/2)
        
    def loop(self, ev):
        if not self.active:
            return False

        updates = []

        if self.state == WallrGameMode.STATE_START:
            # Draw the start screen sprites
            self.startScreenSprites.update()
            self.startScreenSprites.clear(self.screen, self.background)
            updates = self.startScreenSprites.draw(self.screen)

            # Check if the key has been pressed, and switch to
            # play mode if so
            if ev.type == pygame.KEYDOWN:
                # Start the game
                self.state = WallrGameMode.STATE_PLAY
                self.fuelGauge.fillTank( 
                        lambda: self.fuelGauge.setConstantRate(5, self.outOfFuel))
                self.gameScreenSprites.add(self.traffic_light)
                self.traffic_light.start()
                self.screen.blit(self.background, (0,0))
                

        elif (self.state == WallrGameMode.STATE_WAIT) or (self.state == WallrGameMode.STATE_PLAY):
            # Update and draw the widgets
            self.gameScreenSprites.update()
            self.gameScreenSprites.clear(self.screen, self.background)
            updates = self.gameScreenSprites.draw(self.screen)

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
        
    def outOfFuel(self):
        print "Out of fuel"

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
        signal.signal(signal.SIGINT, self.terminate)

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
        
        globals()['center'] = lambda img, y: (self.screen.get_rect().width/2-img.get_rect().width/2, y)

        self.modeLock = WallrLockMode(self.screen, self.background)
        self.modeGame = WallrGameMode(self.screen, self.background)

        self.create()

    def terminate(self, sig, frm):
        print "Terminating"
        self.running = False
        self.trk.terminate()
        self.trk.join()
        pygame.display.quit()
        sys.exit(0)

    def init_display(self):
        "Ininitializes a new pygame screen using the framebuffer"
        # Based on "Python GUI in Linux framer buffer"
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

            if not cm.loop(event):
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

