from math import ceil, floor
import pygame as pg

from engine import Board
from entities import Entity, Wirable
from helpers import V2, clamp
from constants import *



class Camera:
    """stores a center point and a zoom level (using floating-point board coordinates)"""
    min_zoom_level = 0.3
    max_zoom_level = 4.0

    pan_speed = 0.15
    zoom_speed = 0.10

    def __init__(self, center: 
        V2, zoom_level: float):
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
    
    def get_grid_line_width(self):
        w = round(DEFAULT_GRID_LINE_WIDTH * self.zoom_level)
        return clamp(w, MIN_GRID_LINE_WIDTH, MAX_GRID_LINE_WIDTH)

    def get_wire_width(self):
        w = round(DEFAULT_WIRE_WIDTH * self.zoom_level)
        return clamp(w, MIN_GRID_LINE_WIDTH, MAX_GRID_LINE_WIDTH)


def render_board(
    board: Board,
    surf: pg.Surface,
    cam: Camera,
    edit_mode: bool = False,
    selected_entity: Entity = None, 
    substep_progress: float = 0.0,
    wiring_visible: bool = True
):
    """render `board` to `surf` with the given parameters"""
    # TODO: draw carpets, then grid, then blocks
    # z_pos:     < 0          = 0        > 0
    surf.fill(VIEWPORT_BG_COLOR)

    s = cam.get_cell_size_px()
    surf_center = V2(*surf.get_rect().center)
    surf_width, surf_height = surf.get_size()

    def grid_to_px(pos: V2) -> V2:
        return (surf_center + (pos - cam.center) * s).floor()

    w = surf_width / s + 2
    h = surf_height / s + 2
    grid_rect = pg.Rect(
        floor(cam.center.x - w / 2),
        floor(cam.center.y - h / 2),
        ceil(w) + 1,
        ceil(h) + 1
    )
    
    grid_line_width = cam.get_grid_line_width()

    # draw board
    for grid_pos, cell in board.get_cells(grid_rect):
        if not cell: continue
        draw_pos = grid_to_px(grid_pos)
        neighborhood = [
            [board.get(*(grid_pos + V2(x_offset, y_offset))) for x_offset in range(-2, 3)]
            for y_offset in range(-2, 3)
        ]
        for e in sorted(cell, key=lambda e: e.draw_precedence):
            rect = pg.Rect(*draw_pos, s + 1, s + 1)
            e.draw_onto(surf, rect, edit_mode, selected_entity is e, substep_progress, neighborhood)
            
    # draw grid with dynamic line width
    for x in range(grid_rect.width):
        x_grid = grid_rect.left + x
        x_px, _ = grid_to_px(V2(x_grid, 0))
        pg.draw.line(
            surf,
            GRID_LINE_COLOR,
            (x_px, 0),
            (x_px, surf_height),
            width=grid_line_width
        )
    for y in range(grid_rect.height):
        y_grid = grid_rect.top + y
        _,  y_px = grid_to_px(V2(0, y_grid))
        pg.draw.line(
            surf,
            GRID_LINE_COLOR,
            (0, y_px),
            (surf_width, y_px),
            width=grid_line_width
        )
    
    # draw wires
    # TODO: make lines correct thickness when slanted
    # TODO: antialias lines
    if wiring_visible:
        wire_width = cam.get_wire_width()
        for pos, e in board.get_all(filter_type=Wirable):
            for index, (is_input, f, f_index) in enumerate(e.wirings):
                if f is None: continue
                f_pos = board.find(f)
                if f_pos is None:
                    continue
                    # raise RuntimeError("unable to find desired entity while drawing wiring")
                start = grid_to_px(pos + e.get_port_offset(is_input, index)) 
                end = grid_to_px(f_pos + f.get_port_offset(not is_input, f_index))
                color = WIRE_COLOR_ON if e.port_states[index] else WIRE_COLOR_OFF
                pg.draw.line(surf, color, tuple(start), tuple(end), wire_width)


class SnapshotProvider:
    """provides a clean interface for obtaining snapshots of the rendered board"""
    # TODO: decide if we like showing the selected_entity highlight in the snapshot or not
    zoom_level = 0.45    # arbitrary choice

    def __init__(self, level_runner):
        self.level_runner = level_runner

    def take_snapshot(self, entity, dims) -> pg.Surface:
        surf = pg.Surface(dims)
        if entity is self.level_runner.held_entity:
            return self.take_snapshot_at_mouse(dims)
            # # TODO: maybe draw a hand icon here showing that the entity is being held (?)
            # # for now, draw a fake empty board
            # cam = Camera(V2(0.5, 0.5), self.zoom_level)
            # render_board(
            #     Board(), surf, cam,
            #     selected_entity=self.level_runner.selected_entity,
            #     substep_progress=self.level_runner.substep_progress
            # )
        else:
            pos = self.level_runner.level.board.find(entity)
            if pos is None:
                raise ValueError(f"desired entity not found while taking snapshot ({entity})")
            cam = Camera(pos + V2(0.5, 0.5), self.zoom_level)
            render_board(
                self.level_runner.level.board, surf, cam,
                selected_entity=self.level_runner.selected_entity,
                substep_progress=self.level_runner.substep_progress
            )
        return surf
    
    def take_snapshot_at_mouse(self, dims):
        surf = pg.Surface(dims)
        pos = self.level_runner.camera.get_world_coords(
            self.level_runner.mouse_pos,
            self.level_runner.screen_width,
            self.level_runner.screen_height,
        )
        cam = Camera(pos, self.zoom_level)
        render_board(
            self.level_runner.level.board, surf, cam,
            selected_entity=self.level_runner.selected_entity,
            substep_progress=self.level_runner.substep_progress
        )
        return surf
