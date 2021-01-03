from engine import Board, Level
from entities import *


test_board = Board({
        (3, 3): [ResourceTile(Color.RED), ResourceExtractor()],
        (5, 4): [Barrel(Color.RED, Direction.SOUTH)],
        (2, 7): [Barrel(Color.YELLOW, Direction.EAST)],
        (-1, -1): [Barrel(Color.BLUE_GREEN, Direction.NORTH)],
        (3, 0): [Boostpad(Direction.WEST)]
    })

test_level = Level(test_board, [
    (ResourceExtractor, 2),
    (Boostpad, 7),
])
