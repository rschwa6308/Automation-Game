# --- UI-Widgets for the Editor Panel --- #
from typing import Callable
import pygame as pg
from pygame.freetype import get_default_font

from helpers import V2, Direction, draw_aacircle, draw_chevron, render_text_centered

# from entities import Entity


class Widget:
    aspect_ratio = 1.0
    
    def draw_onto(self, surf, rect) -> None:
        # print(rect.width // rect.height, int(self.aspect_ratio))
        assert(rect.width // rect.height == int(self.aspect_ratio))
        pg.draw.rect(surf, (0, 0, 0), rect, width=1)
    
    def handle_click(self, pos: V2) -> None:
        """handle a left-click event; `pos` is given in coordinates wrt to the editor surf"""


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

    def draw_onto(self, surf, rect: pg.Rect):
        # super().draw_onto(surf, rect)
        s = rect.width
        compass_center = round(V2(rect.centerx, rect.centery - s * 0.1))
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
        render_text_centered(self.attr, (0, 0, 0), surf, V2(rect.centerx, rect.bottom - s * 0.15), 22)
    
    def handle_click(self, pos: V2):
        # print(pos)
        # print(self.hitboxes)
        for d, hitbox in self.hitboxes:
            if hitbox.collidepoint(*pos):
                self.set_value(d)
                break


class SmallIntEditor(AttrEditor):
    aspect_ratio = 3.0

    def draw_onto(self, surf, rect):
        super().draw_onto(surf, rect)
        # TODO: draw number selector boxes