# --- Rendering and UI --- #
import os

from animations import Animation
from entities import Barrel
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"   # cringe
import pygame as pg
from math import floor, ceil

from engine import Level
from levels import test_level
from helpers import Direction, V2
from colors import Color, COLOR_RBG_MAP


# Display-Related Constants
DEFAULT_SCREEN_WIDTH = 800
DEFAULT_SCREEN_HEIGHT = 600

MIN_SCREEN_WIDTH = 300
MIN_SCREEN_HEIGHT = 200

TARGET_FPS = 60


# Layout-Related Constants
SHELF_HEIGHT = 100
SHELF_ANIMATION_SPEED = 10  # pixels per frame

DEFAULT_CELL_SIZE_PX = 64


# Aesthetics-Related Constants
SHELF_BG_COLOR = (127, 127, 127)
VIEWPORT_BG_COLOR = (255, 255, 255)

GRID_LINE_COLOR = (0, 0, 0)
DEFAULT_GRID_LINE_WIDTH = 2
MIN_GRID_LINE_WIDTH = 2
MAX_GRID_LINE_WIDTH = 5


class Camera:
    min_zoom_level = 0.3
    max_zoom_level = 5.0

    pan_speed = 0.15
    zoom_speed = 0.10

    """stores a center point and a zoom level (using floating-point board coordinates)"""
    def __init__(self, center: V2, zoom_level: float):
        self.center = center
        self.zoom_level = zoom_level
        self.rectify_zoom_level()
    
    def pan(self, disp: V2):
        """translate `rect` by the given displacement (scaled according to zoom level)"""
        self.center += disp * self.pan_speed * (1 / self.zoom_level)
    
    def zoom(self, amt: float):
        """increase zoom level by amt"""
        self.zoom_level += amt * self.zoom_speed
        self.rectify_zoom_level()
    
    def rectify_zoom_level(self):
        """ensure `min_zoom_level <= zoom_level <= max_zoom_level` is in bounds"""
        self.zoom_level = min(max(self.zoom_level, self.min_zoom_level), self.max_zoom_level)
    
    def get_cell_size_px(self):
        return DEFAULT_CELL_SIZE_PX * self.zoom_level


