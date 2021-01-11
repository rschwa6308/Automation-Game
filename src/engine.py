# --- Internal Level Representation and Gamerules --- #
from typing import Collection, Mapping, Tuple, Type, Sequence
from functools import reduce
from copy import deepcopy
import pygame as pg             # for type hints

from entities import *
from helpers import V2


class Board:
    """a hashing based sparse-matrix representation of an infinite 2D game board; uses inverted y-axis convention"""
    board_type = Mapping[Tuple[int, int], Collection[Entity]]

    def __init__(self, cells: board_type = {}):
        if not all(all(isinstance(e, Entity) for e in cell) for cell in cells.values()):
            raise ValueError("Invalid board contents; cells can only contain `Entity`s")
        
        cells = {k: v for k, v in cells.items() if v}   # eliminate empty cells
        self.cells = cells
    
    def get(self, x, y):
        """returns a tuple containing all entities at the specified location"""
        if (x, y) in self.cells:
            return tuple(self.cells[(x, y)])   # return an immutable type
        else:
            return tuple()
    
    def get_cells(self, window: pg.Rect = None):
        """returns a generator containing all non-empty cells (along with positions) contained within `window`"""
        if window is None:
            for pos, cell in self.cells.items():
                yield V2(*pos), cell
        else:
            # choose the most efficient iteration method
            # if this ever proves insufficient (doubtful), use a more efficient data structure (e.g. 2D range tree)
            if window.width * window.height < self.get_cell_count():
                for x in range(window.width):
                    for y in range(window.height):
                        pos = (window.left + x, window.top + y)
                        if pos in self.cells:
                            yield V2(*pos), self.cells[pos]
                return (
                    V2(*window.topleft) + V2(x, y)
                    for y in range(window.height)
                    for x in range(window.width)
                )
            else:
                # when window is large, this will almost always be preferred
                for pos, cell in self.cells.items():
                    if window.collidepoint(*pos):
                        yield V2(*pos), cell
    
    def get_cell_count(self):
        """returns the number of non-empty cells"""
        return len(self.cells)

    def get_all(self, filter_type: Type[Entity] = Entity):
        """returns a generator containing all present entities (with positions)"""
        for pos, cell in self.cells.items():
            for e in cell:
                if isinstance(e, filter_type):
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
    
    def get_bounding_rect(self, margin: int = 0) -> pg.Rect:
        """returns the minimal rect completely containing all non-empty cells (with the given margin)"""
        min_x = min(pos[0] for pos in self.cells) - margin
        max_x = max(pos[0] for pos in self.cells) + margin
        min_y = min(pos[1] for pos in self.cells) - margin
        max_y = max(pos[1] for pos in self.cells) + margin

        return pg.Rect(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)

    def get_grid(self, margin: int = 0) -> Sequence[Sequence[Collection[Entity]]]:
        """compute minimal dense-matrix representation (with the given margin)"""
        bounding_rect = self.get_bounding_rect(margin=margin)

        grid = [[None for _ in range(bounding_rect.width)] for _ in range(bounding_rect.height)]

        for x in range(bounding_rect.width):
            for y in range(bounding_rect.height):
                pos = (bounding_rect.left + x, bounding_rect.top + y)
                grid[y][x] = self.get(*pos)
        
        return grid

    def __str__(self):
        def get_ascii_str(cell):
            return "".join(e.ascii_str for e in cell).rjust(2, ".")
        
        grid = self.get_grid(margin=1)

        return "\n".join(
            " ".join(get_ascii_str(cell) for cell in row)
            for row in grid     # do not flip y-axis
        )


class Palette:
    def __init__(self, items: Mapping[Type[Entity], int] = {}):
        self.items = items

    def get_all(self) -> Sequence[Tuple[Type[Entity], int]]:
        """return a list of all items (with counts) sorted by name"""
        return sorted(self.items.items(), key=lambda item: item[0].name)
    
    def remove(self, entity: Entity):
        e_type = type(entity)
        self.items[e_type] -= 1

        if self.items[e_type] == 0:
            self.items.pop(e_type)
    
    def add(self, entity: Entity):
        e_type = type(entity)
        if e_type not in self.items:
            self.items[e_type] = 0

        self.items[e_type] += 1


class Level:
    default_width = 10
    default_height = 8

    def __init__(
        self,
        board: Board = None,
        palette: Palette = None
    ):
        if board is None:
            board = Board()
        
        if palette is None:
            palette = Palette()

        self.board = board
        self.palette = palette

        self.starting_state: Tuple[Board, Palette] = (deepcopy(board), deepcopy(palette))

        self.step_count = 0
        self.won = False
    
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

        # apply resource extractors
        self.apply_resource_extractors()

        # apply merges
        self.apply_merges()

        # apply sensors & pistons

        # apply rotations
        self.apply_rotations()

        # apply targets
        self.apply_targets()

        # check for win
        self.check_won()
        
        self.step_count += 1
    
    def apply_resource_extractors(self):
        for pos, e in list(self.board.get_all(filter_type=ResourceExtractor)):     # list() avoids concurrent modification
            if self.step_count % e.period == e.phase - 1:
                for d in self.board.get(*pos):
                    if isinstance(d, ResourceTile):
                        # spawn (at most) one new barrel here
                        self.board.insert(*pos, Barrel(d.color, e.orientation))
                        break

    def apply_translations(self):
        for pos, e in list(self.board.get_all()):       # list() avoids concurrent modification
            if e.moves:
                dest = pos + e.velocity
                if self.is_walkable(dest):
                    # move the entity to the dest
                    self.board.remove(*pos, e)
                    self.board.insert(*dest, e)
                    # TODO: barrel leak stuff here

    def apply_merges(self):
        for pos, cell in list(self.board.get_cells()):    #  list() avoids concurrent modification
            mergable = [e for e in cell if e.merges]
            if len(mergable) > 1:
                # merge repeatably
                res = sum(mergable[1:], mergable[0])
                self.board.remove(*pos, *mergable)
                self.board.insert(*pos, res)
    
    def apply_rotations(self):
        for pos, e in list(self.board.get_all(filter_type=Boostpad)):
            for d in self.board.get(*pos):
                if d.moves:
                    d.velocity = e.orientation
    
    def apply_targets(self):
        for pos, e in list(self.board.get_all(filter_type=Target)):
            for d in self.board.get(*pos):
                if isinstance(d, Barrel):
                    self.board.remove(*pos, d)  # absorb barrel regardless of color
                    if d.color is e.color:
                        e.count -= 1
    
    def check_won(self):
        self.won = all(e.count == 0 for _, e in self.board.get_all(filter_type=Target))

    def reset(self):
        self.board, self.palette = self.starting_state
        self.step_count = 0
        self.won = False
    
    def save_state(self):
        """save the current board and palette state"""
        self.saved_state = (deepcopy(self.board), deepcopy(self.palette))

    def load_saved_state(self):
        """revert `board` and `palette` to their states at the last call to `save_state`"""
        self.board, self.palette = self.saved_state
        self.step_count = 0
        self.won = False


from time import sleep

if __name__ == "__main__":

    test_board = Board({
        (3, 3): [ResourceTile(Color.RED), ResourceExtractor()],
        (5, 4): [Barrel(Color.RED, Direction.EAST)],
        (8, 7): [Barrel(Color.YELLOW, Direction.SOUTH)]
    })

    test_level = Level(test_board)

    for _ in range(10):
        print(test_level)
        print()
        sleep(1)
        test_level.step()