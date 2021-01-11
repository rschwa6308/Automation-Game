# --- UI-Widgets for the Editor Panel --- #
from typing import Callable, Tuple
import pygame as pg
from pygame.freetype import get_default_font

from helpers import V2, Direction, clamp, draw_aacircle, draw_chevron, draw_rectangle, render_text_centered, render_text_left_justified


FONT_SIZE = 20


class Widget:
    aspect_ratio = 1.0
    
    def draw_onto(self, surf: pg.Surface, rect: pg.Rect) -> None:
        assert(rect.width // rect.height == int(self.aspect_ratio))
        # pg.draw.rect(surf, (0, 0, 0), rect, width=1)
    
    def handle_click(self, pos: V2) -> None:
        """handle a left-click event; `pos` is given in coordinates wrt to the editor surf"""


class Spacing(Widget):
    def __init__(self, aspect_ratio) -> None:
        super().__init__()
        self.aspect_ratio = aspect_ratio


class AttrEditor(Widget):
    def __init__(self, entity, attr: str):
        self.entity = entity
        self.attr = attr
    
    def get_value(self):
        return self.entity.__getattribute__(self.attr)
    
    def set_value(self, value):
        self.entity.__setattr__(self.attr, value)
    

class DirectionEditor(AttrEditor):
    aspect_ratio = 1.0

    def __init__(self, entity, attr: str):
        super().__init__(entity, attr)
        self.hitboxes = []

    def draw_onto(self, surf: pg.Surface, rect: pg.Rect):
        super().draw_onto(surf, rect)
        s = rect.width
        compass_center = round(V2(rect.centerx, rect.centery - s * 0.1))
        # pg.draw.circle(surf, (0, 0, 0), tuple(compass_center), round(s * 0.1), width=round(s * 0.05))
        # draw_aacircle(surf, *compass_center, round(s * 0.05), (0, 0, 0))
        self.hitboxes = [
            (d, draw_chevron(
                surf,
                compass_center + d * s * 0.3,
                d,
                (255, 255, 255) if self.get_value() is d else (0, 0, 0),
                s * 0.15,
                s * 0.05
            ))
            for d in Direction
            if d is not Direction.NONE
        ]
        render_text_centered(self.attr, (0, 0, 0), surf, V2(rect.centerx, rect.bottom - s * 0.18), FONT_SIZE)
    
    def handle_click(self, pos: V2):
        for d, hitbox in self.hitboxes:
            if hitbox.collidepoint(*pos):
                self.set_value(d)
                break


class SmallIntEditor(AttrEditor):
    aspect_ratio = 6.0

    def __init__(self, entity, attr: str, limits: Tuple[int, int]):
        super().__init__(entity, attr)
        self.limits = limits
        self.hitboxes = []

        # ensure value is within limits
        self.set_value(clamp(self.get_value(), *limits))

    def draw_onto(self, surf: pg.Surface, rect: pg.Rect):
        super().draw_onto(surf, rect)
        render_text_left_justified(self.attr, (0, 0, 0), surf, V2(rect.left + 6, rect.centery), FONT_SIZE)
        # TODO: draw number selector boxes
        box_width = int(rect.height * 0.75)
        box_height = int(rect.height * 0.75)
        box_thickness = 2
        self.hitboxes.clear()
        for i, n in enumerate(range(self.limits[0], self.limits[1] + 1)):   # inclusive
            box = pg.Rect(
                rect.left + rect.width * 0.4 + (box_width - box_thickness) * i,
                rect.centery - box_height / 2,
                box_width, 
                box_height
            )
            color = (255, 255, 255) if n == self.get_value() else (0, 0, 0)
            draw_rectangle(surf, box, (0, 0, 0), thickness=box_thickness)
            render_text_centered(str(n), color, surf, box.center, FONT_SIZE)
            self.hitboxes.append((n, box))
    
    def handle_click(self, pos: V2) -> None:
        for n, hitbox in self.hitboxes:
            if hitbox.collidepoint(*pos):
                self.set_value(n)
                break