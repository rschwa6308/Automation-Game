from typing import Sequence
import pygame as pg
import pygame.gfxdraw

from helpers import V2


NUM_STEPS = 25      # looks flawless at 100, but can be made lower if need speed

def draw_bezier_curve(surf, points: Sequence[V2], color, width=1, draw_points=False, antialising=True):
    """
    draws `O(width ** 2)` 1-wide bezier curves; circular endcaps and antialising
    TODO: this is idiotic
    TODO: clamp the offset start and end points to the original bounding box;
    TODO: might be able to get away with only drawing the perimeter of the circle, which is `O(width)`
    """
    if draw_points:
        for p in points:
            pg.draw.circle(surf, color, tuple(p), width * 1.5)
    
    if width <= 2:
        antialising = False
    
    radius = width / 2
    base_alpha = color[3] if len(color) == 4 else 255
    for i in range(width):
        for j in range(width):
            offset = V2(-width // 2 + i, -width // 2 + j)
            if width > 2 and offset.length() > radius: continue

            if antialising:
                alpha = base_alpha * (1 - (offset.length() / radius))
            else:
                alpha = base_alpha
            # print(alpha)
            offset_points = [p + offset for p in points]
            pg.gfxdraw.bezier(surf, offset_points, NUM_STEPS, (*color, alpha))


def draw_ess_curve(surf, start: V2, end: V2, color, width=1, sharpness=0.5):
    """
    draw an "S" shaped bezier curve between the two given points;
    orientation of S is chosen to minimize curvature;
    TODO: when start and end are in the same row/column, draw a line instead (avoids obvious aliasing)
    """
    s = sharpness
    
    delta = end - start
    if abs(delta.x) > abs(delta.y):
        control_points = [
            V2(start.x + delta.x * s, start.y),
            V2(end.x - delta.x * s, end.y)
        ]
    else:
        control_points = [
            V2(start.x, start.y + delta.y * s),
            V2(end.x, end.y - delta.y * s)
        ]    
    draw_bezier_curve(surf, [start, *control_points, end], color, width)





if __name__ == "__main__":
    BG_COLOR = (255, 255, 255)
    CURVE_COLOR = (255, 0, 0)


    screen = pg.display.set_mode((1000, 800))
    clock = pg.time.Clock()
    alive = True
    while alive:
        clock.tick(60)

        for event in pg.event.get():
            if event.type == pg.QUIT:
                alive = False
        
        screen.fill(BG_COLOR)
        draw_ess_curve(
            screen,
            V2(100, 100),
            V2(*pg.mouse.get_pos()),
            CURVE_COLOR,
            width=5,
            sharpness=0.75
        )
        
        pg.display.update()
