# --- Rendering and UI --- #
from typing import Union, Type, Sequence, Tuple
from math import floor, ceil
import pygame as pg

from entities import Entity
from widgets import Widget
from engine import Level
from levels import test_level, test_level2
from helpers import V2, draw_aapolygon, render_text_centered, clamp, wrap_text


# Display-Related Constants
DEFAULT_SCREEN_WIDTH    = 1000
DEFAULT_SCREEN_HEIGHT   = 800

MIN_SCREEN_WIDTH        = 300
MIN_SCREEN_HEIGHT       = 200

TARGET_FPS              = 60


# Layout-Related Constants
DEFAULT_CELL_SIZE       = 64    # pixels

SHELF_HEIGHT            = 100   # pixels
EDITOR_WIDTH            = 200   # pixels

SHELF_ANIMATION_SPEED   = 15    # pixels per frame
EDITOR_ANIMATION_SPEED  = 30    # pixels per frame

PALETTE_ITEM_SIZE       = 64    # pixels
PALETTE_ITEM_SPACING    = 8     # pixels
SHELF_ICON_SIZE         = 40    # pixels (play/pause button size)
SHELF_ICON_SPACING      = 16    # pixels
EDITOR_WIDGET_SPACING   = 8     # pixels



# Aesthetics-Related Constants
VIEWPORT_BG_COLOR           = (255, 255, 255)
SHELF_BG_COLOR              = (127, 127, 127, 240)  # mostly opaque
EDITOR_BG_COLOR             = (127, 127, 127, 240)  # ^^^
GRID_LINE_COLOR             = (0, 0, 0)
SHELF_ICON_COLOR_ON         = (0, 0, 0)             # TODO: pick actual colors here (or use actual icons)
SHELF_ICON_COLOR_OFF        = (200, 200, 200)       # ^^^

DEFAULT_GRID_LINE_WIDTH     = 2
MIN_GRID_LINE_WIDTH         = 1
MAX_GRID_LINE_WIDTH         = 5


# Misc Constants
LEVEL_STEP_INTERVAL = 1000  # milliseconds
FAST_FORWARD_FACTOR = 2


class Camera:
    """stores a center point and a zoom level (using floating-point board coordinates)"""

    min_zoom_level = 0.4
    max_zoom_level = 4.0

    pan_speed = 0.15
    zoom_speed = 0.10

    def __init__(self, center: V2, zoom_level: float):
        self.center = center
        self.zoom_level = clamp(zoom_level, self.min_zoom_level, self.max_zoom_level)
    
    def pan(self, disp: V2):
        """translate `center` by the given displacement (scaled according to zoom level)"""
        self.center += disp * self.pan_speed * (1 / self.zoom_level)
    
    def pan_abs(self, disp: V2):
        """translate `center` by the given displacement"""
        self.center += disp
    
    def zoom(self, amt: float, pivot: V2):
        """increase zoom level by `amt` about `pivot`"""
        amt *= self.zoom_speed
        amt = min(amt, self.max_zoom_level - self.zoom_level)
        amt = max(amt, self.min_zoom_level - self.zoom_level)

        # pan to keep pivot in same location on screen
        disp_px_before = (pivot - self.center) * self.zoom_level
        self.zoom_level += amt
        disp_px_after = (pivot - self.center) * self.zoom_level

        diff_px = disp_px_after - disp_px_before
        diff = diff_px / self.zoom_level
        self.pan_abs(diff)
    
    def get_cell_size_px(self):
        s = round(DEFAULT_CELL_SIZE * self.zoom_level)
        return s - s%2  # force even
    
    def get_world_coords(self, pos: V2, screen_width, screen_height):
        """converts the given pixel `pos` to world coordinates"""
        screen_center = V2(screen_width / 2, screen_height / 2)
        diff = pos - screen_center
        return self.center + diff * (1 / self.get_cell_size_px())


