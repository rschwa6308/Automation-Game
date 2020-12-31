from engine import Board, Level
from entities import *


test_board = Board({
        (3, 3): [ResourceTile(Color.RED)],
        (3, 3): [ResourceExtractor()],
        (5, 4): [Barrel(Color.RED, Direction.SOUTH)],
        (2, 7): [Barrel(Color.YELLOW, Direction.EAST)],
        (-1, -1): [Barrel(Color.BLUE_GREEN, Direction.NORTH)]
    })

test_level = Level(test_board, [
    (ResourceExtractor, 2),
    (ResourceTile, 7),
])
