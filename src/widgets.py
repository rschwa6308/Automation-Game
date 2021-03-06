# --- UI-Widgets for the Editor Panel --- #
from typing import Callable, Tuple, Union
import pygame as pg

from helpers import V2, Direction, clamp, draw_aacircle, draw_chevron, draw_rectangle, rect_union, render_text_centered, render_text_left_justified
from constants import EDITOR_WIDTH, HIGHLIGHT_COLOR

FONT_SIZE = EDITOR_WIDTH / 11


class Widget:
    aspect_ratio = 1.0
    
    def draw_onto(self, surf: pg.Surface, rect: pg.Rect, **kwargs) -> None:
        assert(rect.width // rect.height == int(self.aspect_ratio))
        # draw bounding box
        # pg.draw.rect(surf, (0, 0, 0), rect, width=1)
    
    def handle_click(self, pos: V2) -> bool:
        """
        handle a left-click event;
        `pos` is given in coordinates wrt to the editor surf;
        return True iff we wish to indicate to the level runner that this wiring widget is in use
        """
        return False
    
    def get_attr(self, attr_str):
        return self.entity.__getattribute__(self.parse_attr_string(attr_str))
    
    @staticmethod
    def parse_attr_string(string: str):
        prefix = "localvar:"
        if not string.startswith(prefix):
            raise ValueError(f"invalid attr string: {string}")
        
        return string[len(prefix):]



class Spacing(Widget):
    def __init__(self, aspect_ratio) -> None:
        super().__init__()
        self.aspect_ratio = aspect_ratio


class AttrEditor(Widget):
    def __init__(self, entity, attr: str):
        self.entity = entity
        self.attr = attr
    
    def get_value(self):
        return self.get_attr(self.attr)
    
    def set_value(self, value):
        self.entity.__setattr__(self.parse_attr_string(self.attr), value)
    

class DirectionEditor(AttrEditor):
    aspect_ratio = 1.25

    def __init__(self, entity, attr: str, label: str):
        super().__init__(entity, attr)

        self.label = label
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
                compass_center + d * s * 0.25,
                d,
                (255, 255, 255) if self.get_value() is d else (0, 0, 0),
                s * 0.12,
                s * 0.04
            ))
            for d in Direction
            if d is not Direction.NONE
        ]
        render_text_centered(self.label, (0, 0, 0), surf, V2(rect.centerx, rect.bottom - s * 0.16), FONT_SIZE)
    
    def handle_click(self, pos: V2):
        for d, hitbox in self.hitboxes:
            if hitbox.collidepoint(*pos):
                self.set_value(d)
                break
        
        return False


