# --- Rendering and UI --- #
import os

from animations import Animation
from entities import Barrel
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"   # cringe
import pygame as pg
import pygame.freetype
from math import floor, ceil

from engine import Level
from levels import test_level
from helpers import Direction, V2
from colors import Color, COLOR_RBG_MAP


# Display-Related Constants
DEFAULT_SCREEN_WIDTH  = 800
DEFAULT_SCREEN_HEIGHT = 600

MIN_SCREEN_WIDTH  = 300
MIN_SCREEN_HEIGHT = 200

TARGET_FPS = 60


# Layout-Related Constants
SHELF_HEIGHT          = 100 # pixels
SHELF_ANIMATION_SPEED = 15  # pixels per frame

DEFAULT_CELL_SIZE     = 64 # pixels

PALETTE_ITEM_SIZE     = 64  # pixels
PALETTE_ITEM_SPACING  = 8   # pixels


# Aesthetics-Related Constants
SHELF_BG_COLOR            = (127, 127, 127, 191)
VIEWPORT_BG_COLOR         = (255, 255, 255)
VELOCITY_CHEVRON_COLOR    = (0, 0, 0)
GRID_LINE_COLOR           = (0, 0, 0)

DEFAULT_GRID_LINE_WIDTH   = 2
MIN_GRID_LINE_WIDTH       = 1
MAX_GRID_LINE_WIDTH       = 5


