from engine import Board, Level, Palette
from entities import *


test_board = Board({
        (3, 3): [ResourceTile(Color.RED), ResourceExtractor()],
        (5, 4): [Barrel(Color.RED, Direction.SOUTH)],
        (2, 7): [Barrel(Color.YELLOW, Direction.EAST)],
        (-1, -1): [Barrel(Color.BLUE_GREEN, Direction.NORTH)],
        (3, 0): [Boostpad(Direction.WEST)],
        (-5, 5): [ResourceTile(Color.BLUE), ResourceExtractor()],
        (-5, 2): [Target(Color.BLUE, 5)],
        (-5, 0): [Boostpad(Direction.NORTH)],
        (1, 1): [Barrier()],
        (1, 2): [Barrier()],
        (1, 3): [Barrier()],
        (1, 0): [Barrier()],
        (2, 0): [Barrier()],
        (2, 1): [Barrier()],
    })

test_palette = Palette({
    ResourceExtractor: 2,
    Boostpad: 7,
})

test_level = Level(test_board, test_palette)
