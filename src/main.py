# --- Rendering and UI --- #
from typing import List, Union, Type, Sequence, Tuple, Optional
from math import floor, ceil
import pygame as pg

from entities import Entity, Wirable
from modals import Modal
from postprocessing import PostprocessingEffect
from widgets import Widget, WireEditor
from engine import Board, Level
from rendering import Camera, DEFAULT_CELL_SIZE, SnapshotProvider, render_board
from levels import *
from helpers import V2, draw_aapolygon, draw_rect_alpha, render_text_centered_x_wrapped, render_text_centered_xy, clamp
from constants import *


class LevelRunner:
    # pan_keys_map = {
    #     pg.K_w: Direction.NORTH,
    #     pg.K_s: Direction.SOUTH,
    #     pg.K_a: Direction.WEST,
    #     pg.K_d: Direction.EAST
    # }A

    def __init__(self, level_queue: List[Level], postprocessing_effects: Sequence[PostprocessingEffect]=[]):
        self.level_queue = level_queue
        self.postprocessing_effects = postprocessing_effects

        self.screen_width = DEFAULT_SCREEN_WIDTH
        self.screen_height = DEFAULT_SCREEN_HEIGHT

        self.advance_level()

        self.keys_pressed = set()
        self.mouse_buttons_pressed = set()
        self.mouse_pos = V2(0, 0)

        self.palette_rects: Sequence[Tuple[pg.Rect, Type[Entity]]]  = []    # store palette item rects for easier collision
        self.widget_rects: Sequence[Tuple[pg.Rect, Widget]]         = []    # store widget rects for easier collision
        self.shelf_icon_rects: Sequence[Tuple[pg.Rect, str]]        = []    # store shelf icon rects for easier collision

        self.snapshot_provider = SnapshotProvider(self)

    def advance_level(self):
        if not self.level_queue:
            raise RuntimeError("Cannot advance to next level; Error queue is empty!")

        self.level, *self.level_queue = self.level_queue
        self.reset_level()

    def reset_level(self):
        self.shelf_height_onscreen = SHELF_HEIGHT

        self.edit_mode = True
        self.paused = False
        self.fast_forward = False

        self.slow_motion = False

        self.wiring_widget: Optional[WireEditor] = None     # if not None, the WireEditor that is currently being used

        self.shelf_state = "open"           # "open", "closed", "opening", or "closing"
        self.editor_state = "closed"        # "open", "closed", "opening", or "closing"
        self.editor_state_queue = []
        self.substep_progress = 0.0         # float in [0, 1) denoting fraction of current step completed (for animation)

        self.editor_width_onscreen = 0
        self.editor_content_height = None

        self.editor_scroll_amt = 0

        # initialize camera to contain `level.board` (with some margin)
        rect = self.level.board.get_bounding_rect(margin=3)   # arbitrary value
        zoom_level = min(self.screen_width / rect.width, self.screen_height / rect.height) / DEFAULT_CELL_SIZE
        self.camera = Camera(center=V2(*rect.center), zoom_level=zoom_level)

        # initialize refresh sentinels
        self.window_size_changed    = True
        self.viewport_changed       = True
        self.shelf_changed          = True
        self.editor_changed         = True
        self.reblit_needed          = True

        self.held_entity: Union[Entity, None] = None
        self.hold_point: V2 = V2(0, 0)  # in [0, 1]^2

        self.selected_entity: Union[Entity, None] = None
        self.editing_entity: Union[Entity, None] = None
        # self.selected_entity_queue = []

        self.pressed_icon: Optional[str] = None

        self.current_modal: Union[Modal, None] = None


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

            # fetch events
            events = list(pg.event.get())

            # pass events to any modals
            if self.current_modal:
                self.current_modal.handle_events(events)    # consumes events

            self.handle_events(events)                      # consumes events
            
            # handle overlay animations
            self.handle_shelf_animation()
            self.handle_editor_animation()

            # switch editing entity only when panel is closed or opening
            if self.editor_state in ("closed", "opening"):
                if self.editing_entity is not self.selected_entity:
                    self.editor_scroll_amt = 0      # reset scroll amount
                self.editing_entity = self.selected_entity
                self.editor_changed = True
            
            # handle level win state
            if self.level.won:
                if self.current_modal is None:
                    print("Level has been won, generating modal")
                    self.generate_congrats_modal()
            
            # handle level execution
            if not self.edit_mode and not self.paused:
                execution_speed_factor = 1.0

                if self.fast_forward:
                    execution_speed_factor *= FAST_FORWARD_FACTOR
                
                if self.slow_motion:
                    execution_speed_factor *= SLOW_MOTION_FACTOR

                interval = LEVEL_SUBSTEP_INTERVAL / execution_speed_factor
                self.substep_progress += clock.get_time() / interval
                if self.substep_progress >= 1.0:
                    self.substep_progress -= 1.0
                    self.level.substep()
                self.viewport_changed = True
                self.editor_changed = True      # needed for updating snapshots

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
            
            # handle modal rendering
            if self.current_modal:
                self.current_modal.draw_onto(self.screen)
            
            # apply postprocessing effects
            for effect in self.postprocessing_effects:
                self.screen = effect.apply_effect(self.screen)
            self.true_screen.blit(self.screen, (0, 0))

            # # TEMPORARY
            # fps = round(clock.get_fps())
            # pg.draw.rect(self.true_screen, (0, 0, 0), pg.Rect(0, 0, 30, 30))
            # render_text_centered(str(fps), (255, 255, 255), self.true_screen, (15, 15), 25)

            pg.display.update()

    def handle_events(self, events):
        for event in events:
            if event.type == pg.QUIT:
                self.running = False
            elif event.type == pg.VIDEORESIZE:
                self.handle_window_resize(event.w, event.h)
            elif event.type == pg.KEYDOWN:
                # --------- TEMPORARY -------#
                if event.key in (pg.K_RETURN, pg.K_KP_ENTER):
                    self.level.won = True
                    print("FORCING LEVEL WIN")
                # ---------------------------#
                self.keys_pressed.add(event.key)
                self.handle_keydown(event.key)
            elif event.type == pg.KEYUP:
                self.keys_pressed.discard(event.key)
                self.handle_keyup(event.key)
            elif event.type == pg.MOUSEBUTTONDOWN:
                self.mouse_buttons_pressed.add(event.button)
                self.handle_mousebuttondown(event.button)
            elif event.type == pg.MOUSEBUTTONUP:
                self.mouse_buttons_pressed.discard(event.button)
                self.handle_mousebuttonup(event.button)
            elif event.type == pg.MOUSEMOTION:
                self.mouse_pos = V2(*event.pos)
                self.handle_mousemotion(event.rel)
        
        self.handle_keys_pressed()

        return set()    # we consume all events

    def handle_window_resize(self, new_width, new_height):
        self.screen_width = max(new_width, MIN_SCREEN_WIDTH)
        self.screen_height = max(new_height, MIN_SCREEN_HEIGHT)
        self.screen = pg.Surface((self.screen_width, self.screen_height))
        self.true_screen = pg.display.set_mode((self.screen_width, self.screen_height), pg.RESIZABLE)
        self.window_size_changed = True

        self.viewport_surf = pg.Surface((self.screen_width, self.screen_height))
        self.shelf_surf = pg.Surface((self.screen_width, SHELF_HEIGHT), pg.SRCALPHA)
        self.editor_surf = pg.Surface((EDITOR_WIDTH, self.screen_height - SHELF_HEIGHT), pg.SRCALPHA)
        # self.editor_surf = pg.Surface((EDITOR_WIDTH, self.screen_height), pg.SRCALPHA)

    def generate_congrats_modal(self):
        self.deselect_entity()
        self.fast_forward = False
        self.slow_motion = True

        # def continue_func():
        #     self.current_modal = None
        #     self.level.won = False
        #     self.slow_motion = False

        def return_func():
            if not self.edit_mode:
                self.toggle_playing()
            self.level.won = False
            self.current_modal = None
            self.slow_motion = False

        def quit_func():
            self.running = False

        buttons = [
            # ("continue current level", continue_func),
            ("return to editor", return_func),
            ("quit", quit_func)
        ]

        if self.level_queue:
            buttons.insert(0, ("next level", self.advance_level))

        self.current_modal = Modal(f"Congrats! You beat {self.level.name}", buttons)

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
        elif self.editor_state_queue:
            self.editor_state = self.editor_state_queue.pop(0)

    def toggle_playing(self):
        # toggle shelf state (initiates animation (if not already in progress))
        if self.shelf_state in ("open", "closed"):
            if self.edit_mode and self.held_entity is None:
                # self.deselect_entity()    
                self.shelf_state = "closing"
                self.edit_mode = False
                self.paused = False
                self.level.save_state()         # freeze current board/palette state
                self.viewport_changed = True
                self.editor_changed = True
            elif not self.edit_mode:
                self.shelf_state = "opening"
                self.level.load_saved_state()   # revert board and palette
                # references are now stale! need to update
                self.update_stale_references()
                self.edit_mode = True
                self.viewport_changed = True
                self.editor_changed = True
        self.substep_progress = 0.0
    
    def update_stale_references(self):
        if self.selected_entity is not None:
            self.selected_entity = self.level.entity_copy_memo[id(self.selected_entity)]
        if self.editing_entity is not None:
            self.editing_entity = self.level.entity_copy_memo[id(self.editing_entity)]

    def handle_keydown(self, key):
        if key == pg.K_ESCAPE:
            self.running = False
        elif key == pg.K_SPACE:
            self.toggle_playing()
        elif key == pg.K_r and self.edit_mode:
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
        mouse_over_shelf = self.mouse_pos.y >= self.screen_height - self.shelf_height_onscreen
        mouse_over_editor = self.mouse_pos.x >= self.screen_width - self.editor_width_onscreen

        # scroll wheel
        if button in (4, 5):
            if button == 4:
                scroll_direction = 1
            elif button == 5:
                scroll_direction = -1
            
            # handle editor scrolling
            editor_scrolled = False
            if mouse_over_editor:
                old_scroll_amt = self.editor_scroll_amt
                self.editor_scroll_amt += scroll_direction * EDITOR_SCROLL_SPEED
                min_scroll_amt = -(self.editor_content_height - self.editor_surf.get_height())
                if min_scroll_amt > 0: min_scroll_amt = 0
                # print("min_scroll_amt", min_scroll_amt)
                self.editor_scroll_amt = clamp(self.editor_scroll_amt, min_scroll_amt, 0)
                editor_scrolled = old_scroll_amt != self.editor_scroll_amt
                if editor_scrolled:
                    self.editor_changed = True
            
            # print(self.editor_scroll_amt)
            
            # # if unable to scroll editor, then zoom the camera
            # if not editor_scrolled:
            # if not over editor editor, then zoom the camera
            if not mouse_over_editor:
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
            
            # if not self.edit_mode:
            #     return

            entity_clicked = None
            clicked_wire_widget = False

            # handle entity holding (left click)
            if mouse_over_shelf:
                adjusted_pos = self.mouse_pos - V2(0, self.screen_height - self.shelf_height_onscreen)
                for rect, e_prototype in self.palette_rects:
                    if rect.collidepoint(*adjusted_pos):
                        # pick up entity (from palette)
                        new = e_prototype.get_instance()  # create new entity
                        self.held_entity = new
                        self.hold_point = V2(0.5, 0.5)
                        self.level.palette.remove(e_prototype)
                        self.deselect_entity()
                        self.select_entity(new)
                        self.shelf_changed = True
                        break
            elif mouse_over_editor:
                if self.edit_mode:      # cannot interact with editor if not in edit mode
                    adjusted_pos = self.mouse_pos - V2(self.screen_width - self.editor_width_onscreen, 0)
                    for hitbox, widget in self.widget_rects:
                        if hitbox.collidepoint(*adjusted_pos):
                            clicked_wire_widget = widget.handle_click(adjusted_pos)
                            if clicked_wire_widget:
                                self.finish_wiring(None)    # deselect previously selected wire widget
                                self.wiring_widget = clicked_wire_widget
                            self.editor_changed = True      # just redraw every time (easier)
                            self.viewport_changed = True    # ^^^
                            break
            else:   # mouse is over board
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
                        if self.edit_mode:
                            self.held_entity = entity_clicked
                            self.hold_point = pos_float.fmod(1)
                            self.level.board.remove(*pos, self.held_entity)
                            self.viewport_changed = True
                        if entity_clicked.editable:
                            self.select_entity(entity_clicked)
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
                    # break all wiring connections
                    if self.held_entity.has_ports:
                        self.held_entity.break_all_connections()
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
                    if self.held_entity.editable:
                        self.select_entity(self.held_entity)
                    self.held_entity = None
                    self.viewport_changed = True

    def handle_mousemotion(self, rel):
        # pan camera if right click is held
        if 3 in self.mouse_buttons_pressed:
            disp = V2(*rel) / self.camera.get_cell_size_px()
            self.camera.pan_abs(-disp)
            self.viewport_changed = True
        
        if self.held_entity is not None:
            self.reblit_needed = True
            self.editor_changed = True
        
        if self.wiring_widget is not None:
            self.editor_changed = True

    def draw_level(self):
        """draw the level onto `viewport_surf` using `self.step_progress` for animation state"""
        render_board(self.level.board, self.viewport_surf, self.camera, self.edit_mode, self.selected_entity, self.substep_progress)

    def draw_shelf(self):        
        self.shelf_surf.fill(SHELF_BG_COLOR)

        # draw palette
        self.palette_rects.clear()
        for i, (e_prototype, count) in enumerate(self.level.palette.get_all()):
            margin = (SHELF_HEIGHT - PALETTE_ITEM_SIZE) // 2
            rect = pg.Rect(
                margin + (PALETTE_ITEM_SIZE + margin + PALETTE_ITEM_SPACING) * i,
                margin,
                PALETTE_ITEM_SIZE,
                PALETTE_ITEM_SIZE
            )
            self.palette_rects.append((rect, e_prototype))
            if count > 0:   # only draw item if there are any left (maintains spacing)
                temp_entity = e_prototype.get_instance()
                temp_entity.draw_onto_base(self.shelf_surf, rect, edit_mode=True)
                # pg.draw.rect(self.shelf_surf, (0, 255, 0), rect)
                pg.draw.circle(self.shelf_surf, (255, 0, 0), rect.topright, 14)
                render_text_centered_xy(str(count), (255, 255, 255), self.shelf_surf, rect.topright, 20, bold=True)

    def draw_editor(self):
        self.editor_surf.fill(EDITOR_BG_COLOR)

        if self.editor_state == "closed" or self.editing_entity is None:
            return      # NoOp

        # render header
        header_font_size = EDITOR_WIDTH / 8
        header_text = self.editing_entity.name
        header_rect = render_text_centered_x_wrapped(
            header_text, (0, 0, 0), header_font_size,
            self.editor_surf, (EDITOR_WIDTH/2, 0), EDITOR_WIDTH,
            padding_top=EDITOR_WIDGET_SPACING,
            bold=True
        )
        y_pos = header_rect.bottom

        # header_font_height = EDITOR_WIDTH / 8
        # for word in wrap_text(header_text, 12):
        #     render_text_centered(
        #         word,
        #         (0, 0, 0),
        #         self.editor_surf,
        #         (EDITOR_WIDTH // 2, y_pos + header_font_height // 2),
        #         header_font_height,
        #         bold=True
        #     )
        #     y_pos += header_font_height
        
        # render read-only indicator
        read_only_indicator_font_height = header_font_size / 2
        if not self.edit_mode:
            render_text_centered_xy(
                "(read-only)",
                (0, 0, 0),
                self.editor_surf,
                (EDITOR_WIDTH // 2, y_pos + read_only_indicator_font_height // 2 + 4),  # pad down just a little extra
                read_only_indicator_font_height,
                bold=True
            )
        y_pos += read_only_indicator_font_height    # leave space regardless

        # draw widgets
        y_pos += EDITOR_WIDGET_SPACING
        self.widget_rects.clear()
        for w in self.editing_entity.widgets:
            h = EDITOR_WIDTH / w.aspect_ratio if w.aspect_ratio else 9999
            rect = pg.Rect(0, y_pos, EDITOR_WIDTH, h)
            w.draw_onto(self.editor_surf, rect, snapshot_provider=self.snapshot_provider)
            self.widget_rects.append((rect, w))
            y_pos += h + EDITOR_WIDGET_SPACING
        
        self.editor_content_height = y_pos - self.editor_scroll_amt

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
            wire_width = self.camera.get_wire_width()
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

        start = grid_to_px(self.level.board.find(self.editing_entity) + V2(0.5, 0.5))
        wire_width = self.camera.get_wire_width()
        pg.draw.line(self.screen, WIRE_COLOR_OFF, tuple(start), tuple(self.mouse_pos), wire_width)

    def select_entity(self, entity):
        self.selected_entity = entity
        self.editor_state_queue.append("opening")
        self.viewport_changed = True
        self.editor_changed = True
    
    def deselect_entity(self):
        self.selected_entity = None
        self.editor_state_queue.append("closing")
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
                self.screen_width - EDITOR_WIDTH/2 - SHELF_ICON_SIZE/2 - (SHELF_ICON_SIZE + SHELF_ICON_SPACING) * (i - 1),
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
            # break connection
            self.wiring_widget.break_connection()
            successful = True
        else:
            # only connect if input-output or output-input and target (`e`) has slot available
            # TODO: if target is at capacity but can further expand it's number of input/output ports, do so automatically
            ao = e.available_outputs()
            ai = e.available_inputs()
            j = None
            if self.wiring_widget.is_input and ao:
                j = min(ao)
            elif not self.wiring_widget.is_input and ai:
                j = min(ai)
            
            if j is not None:
                self.wiring_widget.make_connection(e, j)
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
    # LevelRunner(new_test_level).run()
    LevelRunner([level_1, level_2, level_3, level_4, level_5, level_6]).run()
    # LevelRunner(test_level2, [BarrelDistortion]).run()
    # LevelRunner(minimal_level).run()
