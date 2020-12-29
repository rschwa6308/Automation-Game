# --- Internal Level Representation and Gamerules --- #
from typing import Collection, Mapping, Sequence
from functools import reduce

from entities import *
from helpers import V2


class Board:
    """a hashing based sparse-matrix representation of an infinite 2D game board"""
    board_type = Mapping[V2, Collection[Entity]]

    def __init__(self, cells: board_type = {}):
        if not all(all(isinstance(e, Entity) for e in cell) for cell in cells.values()):
            raise ValueError("Invalid board contents; cells can only contain `Entity`s")

        self.cells = cells
    
    def get(self, pos):
        if pos in self.cells:
            return tuple(self.cells[pos])   # return an immutable type
        else:
            return tuple()
    
    def insert(self, pos, *entities):
        if pos not in self.cells:
            self.cells[pos] = []
        self.cells[pos].extend(entities)
    
    def remove(self, pos, *entities):
        if pos not in self.cells or any(e not in self.cells[pos] for e in entities):
            raise ValueError(f"Cannot remove non-present entities (at pos {pos})")
        
        for e in entities:
            self.cells[pos].remove(e)
    
    def get_all(self):
        for pos, cell in self.cells.items():
            for e in cell:
                yield pos, e
    
    def get_grid(self) -> Sequence[Sequence[Collection[Entity]]]:
        """compute minimal dense-matrix representation"""
        min_x = min(pos.x for pos in self.cells)
        max_x = max(pos.x for pos in self.cells)
        min_y = min(pos.y for pos in self.cells)
        max_y = max(pos.y for pos in self.cells)

        width = max_x - min_x + 1
        height = max_y - min_y + 1

        grid = [[None for _ in range(width)] for _ in range(height)]

        for x in range(width):
            for y in range(height):
                pos = V2(min_x + x, min_y + y)
                print(pos)
                grid[y][x] = self.get(pos)
        
        return grid




class Level:
    default_width = 10
    default_height = 8

    def __init__(
        self,
        board: Board = None
    ):
        if board is None:
            board = Board()

        # self.width = len(board[0])
        # self.height = len(board)
        self.board = board

        # if not all(len(row) == self.width for row in board):
        #     raise ValueError("Invalid board shape; board must be rectangular.")
            
        # if not all(isinstance(e, Entity) for _, e in self.get_entities()):
        #     raise ValueError("Invalid board contents; board can only contain Entities.")
    
    def __str__(self):
        def get_ascii_str(cell):
            return "".join(e.ascii_str for e in cell).rjust(2, ".")

        return "\n".join(
            " ".join(get_ascii_str(cell) for cell in row)
            for row in self.board[::-1]     # flip y-axis
        )
    
    # def get_cell_at(self, x, y):
    #     return self.board[y][x]
    
    # def remove_at(self, x, y, *entities):
    #     cell = self.get_cell_at(x, y)
    #     for e in entities:
    #         cell.remove(e)
    
    # def append_at(self, x, y, *entities):
    #     cell = self.get_cell_at(x, y)
    #     for e in entities:
    #         cell.append(e)
    
    # def get_cells(self):
    #     for x in range(self.width):
    #         for y in range(self.height):
    #             cell = self.get_cell_at(x, y)
    #             yield V2(x, y), cell
    
    # def get_entities(self):
    #     for pos, cell in self.get_cells():
    #         for e in cell:
    #             yield pos, e
    
    def is_in_bounds(self, coords):
        return 0 <= coords[0] < self.width and 0 <= coords[1] < self.height
    
    # Returns true iff the given coords are in bounds and the corresponding tile does not contain a `stops` Entity
    def is_walkable(self, coords):
        if not self.is_in_bounds(coords):
            return False
        
        cell = self.get_cell_at(*coords)
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
                    self.board.remove(pos, e)
                    self.board.insert(dest, e)

    def apply_merges(self):
        for pos, cell in list(self.board.get_all()):    #  list() avoids concurrent modification
            mergable = [e for e in cell if e.merges]
            if len(mergable) > 1:
                # merge repeatably
                res = reduce(lambda a, b: a + b, mergable[1:], mergable[0])
                self.board.remove(pos, *mergable)
                self.board.insert(pos, res)


from time import sleep
from pprint import pprint

if __name__ == "__main__":

    test_board = Board({
        V2(3, 3): [ResourceTile(Color.RED)],
        V2(3, 3): [ResourceExtractor()],
        V2(5, 4): [Barrel(Color.RED, Direction.EAST)],
        V2(8, 7): [Barrel(Color.YELLOW, Direction.SOUTH)]
    })


    print(test_board.get(V2(3, 3)))     # TODO: debug this
    pprint(test_board.get_grid())
    test_level = Level(test_board)

    for _ in range(10):
        print(test_level)
        print()
        sleep(1)
        test_level.step()