class SmallIntEditor(AttrEditor):
    aspect_ratio = 6.0

    def __init__(self, entity, attr: str, limits_def: Tuple[Union[int, str], Union[int, str]], label: str):
        super().__init__(entity, attr)
        self.limits_def = limits_def

        self.label = label
        self.hitboxes = []

        # ensure value is within limits
        self.set_value(clamp(self.get_value(), *self.get_limits()))
    
    def get_limits(self) -> Tuple[int, int]:
        # either return static int or read the localvar attribute value
        low, high = self.limits_def
        return (
            low if isinstance(low, int) else self.get_attr(low),
            high if isinstance(high, int) else self.get_attr(high),
        )

    def draw_onto(self, surf: pg.Surface, rect: pg.Rect, **kwargs):
        super().draw_onto(surf, rect)
        render_text_left_justified(self.label, (0, 0, 0), surf, V2(rect.left + rect.width * 0.03, rect.centery), FONT_SIZE)
        # TODO: draw number selector boxes
        box_width = int(rect.height * 0.75)
        box_height = int(rect.height * 0.75)
        box_thickness = 2
        self.hitboxes.clear()
        low, high = self.get_limits()
        for i, n in enumerate(range(low, high + 1)):   # inclusive
            box = pg.Rect(
                rect.left + rect.width * 0.375 + (box_width - box_thickness // 2) * i,
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


class WireEditor(Widget):
    aspect_ratio = 2.0

    def __init__(self, entity, wire_index: int, label: str):
        self.entity = entity
        self.wire_index = wire_index
        self.label = label
        self.snapshot_rect = None
        self.is_input = entity.wirings[wire_index][0]   # tracks if wire is an input or an output
        self.in_use = False
    
    def get_value(self):
        return (
            self.entity.wirings[self.wire_index][1],
            self.entity.wirings[self.wire_index][2]
        )

    def make_connection(self, e, j):
        self.entity.make_connection(self.wire_index, e, j)
    
    def break_connection(self):
        self.entity.break_connection(self.wire_index)
    
    def draw_onto(self, surf: pg.Surface, rect: pg.Rect, snapshot_provider=None) -> None:
        super().draw_onto(surf, rect)
        render_text_left_justified(self.label, (0, 0, 0), surf, V2(rect.left + rect.width * 0.03, rect.centery), FONT_SIZE)

        w = rect.width * 0.45
        h = w   # rect.height * 0.9
        self.snapshot_rect = pg.Rect(
            rect.left + rect.width * 0.70 - w / 2, rect.top + (rect.height - h) / 2,
            w, h
        )

        # draw background
        pg.draw.rect(surf, (255, 255, 255), self.snapshot_rect)

        if self.get_value()[0] is None and not self.in_use:
            size = FONT_SIZE * 0.65
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
            # break connection
            self.break_connection()
            self.in_use = True
            return True


# class Button(Widget):
    # def __init__(self, entity, on_press: Callable):
    #     self.entity = entity
    #     self.on_press = on_press

    #     self.hitbox: pg.Rect = None      # set in self.draw_onto
    
    # def handle_click(self, pos: V2) -> bool:
    #     if self.hitbox is not None and self.hitbox.collidepoint(*pos):
    #         self.on_press()
    

class MinusPlusButton(Widget):
    """
    a widget that displays a minus and a plus button (- / +);
    if supplied, `limits` and `attr` control whether either button should be hidden
    """
    aspect_ratio = 7.0

    def __init__(self, entity, on_press_minus: Callable, on_press_plus: Callable, limits=None, attr=None):
        self.entity = entity
        self.on_press_minus = on_press_minus
        self.on_press_plus = on_press_plus

        self.limits = limits
        self.attr = attr

        self.minus_hitbox: pg.Rect = None   # set in self.draw_onto
        self.plus_hitbox: pg.Rect = None    # set in self.draw_onto
    
    def handle_click(self, pos: V2) -> bool:
        if self.minus_hitbox is not None and self.minus_hitbox.collidepoint(*pos):
            self.on_press_minus()
        elif self.plus_hitbox is not None and self.plus_hitbox.collidepoint(*pos):
            self.on_press_plus()

    def draw_onto(self, surf: pg.Surface, rect: pg.Rect, **kwargs) -> None:
        super().draw_onto(surf, rect, **kwargs)

        radius = round(rect.height * 0.40)
        border_width = 2
        # draw_width = round(rect.height * 0.075)
        spacing = radius * 2 + border_width

        if self.attr is None:
            minus_visible = True
            plus_visible = True
        else:
            minus_visible = self.get_attr(self.attr) > self.limits[0]
            plus_visible = self.get_attr(self.attr) < self.limits[1]

        if not (minus_visible or plus_visible):
            raise RuntimeError("at least one of minus/plus buttons must be visible")
        
        if minus_visible and plus_visible:
            minus_center = (rect.centerx - spacing//2, rect.centery)
            plus_center = (rect.centerx + spacing//2, rect.centery)
        elif minus_visible:
            minus_center = rect.center
        elif plus_visible:
            plus_center = rect.center

        self.minus_hitbox = pg.Rect(
            minus_center[0] - radius, minus_center[1] - radius,
            radius * 2, radius * 2
        ) if minus_visible else None

        self.plus_hitbox = pg.Rect(
            plus_center[0] - radius, plus_center[1] - radius,
            radius * 2, radius * 2
        ) if plus_visible else None

        background_color = (255, 255, 255)
        border_color = (0, 0, 0)
        icon_color = (0, 0, 0)
        icon_font_size = FONT_SIZE * 1.0

        # draw background and border
        combined_rect = rect_union([self.minus_hitbox, self.plus_hitbox])
        pg.draw.rect(surf, background_color, combined_rect, border_radius=radius)
        pg.draw.rect(surf, border_color, combined_rect, width=border_width, border_radius=radius)

        # draw "-" button
        if minus_visible:
            render_text_centered("-", icon_color, surf, self.minus_hitbox.center, icon_font_size)

        # draw "+" button
        if plus_visible:
            render_text_centered("+", icon_color, surf, self.plus_hitbox.center, icon_font_size)

        # draw divider
        if minus_visible and plus_visible:
            pg.draw.line(
                surf, icon_color,
                (rect.centerx, rect.centery - radius / 2),
                (rect.centerx, rect.centery + radius / 2),
                width=border_width
            )
            # render_text_centered("|", icon_color, surf, rect.center, FONT_SIZE)
        


