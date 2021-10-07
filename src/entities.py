# --- Level Entities --- #
from __future__ import annotations  # allows self-reference in type annotations
from typing import Collection, Generator, Sequence, Tuple, Optional
from abc import abstractmethod
from math import pi

import pygame as pg
import pygame.freetype
import pygame.gfxdraw
from pygame.transform import threshold

from helpers import V2, Direction, all_subclasses, draw_aacircle, draw_chevron, draw_rectangle, render_text_centered_xy, interpolate_colors, sgn
from colors import Color
from widgets import DirectionEditor, MinusPlusButton, SmallIntEditor, Spacing, Widget, WireEditor, WiringContainer
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
            SmallIntEditor(self, "localvar:period", (2, 5), "period"),      # TODO: decide on the bounds
            SmallIntEditor(self, "localvar:phase", (1, "localvar:period"), "phase"),
        ]
    
    def draw_onto_base(self, surf: pg.Surface, rect: pg.Rect, edit_mode: bool, step_progress: float = 0.0, neighborhood = (([],) * 5,) * 5):
        # TEMPORARY
        s = rect.width
        w = round(s * 0.1)
        draw_aacircle(surf, *rect.center, round(s * 0.35), (210, 210, 210))
        draw_chevron(
            surf,
            V2(*rect.center) + self.orientation * (s * 0.432),
            self.orientation,
            (210, 210, 210),
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
        render_text_centered_xy(
            str(self.count),
            (0, 0, 0),
            surf,
            rect.center,
            s - padding * 1.75,
        )


# TODO: maybe store input wirings and output wirings in separate lists
class Wirable(Entity):
    has_ports = True
    editable = True
    
    # defaults, which can be overridden in child classes
    min_num_inputs = 1
    max_num_inputs = 1

    min_num_outputs = 1
    max_num_outputs = 30    # TESTING

    def __init__(self, locked: bool, **kwargs):
        super().__init__(locked, **kwargs)
        # self.activated = None
        
        # min is default value
        self.num_inputs = self.min_num_inputs
        self.num_outputs = self.min_num_outputs

        # format is [(is_input, other_entity, other_entity's wire_index)]
        self.wirings: Sequence[Sequence[bool, Entity, int]] = [
            [True, None, None] for _ in range(self.num_inputs)
        ] + [
            [False, None, None] for _ in range(self.num_outputs)
        ]
        self.port_states = [None for _ in self.wirings]
        self.ports_visited = [False for _ in self.port_states]

        self.widgets = [
            WiringContainer(
                self,
                self.min_num_inputs, self.max_num_inputs,
                self.min_num_outputs, self.max_num_outputs,
            )
        ]

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
    
    def break_all_connections(self):
        for i in range(len(self.wirings)):
            self.break_connection(i)
    
    def clear_ports_visited(self) -> None:
        self.ports_visited =  [False for _ in self.port_states]

    def clear_ports_states(self) -> None:
        self.port_states =  [None for _ in self.port_states]
    
    def resolve_port(self, i) -> bool:
        """Resolve the given port by recursing backwards on inputs, and by calling `self.resolve_output_port` on outputs"""
        # use cached value (requires clearing before every round)
        # if self.port_states[i] not in (None, "visited"):
        # if self.port_states[i] not in ("visited", ):        # TESTING
        #     return self.port_states[i]
        if self.ports_visited[i]:
            # print("CYCLE DETECTED IN WIRING GRAPH")
            return self.port_states[i]
        else:
            self.ports_visited[i] = True
            
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

    def get_port_offset(self, is_input, index):
        return V2(0.5, 0.5)


class Piston(Block, Wirable):
    name = "Piston"
    ascii_str = "P"
    orients = True
    
    max_amt = 0.75

    min_num_outputs = 0
    max_num_outputs = 0

    # boostpads are unlocked by default
    def __init__(self, orientation: Direction = Direction.NORTH, locked: bool = False, **kwargs):
        super().__init__(locked, **kwargs)
        if orientation is Direction.NONE:
            raise ValueError("Piston orientation cannot be `Direction.NONE`")
        self.orientation = orientation
        self.activated = None

        self.widgets.insert(0, DirectionEditor(self, "localvar:orientation", "orientation"))
    
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

    min_num_inputs = 0
    max_num_inputs = 0

    target_entity_type = Barrel

    def __init__(self, orientation: Direction = Direction.NORTH, locked: bool = False, **kwargs):
        super().__init__(locked, **kwargs)
        if orientation is Direction.NONE:
            raise ValueError("Sensor orientation cannot be `Direction.NONE`")
        self.orientation = orientation
        self.activated = None

        self.widgets.insert(0, DirectionEditor(self, "localvar:orientation", "orientation"))
    
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


class PressurePlate(Wirable):
    name = "Pressure Plate"
    ascii_str = "PP"
    orients = False

    min_num_inputs = 0
    max_num_inputs = 0

    target_entity_type = Barrel

    def __init__(self, locked: bool = False, **kwargs):
        super().__init__(locked, **kwargs)
        self.activated = None
    
    def resolve_output_port(self, i) -> bool:
        super().resolve_output_port(i)
        if self.activated is None:
            raise RuntimeError("cannot read output value on a sensor that has not yet obtained a reading (check engine execution order)")
        return self.activated

    def draw_onto_base(self, surf: pg.Surface, rect: pg.Rect, edit_mode: bool, step_progress: float = 0.0, neighborhood = (([],) * 5,) * 5):
        s = rect.width
        padding = s * 0.2
        br = padding / 2
        pg.draw.rect(surf, (50, 50, 50), rect.inflate(-padding, -padding), border_radius=int(br))



class Gate(Wirable):
    """abstract class defining the common behavior of all (single-output) logic gates"""
    orients = False

    min_num_inputs = 2
    max_num_inputs = 5

    left_right_padding = 0.08
    top_bottom_padding = 0.18
    
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
        render_text_centered_xy(text, GATE_PRIMARY_COLOR, surf, rect.center, font_size, bold=True)

    def get_port_offset(self, is_input, index):
        if is_input:
            gate_h = 1.0 - 2*self.top_bottom_padding
            return V2(
                self.left_right_padding,
                self.top_bottom_padding + gate_h * (index + 1) / (self.num_inputs + 1)
            )
        else:
            return V2(
                1.0 - self.left_right_padding,
                0.5
            )


class AndGate(Gate):
    name = "AND Gate"

    def eval(self, *inputs) -> bool:
        return all(inputs)
    
    def draw_onto_base(self, surf: pg.Surface, rect: pg.Rect, edit_mode: bool, step_progress: float=0.0, neighborhood=(([],) * 5,) * 5):
        super().draw_onto_base(surf, rect, edit_mode, step_progress=step_progress, neighborhood=neighborhood)

        m = max(round(rect.width*0.04), 2)
        port_width = m * 2
        port_height = m
        lr_pad = rect.width * self.left_right_padding + port_width
        tb_pad = rect.height * self.top_bottom_padding
        r = rect.height/2 - tb_pad

        # outer
        outer = pg.Rect(
            rect.left + lr_pad , rect.top + tb_pad,
            rect.width - 2*lr_pad - r, rect.height - 2*tb_pad, 
        )
        pg.draw.circle(surf, GATE_PRIMARY_COLOR, 
            (rect.right - lr_pad - r, rect.centery),
            r
        )
        pg.draw.rect(surf, GATE_PRIMARY_COLOR, outer)

        # inner
        
        inner = outer.inflate(-2*m, -2*m)
        inner.width += m
        pg.draw.circle(surf, GATE_BG_COLOR, 
            (rect.right - lr_pad - r, rect.centery),
            r - m
        )
        # draw_aacircle(
        #     surf,
        #     int(rect.right - lr_pad - r), int(rect.centery),
        #     int(r - m),
        #     (255, 255, 255)
        # )
        pg.draw.rect(surf, GATE_BG_COLOR, inner)

        for index in range(self.num_inputs):
            offset = self.get_port_offset(True, index)
            pg.draw.rect(surf, GATE_PRIMARY_COLOR, pg.Rect(
                rect.left + rect.width * offset[0],
                rect.top + rect.height * offset[1] - port_height/2,
                port_width, port_height
            ))
        
        for index in range(self.num_outputs):
            offset = self.get_port_offset(False, index)
            pg.draw.rect(surf, GATE_PRIMARY_COLOR, pg.Rect(
                rect.left + rect.width * offset[0] - (port_width+1),
                rect.top + rect.height * offset[1] - port_height/2,
                port_width+1, port_height
            ))
        

        font_size = rect.width * 0.3
        render_text_centered_xy("AND", GATE_PRIMARY_COLOR, surf, rect.center, font_size, bold=True)


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



# ENTITY_TYPES = [Barrel, Barrier, Boostpad, ResourceExtractor, ResourceTile, Target, Piston, Sensor, PressurePlate, AndGate, OrGate, NotGate]
# get all leaf nodes
ENTITY_TYPES = [c for c in all_subclasses(Entity) if not all_subclasses(c)]
print(ENTITY_TYPES)



class EntityPrototype:
    """a class for storing entity prototypes (e.g. in the palette)"""
    def __init__(self, entity_type, **kwargs):
        self.entity_type = entity_type
        kwargs["locked"] = False
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
