# --- Level Entities --- #
from colors import *


class Entity:
    pass


class Carpet(Entity):
    pass


class Block(Entity):
    pass


class ResourceTile(Carpet):
    name = "Resource Tile"
    