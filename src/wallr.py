import sys, time, os, signal
import random
import TrackerLogPlayer as tracker
from TrackerProxy import TrackerProxy
import trkutil
import pygame, Queue
from WallrResources import RESOURCES, SETTINGS
import WallrSettings, ast
from ProgressBar import ProgressBar
from FuelGauge import FuelGauge
from TrafficLights import TrafficLights
from StaticSprite import StaticSprite
from Clock import Clock
from Timer import Timer

#sans = pygame.font.Font(pygame.font.match_font('sans'), 10)

class Coin(pygame.sprite.Sprite):
    def __init__(self, pos, callback, lifetime):
        pygame.sprite.Sprite.__init__(self)
        c = RESOURCES['fuel_x1']
        self.image = c.image
        self.rect = pygame.Rect(pos, c.image.get_size())
        self.elapsed = 0
        self.lifetime = lifetime
        self.resume()
        
    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False
        self.t0 = time.time()
        
    def update(self):
        if self.paused:
            return

        now = time.time()
        dt = now - self.t0
        self.elapsed += dt
        self.t0 = now
        
        if self.elapsed > self.lifetime:
            self.kill()

    def processCollision(self, p):
        # The coin is always killed on collision
        self.kill()

        # Get a +5 bonus
        return 5

class TankPosition(StaticSprite):
    def __init__(self):
        size = 25
        tank = pygame.Surface((size, size))
        tank.fill((255,255,255))
        tank.set_colorkey((255,255,255))
        pygame.draw.circle(tank, (0,0,255), (size/2, size/2), size/2, 2) 

        super(TankPosition, self).__init__(tank, (0,0))



SIMULATE_TRACKER = False
FORCE_FULLSCREEN = False

if SIMULATE_TRACKER:
    import TrackerLogPlayer as tracker
else:
    import tracker, target

class CoordinateTranslator(object):
    def __init__(self):
        st = WallrSettings.settings
        top_left = ast.literal_eval(st.calibration['top left'])
        bottom_right = ast.literal_eval(st.calibration['bottom right'])
        self.disp_width = int(st.display['width'])
        self.disp_height = int(st.display['height'])
        target_size = int(st.tracker['target size'])
        
        self.xa, self.xb = self.calc_ab(top_left[0], bottom_right[0], 0, self.disp_width - target_size)
        self.ya, self.yb = self.calc_ab(top_left[1], bottom_right[1], 0, self.disp_height - target_size)

    def calc_ab(self, from_min, from_max, to_min, to_max):
        a = (to_min - to_max)*1.0/(from_min - from_max)
        b = to_min - a*from_min
        return (a,b)
    
    def tracker_to_screen(self, pos):
        tx = int(self.xa*pos[0] + self.xb)
        tx = max(0, min(tx, self.disp_width))
        ty = int(self.ya*pos[1] + self.yb)
        ty = max(0, min(ty, self.disp_height))
        return (tx, ty)

    def screen_to_tracker(self, pos):
        tx = int((pos[0] - self.xb) / self.xa)
        ty = int((pos[1] - self.yb) / self.ya)
        return (tx, ty)

