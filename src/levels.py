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


from random import choice
# a, b = choice(list(Color)), choice(list(Color))
a, b = Color.RED, Color.BLUE

test_board2 = Board({
        (-3, 0): [ResourceTile(a), ResourceExtractor(Direction.EAST)],
        (3, 0): [ResourceTile(b), ResourceExtractor(Direction.WEST)],
        (0, 0): [Boostpad(Direction.NORTH)],
        (0, -8): [Target(a + b, 100)]
    })

test_level2 = Level(test_board2, Palette())
