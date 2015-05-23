import sys, time, os, signal
import random, ast
import TrackerLogPlayer as tracker
import pygame, Queue
from WallrResources import RESOURCES, SETTINGS
import WallrSettings
from ProgressBar import ProgressBar
from FuelGauge import FuelGauge
from TrafficLights import TrafficLights
from StaticSprite import StaticSprite
import Clock
from Timer import Timer
from iniparse.config import Undefined

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
        self.clock = Clock.Clock((10, 150))
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
        game_time = self.clock.getTime()
        s = pygame.Surface(self.screen.get_size())
        s.blit(RESOURCES['game_over_image'].image, (0,0))
        font = pygame.font.Font(RESOURCES['game_over_font'].filename, 70)
        text = "GAME OVER"
        i = font.render(text, True, (0,0,0))
        i.set_colorkey((255,255,255))
        s.blit(i, center(i, 30))

        text = "Your time: " + Clock.timeToMMSSTT(game_time)
        i = sans40.render(text, True, (0,0,0))
        s.blit(i, center(i, 90))

        text = "HIGH SCORE"
        i = sans40.render(text, True, (255, 128, 0))
        s.blit(i, center(i, 150))

        table, indx = self.highscore(game_time)
        y = 200
        for k in range(len(table)):
            ent = table[k]
            text = Clock.timeToMMSSTT(ent[0])
            if indx == k:
                color = (255,0,0)
            else:
                color = (0,0,0)
            i = sans30.render(text, True, color)
            s.blit(i, center(i, y))
            y += 40
        
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
        if (self.state == WallrGameMode.STATE_OVER):
            self.state = WallrGameMode.STATE_START

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
            self.location = (int(param['x'])/2, int(param['y'])/2)
            self.tankPosition.setPosition(self.location)

    def switchToPlay(self):
        self.state = WallrGameMode.STATE_WAIT
        self.fuelGauge.fillTank( 
            lambda: self.fuelGauge.setConstantRate(15, self.outOfFuel))
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

    def highscore(self, current):
        currentt = (current, time.time())
        # Read the existing high score table
        table = []
        for i in range(1,6):
            raw = WallrSettings.settings.highscore['entry%d' % i]
            if isinstance(raw, Undefined):
                entry = (0,0)
            else:
                entry = ast.literal_eval(raw)
            table.append(entry)

        # Sort it
        table.sort(cmp=lambda x,y: 1 if x[0] < y[0] else -1)
        
        # Check if the current entry enters the table
        hsindex = None
        for i in range(len(table)):
            if (hsindex is None) and (current > table[i][0]):
                # Insert the new entry an push everything down
                # by one
                table.insert(i, currentt)
                table.pop()
                hsindex = i
                break

        # Write the table back
        for i in range(1,6):
            WallrSettings.settings.highscore['entry%d' % i] = str(table[i-1])
        WallrSettings.save()
                
        return (table, hsindex)

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
        globals()['sans30'] = pygame.font.Font(pygame.font.match_font('sans'), 40)
        globals()['sans40'] = pygame.font.Font(pygame.font.match_font('sans'), 40)
        globals()['sans50'] = pygame.font.Font(pygame.font.match_font('sans'), 50)

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

