import pickle
import os
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

test_palette = Palette([
    (EntityPrototype(ResourceExtractor), 2),
    (EntityPrototype(Boostpad), 1),
])

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

test_level2 = Level(test_board2, Palette([
    (EntityPrototype(Sensor), 3),
    (EntityPrototype(AndGate), 3),
    (EntityPrototype(OrGate), 3),
    (EntityPrototype(NotGate), 3),
    (EntityPrototype(Piston, orientation=Direction.WEST), 2)
]))



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



def disk(center, r, item):
    """
    fill a disk of radius `r` cells with copies of the given item;
    returns dict in Board constructor format
    """
    locs = [
        (center[0] + x, center[1] + y)
        for y in range(-r, r+1) for x in range(-r, r+1)
        if x**2 + y**2 < r**2
    ]

    return {loc: [copy(item)] for loc in locs}


def random_flood(center, n, item):
    """
    starting at the center, randomly flood a total of `n` cells with copies of the given item;
    returns dict in Board constructor format
    """
    locs = set([center])
    while len(locs) < n:

        # temp = list(locs)
        # shuffle(temp)
        # for l in temp:

        l = choice(list(locs))
        d = choice(Direction.nonzero())
        locs.add((l[0] + d.x, l[1] + d.y))
    
    return {loc: [copy(item)] for loc in locs}


# resource_test = Level(Board({
#     **random_flood((0, 0), 30, ResourceTile(Color.BLUE))
# }), Palette({
#     EntityPrototype(ResourceExtractor): 10,
#     EntityPrototype(Boostpad): 10,
# }))



test_level3 = Level(
    Board({
        **random_flood((0, 0), 12, ResourceTile(Color.BLUE)),
        **random_flood((0, 14), 10, ResourceTile(Color.RED)),
        (12, 7): [Target(Color.VIOLET, count=10)],
        (12, 4): [Target(Color.BLUE, count=10)],
        (12, 10): [Target(Color.RED, count=10)],
    }),
    Palette([
        (EntityPrototype(ResourceExtractor), 2),
        (EntityPrototype(Boostpad), 1),
        (EntityPrototype(Sensor), 1),
        (EntityPrototype(Piston), 2)
    ])
)




test_level4 = Level(
    Board({
        **random_flood((0, 0), 12, ResourceTile(Color.GREEN)),
        (3, 5): [Target(Color.GREEN, count=10)],
        (3, 10): [Target(Color.GREEN, count=10)],
        (3, 15): [Target(Color.GREEN, count=10)],
    }),
    Palette([
        (EntityPrototype(ResourceExtractor), 2),
        (EntityPrototype(Sensor), 5),
        (EntityPrototype(Piston), 3),
        (EntityPrototype(AndGate), 2),
        (EntityPrototype(OrGate), 2),
        (EntityPrototype(NotGate), 2)
    ])
)



test_level5 = Level(
    Board({
        **random_flood((0, -2), 12, ResourceTile(Color.RED_VIOLET)),
        (4, 5): [Target(Color.RED_VIOLET, count=16)],
        (4, 10): [Target(Color.RED_VIOLET, count=8)],
        (4, 15): [Target(Color.RED_VIOLET, count=4)],
        (4, 20): [Target(Color.RED_VIOLET, count=2)],
        (4, 25): [Target(Color.RED_VIOLET, count=1)],
    }),
    Palette([
        (EntityPrototype(ResourceExtractor), 2),
        (EntityPrototype(PressurePlate), 6),
        (EntityPrototype(Piston), 5),
        (EntityPrototype(AndGate), 10),
        (EntityPrototype(OrGate), 10),
        (EntityPrototype(NotGate), 10)
    ])
)




# new_palette = Palette([
#     (EntityPrototype(ResourceExtractor, orientation=Direction.WEST), 2),
# ])

# new_test_level = Level(Board(), new_palette)







ASSETS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "assets"
)

LEVELS_DIR = os.path.join(ASSETS_DIR, "levels")


def save_level(level: Level, filename):
    with open(filename, "wb") as f:
        pickle.dump((level.board, level.palette), f)


def load_level(filename) -> Level:
    with open(filename, "rb") as f:
        board, palette = pickle.load(f)
    
    return Level(board, palette)


if __name__ == "__main__":
    filename = os.path.join(LEVELS_DIR, "test_level2_save.lvl")
    save_level(test_level2, filename)

    lvl = load_level(filename)
    print(lvl)
