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
        self.shift: Direction = Direction.NONE  # represents a linear shift (e.g. from a piston)
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
        self.draw_center = V2(*rect.center)
        # travel phase (`velocity`)
        if step_progress < 0.5:
            amt = 0
        else:
            amt = 2 * (step_progress - 0.5)
        travel = self.travel_curve(amt)   
        self.draw_center += self.velocity * (s - 1) * travel
        # `shift` phase
        if self.shift is not Direction.NONE:
            # linear travel from [0.11, 0.11 + 1/16] at speed 8, normal travel from (0.11 + 1/16, 0.5]
            # makes it look like barrel is being pushed and slides to a halt
            a = 0.037   # fine tune 'collision' with piston head
            b = a + 1/16
            if step_progress <= a:
                amt = 0
            elif step_progress <= b:
                amt = 8 * (step_progress - a)
            else:
                amt = self.travel_curve(0.25 + 2 * (step_progress - b))
            self.draw_center += self.shift * (s - 1) * amt

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



class Piston(Block):
    name = "Piston"
    ascii_str = "P"
    orients = True

    # boostpads are unlocked by default
    def __init__(self, orientation: Direction = Direction.NORTH, locked: bool = False):
        super().__init__(locked)
        if (orientation is Direction.NONE):
            raise ValueError("Boostpad orientation cannot be `Direction.NONE`")
        self.orientation = orientation
        self.activated = True   # FOR TESTING
    
    def get_widgets(self) -> Sequence[Widget]:
        return [
            DirectionEditor(self, "orientation")
        ]
    
    def draw_onto_base(self, surf: pg.Surface, rect: pg.Rect, edit_mode: bool, step_progress: float, neighborhood):
        s = rect.width
        max_amt = 0.75
        # extend head at speed 8, then retract head at speed 8
        t = max_amt / 8
        if step_progress <= t:
            amt = 8 * step_progress
        elif step_progress <= 2*t:
            amt = max_amt - 8 * (step_progress - t)
        else:
            amt = 0
        
        extension = round(s * amt)
        # extension = round(max_extension * (1 - abs(2*amt - 1))) if self.activated else 0

        padding = round(s * 0.1)
        temp = pg.Surface(rect.inflate(s * 2, s * 2).size, pg.SRCALPHA)
        temp_rect = temp.get_rect()
        temp.fill((0, 0, 0, 0))
        head_top = temp_rect.centery - s // 2 + padding - extension
        # draw stem
        pg.draw.rect(temp, (127, 127, 127), pg.Rect(
            temp_rect.centerx - s * 0.1,
            head_top,
            s * 0.2,
            s - padding * 3 + extension
        ))
        # draw head
        pg.draw.rect(
            temp, (139, 69, 19),
            pg.Rect(
                temp_rect.centerx - s // 2 + padding,
                head_top,
                s - padding * 2,
                s * 0.25
            ),
            border_radius=round(s * 0.08)
        )
        # draw base
        pg.draw.rect(temp, (0, 0, 0), pg.Rect(
            temp_rect.centerx - s // 2 + padding,
            temp_rect.centery - padding,
            s - padding * 2,
            s * 0.5
        ))

        # rotate and blit to correct position
        temp = pg.transform.rotate(temp, -90 * Direction.nonzero().index(self.orientation))
        surf.blit(temp, rect.inflate(s * 2, s * 2))





ENTITY_TYPES = [Barrel, Barrier, Boostpad, ResourceExtractor, ResourceTile, Target, Piston]