# Misc Constants
LEVEL_STEP_INTERVAL = 800   # milliseconds


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
        return DEFAULT_CELL_SIZE * self.zoom_level


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
        self.shelf_height_onscreen = SHELF_HEIGHT

        self.keys_pressed = set()

        self.edit_mode = True
        self.shelf_state = "open"   # "open", "closed", "opening", or "closing"

        # initialize camera to contain `level.board` (with some margin)
        rect = level.board.get_bounding_rect(margin=3)   # arbitrary value
        zoom_level = min(self.screen_width / rect.width, self.screen_height / rect.height) / DEFAULT_CELL_SIZE
        self.camera = Camera(center=V2(*rect.center), zoom_level=zoom_level)

        # initialize refresh sentinels
        self.layout_changed = False
        self.viewport_changed = False
        self.shelf_changed = False

    def run(self):
        """run the level in a resizable window at `TARGET_FPS`"""
        # initialize display, initialize output surfaces, and adjust camera
        self.handle_window_resize(DEFAULT_SCREEN_WIDTH, DEFAULT_SCREEN_HEIGHT)

        pg.freetype.init()
        self.palette_font = pg.freetype.SysFont("ariel", 16, bold=True)

        # initialize `viewport_surf`, `shelf_surf`, and `shelf_rect`
        # self.refresh_layout()
        self.draw_level()
        self.draw_shelf()

        self.prev_step_elapsed = 0

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

            # handle level execution
            if not self.edit_mode:
                self.prev_step_elapsed += clock.get_time()
                # print(time - self.prev_step_time)
                if self.prev_step_elapsed > LEVEL_STEP_INTERVAL:
                    self.level.step()
                    self.prev_step_elapsed = 0
                    self.viewport_changed = True
            
            # handle output
            if self.window_size_changed:
                # trigger total re-draw
                self.viewport_changed = True
                self.shelf_changed = True
                self.window_size_changed = False

            if self.viewport_changed:
                self.draw_level()
            
            if self.shelf_changed:
                self.draw_shelf()

            if self.viewport_changed or self.shelf_changed:
                self.screen.blit(self.viewport_surf, (0, 0))
                self.screen.blit(self.shelf_surf, (0, self.screen_height - self.shelf_height_onscreen))
                pg.display.update()
                self.viewport_changed = False
                self.shelf_changed = False

    def handle_window_resize(self, new_width, new_height):
        self.screen_width = max(new_width, MIN_SCREEN_WIDTH)
        self.screen_height = max(new_height, MIN_SCREEN_HEIGHT)
        self.screen = pg.display.set_mode((self.screen_width, self.screen_height), pg.RESIZABLE)
        self.window_size_changed = True
        self.viewport_surf = pg.Surface((self.screen_width, self.screen_height), pg.HWSURFACE)
        self.shelf_surf = pg.Surface((self.screen_width, SHELF_HEIGHT), pg.SRCALPHA)

    def handle_shelf_animation(self):
        if self.shelf_state == "closing":
            self.shelf_height_onscreen -= SHELF_ANIMATION_SPEED
            if self.shelf_height_onscreen <= 0:
                self.shelf_height_onscreen = 0
                self.shelf_state = "closed"
                self.edit_mode = False
            self.shelf_changed = True
        elif self.shelf_state == "opening":
            self.shelf_height_onscreen += SHELF_ANIMATION_SPEED
            if self.shelf_height_onscreen >= SHELF_HEIGHT:
                self.shelf_height_onscreen = SHELF_HEIGHT
                self.shelf_state = "open"
                self.edit_mode = True
            self.shelf_changed = True

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
                    self.level.reset()      # reset board and palette
                    self.viewport_changed = True
        # TEMPORARY
        elif key == pg.K_RIGHT:
            self.level.step()
            self.viewport_changed = True

    def handle_keyup(self, key):
        pass

    def handle_keys_pressed(self):
        for key in self.keys_pressed:
            if key in self.pan_keys_map:
                disp = self.pan_keys_map[key]
                self.camera.pan(disp)
                # print("camera center:", self.camera.center)
                self.viewport_changed = True

    def handle_mousebuttondow(self, button):
        if button == 4:    # zoom in
            self.camera.zoom(1)
            self.viewport_changed = True
        elif button == 5:   # zoom out
            self.camera.zoom(-1)
            self.viewport_changed = True

    def draw_level(self):
        """draw the level onto `viewport_surf`"""
        s = self.camera.get_cell_size_px()
        surf_center = V2(*self.viewport_surf.get_rect().center)
        surf_width, surf_height = self.viewport_surf.get_size()

        def grid_to_px(pos: V2) -> V2:
            return round(surf_center + (pos - self.camera.center) * s)
        
        self.viewport_surf.fill(VIEWPORT_BG_COLOR)

        w = surf_width / s
        h = surf_height / s
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
            x_px, _ = grid_to_px(V2(x_grid, 0))
            pg.draw.line(
                self.viewport_surf,
                GRID_LINE_COLOR,
                (x_px, 0),
                (x_px, surf_height),
                width=grid_line_width
            )
        for y in range(grid_rect.height):
            y_grid = grid_rect.top + y - 0.5
            _,  y_px = grid_to_px(V2(0, y_grid))
            pg.draw.line(
                self.viewport_surf,
                GRID_LINE_COLOR,
                (0, y_px),
                (surf_width, y_px),
                width=grid_line_width
            )

        # draw board
        for x in range(grid_rect.width):
            for y in range(grid_rect.height):
                grid_pos = V2(x, y) + V2(*grid_rect.topleft)
                draw_pos = grid_to_px(grid_pos)
                cell = self.level.board.get(*grid_pos)
                for e in cell:
                    # TEMPORARY
                    draw_color_ryb = e.color if isinstance(e, Barrel) else Color.BROWN
                    draw_color_rgb = COLOR_RBG_MAP[draw_color_ryb]
                    pg.draw.circle(self.viewport_surf, draw_color_rgb, tuple(draw_pos), s // 3)
                    # draw velocity indicator chevron
                    if e.moves and e.velocity is not Direction.NONE:
                        # TODO: use `draw_chevron` helper function
                        pass
                        # l = s // 3
                        # for rot in (-1, 1):
                        #     pg.draw.line(
                        #         self.viewport_surf,
                        #         VELOCITY_CHEVRON_COLOR,
                        #         tuple(draw_pos + e.velocity.rot90(rot) * l),
                        #         tuple(draw_pos + e.velocity * l),
                        #         width=grid_line_width * 2   # use double thickness as grid
                        #     )

    def draw_shelf(self):
        if self.shelf_state == "closed":
            return      # NoOp
        
        self.shelf_surf.fill(SHELF_BG_COLOR)

        # draw palette
        for i, (e_type, count) in enumerate(self.level.palette):
            margin = (SHELF_HEIGHT - PALETTE_ITEM_SIZE) // 2
            rect = pg.Rect(
                margin + (PALETTE_ITEM_SIZE + margin + PALETTE_ITEM_SPACING) * i,
                margin,
                PALETTE_ITEM_SIZE,
                PALETTE_ITEM_SIZE
            )
            pg.draw.rect(self.shelf_surf, (0, 255, 0), rect)
            pg.draw.circle(self.shelf_surf, (255, 0, 0), rect.topright, 14)
            text_img, text_rect = self.palette_font.render(str(count), fgcolor=(255, 255, 255))
            self.shelf_surf.blit(
                text_img,
                (rect.right - text_rect.width / 2, rect.top - text_rect.height / 2)
            )
            # print(i, e_type, count)




if __name__ == "__main__":
    LevelRunner(test_level).run()
