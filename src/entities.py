# --- Level Entities --- #
from __future__ import annotations  # allows self-reference in type annotations
from typing import Sequence
from abc import abstractmethod

import pygame as pg
import pygame.freetype
import pygame.gfxdraw
from pygame.transform import threshold

from helpers import V2, Direction, draw_aacircle, draw_chevron, draw_rectangle, render_text_centered, interpolate_colors, sgn
from colors import Color
from widgets import DirectionEditor, SmallIntEditor, Spacing, Widget


VELOCITY_CHEVRON_COLOR      = (0, 0, 0)
HIGHLIGHT_COLOR             = (255, 255, 0)
HIGHLIGHT_THICKNESS_MULT    = 0.10

HIGHLIGHT_INFLATION_FACTOR  = 1.2


class Entity:
    moves: bool = False
    orients: bool = False
    stops: bool = False
    merges: bool = False
    draw_precedence: int = 0

    def __init__(self, locked: bool):
        self.locked = locked
    
    def get_widgets(self) -> Sequence[Widget]:
        return []

    @abstractmethod
    def draw_onto(
        self,
        surf: pg.Surface,
        rect: pg.Rect,
        edit_mode: bool,
        selected: bool = False,
        step_progress: float = 0.0,
        neighborhood = (([],) * 5,) * 5
    ):
        # if selected:
        #     inflation = (HIGHLIGHT_INFLATION_FACTOR - 1) * rect.width
        #     inflated_rect = rect.inflate(inflation, inflation)
        #     inflated_surf = pg.Surface(inflated_rect.size, pg.SRCALPHA)
        #     inflated_surf.fill((0, 0, 0, 0))
        #     self.draw_onto_base(inflated_surf, inflated_surf.get_rect(), edit_mode, step_progress, neighborhood)
        #     temp_surf = pg.Surface(inflated_rect.size, pg.SRCALPHA)
        #     pg.transform.threshold(temp_surf, inflated_surf, (1, 1, 1), threshold=(254, 254, 254, 254), set_color=HIGHLIGHT_COLOR)
        #     # pg.draw.rect(inflated_surf, (255, 0, 0), inflated_surf.get_rect())

        #     # TODO: figure out thresholding nonsense (or just write custom function to do it)
        #     surf.blit(temp_surf, inflated_rect)
        self.draw_onto_base(surf, rect, edit_mode, step_progress, neighborhood)
        if selected:
            draw_rectangle(surf, rect, HIGHLIGHT_COLOR, thickness=rect.width*HIGHLIGHT_THICKNESS_MULT)

    @abstractmethod
    def draw_onto_base(
        self,
        surf: pg.Surface,
        rect: pg.Rect,
        edit_mode: bool,
        step_progress: float = 0.0,
        neighborhood = (([],) * 5,) * 5
    ):
        pass


class Carpet(Entity):
    stops = False
    draw_precedence = 0

    def __init__(self, locked: bool):
        super().__init__(locked)


class Block(Entity):
    stops = True
    draw_precedence = 1

    def __init__(self, locked: bool):
        super().__init__(locked)


class Barrier(Block):
    name = "Barrier"
    ascii_str = "█"
    stops = True
    
    # barriers are locked by default
    def __init__(self, locked: bool = True):
        super().__init__(locked)

    def draw_onto_base(self, surf: pg.Surface, rect: pg.Rect, edit_mode: bool, step_progress: float = 0.0, neighborhood = (([],) * 5,) * 5):
        pg.draw.rect(surf, (50, 50, 50), rect)

        s = rect.width
        # if selected:
        #     draw_rectangle(surf, rect, HIGHLIGHT_COLOR, thickness=s*HIGHLIGHT_THICKNESS_MULT)


