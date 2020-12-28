# --- Level Entities --- #
from helpers import Direction
from colors import Color



class Entity:
    moves: bool = False
    stops: bool = False
    merges: bool = False


class Carpet(Entity):
    stops = False


class Block(Entity):
    stops = True



class Barrel(Block):
    name = "Barrel"
    ascii_str = "B"
    moves = True
    stops = False
    merges = True

    def __init__(self, color: Color, velocity: Direction = Direction.NONE):
        self.color = color
        self.velocity = velocity
    
    def __add__(self, other):
        return Barrel(self.color + other.color)


class ResourceTile(Carpet):
    name = "Resource Tile"
    ascii_str = "O"

    def __init__(self, color: Color):
        self.color = color


class ResourceExtractor(Block):
    name = "Resource Extractor"
    ascii_str = "X"

    def __init__(self, orientation: Direction = Direction.NORTH):
        self.orientation = orientation
