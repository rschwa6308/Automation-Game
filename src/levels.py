from engine import Level
from entities import *


test_board = Level.get_empty_board(15, 8)
test_board[3][3].append(ResourceTile(Color.RED))
test_board[3][3].append(ResourceExtractor())
test_board[4][5].append(Barrel(Color.RED, Direction.EAST))
test_board[7][8].append(Barrel(Color.YELLOW, Direction.SOUTH))
test_level = Level(test_board)
