# --- UI-Widgets for the Editor Panel --- #
from typing import Tuple
import pygame as pg

from helpers import V2, Direction, clamp, draw_chevron, draw_rectangle, render_text_centered, render_text_left_justified
from constants import HIGHLIGHT_COLOR

FONT_SIZE = 20


class Widget:
    aspect_ratio = 1.0
    
    def draw_onto(self, surf: pg.Surface, rect: pg.Rect, **kwargs) -> None:
        assert(rect.width // rect.height == int(self.aspect_ratio))
        # pg.draw.rect(surf, (0, 0, 0), rect, width=1)
    
    def handle_click(self, pos: V2) -> bool:
        """
        handle a left-click event;
        `pos` is given in coordinates wrt to the editor surf;
        return True iff we wish to indicate to the level runner that this wiring widget is in use
        """
        return False


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

    def draw_onto(self, surf: pg.Surface, rect: pg.Rect, **kwargs):
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
        
        return False


class SmallIntEditor(AttrEditor):
    aspect_ratio = 6.0

    def __init__(self, entity, attr: str, limits: Tuple[int, int]):
        super().__init__(entity, attr)
        self.limits = limits
        self.hitboxes = []

        # ensure value is within limits
        self.set_value(clamp(self.get_value(), *limits))

    def draw_onto(self, surf: pg.Surface, rect: pg.Rect, **kwargs):
        super().draw_onto(surf, rect)
        render_text_left_justified(self.attr, (0, 0, 0), surf, V2(rect.left + 6, rect.centery), FONT_SIZE)
        # TODO: draw number selector boxes
        box_width = int(rect.height * 0.75)
        box_height = int(rect.height * 0.75)
        box_thickness = 2
        self.hitboxes.clear()
        for i, n in enumerate(range(self.limits[0], self.limits[1] + 1)):   # inclusive
            box = pg.Rect(
                rect.left + rect.width * 0.4 + (box_width - box_thickness // 2) * i,
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
        
        return False


class WireEditor:
    aspect_ratio = 2.0

    def __init__(self, entity, wire_index: int, title: str):
        self.entity = entity
        self.wire_index = wire_index
        self.title = title
        self.snapshot_rect = None
        self.is_input = entity.wirings[wire_index][0]   # tracks if wire is an input or an output
        self.in_use = False
        # self.old_value = (None, None)
    
    def get_value(self):
        return (
            self.entity.wirings[self.wire_index][1],
            self.entity.wirings[self.wire_index][2]
        )

    def set_value(self, e, i):
        # self.old_value = self.get_value()
        self.entity.wirings[self.wire_index][1] = e
        self.entity.wirings[self.wire_index][2] = i
    
    def draw_onto(self, surf: pg.Surface, rect: pg.Rect, snapshot_provider=None) -> None:
        render_text_left_justified(self.title, (0, 0, 0), surf, V2(rect.left + 6, rect.centery), FONT_SIZE)

        w = rect.width * 0.4
        h = rect.height * 0.8
        self.snapshot_rect = pg.Rect(
            rect.left + rect.width * 0.70 - w / 2, rect.top + (rect.height - h) / 2,
            w, h
        )

        # draw background
        pg.draw.rect(surf, (255, 255, 255), self.snapshot_rect)

        if self.get_value()[0] is None and not self.in_use:
            size = FONT_SIZE * 0.6
            render_text_centered(
                "not", (63, 63, 63), surf,
                (self.snapshot_rect.centerx, self.snapshot_rect.centery - size/2), size
            )
            render_text_centered(
                "connected", (63, 63, 63), surf,
                (self.snapshot_rect.centerx, self.snapshot_rect.centery + size/2), size
            )
        else:
            if self.in_use:
                snap = snapshot_provider.take_snapshot_at_mouse(self.snapshot_rect.size)
            else:
                snap = snapshot_provider.take_snapshot(self.get_value()[0], self.snapshot_rect.size)
            surf.blit(snap, self.snapshot_rect)

        # draw border
        color = HIGHLIGHT_COLOR if self.in_use else (0, 0, 0)
        pg.draw.rect(surf, color, self.snapshot_rect, 2)
    
    def handle_click(self, pos: V2) -> None:
        if self.snapshot_rect.collidepoint(*pos):
            # break other side of connection
            other, j = self.get_value()
            if other is not None:
                other.wirings[j][1] = None
                other.wirings[j][2] = None
            self.set_value(None, None)
            self.in_use = True
            return True