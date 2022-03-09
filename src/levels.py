from engine import Board, Level, Palette
from entities import *
from level_helpers import disk, random_flood


level_1 = Level(
    Board({
        **random_flood((0, 0), 10, ResourceTile(Color.BLUE)),
        (12, 0): [Target(Color.BLUE, count=10)],
    }),
    Palette([
        (EntityPrototype(ResourceExtractor), 1)
    ]),
    name="Level 1"
)


level_2 = Level(
    Board({
        **random_flood((0, 0), 10, ResourceTile(Color.RED)),
        (8, 8): [Target(Color.RED, count=10)],
    }),
    Palette([
        (EntityPrototype(ResourceExtractor), 1),
        (EntityPrototype(Boostpad), 1),
    ]),
    name="Level 2"
)


level_3 = Level(
    Board({
        # **random_flood((0, -5), 6, ResourceTile(Color.BLUE)),
        # **random_flood((0, 5), 6, ResourceTile(Color.RED)),
        **disk((0, -5), 2, ResourceTile(Color.BLUE)),
        **disk((0, 5), 2, ResourceTile(Color.RED)),
        (8, 0): [Target(Color.RED + Color.BLUE, count=10)],
    }),
    Palette([
        (EntityPrototype(ResourceExtractor), 2),
        (EntityPrototype(Boostpad), 1),
    ]),
    name="Level 3"
)


level_4 = Level(
    Board({
        **disk((-4, 2), 2, ResourceTile(Color.BLUE)),
        **disk((4, 2), 2, ResourceTile(Color.GREEN)),
        (-4, 7): [Target(Color.BLUE, count=10)],
        (4, 7): [Target(Color.GREEN, count=15)],
    }),
    Palette([
        (EntityPrototype(ResourceExtractor), 2),
    ]),
    name="Level 4"
)


level_5 = Level(
    Board({
        **disk((-4, 2), 2, ResourceTile(Color.BLUE)),
        **disk((4, 2), 2, ResourceTile(Color.ORANGE)),
        (-4, 7): [Target(Color.BLUE, count=10)],
        (4, 7): [Target(Color.ORANGE, count=20)],
    }),
    Palette([
        (EntityPrototype(ResourceExtractor), 2),
    ]),
    name="Level 5"
)


level_6 = Level(
    Board({
        **disk((-4, 2), 2, ResourceTile(Color.BLUE)),
        **disk((4, 2), 2, ResourceTile(Color.RED_VIOLET)),
        **disk((4, 12), 2, ResourceTile(Color.RED_VIOLET)),
        (-4, 7): [Target(Color.BLUE, count=10)],
        (8, 7): [Target(Color.RED_VIOLET, count=17)],
        (4, 7): [Boostpad(orientation=Direction.EAST)]
    }),
    Palette([
        (EntityPrototype(ResourceExtractor), 3),
    ]),
    name="Level 6"
)


level_7 = Level(
    Board({
        **random_flood((0, 0), 10, ResourceTile(Color.BLUE_GREEN)),
        (8, -8): [Target(Color.BLUE_GREEN, count=10)],
    }),
    Palette([
        (EntityPrototype(ResourceExtractor), 1),
        (EntityPrototype(Sensor), 1),
        (EntityPrototype(Piston), 1),
    ]),
    name="Level 7"
)


level_8 = Level(
    Board({
        **random_flood((0, 0), 10, ResourceTile(Color.RED_ORANGE)),
        (8, -8): [Target(Color.RED_ORANGE, count=10)],
        (0, -13): [Target(Color.RED_ORANGE, count=10)],
    }),
    Palette([
        (EntityPrototype(ResourceExtractor), 1),
        (EntityPrototype(Sensor), 1),
        (EntityPrototype(Piston), 1),
    ]),
    name="Level 8"
)


level_9 = Level(
    Board({
        **disk((0, 0), 2, ResourceTile(Color.BLUE)),
        **disk((0, 14), 2, ResourceTile(Color.RED)),
        (12, 7): [Target(Color.VIOLET, count=10)],
        (12, 4): [Target(Color.BLUE, count=10)],
        (12, 10): [Target(Color.RED, count=10)],
    }),
    Palette([
        (EntityPrototype(ResourceExtractor), 2),
        (EntityPrototype(Boostpad), 1),
        (EntityPrototype(Sensor), 1),
        (EntityPrototype(Piston), 2)
    ]),
    name="Level 9"
)


level_10 = Level(
    Board({
        **disk((0, 3), 2, ResourceTile(Color.GREEN)),
        (5, 0): [Target(Color.GREEN, count=1)],
        (8, 3): [Target(Color.GREEN, count=14)],
        **disk((-3, 12), 2, ResourceTile(Color.BROWN)),
        **disk((3, 12), 2, ResourceTile(Color.BROWN)),
    }),
    Palette([
        (EntityPrototype(ResourceExtractor), 3),
        (EntityPrototype(Sensor), 2),
        (EntityPrototype(Piston), 2),
        (EntityPrototype(AndGate), 1)
    ]),
    name="Level 10"
)


# TODO
# - intro to sensors & pistons
# - using sensors & pistons to split a single stream
# - using sensors & pistons to split a stream + merging colors
# - intro to logic gates
# ...
