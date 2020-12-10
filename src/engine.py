# --- Internal Level Representation and Gamerules --- #
from typing import Sequence, Tuple, Union
from entities import *


class Level:
    DEFAULT_WIDTH = 10
    DEFAULT_HEIGHT = 8

    entity_str_map = {
        type(None): ".",
        ResourceTile: "O",
        ResourceExtractor: "X"
    }

    @staticmethod
    def get_empty_board(width, height):
        return [
            [[None, None] for _ in range(width)]
            for _ in range(height)
        ]


    def __init__(
        self,
        board: Sequence[Sequence[Tuple[Union[Carpet, None], Union[Block, None]]]] = None
    ):
        if board is None:
            board = Level.get_empty_board(self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT)

        self.width = len(board[0])
        self.height = len(board)
        self.board = board

        if not all(len(row) == self.width for row in board):
            raise ValueError("Board must be rectangular, you fool you absolute buffoon")
            
        # if not all(all(isinstance(cell[0], Carpet) and isinstance(cell[1], Block) for cell in row) for row in board):
        #     raise ValueError("Board cells must be of form (Carpet, Block)")
    
    def __str__(self):
        return "\n".join(
            " ".join(
                self.entity_str_map[type(cell[0])] + self.entity_str_map[type(cell[1])]
                for cell in row
            )
            for row in self.board
        )





if __name__ == "__main__":
    test_board = Level.get_empty_board(15, 8)
    test_board[3][5][0] = ResourceTile(Color.RED)
    test_board[3][5][1] = ResourceExtractor()
    test_level = Level(test_board)
    print(test_level)