class Barrel(Block):
    name = "Barrel"
    ascii_str = "B"
    moves = True
    stops = False
    merges = True
    draw_precedence = 2     # on top of all other blocks

    # barrels are unlocked by default
    def __init__(self, color: Color, velocity: Direction = Direction.NONE, locked: bool = False):
        super().__init__(locked)
        self.color = color
        self.velocity = velocity
        self.leaky = False
        self.draw_center = V2(0, 0)

    def __add__(self, other):
        return Barrel(self.color + other.color)
    
    @staticmethod
    def travel_curve(x):
        """integral of speed curve f'(x) = 2 - 2|2x - 1| with 0.5 hang time at the end"""
        if x <= 0.25:
            return 8 * x**2
        elif x <= 0.5:
            x -= 0.25
            return 0.5 + (4*x - 8*x**2)
        else:
            return 1.0

    def draw_onto_base(self, surf: pg.Surface, rect: pg.Rect, edit_mode: bool, step_progress: float = 0.0, neighborhood = (([],) * 5,) * 5):
        s = rect.width
        # travel = step_progress                          # continuous constant motion
        # travel = min(1.0, step_progress * 2)            # travel full distance during first half of step
        # travel = max(0.0, (step_progress - 0.5) * 2)    # travel full distance during second half of step
        travel = self.travel_curve(step_progress)
        # print(travel)
        self.draw_center = V2(*rect.center) + self.velocity * (rect.width - 1) * travel
        draw_radius = s * 0.3

        draw_color_rgb = self.color.rgb()

        # check for intersection with other barrel
        # if intersection found, take weighted average of colors
        n = len(neighborhood)
        for x in range(-n//2, n//2 + 1):
            for y in range(-n//2, n//2 + 1):
                if x == 0 and y == 0: continue  # skip self
                for e in neighborhood[y + n//2][x + n//2]:
                    if isinstance(e, Barrel):
                        dist = (e.draw_center - self.draw_center).length()
                        if dist < draw_radius * 2:
                            percentage = 1.0 - dist / (2 * draw_radius)
                            # print(f"intersecting by {dist} pixels ({percentage * 100:.0f}%)")
                            # smoothly transition towards merged color
                            draw_color_rgb = interpolate_colors(self.color.rgb(), (self.color + e.color).rgb(), percentage)
        
        # pg.draw.circle(surf, draw_color_rgb, tuple(self.draw_center), draw_radius)
        draw_aacircle(surf, *round(self.draw_center), round(draw_radius), draw_color_rgb)

        if edit_mode:
            draw_chevron(
                surf,
                self.draw_center + self.velocity * (s * 0.42),
                self.velocity,
                VELOCITY_CHEVRON_COLOR,
                round(s * 0.25),
                round(s ** 0.5 * 0.4),
                angle=120
            )
        
        # if selected:
        #     draw_rectangle(surf, rect, HIGHLIGHT_COLOR, thickness=s*HIGHLIGHT_THICKNESS_MULT)


class ResourceTile(Carpet):
    name = "Resource Tile"
    ascii_str = "O"

    # resource tiles are always locked
    def __init__(self, color: Color):
        super().__init__(True)
        self.color = color
    
    def draw_onto_base(self, surf: pg.Surface, rect: pg.Rect, edit_mode: bool, step_progress: float = 0.0, neighborhood = (([],) * 5,) * 5):
        r = round(rect.width * 0.75)    # 0.4 also looks good (different, but good)
        # round corner iff both neighbors are empty
        def contains_match(cell): return any(isinstance(e, ResourceTile) and e.color is self.color for e in cell)
        left = contains_match(neighborhood[2][1])
        top = contains_match(neighborhood[1][2])
        right = contains_match(neighborhood[2][3])
        bottom = contains_match(neighborhood[3][2])
        pg.draw.rect(
            surf, self.color.rgb(), rect,
            border_top_left_radius=-1 if top or left else r,
            border_top_right_radius=-1 if top or right else r,
            border_bottom_right_radius=-1 if bottom or right else r,
            border_bottom_left_radius=-1 if bottom or left else r,
        )

        s = rect.width
        # if selected:
        #     draw_rectangle(surf, rect, HIGHLIGHT_COLOR, thickness=s*HIGHLIGHT_THICKNESS_MULT)


class ResourceExtractor(Block):
    name = "Resource Extractor"
    ascii_str = "X"
    orients = True

    # resource extractors are unlocked by default
    def __init__(self, orientation: Direction = Direction.NORTH, locked: bool = False):
        super().__init__(locked)
        self.orientation = orientation
        self.period = 3
        self.phase = 1
    
    def get_widgets(self) -> Sequence[Widget]:
        return [
            DirectionEditor(self, "orientation"),
            # Spacing(20.0),
            SmallIntEditor(self, "period", (1, 5)),
            SmallIntEditor(self, "phase", (1, self.period)),
        ]
    
    def draw_onto_base(self, surf: pg.Surface, rect: pg.Rect, edit_mode: bool, step_progress: float = 0.0, neighborhood = (([],) * 5,) * 5):
        # TEMPORARY
        s = rect.width
        w = round(s * 0.1)
        draw_aacircle(surf, *rect.center, round(s * 0.35), (220, 220, 220))
        draw_chevron(
            surf,
            V2(*rect.center) + self.orientation * (s * 0.432),
            self.orientation,
            (220, 220, 220),
            round(s * 0.28),
            w,
            angle=108
        )

        # if selected:
        #     draw_rectangle(surf, rect, HIGHLIGHT_COLOR, thickness=s*HIGHLIGHT_THICKNESS_MULT)


class Boostpad(Carpet):
    name = "Boostpad"
    ascii_str = "X"
    orients = True

    # boostpads are unlocked by default
    def __init__(self, orientation: Direction = Direction.NORTH, locked: bool = False):
        super().__init__(locked)
        if (orientation is Direction.NONE):
            raise ValueError("Boostpad orientation cannot be `Direction.NONE`")
        self.orientation = orientation
    
    def get_widgets(self) -> Sequence[Widget]:
        return [
            DirectionEditor(self, "orientation")
        ]
    
    def draw_onto_base(self, surf: pg.Surface, rect: pg.Rect, edit_mode: bool, step_progress: float = 0.0, neighborhood = (([],) * 5,) * 5):
        s = rect.width        
        for i in range(3):
            draw_chevron(
                surf,
                V2(*rect.center) + self.orientation * (i - 0.4) * (s // 5),
                self.orientation,
                (0, 0, 0),
                s // 3,
                round(s * 0.05)
            )
        
        # if selected:
        #     draw_rectangle(surf, rect, HIGHLIGHT_COLOR, thickness=s*HIGHLIGHT_THICKNESS_MULT)


class Target(Carpet):
    name = "Target"
    ascii_str = "T"

    # targets are always locked
    def __init__(self, color: Color, count: int):
        super().__init__(True)
        self.color = color
        self.count = count
    
    def draw_onto_base(self, surf: pg.Surface, rect: pg.Rect, edit_mode: bool, step_progress: float = 0.0, neighborhood = (([],) * 5,) * 5):
        s = rect.width
        pg.draw.rect(surf, self.color.rgb(), rect)
        padding = s * 0.35
        radius = round(s * 0.2)
        pg.draw.rect(surf, (255, 255, 255), rect.inflate(-padding, -padding), border_radius=radius)
        render_text_centered(
            str(self.count),
            (0, 0, 0),
            surf,
            rect.center,
            s - padding * 1.75,
        )

        # if selected:
        #     draw_rectangle(surf, rect, HIGHLIGHT_COLOR, thickness=s*HIGHLIGHT_THICKNESS_MULT)

ENTITY_TYPES = [Barrel, Barrier, Boostpad, ResourceExtractor, ResourceTile, Target]