class LevelRunner:
    pan_keys_map = {
        pg.K_w: Direction.NORTH,
        pg.K_s: Direction.SOUTH,
        pg.K_a: Direction.WEST,
        pg.K_d: Direction.EAST
    }

    def __init__(self, level: Level):
        self.level = level

        self.screen_width = DEFAULT_SCREEN_WIDTH
        self.screen_height = DEFAULT_SCREEN_HEIGHT
        self.shelf_height = SHELF_HEIGHT

        self.keys_pressed = set()

        self.edit_mode = True
        self.shelf_state = "open"   # "open", "closed", "opening", or "closing"

        # initialize camera to contain `level.board` (with some margin)
        rect = level.board.get_bounding_rect(margin=3)   # arbitrary value
        zoom_level = min(self.screen_width / rect.width, self.screen_height / rect.height) / DEFAULT_CELL_SIZE_PX
        self.camera = Camera(center=V2(*rect.center), zoom_level=zoom_level)

        # initialize `shelf_rect`
        self.refresh_layout()

        # initialize refresh sentinels
        self.layout_changed = False
        self.contents_changed = False

    def run(self):
        """run the level in a resizable window at `TARGET_FPS`"""
        # initialize display and adjust camera
        self.handle_window_resize(DEFAULT_SCREEN_WIDTH, DEFAULT_SCREEN_HEIGHT)

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
                    self.keys_pressed.add(event.key)
                    self.handle_keydown(event.key)
                elif event.type == pg.KEYUP:
                    self.keys_pressed.remove(event.key)
                    self.handle_keyup(event.key)
                elif event.type == pg.MOUSEBUTTONDOWN:
                    self.handle_mousebuttondow(event.button)
            
            self.handle_keys_pressed()
            
            # handle shelf animation
            self.handle_shelf_animation()
            
            # handle output
            if self.layout_changed:
                self.refresh_layout()
                self.layout_changed = False
                self.contents_changed = True    # trigger re-draw

            if self.contents_changed:
                self.draw_background()
                self.draw_level()
                self.draw_shelf()
                self.contents_changed = False
                pg.display.update()

    def refresh_layout(self):
        self.shelf_rect = pg.Rect(0, self.screen_height - self.shelf_height, self.screen_width, self.shelf_height)

    def handle_window_resize(self, new_width, new_height):
        self.screen_width = max(new_width, MIN_SCREEN_WIDTH)
        self.screen_height = max(new_height, MIN_SCREEN_HEIGHT)
        self.screen = pg.display.set_mode((self.screen_width, self.screen_height), pg.RESIZABLE)
        self.layout_changed = True

    def handle_shelf_animation(self):
        if self.shelf_state == "closing":
            self.shelf_height -= SHELF_ANIMATION_SPEED
            if self.shelf_height <= 0:
                self.shelf_height = 0
                self.shelf_state = "closed"
                self.edit_mode = False
            self.layout_changed = True
        elif self.shelf_state == "opening":
            self.shelf_height += SHELF_ANIMATION_SPEED
            if self.shelf_height >= SHELF_HEIGHT:
                self.shelf_height = SHELF_HEIGHT
                self.shelf_state = "open"
                self.edit_mode = True
            self.layout_changed = True

    def handle_keydown(self, key):
        if key == pg.K_ESCAPE:
            self.running = False
        elif key == pg.K_SPACE:
            # toggle shelf state (initiates animation (if not already in progress))
            if self.shelf_state in ("open", "closed"):
                if self.shelf_state == "open":
                    self.shelf_state = "closing"
                elif self.shelf_state == "closed":
                    self.shelf_state = "opening"
        # TEMPORARY
        elif key == pg.K_RIGHT:
            self.level.step()
            self.contents_changed = True

    def handle_keyup(self, key):
        pass

    def handle_keys_pressed(self):
        for key in self.keys_pressed:
            if key in self.pan_keys_map:
                disp = self.pan_keys_map[key]
                self.camera.pan(disp)
                # print("camera center:", self.camera.center)
                self.contents_changed = True

    def handle_mousebuttondow(self, button):
        if button == 4:    # zoom in
            self.camera.zoom(1)
            self.contents_changed = True
        elif button == 5:   # zoom out
            self.camera.zoom(-1)
            self.contents_changed = True

    def draw_background(self):
        self.screen.fill(VIEWPORT_BG_COLOR)

    def draw_level(self):
        s = self.camera.get_cell_size_px()
        screen_center = V2(*self.screen.get_rect().center)
        # offset = self.camera.center.fmod(s)

        def convert(pos: V2) -> V2:
            return round(screen_center + (pos - self.camera.center) * s)

        w = self.screen_width / s
        h = self.screen_height / s
        grid_rect = pg.Rect(
            floor(self.camera.center.x - w / 2),
            floor(self.camera.center.y - h / 2),
            ceil(w) + 2,
            ceil(h) + 2
        )

        # draw grid with dynamic line width
        grid_line_width = round(DEFAULT_GRID_LINE_WIDTH * self.camera.zoom_level ** 0.5)
        grid_line_width = min(max(grid_line_width, MIN_GRID_LINE_WIDTH), MAX_GRID_LINE_WIDTH)
        for x in range(grid_rect.width):
            x_grid = grid_rect.left + x - 0.5
            x_px, _ = convert(V2(x_grid, 0))
            pg.draw.line(
                self.screen,
                GRID_LINE_COLOR,
                (x_px, 0),
                (x_px, self.screen_height),
                width=grid_line_width
            )
        for y in range(grid_rect.height):
            y_grid = grid_rect.top + y - 0.5
            _,  y_px = convert(V2(0, y_grid))
            pg.draw.line(
                self.screen,
                GRID_LINE_COLOR,
                (0, y_px),
                (self.screen_width, y_px),
                width=grid_line_width
            )

        # draw board
        for x in range(grid_rect.width):
            for y in range(grid_rect.height):
                grid_pos = V2(x, y) + V2(*grid_rect.topleft)
                draw_pos = convert(grid_pos)
                cell = self.level.board.get(*grid_pos)
                for e in cell:
                    # TEMPORARY
                    draw_color_ryb = e.color if isinstance(e, Barrel) else Color.BROWN
                    draw_color_rgb = COLOR_RBG_MAP[draw_color_ryb]
                    pg.draw.circle(self.screen, draw_color_rgb, tuple(draw_pos), s // 3)

    def draw_shelf(self):
        if self.shelf_state != "closed":
            pg.draw.rect(self.screen, SHELF_BG_COLOR, self.shelf_rect)




if __name__ == "__main__":
    LevelRunner(test_level).run()
