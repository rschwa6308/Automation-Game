# --- Level Entities --- #
from colors import Color


class Entity:
    pass


class Carpet(Entity):
    pass


class Block(Entity):
    pass




class Barrel(Block):
    name = "Barrel"

    def __init__(self, color: Color):
        self.color = color


class ResourceTile(Carpet):
    name = "Resource Tile"

    def __init__(self, color: Color):
        self.color = color


class ResourceExtractor(Block):
    name = "Resource Extractor"

    def __init__(self, orientation):
        self.orientation = orientation
        # TODO: figure out how to store NSEW :)
