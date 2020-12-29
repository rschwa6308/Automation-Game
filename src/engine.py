# --- Internal Level Representation and Gamerules --- #
from typing import Sequence
from functools import reduce

from entities import *
from helpers import V2


class Level:
    default_width = 10
    default_height = 8

    board_type = Sequence[Sequence[Sequence[Entity]]]

    @staticmethod
    def get_empty_board(width, height) -> board_type:
        return [
            [[] for _ in range(width)]
            for _ in range(height)
        ]


    def __init__(
        self,
        board: board_type = None
    ):
        if board is None:
            board = Level.get_empty_board(self.default_width, self.default_height)

        self.width = len(board[0])
        self.height = len(board)
        self.board = board

        if not all(len(row) == self.width for row in board):
            raise ValueError("Invalid board shape; board must be rectangular.")
            
        if not all(isinstance(e, Entity) for _, e in self.get_entities()):
            raise ValueError("Invalid board contents; board can only contain Entities.")
    
    def __str__(self):
        def get_ascii_str(cell):
            return "".join(e.ascii_str for e in cell).rjust(2, ".")

        return "\n".join(
            " ".join(get_ascii_str(cell) for cell in row)
            for row in self.board[::-1]     # flip y-axis
        )
    
    def get_cell_at(self, x, y):
        return self.board[y][x]
    
    def remove_at(self, x, y, *entities):
        cell = self.get_cell_at(x, y)
        for e in entities:
            cell.remove(e)
    
    def append_at(self, x, y, *entities):
        cell = self.get_cell_at(x, y)
        for e in entities:
            cell.append(e)
    
    def get_cells(self):
        for x in range(self.width):
            for y in range(self.height):
                cell = self.get_cell_at(x, y)
                yield V2(x, y), cell
    
    def get_entities(self):
        for pos, cell in self.get_cells():
            for e in cell:
                yield pos, e
    
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
        for pos, e in list(self.get_entities()):    # list() avoids concurrent modification
            if e.moves:
                dest = pos + e.velocity
                if self.is_walkable(dest):
                    # move the entity to the dest
                    self.remove_at(*pos, e)
                    self.append_at(*dest, e)
                    # self.get_cell_at(*pos).remove(e)
                    # self.get_cell_at(*dest).append(e)

    def apply_merges(self):
        for pos, cell in self.get_cells():
            mergable = [e for e in cell if e.merges]
            if len(mergable) > 1:
                # merge repeatably
                res = reduce(lambda a, b: a + b, mergable[1:], mergable[0])
                self.remove_at(*pos, *mergable)
                self.append_at(*pos, res)

            

            


from time import sleep

if __name__ == "__main__":
    test_board = Level.get_empty_board(15, 8)
    test_board[3][3].append(ResourceTile(Color.RED))
    test_board[3][3].append(ResourceExtractor())
    test_board[4][5].append(Barrel(Color.RED, Direction.EAST))
    test_board[7][8].append(Barrel(Color.YELLOW, Direction.SOUTH))
    test_level = Level(test_board)

    for _ in range(10):
        print(test_level)
        print()
        sleep(1)
        test_level.step()