trx = CoordinateTranslator()


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
        lock_rect = ast.literal_eval(WallrSettings.settings.display['lock rect'])
        pygame.draw.rect(self.image, (255,0,0), pygame.Rect(
                (lock_rect[0], lock_rect[1]), 
                (lock_rect[2]-lock_rect[0], lock_rect[3]-lock_rect[1])), 10)

        # Draw the text
        ##fontname = pygame.font.match_font('sans')
        ##font = pygame.font.Font(fontname, 34)
        ##text = "Please place the tank in the rectangle"
        ##st = font.render(text, True, (0,0,0))
        ##self.image.blit(st, (self.screen.get_width()/2-st.get_width()/2, 200))
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
        self.tankPosition = TankPosition()
        self.gameScreenSprites = pygame.sprite.RenderUpdates([
            self.fuelGauge,
            self.traffic_light,
            self.clock,
            self.tankPosition])
        self.location = None
        self.prevLocation = None

        # Others
        ########
        # Create a group for pseudo-sprites
        self.updateables = pygame.sprite.Group()
        self.challanges = pygame.sprite.RenderUpdates()
        self.nextCoin = None

    def createGameOverScreen(self, lastscore):
        s = self.background.copy()
        i = RESOURCES['gameover'].image
        s.blit(i, center(i, 30))
        
        self.gameOverScreen = s

    def pause(self):
        self.clock.pause()
        self.fuelGauge.pause()
        for sp in self.challanges.sprites():
            sp.pause()

    def resume(self):
        print "Resume game"
        self.screen.blit(self.background, (0,0))

        if (self.state == WallrGameMode.STATE_PLAY):
            self.state = WallrGameMode.STATE_WAIT

        if (self.state == WallrGameMode.STATE_WAIT):
            self.gameScreenSprites.add(self.traffic_light)
            self.traffic_light.start()

        elif self.state == WallrGameMode.STATE_OVER:
            self.screen.blit(self.gameOverScreen, (0,0))

        pygame.display.update()
        self.active = True

    def resume_play(self):
        self.state = WallrGameMode.STATE_PLAY
        self.clock.resume()
        self.fuelGauge.resume()
        for sp in self.challanges.sprites():
            sp.resume()

    def trackerMessage(self, msg, param):
        if msg == tracker.MSG_SWITCH_TO_ACQ:
            print "Switch back"
            self.active = False
        if msg == tracker.MSG_COORDINATES:
            self.location = trx.tracker_to_screen((param['x'], param['y']))
            self.tankPosition.setPosition(self.location)

    def switchToStart(self):
        self.state = WallrGameMode.STATE_START
        self.screen.blit(self.background, (0,0))
        pygame.display.update()

    def switchToPlay(self):
        self.state = WallrGameMode.STATE_WAIT
        self.fuelGauge.fillTank( 
            lambda: self.fuelGauge.setConstantRate(5, self.outOfFuel))
        self.fuelGauge.resume()
        self.gameScreenSprites.add(self.traffic_light)
        self.traffic_light.start()
        self.screen.blit(self.background, (0,0))
        self.clock.allSegments(True)
        self.updateables.add(Timer(1, lambda: self.clock.allSegments(False),
                                   start = True))

    def switchToGameOver(self):
        self.state = WallrGameMode.STATE_OVER
        self.createGameOverScreen(0)
        
        # In game over mode, the screen is drawn
        # only once
        self.screen.blit(self.gameOverScreen, (0,0))
        pygame.display.update()

        self.updateables.add(Timer(10, lambda: self.switchToStart(),
                                   start = True))

    def generateCoins(self):
        r = random.randint(0, 1000)
        gen = (r < 5)
        if gen:
            # Generate a new coin
            forbidden = [ self.fuelGauge.rect ]
            scr = (self.screen.get_width() - 40,
                   self.screen.get_height() - 40)
            while True:
                # Get a random point
                p = (
                    random.randint(1, scr[0]),
                    random.randint(1, scr[1]))
                print p
                # Make sure the point is not in the
                # forbidden list
                for r in forbidden:
                    if r.collidepoint(p):
                        continue

                break

            c = Coin(p, None, 15)
            self.challanges.add(c)
        
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
                self.switchToPlay()
                

        elif (self.state == WallrGameMode.STATE_WAIT) or (self.state == WallrGameMode.STATE_PLAY):
            # Update and draw the widgets
            self.gameScreenSprites.update()
            self.gameScreenSprites.clear(self.screen, self.background)
            updates = self.gameScreenSprites.draw(self.screen)
            
            if (self.state == WallrGameMode.STATE_PLAY):
                # Update and draw the challanges
                self.challanges.update()
                self.challanges.clear(self.screen, self.background)
                updates += self.challanges.draw(self.screen)

                # Check if the tank collided any challage
                tl = (self.tankPosition.rect.x,
                      self.tankPosition.rect.y)
                collided = pygame.sprite.spritecollide(self.tankPosition,
                                                       self.challanges,
                                                       False)
                bonus = 0
                for c in collided:
                    # Calculate the collision point inside
                    # the sprite rect
                    p = (
                        c.rect.x + tl[0],
                        c.rect.y + tl[1])
                    bonus += c.processCollision(p)
                
                if bonus != 0:
                    self.fuelGauge.addFuel(bonus)

                # Generate new challanges
                self.generateCoins()

        # Update all the pseudo-sprites
        self.updateables.update()

        if (self.state != WallrGameMode.STATE_OVER):
            # Finally, draw the screen
            pygame.display.update(updates)

        return True
        
    def outOfFuel(self):
        print "Out of fuel"
        self.switchToGameOver()

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
        if SIMULATE_TRACKER:
            # Initialize the simulation tracker
            self.trk = tracker.TrackerLogPlayer(self.trackerCallback, 'tracker.log')
        else:
            # Initialize the tracker, and set the (calibrated) initial
            # search window position
            #self.trk = tracker.Tracker(self.trackerCallback, target.TrackingTarget)
            w = ast.literal_eval(WallrSettings.settings.display['lock rect'])
            w_bottomright = trx.screen_to_tracker((w[0], w[1]))
            w_topleft = trx.screen_to_tracker((w[2], w[3]))
            print w_topleft
            print w_bottomright
            w_rect = trkutil.Rectangle(w_topleft[0], w_topleft[1], w_bottomright[0], w_bottomright[1])

            self.trk = TrackerProxy(tracker.Tracker, self.trackerCallback, 
                                    targetCls = target.TrackingTarget, search_win = w_rect)

        # Start the tracker
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
        if disp_no and not FORCE_FULLSCREEN:
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

