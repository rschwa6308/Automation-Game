from enum import Enum
import math

import pygame as pg

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
    
    def __add__(self, other):
        return V2(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other):
        return V2(self.x - other.x, self.y - other.y)
    
    def __mul__(self, factor):
        return V2(self.x * factor, self.y * factor)
    
    def __round__(self):
        return V2(round(self.x), round(self.y))
    
    def fmod(self, div):
        return V2(math.fmod(self.x, div), math.fmod(self.y, div))
    
    # def rotate(self, angle: int):
    #     """return a new V2 of the same length rotated clockwise by `angle` degrees"""
    #     angle = math.radians(angle)
    #     return V2(
    #         self.x * math.cos(angle) - self.y * math.sin(angle),
    #         self.x * math.sin(angle) + self.y * math.cos(angle),
    #     )


class Direction(V2, Enum):
    NONE = (0, 0)
    NORTH = (0, -1)
    EAST = (1, 0)
    SOUTH = (0, 1)
    WEST = (-1, 0)

    def rot90(self, n: int):
        """return the `Direction` that results from rotating 90 degrees clockwise `n` times (can be negative)"""
        if self is Direction.NONE:
            return Direction.NONE
        
        l = list(Direction)[1:]
        return l[(l.index(self) + n) % 4]
        


def draw_chevron(surf: pg.Surface, dest: V2, orientation: Direction, color, width: int):
    """draws a chevron on `surf` pointing in the given orientation with the tip at `dest`"""
    pg.draw.line(
        surf,
        color,
        
        # tuple(draw_pos + e.velocity.rot90(rot) * l),
        # tuple(draw_pos + e.velocity * l),
        width=width
    )


if __name__ == "__main__":
    test = V2(5, -2)
    print(test)
    print(*test)
    print(test[1])
    print(test * 3)

    print(Direction.NORTH)
    print(Direction.NORTH.rot90(-2))
