# --- Level Entities --- #
from helpers import V2, Direction, draw_chevron, render_text_centered
from colors import Color, COLOR_RBG_MAP

import pygame as pg
import pygame.freetype

pygame.freetype.init()


VELOCITY_CHEVRON_COLOR    = (0, 0, 0)



class Entity:
    moves: bool = False
    stops: bool = False
    merges: bool = False
    draw_precedence: int = 0

    def __init__(self, locked: bool):
        self.locked = locked

    def draw_onto(self, surf: pg.Surface, rect: pg.Rect, edit_mode: bool):
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

    def draw_onto(self, surf: pg.Surface, rect: pg.Rect, edit_mode: bool):
        pg.draw.rect(surf, (50, 50, 50), rect)


class Barrel(Block):
    name = "Barrel"
    ascii_str = "B"
    moves = True
    stops = False
    merges = True

    # barrels are unlocked by default
    def __init__(self, color: Color, velocity: Direction = Direction.NONE, locked: bool = False):
        super().__init__(locked)
        self.color = color
        self.velocity = velocity
        self.leaky = False

    def __add__(self, other):
        return Barrel(self.color + other.color)

    def draw_onto(self, surf: pg.Surface, rect: pg.Rect, edit_mode: bool):
        s = rect.width
        draw_color_rgb = COLOR_RBG_MAP[self.color]
        pg.draw.circle(surf, draw_color_rgb, rect.center, s * 0.3)
        if edit_mode:
            draw_chevron(
                surf,
                V2(*rect.center) + self.velocity * (s * 0.42),
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
    
    def draw_onto(self, surf: pg.Surface, rect: pg.Rect, edit_mode: bool):
        pg.draw.rect(surf, COLOR_RBG_MAP[self.color], rect)


class ResourceExtractor(Block):
    name = "Resource Extractor"
    ascii_str = "X"
    period = 3

    # resource extractors are unlocked by default
    def __init__(self, orientation: Direction = Direction.NORTH, locked: bool = False):
        super().__init__(locked)
        self.orientation = orientation
    
    def draw_onto(self, surf: pg.Surface, rect: pg.Rect, edit_mode: bool):
        # TEMPORARY
        s = rect.width
        w = round(s * 0.1)
        pg.draw.circle(surf, (220, 220, 220), rect.center, s // 3, width=w)
        draw_chevron(
            surf,
            V2(*rect.center) + self.orientation * (s * 0.432),
            self.orientation,
            (220, 220, 220),
            round(s * 0.28),
            w,
            angle=100
        )


class Boostpad(Carpet):
    name = "Boostpad"
    ascii_str = "X"

    # boostpads are unlocked by default
    def __init__(self, orientation: Direction = Direction.NORTH, locked: bool = False):
        super().__init__(locked)
        if (orientation is Direction.NONE):
            raise ValueError("Boostpad orientation cannot be `Direction.NONE`")

        self.orientation = orientation
    
    def draw_onto(self, surf: pg.Surface, rect: pg.Rect, edit_mode: bool):
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
    count_font = pg.freetype.SysFont("arial", 20)

    # targets are always locked
    def __init__(self, color: Color, count: int):
        super().__init__(True)
        self.color = color
        self.count = count
    
    def draw_onto(self, surf: pg.Surface, rect: pg.Rect, edit_mode: bool):
        s = rect.width
        pg.draw.rect(surf, COLOR_RBG_MAP[self.color], rect)
        padding = s * 0.35
        radius = round(s * 0.2)
        pg.draw.rect(surf, (255, 255, 255), rect.inflate(-padding, -padding), border_radius=radius)
        # TODO: use `Font.get_sizes()` to change font size
        render_text_centered(
            self.count_font,
            str(self.count),
            (0, 0, 0),
            surf,
            rect.center
        )
