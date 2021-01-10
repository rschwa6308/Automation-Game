# --- UI-Widgets for the Editor Panel --- #
from typing import Callable
import pygame as pg

# from entities import Entity


class Widget:
    aspect_ratio = 1.0
    
    def draw_onto(self, surf, rect):
        # print(rect.width // rect.height, int(self.aspect_ratio))
        assert(rect.width // rect.height == int(self.aspect_ratio))
        pg.draw.rect(surf, (0, 0, 0), rect)


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

    def draw_onto(self, surf, rect):
        super().draw_onto(surf, rect)
        # TODO: draw compass rose


class SmallIntEditor(AttrEditor):
    aspect_ratio = 3.0

    def draw_onto(self, surf, rect):
        super().draw_onto(surf, rect)
        # TODO: draw number selector boxes