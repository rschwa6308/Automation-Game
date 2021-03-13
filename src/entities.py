# --- Level Entities --- #
from __future__ import annotations  # allows self-reference in type annotations
from typing import Collection, Generator, Sequence, Tuple, Optional
from abc import abstractmethod
from math import pi

import pygame as pg
import pygame.freetype
import pygame.gfxdraw
from pygame.transform import threshold

from helpers import V2, Direction, all_subclasses, draw_aacircle, draw_chevron, draw_rectangle, render_text_centered, interpolate_colors, sgn
from colors import Color
from widgets import DirectionEditor, MinusPlusButton, SmallIntEditor, Spacing, Widget, WireEditor
from constants import *


VELOCITY_CHEVRON_COLOR      = (0, 0, 0)
HIGHLIGHT_THICKNESS_MULT    = 0.10

HIGHLIGHT_INFLATION_FACTOR  = 1.2


class Entity:
    moves: bool = False
    orients: bool = False
    stops: bool = False
    merges: bool = False
    editable: bool = False
    has_ports: bool = False
    draw_precedence: int = 0

    def __init__(self, locked: bool, prototype: EntityPrototype = None):
        self.locked = locked
        self.animations = []

        # if prototype not supplied, assume default 'vanilla' prototype
        if prototype is None:
            prototype = EntityPrototype(type(self))
        
        self.prototype = prototype
    
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

    def __init__(self, locked: bool, **kwargs):
        super().__init__(locked, **kwargs)


class Block(Entity):
    stops = True
    draw_precedence = 1

    def __init__(self, locked: bool, **kwargs):
        super().__init__(locked, **kwargs)


