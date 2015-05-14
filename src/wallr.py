import sys, time
import TrackerLogPlayer as tracker
import pygame, Queue
from WallrResources import RESOURCES, SETTINGS
import ProgressBar

class WallrLockMode(object):
    def __init__(self, screen, background, callback):
        self.screen = screen
        self.background = background
        self.progress = ProgressBar.ProgressBar(130, 30,
                                                (255, 250))
        self.widgets = pygame.sprite.RenderUpdates([self.progress])

    def start(self):
        # Clear the screen
        self.screen.blit(self.background, (0,0))
        # Draw the "lock rectangle"
        pygame.draw.rect(self.screen, (255,0,0),
                         pygame.Rect(SETTINGS['lock_rect']), 10)
        # Draw the text
        fontname = pygame.font.match_font('sans')
        font = pygame.font.Font(fontname, 34)
        text = "Please place the tank in the rectangle"
        st = font.render(text, True, (0,0,0))
        self.screen.blit(st, (self.screen.get_width()/2-st.get_width()/2, 200))
        # Logo
        logo = RESOURCES['logo']
        self.screen.blit(logo.image, (self.screen.get_width()/2-logo.get_rect().width/2, 320))

        pygame.display.update()

    def trackerMessage(self, msg, params):
        if msg == tracker.MSG_LOCK_PROGRESS:
            self.progress.setProgress(params)

    def loop(self):
        # Update and draw the progress bar
        self.widgets.update()
        self.widgets.clear(self.screen, self.background)
        updates = self.widgets.draw(self.screen)
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
    MODE_GAME = 0

    def __init__(self):
        self.mode = WallrMain.MODE_LOCK

        # Instantiate a tracker and connect it to the
        # local callback
        self.trkMessages = Queue.Queue()
        self.trk = tracker.TrackerLogPlayer('tracker.log', self.trackerCallback)
        self.trk.start()


        # Initialize PyGame and create a screen and a background
        pygame.init()
        self.screen = pygame.display.set_mode(SETTINGS['screen_size'])
        self.background = pygame.Surface(SETTINGS['screen_size'])
        self.background.fill(SETTINGS['background_color'])
        
        self.modeLock = WallrLockMode(self.screen, self.background, None)

    def trackerCallback(self, msg, params):
        # Synchronize the tracker messages through a queue
        self.trkMessages.put((msg, params))
        
    def start(self):
        self.running = True
        self.modeLock.start()
        while self.running:
            event = pygame.event.poll()
            if event.type == pygame.QUIT:
                self.running = False

            # Check if a message is available on the queue
            # from the tracker
            if not self.trkMessages.empty():
                m = self.trkMessages.get()

                if self.mode == WallrMain.MODE_LOCK:
                    self.modeLock.trackerMessage(*m)
            
                    
            if self.mode == WallrMain.MODE_LOCK:
                self.modeLock.loop()
game = WallrMain()
game.start()

