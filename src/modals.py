from typing import Callable, Sequence, Tuple, Set

import pygame as pg

from constants import MODAL_HIGHLIGHT_COLOR, MODAL_PRIMARY_COLOR, MODAL_WIDTH, MODAL_HEIGHT, MODAL_MAT_COLOR, MODAL_BG_COLOR
from helpers import V2, render_text_centered_x_wrapped, render_text_centered_xy, render_text_centered_xy_wrapped


class Modal:
    def __init__(self, message: str, buttons: Sequence[Tuple[str, Callable]]):
        self.message = message
        self.buttons = buttons

        self.button_rects = [None] * len(buttons)
        self.button_id_hovered = None
    
    def draw_onto(self, screen):
        # draw opacity mat
        mat = pg.Surface(screen.get_size())
        *rgb, a = MODAL_MAT_COLOR
        mat.fill(rgb)
        mat.set_alpha(a)

        screen.blit(mat, (0, 0))

        r = screen.get_rect()
        modal_rect = pg.Rect(
            (r.centerx - MODAL_WIDTH/2, r.centery - MODAL_HEIGHT/2),
            (MODAL_WIDTH, MODAL_HEIGHT),
            width=0
        )

        br = 16

        # draw background
        pg.draw.rect(screen, MODAL_BG_COLOR, modal_rect, width=0, border_radius=br)

        # draw border
        pg.draw.rect(screen, MODAL_PRIMARY_COLOR, modal_rect, width=4, border_radius=br)

        # draw message
        render_text_centered_x_wrapped(
            self.message, MODAL_PRIMARY_COLOR, 35,
            screen, modal_rect.midtop, modal_rect.width,
            padding_top=100, padding_sides=30
        )

        # draw buttons
        # TODO: refactor these as proper Widgets
        button_margin_sides = 30
        button_margin_top = 5
        button_margin_bottom = 5
        button_height = 50
        for i, (label, _) in enumerate(self.buttons):
            button_rect = pg.Rect(
                modal_rect.left + button_margin_sides,
                modal_rect.centery + 100 + button_margin_top * (i+1) + button_height * i + button_margin_bottom * i,
                modal_rect.width - button_margin_sides * 2,
                button_height
            )

            self.button_rects[i] = button_rect

            if i == self.button_id_hovered:
                pg.draw.rect(screen, MODAL_HIGHLIGHT_COLOR, button_rect, border_radius=16, width=0)

            pg.draw.rect(screen, MODAL_PRIMARY_COLOR, button_rect, border_radius=16, width=2)

            render_text_centered_xy_wrapped(
                label, MODAL_PRIMARY_COLOR, 25,
                screen, button_rect.center, modal_rect.width,
                padding_sides=60
            )

    def handle_events(self, events: Set):
        for event in events:
            if event.type == pg.MOUSEBUTTONDOWN:
                for i, button_rect in enumerate(self.button_rects):
                    if button_rect.collidepoint(event.pos):
                        self.buttons[i][1]()
                events.remove(event)
            elif event.type == pg.MOUSEMOTION:
                for i, button_rect in enumerate(self.button_rects):
                    if button_rect.collidepoint(event.pos):
                        self.button_id_hovered = i
                        break
                else:
                    self.button_id_hovered = None
                events.remove(event)


    