class LevelRunner:
    # pan_keys_map = {
    #     pg.K_w: Direction.NORTH,
    #     pg.K_s: Direction.SOUTH,
    #     pg.K_a: Direction.WEST,
    #     pg.K_d: Direction.EAST
    # }

    def __init__(self, level: Level):
        self.level = level

        self.screen_width = DEFAULT_SCREEN_WIDTH
        self.screen_height = DEFAULT_SCREEN_HEIGHT
        self.shelf_height_onscreen = SHELF_HEIGHT
        self.editor_width_onscreen = 0

        self.keys_pressed = set()
        self.mouse_buttons_pressed = set()
        self.mouse_pos = V2(0, 0)

        self.edit_mode = True
        self.paused = False
        self.fast_forward = False

        self.shelf_state = "open"       # "open", "closed", "opening", or "closing"
        self.editor_state = "closed"    # "open", "closed", "opening", or "closing"
        self.step_progress = 0.0        # float in [0, 1] denoting fraction of current step completed (for animation)

        # initialize camera to contain `level.board` (with some margin)
        rect = level.board.get_bounding_rect(margin=3)   # arbitrary value
        zoom_level = min(self.screen_width / rect.width, self.screen_height / rect.height) / DEFAULT_CELL_SIZE
        self.camera = Camera(center=V2(*rect.center), zoom_level=zoom_level)

        # initialize refresh sentinels
        self.window_size_changed    = False
        self.viewport_changed       = False
        self.shelf_changed          = False
        self.editor_changed         = False
        self.reblit_needed          = False

        self.held_entity: Union[Entity, None] = None
        self.hold_point: V2 = V2(0, 0)  # in [0, 1]^2

        self.selected_entity: Union[Entity, None] = None

        self.palette_rects: Sequence[Tuple[pg.Rect, Type[Entity]]] = [] # store palette item rects for easier collision
        self.widget_rects: Sequence[Tuple[pg.Rect, Widget]] = []        # store widget rects for easier collision
        self.shelf_icon_rects: Sequence[Tuple[pg.Rect, str]] = []       # store shelf icon rects for easier collision

    def run(self):
        """run the level in a resizable window at `TARGET_FPS`"""
        # initialize display, initialize output surfaces, and adjust camera
        self.handle_window_resize(DEFAULT_SCREEN_WIDTH, DEFAULT_SCREEN_HEIGHT)

        # initialize surfaces
        self.draw_level()
        self.draw_shelf()
        self.draw_editor()

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
                    self.mouse_buttons_pressed.add(event.button)
                    self.handle_mousebuttondown(event.button)
                elif event.type == pg.MOUSEBUTTONUP:
                    self.mouse_buttons_pressed.remove(event.button)
                    self.handle_mousebuttonup(event.button)
                elif event.type == pg.MOUSEMOTION:
                    self.mouse_pos = V2(*event.pos)
                    self.handle_mousemotion(event.rel)
            
            self.handle_keys_pressed()
            
            # handle overlay animations
            self.handle_shelf_animation()
            self.handle_editor_animation()

            # handle level execution
            if not self.edit_mode and not self.paused:
                self.prev_step_elapsed += clock.get_time()
                # if enough time has elapsed, step the level
                interval = LEVEL_STEP_INTERVAL // (FAST_FORWARD_FACTOR if self.fast_forward else 1)
                if self.prev_step_elapsed > interval:
                    self.level.step()
                    self.prev_step_elapsed = 0
                    if self.level.won:
                        print("good job")
                        # TODO: show congrats screen or something
                # update step progress
                self.step_progress = self.prev_step_elapsed / LEVEL_STEP_INTERVAL
                self.viewport_changed = True
            
            # handle output
            if self.window_size_changed:
                # trigger total re-draw
                self.viewport_changed = True
                self.shelf_changed = True
                self.editor_changed = True
                self.window_size_changed = False

            if self.viewport_changed:
                self.draw_level()
                self.reblit_needed = True
                self.viewport_changed = False
            
            if self.shelf_changed:
                self.draw_shelf()
                self.reblit_needed = True
                self.shelf_changed = False
            
            if self.editor_changed:
                self.draw_editor()
                self.reblit_needed = True
                self.editor_changed = False

            if self.reblit_needed:
                # blit updated surfs to the screen
                self.screen.blit(self.viewport_surf, (0, 0))
                self.screen.blit(self.shelf_surf, (0, self.screen_height - self.shelf_height_onscreen))
                self.screen.blit(self.editor_surf, (self.screen_width - self.editor_width_onscreen, 0))
                # draw held entity at cursor
                self.draw_held_entity()
                # draw play/pause controls
                self.draw_play_pause()
                self.reblit_needed = False
                pg.display.update()
            
            # TEMPORARY
            # fps = round(clock.get_fps())
            # pg.draw.rect(self.screen, (0, 0, 0), pg.Rect(0, 0, 30, 30))
            # render_text_centered(str(fps), (255, 255, 255), self.screen, (15, 15), 25)
            # pg.display.update()
                
    def handle_window_resize(self, new_width, new_height):
        self.screen_width = max(new_width, MIN_SCREEN_WIDTH)
        self.screen_height = max(new_height, MIN_SCREEN_HEIGHT)
        self.screen = pg.display.set_mode((self.screen_width, self.screen_height), pg.RESIZABLE)
        self.window_size_changed = True

        self.viewport_surf = pg.Surface((self.screen_width, self.screen_height))
        self.shelf_surf = pg.Surface((self.screen_width, SHELF_HEIGHT), pg.SRCALPHA)
        self.editor_surf = pg.Surface((EDITOR_WIDTH, self.screen_height - SHELF_HEIGHT), pg.SRCALPHA)

    def handle_shelf_animation(self):
        if self.shelf_state == "closing":
            self.shelf_height_onscreen -= SHELF_ANIMATION_SPEED
            if self.shelf_height_onscreen <= 0:
                self.shelf_height_onscreen = 0
                self.shelf_state = "closed"
            self.reblit_needed = True
        elif self.shelf_state == "opening":
            self.shelf_height_onscreen += SHELF_ANIMATION_SPEED
            if self.shelf_height_onscreen >= SHELF_HEIGHT:
                self.shelf_height_onscreen = SHELF_HEIGHT
                self.shelf_state = "open"
            self.reblit_needed = True

    def handle_editor_animation(self):
        if self.editor_state == "closing":
            self.editor_width_onscreen -= EDITOR_ANIMATION_SPEED
            if self.editor_width_onscreen <= 0:
                self.editor_width_onscreen = 0
                self.editor_state = "closed"
            self.reblit_needed = True
        elif self.editor_state == "opening":
            self.editor_width_onscreen += EDITOR_ANIMATION_SPEED
            if self.editor_width_onscreen >= EDITOR_WIDTH:
                self.editor_width_onscreen = EDITOR_WIDTH
                self.editor_state = "open"
            self.reblit_needed = True

    def toggle_playing(self):
        # toggle shelf state (initiates animation (if not already in progress))
        if self.shelf_state in ("open", "closed"):
            if self.edit_mode and self.held_entity is None:
                self.deselect_entity()
                self.shelf_state = "closing"
                self.edit_mode = False
                self.paused = False
                self.level.save_state()         # freeze current board/palette state
                self.viewport_changed = True
            elif not self.edit_mode:
                self.shelf_state = "opening"
                self.level.load_saved_state()   # revert board and palette
                self.edit_mode = True
                self.viewport_changed = True

    def handle_keydown(self, key):
        if key == pg.K_ESCAPE:
            self.running = False
        elif key == pg.K_SPACE:
            self.toggle_playing()
        elif key == pg.K_r:
            # rotate held/selected entity
            e = self.held_entity if self.held_entity else self.selected_entity
            if e and e.orients:
                e.orientation = e.orientation.rot90(1)
                self.viewport_changed = True
                self.editor_changed = True

    def handle_keyup(self, key):
        pass

    def handle_keys_pressed(self):
        pass
        # for key in self.keys_pressed:
        #     if key in self.pan_keys_map:
        #         disp = self.pan_keys_map[key]
        #         self.camera.pan(disp)
        #         # print("camera center:", self.camera.center)
        #         self.viewport_changed = True

    def handle_mousebuttondown(self, button):
        # handle camera zooming (scroll wheel)
        zoom_direction = 0
        if button == 4:    # zoom in
            zoom_direction = 1
        elif button == 5:   # zoom out
            zoom_direction = -1
        
        if zoom_direction != 0:
            pivot = self.camera.get_world_coords(self.mouse_pos, self.screen_width, self.screen_height)
            self.camera.zoom(zoom_direction, pivot)
            self.viewport_changed = True
        
        # left click
        if button == 1:
            # handle shelf icons
            for rect, icon in self.shelf_icon_rects:
                if rect.collidepoint(*self.mouse_pos):
                    # print(icon)
                    if icon == "play":
                        if self.edit_mode:
                            self.toggle_playing()
                        else:
                            self.paused = not self.paused
                    elif icon == "stop":
                        self.toggle_playing()
                    elif icon == "fast_forward":
                        self.fast_forward = not self.fast_forward
                    self.reblit_needed = True

            if not self.edit_mode:
                return
            # handle entity holding (left click)
            if self.mouse_pos.y >= self.screen_height - self.shelf_height_onscreen:
                # cursor is over shelf
                adjusted_pos = self.mouse_pos - V2(0, self.screen_height - self.shelf_height_onscreen)
                for rect, e_type in self.palette_rects:
                    if rect.collidepoint(*adjusted_pos):
                        # pick up entity (from palette)
                        self.held_entity = e_type()  # create new entity
                        self.hold_point = V2(0.5, 0.5)
                        self.level.palette.remove(self.held_entity)
                        self.deselect_entity()
                        self.shelf_changed = True
                        break
            elif self.mouse_pos.x >= self.screen_width - self.editor_width_onscreen:
                # cursor is over editor
                adjusted_pos = self.mouse_pos - V2(self.screen_width - self.editor_width_onscreen, 0)
                for hitbox, widget in self.widget_rects:
                    if hitbox.collidepoint(*adjusted_pos):
                        widget.handle_click(adjusted_pos)
                        self.editor_changed = True      # just redraw every time (easier)
                        self.viewport_changed = True    # ^^^
                        break
            else:
                # cursor is over board
                pos_float = self.camera.get_world_coords(self.mouse_pos, self.screen_width, self.screen_height)
                pos = pos_float.floor()
                cell = self.level.board.get(*pos)
                if cell:
                    e = cell[-1]    # select last element; TODO: figure out if this is a problem lol
                    if not e.locked:
                        # pick up entity (from board)
                        self.held_entity = e
                        self.hold_point = pos_float.fmod(1)
                        self.level.board.remove(*pos, self.held_entity)
                        # deselect current selection if picking up something else
                        if self.selected_entity is not self.held_entity:
                            self.deselect_entity()
                        self.viewport_changed = True
                else:
                    self.deselect_entity()
   
    def handle_mousebuttonup(self, button):
        # handle entity holding (left click)
        if button == 1 and self.held_entity is not None:
            if self.mouse_pos.y >= self.screen_height - self.shelf_height_onscreen:
                # cursor is over shelf
                self.level.palette.add(self.held_entity)
                self.shelf_changed = True
                self.held_entity = None
                self.deselect_entity()
            else:
                # cursor is over board
                pos = (self.camera.get_world_coords(self.mouse_pos, self.screen_width, self.screen_height)).floor()
                # drop entity
                self.level.board.insert(*pos, self.held_entity)
                # select entity that was just dropped
                self.select_entity(self.held_entity)
                self.held_entity = None

    def handle_mousemotion(self, rel):
        # pan camera if right click is held
        if 3 in self.mouse_buttons_pressed:
            disp = V2(*rel) / self.camera.get_cell_size_px()
            self.camera.pan_abs(-disp)
            self.viewport_changed = True
        
        if self.held_entity is not None:
            self.reblit_needed = True

    def draw_level(self):
        """draw the level onto `viewport_surf` using `self.step_progress` for animation state"""
        # TODO: draw grid first (???)
        self.viewport_surf.fill(VIEWPORT_BG_COLOR)

        s = self.camera.get_cell_size_px()
        surf_center = V2(*self.viewport_surf.get_rect().center)
        surf_width, surf_height = self.viewport_surf.get_size()

        def grid_to_px(pos: V2) -> V2:
            return (surf_center + (pos - self.camera.center) * s).floor()

        w = surf_width / s + 2
        h = surf_height / s + 2
        grid_rect = pg.Rect(
            floor(self.camera.center.x - w / 2),
            floor(self.camera.center.y - h / 2),
            ceil(w) + 1,
            ceil(h) + 1
        )
        
        grid_line_width = round(DEFAULT_GRID_LINE_WIDTH * self.camera.zoom_level ** 0.5)
        grid_line_width = clamp(grid_line_width, MIN_GRID_LINE_WIDTH, MAX_GRID_LINE_WIDTH)
        # grid_line_width = 1

        # draw board
        for grid_pos, cell in self.level.board.get_cells(grid_rect):
            if not cell: continue
            draw_pos = grid_to_px(grid_pos)
            neighborhood = [
                [self.level.board.get(*(grid_pos + V2(x_offset, y_offset))) for x_offset in range(-2, 3)]
                for y_offset in range(-2, 3)
            ]
            for e in sorted(cell, key=lambda e: e.draw_precedence):
                rect = pg.Rect(*draw_pos, s + 1, s + 1)
                e.draw_onto(self.viewport_surf, rect, self.edit_mode, self.selected_entity is e, self.step_progress, neighborhood)
                
        # draw grid with dynamic line width
        for x in range(grid_rect.width):
            x_grid = grid_rect.left + x
            x_px, _ = grid_to_px(V2(x_grid, 0))
            pg.draw.line(
                self.viewport_surf,
                GRID_LINE_COLOR,
                (x_px, 0),
                (x_px, surf_height),
                width=grid_line_width
            )
        for y in range(grid_rect.height):
            y_grid = grid_rect.top + y
            _,  y_px = grid_to_px(V2(0, y_grid))
            pg.draw.line(
                self.viewport_surf,
                GRID_LINE_COLOR,
                (0, y_px),
                (surf_width, y_px),
                width=grid_line_width
            )

    def draw_shelf(self):
        if self.shelf_state == "closed":
            return      # NoOp
        
        self.shelf_surf.fill(SHELF_BG_COLOR)

        # draw palette
        self.palette_rects.clear()
        for i, (e_type, count) in enumerate(self.level.palette.get_all()):
            margin = (SHELF_HEIGHT - PALETTE_ITEM_SIZE) // 2
            rect = pg.Rect(
                margin + (PALETTE_ITEM_SIZE + margin + PALETTE_ITEM_SPACING) * i,
                margin,
                PALETTE_ITEM_SIZE,
                PALETTE_ITEM_SIZE
            )
            self.palette_rects.append((rect, e_type))
            if count > 0:   # only draw item if there are any left (maintains spacing)
                temp_entity = e_type()
                temp_entity.draw_onto(self.shelf_surf, rect, edit_mode=True)
                # pg.draw.rect(self.shelf_surf, (0, 255, 0), rect)
                pg.draw.circle(self.shelf_surf, (255, 0, 0), rect.topright, 14)
                render_text_centered(str(count), (255, 255, 255), self.shelf_surf, rect.topright, 22, bold=True)

    def draw_editor(self):
        self.editor_surf.fill(EDITOR_BG_COLOR)

        if self.editor_state == "closed" or self.selected_entity is None:
            return      # NoOp

        y_pos = EDITOR_WIDGET_SPACING

        # render header
        header_font_height = 26
        for word in wrap_text(self.selected_entity.name, 12):
            render_text_centered(
                word,
                (0, 0, 0),
                self.editor_surf,
                (EDITOR_WIDTH // 2, y_pos + header_font_height // 2),
                header_font_height,
                bold=True
            )
            y_pos += header_font_height

        # draw widgets
        y_pos += EDITOR_WIDGET_SPACING
        self.widget_rects.clear()
        for w in self.selected_entity.get_widgets():
            h = EDITOR_WIDTH / w.aspect_ratio
            rect = pg.Rect(0, y_pos, EDITOR_WIDTH, h)
            w.draw_onto(self.editor_surf, rect)
            self.widget_rects.append((rect, w))
            y_pos += h + EDITOR_WIDGET_SPACING

    def draw_held_entity(self):
        if self.held_entity is None:
            return
        s = self.camera.get_cell_size_px()
        rect = pg.Rect(*self.mouse_pos, s + 1, s + 1)
        rect.move_ip(*(-self.hold_point * s - V2(1, 1)))
        self.held_entity.draw_onto(self.screen, rect, self.edit_mode)

    def select_entity(self, entity):
        self.selected_entity = entity
        self.editor_state = "opening"
        self.viewport_changed = True
        self.editor_changed = True
    
    def deselect_entity(self):
        self.selected_entity = None
        self.editor_state = "closing"
        self.viewport_changed = True
        self.editor_changed = True

    def draw_play_pause(self):
        # # TEMPORARY
        # if not self.edit_mode:
        #     w = SHELF_ICON_SIZE * 3 + SHELF_ICON_SPACING * 4
        #     bg = pg.Surface((w, SHELF_HEIGHT))
        #     bg.fill((127, 127, 127))
        #     bg.set_alpha(240)
        #     self.screen.blit(bg, (self.screen_width - w, self.screen_height - SHELF_HEIGHT))

        if self.edit_mode:
            shelf_icons = ["play", None]
        else:
            shelf_icons = ["stop", "play", "fast_forward"]
        
        self.shelf_icon_rects.clear()
        for i, icon in enumerate(shelf_icons[::-1]):
            rect = pg.Rect(
                self.screen_width - (SHELF_ICON_SIZE + SHELF_ICON_SPACING) * (i + 1),
                self.screen_height - (SHELF_HEIGHT + SHELF_ICON_SIZE) // 2,
                SHELF_ICON_SIZE,
                SHELF_ICON_SIZE
            )
            self.shelf_icon_rects.append((rect, icon))
            # pg.draw.rect(self.screen, (0, 0, 0), rect, width=1)
            if icon == "play":
                # color = SHELF_ICON_COLOR_OFF if not self.edit_mode and self.paused else SHELF_ICON_COLOR_ON
                color = SHELF_ICON_COLOR_OFF if self.edit_mode or self.paused else SHELF_ICON_COLOR_ON
                draw_aapolygon(self.screen, [
                    rect.topleft,
                    rect.bottomleft,
                    rect.midright
                ], color)
            elif icon == "stop":
                draw_aapolygon(self.screen, [
                    rect.topleft,
                    rect.bottomleft,
                    rect.bottomright,
                    rect.topright
                ], SHELF_ICON_COLOR_OFF)
            elif icon == "fast_forward":
                color = SHELF_ICON_COLOR_ON if self.fast_forward else SHELF_ICON_COLOR_OFF
                draw_aapolygon(self.screen, [
                    rect.topleft,
                    rect.bottomleft,
                    (rect.right - rect.width // 2.5, rect.centery)
                ], color)
                draw_aapolygon(self.screen, [
                    (rect.left + rect.width // 2.5, rect.top),
                    (rect.left + rect.width // 2.5, rect.bottom),
                    (rect.right, rect.centery)
                ], color)

if __name__ == "__main__":
    LevelRunner(test_level2).run()
