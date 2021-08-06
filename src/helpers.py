from enum import Enum
import math
from typing import Sequence
import pygame as pg
import pygame.freetype


class V2:
    """2D vector class"""
    def __init__(self, x, y):
        self.x = x
        self.y = y
    
    def __str__(self):
        return f"V2({self.x}, {self.y})"
    
    def __iter__(self):
        return iter((self.x, self.y))
    
    def __getitem__(self, item):
        return (self.x, self.y)[item]
    
    def __eq__(self, other) -> bool:
        return self.x == other.x and self.y == other.y
    
    def __add__(self, other):
        return V2(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other):
        return V2(self.x - other.x, self.y - other.y)
    
    def __mul__(self, factor):
        return V2(self.x * factor, self.y * factor)
    
    def __truediv__(self, d):
        return self * (1 / d)
    
    def __neg__(self):
        return V2(-self.x, -self.y)
    
    def __round__(self):
        return V2(round(self.x), round(self.y))
    
    def length(self):
        """L^2 vector norm"""
        return (self.x ** 2 + self.y ** 2) ** 0.5
    
    def fmod(self, div):
        return V2(math.fmod((math.fmod(self.x, div) + div), div), math.fmod((math.fmod(self.y, div) + div), div))
    
    def rotate(self, angle: int):
        """return a new V2 of the same length rotated clockwise by `angle` degrees"""
        angle = math.radians(angle)
        return V2(
            self.x * math.cos(angle) - self.y * math.sin(angle),
            self.x * math.sin(angle) + self.y * math.cos(angle),
        )
    
    def floor(self):
        """return a new V2 with the components floored"""
        return V2(math.floor(self.x), math.floor(self.y))


class Direction(V2, Enum):
    NONE = (0, 0)
    NORTH = (0, -1)
    EAST = (1, 0)
    SOUTH = (0, 1)
    WEST = (-1, 0)

    @staticmethod
    def nonzero():
        return [Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST]

    def rot90(self, n: int):
        """return the `Direction` that results from rotating 90 degrees clockwise `n` times (can be negative)"""
        if self is Direction.NONE:
            return Direction.NONE
        
        l = Direction.nonzero()
        return l[(l.index(self) + n) % 4]
        

# --- Text/Fonts --- #
pg.freetype.init()
default_font = pg.freetype.SysFont("consolas", 16)      # should be monospaced (makes life easier)

def render_text_centered_x(text, color, surf, dest, font_size, bold=False):
    s = int(font_size)
    # s = max([rec for rec in default_font.get_sizes() if rec[1] <= height], key=lambda rec: rec[1])[0]
    style = pg.freetype.STYLE_STRONG if bold else pg.freetype.STYLE_DEFAULT
    text_img, text_rect = default_font.render(text, fgcolor=color, size=s, style=style)
    surf.blit(
        text_img,
        (dest[0] - text_rect.width / 2, dest[1])
    )

def render_text_centered_xy(text, color, surf, dest, font_size, bold=False):
    s = int(font_size)
    # s = max([rec for rec in default_font.get_sizes() if rec[1] <= height], key=lambda rec: rec[1])[0]
    style = pg.freetype.STYLE_STRONG if bold else pg.freetype.STYLE_DEFAULT
    text_img, text_rect = default_font.render(text, fgcolor=color, size=s, style=style)
    surf.blit(
        text_img,
        (dest[0] - text_rect.width / 2, dest[1] - text_rect.height / 2)
    )

def render_text_left_justified(text, color, surf, dest, font_size, bold=False):
    s = int(font_size)
    # s = max([rec for rec in default_font.get_sizes() if rec[1] <= height], key=lambda rec: rec[1])[0]
    style = pg.freetype.STYLE_STRONG if bold else pg.freetype.STYLE_DEFAULT
    text_img, text_rect = default_font.render(text, fgcolor=color, size=s, style=style)
    surf.blit(
        text_img,
        (dest[0], dest[1] - text_rect.height / 2)
    )

def render_text_centered_x_wrapped(
    text, color, font_size, surf,
    midtop, line_width_px,
    padding_top=0, padding_bottom=0, padding_sides=0, **kwargs
):
    line_width_chars = (line_width_px - padding_sides*2) // (font_size/2)
    line_height_px = round(font_size * 1.1)
    lines = wrap_text(text, line_width_chars)

    total_text_height = line_height_px * len(lines)
    for i, line in enumerate(lines):
        render_text_centered_x(
            line, color, surf,
            V2(*midtop) + V2(0, padding_top + line_height_px * i),
            font_size,
            **kwargs
        )
    
    return pg.Rect(
        midtop[0] - line_width_px/2, midtop[1],
        line_width_px, total_text_height + padding_bottom
    )

