# --- Rendering and UI --- #
from typing import Union, Type, Sequence, Tuple, Optional
from math import floor, ceil
import pygame as pg

from entities import Entity, Wirable
from widgets import Widget, WireEditor
from engine import Board, Level
from rendering import Camera, DEFAULT_CELL_SIZE, SnapshotProvider, render_board
from levels import test_level, test_level2, resource_test, test_level3
from helpers import V2, draw_aapolygon, draw_rect_alpha, render_text_centered, clamp, wrap_text
from constants import *


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

        self.wiring_widget: Optional[WireEditor] = None     # if not None, the WireEditor that is currently being used

        self.shelf_state = "open"       # "open", "closed", "opening", or "closing"
        self.editor_state = "closed"    # "open", "closed", "opening", or "closing"
        self.substep_progress = 0.0        # float in [0, 1) denoting fraction of current step completed (for animation)

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

        self.pressed_icon: Optional[str] = None

        self.palette_rects: Sequence[Tuple[pg.Rect, Type[Entity]]]  = []    # store palette item rects for easier collision
        self.widget_rects: Sequence[Tuple[pg.Rect, Widget]]         = []    # store widget rects for easier collision
        self.shelf_icon_rects: Sequence[Tuple[pg.Rect, str]]        = []    # store shelf icon rects for easier collision

        self.snapshot_provider = SnapshotProvider(self)

    def run(self):
        """run the level in a resizable window at `TARGET_FPS`"""
        # initialize display, initialize output surfaces, and adjust camera
        self.handle_window_resize(DEFAULT_SCREEN_WIDTH, DEFAULT_SCREEN_HEIGHT)

        # initialize surfaces
        self.draw_level()
        self.draw_shelf()
        self.draw_editor()

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
                interval = LEVEL_SUBSTEP_INTERVAL / (FAST_FORWARD_FACTOR if self.fast_forward else 1)
                self.substep_progress += clock.get_time() / interval
                if self.substep_progress >= 1.0:
                    self.substep_progress -= 1.0
                    self.level.substep()
                    if self.level.won:
                        # pass
                        print("YOU WON!!!")
                        # TODO: show congrats screen or something
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
                # draw wiring mode indicator
                self.draw_wiring_indicator()
                # draw play/pause controls
                self.draw_shelf_icons()
                self.reblit_needed = False
                # pg.display.update()
            
            # TEMPORARY
            fps = round(clock.get_fps())
            pg.draw.rect(self.screen, (0, 0, 0), pg.Rect(0, 0, 30, 30))
            render_text_centered(str(fps), (255, 255, 255), self.screen, (15, 15), 25)
            pg.display.update()
                
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
        self.substep_progress = 0.0

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
                    self.pressed_icon = icon
                    self.reblit_needed = True
            
            if not self.edit_mode:
                return

            entity_clicked = None
            clicked_wire_widget = False

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
                        clicked_wire_widget = widget.handle_click(adjusted_pos)
                        if clicked_wire_widget:
                            self.finish_wiring(None)    # deselect previously selected wire widget
                            self.wiring_widget = widget
                        self.editor_changed = True      # just redraw every time (easier)
                        self.viewport_changed = True    # ^^^
                        break
            else:
                # cursor is over board
                pos_float = self.camera.get_world_coords(self.mouse_pos, self.screen_width, self.screen_height)
                pos = pos_float.floor()
                cell = self.level.board.get(*pos)
                if cell:
                    entity_clicked = cell[-1]    # click last element; TODO: figure out if this is a problem lol
            
                if self.wiring_widget is None:  # don't change selection if in wiring mode
                    # deselect current selection if clicking on something else
                    if self.selected_entity is not entity_clicked:
                        self.deselect_entity()
                    if entity_clicked is not None and not entity_clicked.locked:
                        # pick up entity (from board)
                        self.held_entity = entity_clicked
                        self.hold_point = pos_float.fmod(1)
                        self.level.board.remove(*pos, self.held_entity)
                        self.viewport_changed = True
                    else:
                        self.deselect_entity()

            if not clicked_wire_widget:
                self.finish_wiring(entity_clicked)
   
    def handle_mousebuttonup(self, button):
        # left click
        if button == 1:
            # handle shelf icons
            if self.pressed_icon is not None:
                if self.pressed_icon == "play/pause":
                    if self.edit_mode:
                        self.toggle_playing()
                    else:
                        self.paused = not self.paused
                elif self.pressed_icon == "stop":
                    self.toggle_playing()
                elif self.pressed_icon == "fast_forward":
                    self.fast_forward = not self.fast_forward
                self.pressed_icon = None
                self.reblit_needed = True
            
            # handle entity holding
            if self.held_entity is not None:
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
        
        if self.wiring_widget is not None:
            self.reblit_needed = True
            self.editor_changed = True

    def draw_level(self):
        """draw the level onto `viewport_surf` using `self.step_progress` for animation state"""
        render_board(self.level.board, self.viewport_surf, self.camera, self.edit_mode, self.selected_entity, self.substep_progress)

    def draw_shelf(self):        
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
                temp_entity.draw_onto_base(self.shelf_surf, rect, edit_mode=True)
                # pg.draw.rect(self.shelf_surf, (0, 255, 0), rect)
                pg.draw.circle(self.shelf_surf, (255, 0, 0), rect.topright, 14)
                render_text_centered(str(count), (255, 255, 255), self.shelf_surf, rect.topright, 20, bold=True)

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
        for w in self.selected_entity.widgets:
            h = EDITOR_WIDTH / w.aspect_ratio
            rect = pg.Rect(0, y_pos, EDITOR_WIDTH, h)
            w.draw_onto(self.editor_surf, rect, snapshot_provider=self.snapshot_provider)
            self.widget_rects.append((rect, w))
            y_pos += h + EDITOR_WIDGET_SPACING

    def draw_held_entity(self):
        if self.held_entity is None: return
        s = self.camera.get_cell_size_px()
        rect = pg.Rect(*self.mouse_pos, s + 1, s + 1)
        rect.move_ip(*(-self.hold_point * s))
        self.held_entity.draw_onto(self.screen, rect, self.edit_mode)   # pass in True here to show selection highlight

        # TEMPORARY: copied from `render_board`
        s = self.camera.get_cell_size_px()
        def grid_to_px(pos: V2) -> V2:
            return (V2(*self.viewport_surf.get_rect().center) + (pos - self.camera.center) * s).floor()

        # draw wiring while moving entity
        if self.held_entity.has_ports:
            wire_width = round(DEFAULT_GRID_LINE_WIDTH * self.camera.zoom_level ** 0.5)
            for _, other, _ in self.held_entity.wirings:
                if other is not None:
                    other_pos = grid_to_px(self.level.board.find(other) + V2(0.5, 0.5))
                    pg.draw.line(self.screen, WIRE_COLOR_OFF, tuple(other_pos), rect.center, wire_width)


    def draw_wiring_indicator(self):
        if self.wiring_widget is None: return

        # TEMPORARY: copied from `render_board`
        s = self.camera.get_cell_size_px()
        def grid_to_px(pos: V2) -> V2:
            return (V2(*self.viewport_surf.get_rect().center) + (pos - self.camera.center) * s).floor()

        start = grid_to_px(self.level.board.find(self.selected_entity) + V2(0.5, 0.5))
        wire_width = round(DEFAULT_GRID_LINE_WIDTH * self.camera.zoom_level ** 0.5)
        pg.draw.line(self.screen, WIRE_COLOR_OFF, tuple(start), tuple(self.mouse_pos), wire_width)


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

    def draw_shelf_icons(self):
        if self.edit_mode:
            shelf_icons = ["play/pause", None]
        else:
            shelf_icons = ["stop", "play/pause", "fast_forward"]
        
        self.shelf_icon_rects.clear()
        for i, icon in enumerate(shelf_icons[::-1]):
            rect = pg.Rect(
                self.screen_width - (SHELF_ICON_SIZE + SHELF_ICON_SPACING) * (i + 1),
                self.screen_height - (SHELF_HEIGHT + SHELF_ICON_SIZE) // 2,
                SHELF_ICON_SIZE,
                SHELF_ICON_SIZE
            )
            self.shelf_icon_rects.append((rect.copy(), icon))

            # determine foreground and background draw colors
            color = SHELF_ICON_COLOR
            bg_color = SHELF_ICON_BG_COLOR
            if icon == "fast_forward" and not self.fast_forward:
                color = SHELF_ICON_COLOR_OFF
            if icon == self.pressed_icon:
                color = SHELF_ICON_COLOR_PRESSED
                bg_color = SHELF_ICON_BG_COLOR_PRESSED
            
            # prevent double opacity when shelf is open
            if self.shelf_state == "open":
                bg_color = (*bg_color[:3], 0)

            if icon is not None:
                # draw gray background
                draw_rect_alpha(self.screen, bg_color, rect, width=0, border_radius=16)
                pg.draw.rect(self.screen, color, rect, width=4, border_radius=16)
            
            rect.inflate_ip(-SHELF_ICON_PADDING, -SHELF_ICON_PADDING)
            if icon == "play/pause":
                if self.paused or self.edit_mode:
                    draw_aapolygon(self.screen, [
                        rect.topleft,
                        rect.bottomleft,
                        rect.midright
                    ], color)
                else:
                    w = round(rect.width // 3)
                    draw_aapolygon(self.screen, [
                        rect.topleft,
                        rect.bottomleft,
                        (rect.left + w, rect.bottom),
                        (rect.left + w, rect.top)
                    ], color)
                    draw_aapolygon(self.screen, [
                        rect.topright,
                        rect.bottomright,
                        (rect.right - w, rect.bottom),
                        (rect.right - w, rect.top)
                    ], color)
            elif icon == "stop":
                draw_aapolygon(self.screen, [
                    rect.topleft,
                    rect.bottomleft,
                    rect.bottomright,
                    rect.topright
                ], color)
            elif icon == "fast_forward":
                draw_aapolygon(self.screen, [
                    rect.topleft,
                    rect.bottomleft,
                    (rect.right - rect.width // 2.2, rect.centery)
                ], color)
                draw_aapolygon(self.screen, [
                    (rect.left + rect.width // 2.2, rect.top),
                    (rect.left + rect.width // 2.2, rect.bottom),
                    (rect.right, rect.centery)
                ], color)

    def finish_wiring(self, e):
        if self.wiring_widget is None: return           # NoOp

        successful = False

        if any([
            e is None,
            e is self.wiring_widget.entity,             # cannot connect to self
            not isinstance(e, Wirable)
        ]):
            # clear connection
            self.wiring_widget.set_value(None, None)
            successful = True
        else:
            # only connect if input-output or output-input and target (`e`) has slot available
            ao = e.available_outputs()
            ai = e.available_inputs()
            if self.wiring_widget.is_input and ao:
                j = min(ao)
                self.wiring_widget.set_value(e, j)
                e.wirings[j][1] = self.wiring_widget.entity     # other side of connection
                e.wirings[j][2] = self.wiring_widget.wire_index # ^^^
                successful = True
            elif not self.wiring_widget.is_input and ai:
                j = min(ai)
                self.wiring_widget.set_value(e, j)
                e.wirings[j][1] = self.wiring_widget.entity     # other side of connection
                e.wirings[j][2] = self.wiring_widget.wire_index # ^^^
                successful = True
                    
        if successful:
            self.wiring_widget.in_use = False
            self.wiring_widget = None
            self.editor_changed = True
            self.viewport_changed = True
        else:
            # TODO: maybe play a sound here (or otherwise indicate soft failure)
            print("INVALID CONNECTION (no compatible un-used ports)")


if __name__ == "__main__":
    LevelRunner(test_level2).run()
