from enum import Enum
from math import fmod


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
        return V2(fmod(self.x, div), fmod(self.y, div))


class Direction(V2, Enum):
    NONE = (0, 0)
    NORTH = (0, -1)
    SOUTH = (0, 1)
    EAST = (1, 0)
    WEST = (-1, 0)


if __name__ == "__main__":
    test = V2(5, -2)
    print(test)
    print(*test)
    print(test[1])
    print(test * 3)

    print(Direction.NORTH)