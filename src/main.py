# --- Rendering and UI --- #
import os

from animations import Animation
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"   # cringe
import pygame as pg

from engine import Level
from levels import test_level


# Display-Related Constants
DEFAULT_SCREEN_WIDTH = 800
DEFAULT_SCREEN_HEIGHT = 600

MIN_SCREEN_WIDTH = 300
MIN_SCREEN_HEIGHT = 200

TARGET_FPS = 60


# Layout-Related Constants
SHELF_HEIGHT = 100
SHELF_ANIMATION_SPEED = 10  # pixels per frame

SHELF_BG_COLOR = (127, 127, 127)
VIEWPORT_BG_COLOR = (255, 255, 255)


class LevelRunner:
    def __init__(self, level: Level):
        self.level = level
        self.screen_width = DEFAULT_SCREEN_WIDTH
        self.screen_height = DEFAULT_SCREEN_HEIGHT
        self.shelf_height = SHELF_HEIGHT
        self.edit_mode = True
        self.shelf_state = "open"   # "open", "closed", "opening", or "closing"

        # initialize `viewport_rect` and `shelf_rect`
        self.update_layout_rects()

        self.active_animations = []
    
    def run(self):
        """run the level in a resizable window at `TARGET_FPS`"""
        # initialize display
        self.screen = pg.display.set_mode((self.screen_width, self.screen_height), pg.RESIZABLE)

        # mainloop
        clock = pg.time.Clock()
        self.running = True
        while self.running:
            clock.tick(TARGET_FPS)

            # handle input
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    self.running = False
                elif event.type == pg.VIDEORESIZE:
                    self.handle_window_resize(event.w, event.h)
                elif event.type == pg.KEYDOWN:
                    self.handle_keydown(event.key)
            
            # handle shelf animation
            self.handle_shelf_animation()

            # # handle animations (EXPERIMENTAL)
            # self.handle_animations()
            
            # handle output
            pg.draw.rect(self.screen, VIEWPORT_BG_COLOR, self.viewport_rect)
            if self.shelf_state != "closed":
                pg.draw.rect(self.screen, SHELF_BG_COLOR, self.shelf_rect)
            
            pg.display.update()
    
    def update_layout_rects(self):
        self.viewport_rect = pg.Rect(0, 0, self.screen_width, self.screen_height - self.shelf_height)
        self.shelf_rect = pg.Rect(*self.viewport_rect.bottomleft, self.screen_width, self.shelf_height)

    def handle_window_resize(self, new_width, new_height):
        self.screen_width = max(new_width, MIN_SCREEN_WIDTH)
        self.screen_height = max(new_height, MIN_SCREEN_HEIGHT)
        self.screen = pg.display.set_mode((self.screen_width, self.screen_height), pg.RESIZABLE)
        self.update_layout_rects()
    

    def handle_shelf_animation(self):
        if self.shelf_state == "closing":
            self.shelf_height -= SHELF_ANIMATION_SPEED
            if self.shelf_height <= 0:
                self.shelf_height = 0
                self.shelf_state = "closed"
                self.edit_mode = False
            self.update_layout_rects()
        elif self.shelf_state == "opening":
            self.shelf_height += SHELF_ANIMATION_SPEED
            if self.shelf_height >= SHELF_HEIGHT:
                self.shelf_height = SHELF_HEIGHT
                self.shelf_state = "open"
                self.edit_mode = True
            self.update_layout_rects()
    
    # EXPERIMENTAL
    def handle_animations(self):
        # print(self.active_animations)
        for anim in self.active_animations:
            anim.step()
            # TODO: ensure no concurrent modificaton bugs
            if anim.done:
                self.active_animations.remove(anim)

    def handle_keydown(self, key):
        if self.shelf_state == "open":
            self.shelf_state = "closing"
        elif self.shelf_state == "closed":
            self.shelf_state = "opening"
        
        # EXPERIMENTAL
        # speed = 10

        # if self.edit_mode:
        #     # instantiate a close_shelf animation
        #     def close_shelf_step(r):
        #         r.shelf_height = max(r.shelf_height - speed, 0)
        #         r.update_layout_rects()
        #     def close_shelf_end(r): r.edit_mode = False
        #     anim = Animation(self, [
        #         (close_shelf_step, self.shelf_height // speed + 1),
        #         (close_shelf_end, 1)
        #     ])
        # else:
        #     # instantiate an open_shelf animation
        #     def open_shelf_start(r): r.edit_mode = True
        #     def open_shelf_step(r):
        #         r.shelf_height = min(r.shelf_height + speed, DEFAULT_SHELF_HEIGHT)
        #         r.update_layout_rects()
        #     anim = Animation(self, [
        #         (open_shelf_start, 1),
        #         (open_shelf_step, DEFAULT_SHELF_HEIGHT // speed + 1),
        #     ])
        # self.active_animations.append(anim)

        

if __name__ == "__main__":
    LevelRunner(test_level).run()
