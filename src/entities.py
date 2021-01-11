# --- Level Entities --- #
from __future__ import annotations  # allows self-reference in type annotations
from typing import Collection, Sequence, Tuple, Union
from abc import abstractmethod
from widgets import DirectionEditor, SmallIntEditor, Spacing, Widget

from helpers import V2, Direction, draw_aacircle, draw_chevron, draw_rectangle, render_text_centered, interpolate_colors, sgn
from colors import Color

import pygame as pg
import pygame.freetype
import pygame.gfxdraw

pygame.freetype.init()


VELOCITY_CHEVRON_COLOR      = (0, 0, 0)
HIGHLIGHT_COLOR             = (255, 255, 0)
HIGHLIGHT_THICKNESS_MULT    = 0.10


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

    def draw_onto(self, surf: pg.Surface, rect: pg.Rect, edit_mode: bool, selected: bool = False, step_progress: float = 0.0, neighborhood = (([],) * 5,) * 5):
        pg.draw.rect(surf, (50, 50, 50), rect)

        s = rect.width
        if selected:
            draw_rectangle(surf, rect, HIGHLIGHT_COLOR, thickness=s*HIGHLIGHT_THICKNESS_MULT)


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

    def draw_onto(self, surf: pg.Surface, rect: pg.Rect, edit_mode: bool, selected: bool = False, step_progress: float = 0.0, neighborhood = (([],) * 5,) * 5):
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
        # pg.gfxdraw.aacircle(surf, *round(self.draw_center), draw_radius, draw_color_rgb)
        # pg.gfxdraw.filled_circle(surf, *round(self.draw_center), draw_radius, draw_color_rgb)

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
        
        if selected:
            draw_rectangle(surf, rect, HIGHLIGHT_COLOR, thickness=s*HIGHLIGHT_THICKNESS_MULT)


class ResourceTile(Carpet):
    name = "Resource Tile"
    ascii_str = "O"

    # resource tiles are always locked
    def __init__(self, color: Color):
        super().__init__(True)
        self.color = color
    
    def draw_onto(self, surf: pg.Surface, rect: pg.Rect, edit_mode: bool, selected: bool = False, step_progress: float = 0.0, neighborhood = (([],) * 5,) * 5):
        pg.draw.rect(surf, self.color.rgb(), rect)
    
        s = rect.width
        if selected:
            draw_rectangle(surf, rect, HIGHLIGHT_COLOR, thickness=s*HIGHLIGHT_THICKNESS_MULT)


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
    
    def draw_onto(self, surf: pg.Surface, rect: pg.Rect, edit_mode: bool, selected: bool = False, step_progress: float = 0.0, neighborhood = (([],) * 5,) * 5):
        # TEMPORARY
        s = rect.width
        w = round(s * 0.1)
        draw_aacircle(surf, *rect.center, round(s * 0.35), (220, 220, 220))
        # pg.draw.circle(surf, (220, 220, 220), rect.center, s // 3, width=w)
        draw_chevron(
            surf,
            V2(*rect.center) + self.orientation * (s * 0.432),
            self.orientation,
            (220, 220, 220),
            round(s * 0.28),
            w,
            angle=108
        )

        if selected:
            draw_rectangle(surf, rect, HIGHLIGHT_COLOR, thickness=s*HIGHLIGHT_THICKNESS_MULT)


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
    
    def draw_onto(self, surf: pg.Surface, rect: pg.Rect, edit_mode: bool, selected: bool = False, step_progress: float = 0.0, neighborhood = (([],) * 5,) * 5):
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
        
        if selected:
            draw_rectangle(surf, rect, HIGHLIGHT_COLOR, thickness=s*HIGHLIGHT_THICKNESS_MULT)


class Target(Carpet):
    name = "Target"
    ascii_str = "T"
    # count_font = pg.freetype.SysFont("arial", 20)

    # targets are always locked
    def __init__(self, color: Color, count: int):
        super().__init__(True)
        self.color = color
        self.count = count
    
    def draw_onto(self, surf: pg.Surface, rect: pg.Rect, edit_mode: bool, selected: bool = False, step_progress: float = 0.0, neighborhood = (([],) * 5,) * 5):
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

        if selected:
            draw_rectangle(surf, rect, HIGHLIGHT_COLOR, thickness=s*HIGHLIGHT_THICKNESS_MULT)