def render_text_centered_xy_wrapped(
    text, color, font_size,
    surf, center, line_width_px,
    padding_top=0, padding_bottom=0, padding_sides=0, **kwargs
):
    line_width_chars = (line_width_px - padding_sides*2) // (font_size/2)
    line_height_px = round(font_size * 1.1)
    lines = wrap_text(text, line_width_chars)

    total_text_height = line_height_px * len(lines)
    midtop = V2(*center) - V2(0, total_text_height/2)
    for i, line in enumerate(lines):
        # print(line)
        if len(lines) % 2:
            # print("x and y")
            render_text_centered_x(
                line, color, surf,
                midtop + V2(0, line_height_px * i),
                font_size,
                **kwargs
            )
        else:
            # print("x only")
            render_text_centered_xy(
                line, color, surf,
                midtop + V2(0, line_height_px * (i + 0.5)),
                font_size,
                **kwargs
            )
    
    return pg.Rect(
        midtop[0] - line_width_px/2, midtop[1],
        line_width_px, total_text_height + padding_top + padding_bottom
    )
# ------------------ #


# --- Drawing --- #
def draw_chevron(surf: pg.Surface, dest: V2, orientation: V2, color, length: int, width: int, angle: int = 90) -> pg.Rect:
    """draws a chevron on `surf` pointing in the given orientation with the tip at `dest`"""
    a = dest - orientation.rotate(angle // 2) * length
    b = dest - orientation.rotate(-angle // 2) * length
    return pg.draw.polygon(
        surf,
        color,
        [
            tuple(dest),
            tuple(round(a)),
            tuple(round(a - orientation.rotate(-angle // 2) * width)),
            tuple(round(dest - orientation * (width / math.sin(math.radians(angle) / 2)))),
            tuple(round(b - orientation.rotate(angle // 2) * width)),
            tuple(round(b))
        ]
    )

def draw_aacircle(surf, x, y, r, color):
    """draws a filled anti-aliased circle at the given position and radius"""
    pg.gfxdraw.aacircle(surf, x, y, r, color)
    pg.gfxdraw.filled_circle(surf, x, y, r, color)


def draw_aapolygon(surf, points, color):
    pg.gfxdraw.aapolygon(surf, points, color)
    pg.gfxdraw.filled_polygon(surf, points, color)


def draw_rectangle(surf, rect, color, thickness=1):
    """draws a rectangle with given draw thickness"""
    # thickness += 1
    a = 1 - thickness % 2   # adjustment
    pg.draw.rect(surf, color, pg.Rect(rect.left, rect.top, rect.width, thickness))
    pg.draw.rect(surf, color, pg.Rect(rect.left, rect.bottom - thickness + 1, rect.width + a, thickness))   # `+ a` fills in bottom right pixel
    pg.draw.rect(surf, color, pg.Rect(rect.left, rect.top, thickness, rect.height))
    pg.draw.rect(surf, color, pg.Rect(rect.right - thickness + 1, rect.top, thickness, rect.height))

def draw_rect_alpha(surface, color, rect, width=0, border_radius=0):
    assert(len(color) == 4)
    shape_surf = pg.Surface(rect.size)
    shape_surf.set_colorkey((0, 0, 0))
    shape_surf.set_alpha(color[-1])
    pg.draw.rect(shape_surf, color[:3], shape_surf.get_rect(), width=width, border_radius=border_radius)
    surface.blit(shape_surf, rect.topleft)
# --------------- #


# --- Misc --- #
def wrap_text(text, line_length) -> Sequence[str]:
    """splits the given `text` into lines of length at most `line_length` (seperating only at spaces)"""
    words = text.split()
    assert(all(len(word)<= line_length for word in words))  # not possible otherwise
    lines = [[]]
    for word in words:
        if len(" ".join(lines[-1] + [word])) <= line_length:
            lines[-1].append(word)
        else:
            lines.append([word])
    return [" ".join(line) for line in lines]

def clamp(value, min_v, max_v):
    """return rectified value (i.e. the closest point in [`min_v`, `max_v`])"""
    return max(min_v, min(value, max_v))

def sgn(x):
    return 1 if x >= 0 else -1

def interpolate_colors(a, b, bias):
    """takes two RGB tuples and returns a componentwise weighted average"""
    return (
        int(a[0] * (1 - bias) + b[0] * bias),
        int(a[1] * (1 - bias) + b[1] * bias),
        int(a[2] * (1 - bias) + b[2] * bias),
    )

def all_subclasses(cls):
    return set(cls.__subclasses__()).union(
        [s for c in cls.__subclasses__() for s in all_subclasses(c)])

def rect_union(rects):
    rect = None
    for r in rects:
        if r is None: continue
        if rect is None:
            rect = r.copy()
        else:
            rect.union_ip(r)
    return rect
# ------------ #


if __name__ == "__main__":
    test = V2(5, -2)
    print(test)
    print(*test)
    print(test[1])
    print(test * 3)

    print(Direction.NORTH)
    print(Direction.NORTH.rot90(-2))

    print(wrap_text("this is a test string containing long and short words", 12))