# --- Level Entities --- #
from helpers import V2, Direction, draw_chevron
from colors import Color, COLOR_RBG_MAP

import pygame as pg



VELOCITY_CHEVRON_COLOR    = (0, 0, 0)



class Entity:
    moves: bool = False
    stops: bool = False
    merges: bool = False
    draw_precedence: int = 0

    def draw_onto(self, surf: pg.Surface, rect: pg.Rect, edit_mode: bool):
        pass


class Carpet(Entity):
    stops = False
    draw_precedence = 0


class Block(Entity):
    stops = True
    draw_precedence = 1



class Barrel(Block):
    name = "Barrel"
    ascii_str = "B"
    moves = True
    stops = False
    merges = True

    def __init__(self, color: Color, velocity: Direction = Direction.NONE):
        self.color = color
        self.velocity = velocity

    def __add__(self, other):
        return Barrel(self.color + other.color)

    def draw_onto(self, surf, rect, edit_mode):
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

    def __init__(self, color: Color):
        self.color = color
    
    def draw_onto(self, surf: pg.Surface, rect: pg.Rect, edit_mode: bool):
        pg.draw.rect(surf, COLOR_RBG_MAP[self.color], rect)


class ResourceExtractor(Block):
    name = "Resource Extractor"
    ascii_str = "X"
    period = 3

    def __init__(self, orientation: Direction = Direction.NORTH):
        self.orientation = orientation
    
    def draw_onto(self, surf: pg.Surface, rect: pg.Rect, edit_mode: bool):
        # TEMPORARY
        s = rect.width
        w = round(s * 0.1)
        pg.draw.circle(surf, (255, 255, 255), rect.center, s // 3, width=w)
        draw_chevron(
            surf,
            V2(*rect.center) + self.orientation * (s * 0.435),
            self.orientation,
            (255, 255, 255),
            round(s * 0.28),
            w,
            angle=100
        )


class Boostpad(Carpet):
    name = "Boostpad"
    ascii_str = "X"

    def __init__(self, orientation: Direction = Direction.NORTH):
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


