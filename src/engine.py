# --- Internal Level Representation and Gamerules --- #
from typing import Collection, Mapping, Tuple, Sequence
from functools import reduce

from entities import *
from helpers import V2


class Board:
    """a hashing based sparse-matrix representation of an infinite 2D game board"""
    board_type = Mapping[Tuple[int, int], Collection[Entity]]

    def __init__(self, cells: board_type = {}):
        if not all(all(isinstance(e, Entity) for e in cell) for cell in cells.values()):
            raise ValueError("Invalid board contents; cells can only contain `Entity`s")

        self.cells = cells
    
    def get(self, x, y):
        """returns a tuple containing all entities at the specified location"""
        if (x, y) in self.cells:
            return tuple(self.cells[(x, y)])   # return an immutable type
        else:
            return tuple()
    
    def get_cells(self):
        """returns a generator containing all non-empty cells (with positions)"""
        for pos, cell in self.cells.items():
            yield V2(*pos), cell

    def get_all(self):
        """returns a generator containing all present entities (with positions)"""
        for pos, cell in self.cells.items():
            for e in cell:
                yield V2(*pos), e

    def insert(self, x, y, *entities):
        pos = (x, y)
        if pos not in self.cells:
            self.cells[pos] = []
        self.cells[pos].extend(entities)
    
    def remove(self, x, y, *entities):
        pos = (x, y)
        if pos not in self.cells or any(e not in self.cells[pos] for e in entities):
            raise ValueError(f"Cannot remove non-present entities (at pos {pos})")
        
        for e in entities:
            self.cells[pos].remove(e)
    
    
    
    def get_grid(self, margin=0) -> Sequence[Sequence[Collection[Entity]]]:
        """compute minimal dense-matrix representation (with margin)"""
        min_x = min(pos[0] for pos in self.cells) - margin
        max_x = max(pos[0] for pos in self.cells) + margin
        min_y = min(pos[1] for pos in self.cells) - margin
        max_y = max(pos[1] for pos in self.cells) + margin

        width = max_x - min_x + 1
        height = max_y - min_y + 1

        grid = [[None for _ in range(width)] for _ in range(height)]

        for x in range(width):
            for y in range(height):
                pos = (min_x + x, min_y + y)
                grid[y][x] = self.get(*pos)
        
        return grid

    def __str__(self):
        def get_ascii_str(cell):
            return "".join(e.ascii_str for e in cell).rjust(2, ".")
        
        grid = self.get_grid(margin=1)

        return "\n".join(
            " ".join(get_ascii_str(cell) for cell in row)
            for row in grid[::-1]     # flip y-axis
        )



class Level:
    default_width = 10
    default_height = 8

    def __init__(
        self,
        board: Board = None
    ):
        if board is None:
            board = Board()

        self.board = board
    
    def __str__(self):
        return str(self.board)
    
    # Returns true iff the given coords are in bounds and the corresponding tile does not contain a `stops` Entity
    def is_walkable(self, coords):
        cell = self.board.get(*coords)
        return not any(e.stops for e in cell)
    
    def step(self):
        """step the level one time unit"""
        # apply translations
        self.apply_translations()

        # apply merges
        self.apply_merges()

        # apply sensors & pistons

        # apply rotations

        # apply others (?)

    def apply_translations(self):
        for pos, e in list(self.board.get_all()):       # list() avoids concurrent modification
            if e.moves:
                dest = pos + e.velocity
                if self.is_walkable(dest):
                    # move the entity to the dest
                    self.board.remove(*pos, e)
                    self.board.insert(*dest, e)

    def apply_merges(self):
        for pos, cell in list(self.board.get_cells()):    #  list() avoids concurrent modification
            mergable = [e for e in cell if e.merges]
            if len(mergable) > 1:
                # merge repeatably
                res = reduce(lambda a, b: a + b, mergable[1:], mergable[0])
                self.board.remove(*pos, *mergable)
                self.board.insert(*pos, res)


from time import sleep
from pprint import pprint

if __name__ == "__main__":

    test_board = Board({
        (3, 3): [ResourceTile(Color.RED)],
        (3, 3): [ResourceExtractor()],
        (5, 4): [Barrel(Color.RED, Direction.EAST)],
        (8, 7): [Barrel(Color.YELLOW, Direction.SOUTH)]
    })

    test_level = Level(test_board)

    for _ in range(10):
        print(test_level)
        print()
        sleep(1)
        test_level.step()