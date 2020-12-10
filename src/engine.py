# --- Internal Level Representation and Gamerules --- #
from entities import *


class Level:
    entity_str_map = {
        None: ".",
    }

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.board = [[None for _ in range(width)] for _ in range(height)]
    
    def __str__(self):
        return "\n".join(
            "".join(self.entity_str_map[e] for e in row)
            for row in self.board
        )


if __name__ == "__main__":
    test_level = Level(10, 8)
    print(test_level)