class Barrier(Block):
    name = "Barrier"
    ascii_str = "█"
    stops = True
    
    # barriers are locked by default
    def __init__(self, locked: bool = True, **kwargs):
        super().__init__(locked, **kwargs)

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
    def __init__(self, color: Color, velocity: Direction = Direction.NONE, locked: bool = False, **kwargs):
        super().__init__(locked, **kwargs)
        self.color = color
        self.velocity = velocity
        self.leaky = False
        self.draw_center = V2(0, 0)

    def __add__(self, other):
        return Barrel(self.color + other.color)
    
    @staticmethod
    def travel_curve(x):
        """integral of speed curve f'(x) = 2 - 2|2x - 1|"""
        return 1/2 * (-1 + 4*x + (1 - 2*x)**2 * sgn(1/2 - x))


    def draw_onto_base(self, surf: pg.Surface, rect: pg.Rect, edit_mode: bool, step_progress: float = 0.0, neighborhood = (([],) * 5,) * 5):
        s = rect.width
        self.draw_center = V2(*rect.center)

        for anim in self.animations:
            if anim[0] == "translate":
                amt = self.travel_curve(step_progress)
                self.draw_center += anim[1] * (s - 1) * (amt - 1)
            elif anim[0] == "shift":
                a = 0.18
                if step_progress < a:
                    amt = 0
                elif step_progress < 0.5:
                    amt = (step_progress - a) * 2 * Piston.max_amt
                else:
                    amt = self.travel_curve(step_progress)
                self.draw_center += anim[1] * (s - 1) * (amt - 1)

        draw_radius = s * 0.3
        draw_color_rgb = self.color.rgb()

        # check for intersection with other barrel
        # if intersection found, take weighted average of colors
        n = len(neighborhood)
        for x in range(-n//2, n//2 + 1):
            for y in range(-n//2, n//2 + 1):
                for e in neighborhood[y + n//2][x + n//2]:
                    if e is self: continue  # skip self
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
    def __init__(self, color: Color, **kwargs):
        super().__init__(True, **kwargs)
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
    editable = True

    # resource extractors are unlocked by default
    def __init__(self, orientation: Direction = Direction.NORTH, locked: bool = False, **kwargs):
        super().__init__(locked, **kwargs)
        self.orientation = orientation
        self.period = 3
        self.phase = 1

        self.widgets = [
            DirectionEditor(self, "localvar:orientation", "orientation"),
            # Spacing(20.0),
            SmallIntEditor(self, "localvar:period", (1, 5), "period"),
            SmallIntEditor(self, "localvar:phase", (1, "localvar:period"), "phase"),
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
    editable = True

    # boostpads are unlocked by default
    def __init__(self, orientation: Direction = Direction.NORTH, locked: bool = False, **kwargs):
        super().__init__(locked, **kwargs)
        if orientation is Direction.NONE:
            raise ValueError("Boostpad orientation cannot be `Direction.NONE`")
        self.orientation = orientation

        self.widgets = [
            DirectionEditor(self, "localvar:orientation", "orientation")
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
    def __init__(self, color: Color, count: int, **kwargs):
        super().__init__(True, **kwargs)
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


class Wirable(Entity):
    has_ports = True
    editable = True

    def __init__(self, locked: bool, **kwargs):
        super().__init__(locked, **kwargs)
        self.wirings = []
        self.port_states = []

    def available_inputs(self) -> Collection[int]:
        res = []
        for i, (inp, e, j) in enumerate(self.wirings):
            if inp and e is None:
                res.append(i)
        return res

    def available_outputs(self) -> Collection[int]:
        res = []
        for i, (inp, e, j) in enumerate(self.wirings):
            if not inp and e is None:
                res.append(i)
        return res
    
    def make_connection(self, i, other, j):
        if self.wirings[i][0] == other.wirings[j][0]:
            raise ValueError("cannot connect ports of the same type (e.g. input-input)")

        self.wirings[i][1] = other
        self.wirings[i][2] = j
        other.wirings[j][1] = self  # other side of connection
        other.wirings[j][2] = i     # ^^^
    
    def break_connection(self, i):
        _, other, j = self.wirings[i]
        if other is None: return    # NoOp

        other.wirings[j][1] = None  # other side of connection
        other.wirings[j][2] = None  # ^^^
        self.wirings[i][1] = None
        self.wirings[i][2] = None
    
    def clear_ports(self) -> None:
        self.port_states =  [None for _ in self.port_states]
    
    def resolve_port(self, i) -> bool:
        """resolves the given port by recursing backwards on inputs, and by calling `self.resolve_output_port` on outputs"""
        # use cached value (requires clearing before every round)
        if self.port_states[i] not in (None, "visited"):
            return self.port_states[i]
        
        # check to see if node already visited - indicates a cycle in the wiring graph
        if self.port_states[i] == "visited":
            print("CYCLE DETECTED IN WIRING GRAPH")
            res = False                         # for now, just set port to False
        else:
            self.port_states[i] = "visited"
            
            inp, other, j = self.wirings[i]
            if other is None:
                res = False                     # no connection = LOW = False
            elif inp:
                res = other.resolve_port(j)     # the connected entity's output
            else:
                res = self.resolve_output_port(i)

        self.port_states[i] = res               # cache result
        return res

    @abstractmethod
    def resolve_output_port(self, i) -> bool:
        """custom functionality for resolving output port values (e.g. logic gate logic goes here)"""
        if self.wirings[i][0]:
            raise ValueError("resolve_output_port cannot be called on an input port")
        
        return None
    
    def on_ports_resolved(self) -> None:
        """called immediately after all ports have been resolved; used for updating internal state"""
        pass


class Piston(Block, Wirable):
    name = "Piston"
    ascii_str = "P"
    orients = True
    
    max_amt = 0.75

    # boostpads are unlocked by default
    def __init__(self, orientation: Direction = Direction.NORTH, locked: bool = False, **kwargs):
        super().__init__(locked, **kwargs)
        if orientation is Direction.NONE:
            raise ValueError("Piston orientation cannot be `Direction.NONE`")
        self.orientation = orientation
        self.activated = None
        
        # format is [(is_input, other_entity, other_entity's wire_index)]
        self.wirings: Sequence[Sequence[bool, Entity, int]] = [
            [True, None, None],
            [False, None, None]
        ]
        self.port_states = [None for _ in self.wirings]

        self.widgets = [
            DirectionEditor(self, "localvar:orientation", "orientation"),
            WireEditor(self, 0, "input"),
            WireEditor(self, 1, "output"),
        ]
    
    def resolve_output_port(self, i) -> bool:
        super().resolve_output_port(i)
        # if self.activated is None:
        #     raise RuntimeError("cannot read output value on a sensor that has not yet obtained a reading (check engine execution order)")
        return self.resolve_port(0)     # for now, pistons "repeat" their input value
    
    def on_ports_resolved(self):
        self.activated = self.port_states[0]    # set activation to input port state

    def draw_onto_base(self, surf: pg.Surface, rect: pg.Rect, edit_mode: bool, step_progress: float = 0.0, neighborhood = (([],) * 5,) * 5):
        s = rect.width
        extension = 0

        for anim in self.animations:
            if anim[0] == "extend":
                # linear travel out and back
                amt = (1 - abs(2 * step_progress - 1)) * self.max_amt
                extension = round(s * amt)

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


class Sensor(Block, Wirable):
    name = "Sensor"
    ascii_str = "S"
    orients = True

    target_entity_type = Barrel

    def __init__(self, orientation: Direction = Direction.NORTH, locked: bool = False, **kwargs):
        super().__init__(locked, **kwargs)
        if orientation is Direction.NONE:
            raise ValueError("Sensor orientation cannot be `Direction.NONE`")
        self.orientation = orientation
        self.activated = None
        
        # format is [(is_input, other_entity, other_entity's wire_index)]
        self.wirings: Sequence[Sequence[bool, Entity, int]] = [
            [False, None, None]
        ]
        self.port_states = [None for _ in self.wirings]

        self.widgets = [
            DirectionEditor(self, "localvar:orientation", "orientation"),
            WireEditor(self, 0, "output"),
        ]
    
    def resolve_output_port(self, i) -> bool:
        super().resolve_output_port(i)
        if self.activated is None:
            raise RuntimeError("cannot read output value on a sensor that has not yet obtained a reading (check engine execution order)")
        return self.activated

    
    def draw_onto_base(self, surf: pg.Surface, rect: pg.Rect, edit_mode: bool, step_progress: float = 0.0, neighborhood = (([],) * 5,) * 5):
        eye_box_width = rect.width * 0.75
        pupil_radius = rect.width * 0.15
        angular_width = pi * 0.63
        draw_width = round(rect.width * 0.04)
        num_lines = 5
        line_length = rect.width * 0.15

        # draw edges of eye
        pg.draw.arc(surf, (0, 0, 0), pg.Rect(
            rect.left + (rect.width - eye_box_width)/2, rect.centery - pupil_radius,
            eye_box_width, rect.height/2 + pupil_radius
        ), pi/2-angular_width/2, pi/2+angular_width/2, width=draw_width)

        pg.draw.arc(surf, (0, 0, 0), pg.Rect(
            rect.left + (rect.width - eye_box_width)/2, rect.top,
            eye_box_width, rect.height/2 + pupil_radius
        ), -pi/2-angular_width/2, -pi/2+angular_width/2, width=draw_width)

        # draw pupil
        pg.draw.circle(surf, (0, 0, 0), rect.center, pupil_radius)

        for i in range(num_lines):
            theta = 90 / num_lines * (i - num_lines//2)
            offset = self.orientation.rotate(round(theta))
            start = V2(*rect.center) + offset * pupil_radius * 1.4
            end = start + offset * line_length
            pg.draw.line(surf, (0, 0, 0), tuple(start), tuple(end), width=round(draw_width/2))


class Gate(Wirable):
    """abstract class defining the common behavior of all (single-output) logic gates"""
    orients = False

    min_num_inputs = 2
    max_num_inputs = 5

    def __init__(self, locked: bool = False, **kwargs):
        super().__init__(locked, **kwargs)
        self.activated = None
        
        self.num_inputs = self.min_num_inputs

        # format is [(is_input, other_entity, other_entity's wire_index)]
        self.wirings: Sequence[Sequence[bool, Entity, int]] = [
            [True, None, None] for _ in range(self.num_inputs)
        ] + [[False, None, None]]
        self.port_states = [None for _ in self.wirings]

        self.update_widgets()
    
    def update_widgets(self):
        num_inputs_changable = self.max_num_inputs > self.min_num_inputs

        self.widgets = [
            WireEditor(self, i, f"input {i + 1 if num_inputs_changable else ''}") for i in range(self.num_inputs)
        ] + [WireEditor(self, self.num_inputs, f"output")]

        # if interval for num_inputs contains more than 1 possible value, add a MinusPlusButton
        if num_inputs_changable:
            mp_button = MinusPlusButton(
                self, self.remove_input, self.add_input,
                limits=[self.min_num_inputs, self.max_num_inputs],
                attr="localvar:num_inputs"
            )
            self.widgets.insert(self.num_inputs, mp_button)
            self.widgets.insert(self.num_inputs + 1, Spacing(20.0))

    def remove_input(self):
        if self.num_inputs <= self.min_num_inputs: return
        # break the connection
        self.break_connection(self.num_inputs - 1)
        self.num_inputs -= 1
        self.wirings.pop(-2)        # last input
        self.port_states.pop(-2)
        self.update_widgets()

    def add_input(self):
        if self.num_inputs >= self.max_num_inputs: return
        self.num_inputs += 1
        self.wirings.insert(-1, [True, None, None])
        self.port_states.insert(-1, None)
        self.update_widgets()
    
    def resolve_output_port(self, i) -> bool:
        super().resolve_output_port(i)

        return self.eval(*[self.resolve_port(i) for i in range(self.num_inputs)])
    
    @abstractmethod
    def eval(self, *inputs: Sequence[bool]) -> bool:
        raise NotImplementedError("Gate must define an `eval` method")
    
    # TEMPORARY - TODO: implement per gate type
    def draw_onto_base(self, surf: pg.Surface, rect: pg.Rect, edit_mode: bool, step_progress: float=0.0, neighborhood=(([],) * 5,) * 5):
        super().draw_onto_base(surf, rect, edit_mode, step_progress=step_progress, neighborhood=neighborhood)
        font_size = rect.width * 0.3
        text = self.name.split()[0]     # gate type
        render_text_centered(text, (0, 0, 0), surf, rect.center, font_size, bold=True)


class AndGate(Gate):
    name = "AND Gate"

    def eval(self, *inputs) -> bool:
        return all(inputs)


class OrGate(Gate):
    name = "OR Gate"

    def eval(self, *inputs) -> bool:
        return any(inputs)


class NotGate(Gate):
    name = "NOT Gate"

    min_num_inputs = 1
    max_num_inputs = 1

    def eval(self, a: bool) -> bool:
        return not a


# TODO:
# - signal splitters
# - AND gates . . . . Done!
# - OR gates  . . . . Done!
# - NOT gates . . . . Done!



ENTITY_TYPES = [Barrel, Barrier, Boostpad, ResourceExtractor, ResourceTile, Target, Piston, Sensor, AndGate, OrGate, NotGate]
# ENTITY_TYPES = all_subclasses(Entity)
# print(ENTITY_TYPES)



class EntityPrototype:
    """a class for storing entity prototypes (e.g. in the palette)"""
    def __init__(self, entity_type, **kwargs):
        self.entity_type = entity_type
        self.kwargs = kwargs

    def get_instance(self):
        return self.entity_type(prototype=self, **self.kwargs)
    
    # def __hash__(self):
    #     print((self.entity_type, tuple(self.kwargs.items())))
    #     res = (self.entity_type, tuple(self.kwargs.items())).__hash__()
    #     print(res)
    #     return res

    def __eq__(self, o: EntityPrototype) -> bool:
        return self.entity_type == o.entity_type and self.kwargs == o.kwargs
