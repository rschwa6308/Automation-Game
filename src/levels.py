from random import choice, random, shuffle
from copy import copy

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


# a, b = choice(list(Color)), choice(list(Color))
a, b = Color.RED, Color.BLUE

test_board2 = Board({
    (-3, 0): [ResourceTile(a), ResourceExtractor(Direction.EAST)],
    (3, 0): [ResourceTile(b), ResourceExtractor(Direction.WEST)],
    (0, 0): [Boostpad(Direction.NORTH)],
    (5, -8): [Target(a + b, 10)],
    (5, -5): [Piston()],
    (7, -7): [Piston()],
    (10, -7): [Piston()],
    # (5, -6): [Barrel(Color.YELLOW)],
    # (5, -7): [Barrel(Color.BLUE)],
})

test_level2 = Level(test_board2, Palette({
    Sensor: 3,
    AndGate: 3,
    OrGate: 3,
    NotGate: 3
}))



minimal_level = Level(
    Board({
        (0, 0): [Piston()],
        (0, 5): [Sensor()]
    }),
    Palette()
)


# def random_flood(n, center=(0, 0)):
#     """starting at the origin, randomly flood a total of `n` cells (returns list of locations)"""
#     locs = set([center])
#     while True:
#         if len(locs) >= n:
#             return locs
#         temp = list(locs)
#         shuffle(temp)
#         for l in temp:
#             d = choice(Direction.nonzero())
#             locs.add((l[0] + d.x, l[1] + d.y))



def random_flood(center, n, item):
    """
    starting at the center, randomly flood a total of `n` cells with copies of the given item;
    returns dict in Board constructor format
    """
    locs = set([center])
    while len(locs) < n:

        temp = list(locs)
        shuffle(temp)
        for l in temp:
            d = choice(Direction.nonzero())
            locs.add((l[0] + d.x, l[1] + d.y))
    
    return {loc: [copy(item)] for loc in locs}


resource_test = Level(Board({
    **random_flood((0, 0), 30, ResourceTile(Color.BLUE))
    # loc: [ResourceTile(Color.BLUE)]
    # for loc in random_flood(30)
    # (0, 0): [ResourceTile(Color.BLUE)],
    # (0, 1): [ResourceTile(Color.BLUE)],
    # (1, 0): [ResourceTile(Color.BLUE)],
    # (1, 1): [ResourceTile(Color.BLUE)],
    # (1, 2): [ResourceTile(Color.BLUE)],
    # (-1, 0): [ResourceTile(Color.BLUE)],
    # (0, -1): [ResourceTile(Color.BLUE)],
    # (-2, 0): [ResourceTile(Color.BLUE)],
    # (-2, 1): [ResourceTile(Color.BLUE)],
    # (5, 0): [ResourceTile(Color.BLUE)],
    # (-3, 1): [ResourceTile(Color.ORANGE)],
    # (10, 10): [ResourceTile(Color.RED)],
    # (10, 11): [ResourceTile(Color.RED)],
    # (11, 10): [ResourceTile(Color.RED)],
    # (11, 11): [ResourceTile(Color.RED)],
}), Palette({
    ResourceExtractor: 10,
    Boostpad: 10,
}))


# dirs = list(Direction)
# dirs.remove(Direction.NONE)

# cells = {(0, 0): [ResourceTile(Color.BLUE), ResourceExtractor(choice(dirs))]}

# for x in range(-5, 6):
#     for y in range(-5, 6):
#         if x == 0 and y == 0: continue
#         options = list(dirs)
#         for neighbor in ((x - 1, y), (x, y - 1)):
#             if neighbor in cells:
#                 print(cells[neighbor][-1].orientation.rot90(2))
#                 try: options.remove(cells[neighbor][-1].orientation.rot90(2))
#                 except: pass
#         cells[(x, y)] = [Boostpad(choice(options))]

# # print(cells)

# random_level = Level(Board(cells), Palette())


test_level3 = Level(
    Board({
        **random_flood((0, 0), 12, ResourceTile(Color.BLUE)),
        **random_flood((0, 14), 10, ResourceTile(Color.RED)),
        (12, 7): [Target(Color.VIOLET, count=10)],
        (12, 4): [Target(Color.BLUE, count=10)],
        (12, 10): [Target(Color.RED, count=10)],
    }),
    Palette({
        ResourceExtractor: 2,
        Boostpad: 1,
        Sensor: 1,
        Piston: 2
    })
)

