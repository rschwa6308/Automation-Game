import enum
import pygame as pg

from colors import Color, COLOR_RGB_MAP



CELL_SIZE_PX = 64
CELL_PADDING_PX = 0
LABEL_MARGIN_PX = 4

BACKGROUND_COLOR = (255, 255, 255)

TARGET_FPS = 60


def show_color_grid(grid):
    grid_width, grid_height = len(grid[0]), len(grid)
    screen = pg.display.set_mode((
        grid_width * CELL_SIZE_PX + LABEL_MARGIN_PX,
        grid_height * CELL_SIZE_PX + LABEL_MARGIN_PX
    ))

    screen.fill(BACKGROUND_COLOR)

    for y in range(grid_height):
        for x in range(grid_width):
            color = grid[y][x]
            if color is not None:
                x_margin = LABEL_MARGIN_PX if x > 0 else 0
                y_margin = LABEL_MARGIN_PX if y > 0 else 0
                rect = pg.Rect(
                    CELL_SIZE_PX * x + CELL_PADDING_PX + x_margin,
                    CELL_SIZE_PX * y + CELL_PADDING_PX + y_margin,
                    CELL_SIZE_PX - 2 * CELL_PADDING_PX,
                    CELL_SIZE_PX - 2 * CELL_PADDING_PX
                )
                pg.draw.rect(screen, COLOR_RGB_MAP[color], rect)

    pg.display.update()

    clock = pg.time.Clock()
    alive = True
    while alive:
        clock.tick(TARGET_FPS)

        for event in pg.event.get():
            if event.type == pg.QUIT:
                alive = False


from pprint import pprint
from random import shuffle

if __name__ == "__main__":

    colors = list(Color)

    colors = colors[:-1]        # discard BROWN label
    colors += colors[:1]        # repeat RED at end
    # colors *= 2

    # rot = 0
    # colors = colors[rot:] + colors[:rot]

    # shuffle(colors)

    grid = [
        [None for _ in range(len(colors) + 1)]
        for _ in range(len(colors) + 1)
    ]

    for i, c in enumerate(colors):
        print(c)
        grid[0][i + 1] = c
        grid[i + 1][0] = c
    
    for x, c1 in enumerate(colors):
        for y, c2 in enumerate(colors):
            grid[y + 1][x + 1] = c1 + c2
    
    # pprint(grid)

    show_color_grid(grid)