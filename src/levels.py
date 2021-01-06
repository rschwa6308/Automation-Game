from engine import Board, Level, Palette
from entities import *


test_board = Board({
        (1, 3): [ResourceTile(Color.RED)],
        (3, 0): [Boostpad(Direction.WEST)],
        (-5, 9): [ResourceTile(Color.BLUE)],
        (-5, -3): [Target(Color.VIOLET, 5)],
    })

test_palette = Palette({
    ResourceExtractor: 2,
    Boostpad: 1,
})

test_level = Level(test_board, test_palette)
