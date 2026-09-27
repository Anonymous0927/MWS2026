from __future__ import annotations

from typing import Callable

import pygame

from .. import theme, widgets
from ..scene import Scene
from ..widgets import Button

WINDOW_W = 640
WINDOW_H = 320
WINDOW = pygame.Rect((theme.SCREEN_W - WINDOW_W) // 2, (theme.SCREEN_H - WINDOW_H) // 2,
                     WINDOW_W, WINDOW_H)
TITLE_Y = 40
BODY_Y = 92
BUTTON_Y = 222
BUTTON_W = 260
BUTTON_H = 68
BUTTON_GAP = 32

assert WINDOW.bottom <= theme.SCREEN_H, "確認ウィンドウが画面の高さを超えている"
assert WINDOW.y + BUTTON_Y + BUTTON_H <= WINDOW.bottom, "ボタンがウィンドウからはみ出す"
assert BUTTON_H >= 60, "ボタンの高さは 60 以上（要件定義書 OP-5）"


class ConfirmModal(Scene):

    def __init__(
        self,
        app,
        session,
        title: str,
        lines: tuple[str, ...],
        on_confirm: Callable[[], None],
        confirm_label: str = "進む",
        cancel_label: str = "もどる",
    ) -> None:
        super().__init__(app, session)
        self.title = title
        self.lines = lines
        self._on_confirm = on_confirm
        self.confirm_label = confirm_label
        self.cancel_label = cancel_label


    def buttons(self) -> list[Button]:
        total_width = BUTTON_W * 2 + BUTTON_GAP
        left = WINDOW.centerx - total_width // 2
        top = WINDOW.y + BUTTON_Y

        return [
            Button(
                rect=pygame.Rect(left, top, BUTTON_W, BUTTON_H),
                label=self.cancel_label,
                on_click=self.app.close_modal,
                kind="normal",
            ),
            Button(
                rect=pygame.Rect(left + BUTTON_W + BUTTON_GAP, top, BUTTON_W, BUTTON_H),
                label=self.confirm_label,
                on_click=self._confirm,
                kind="next",
            ),
        ]

    def _confirm(self) -> None:
        self.app.close_modal()
        self._on_confirm()

    def on_escape(self) -> None:
        self.app.close_modal()

    def on_click(self, pos: tuple[int, int]) -> None:
        if not WINDOW.collidepoint(pos):
            self.app.close_modal()


    def draw(self, screen: pygame.Surface) -> None:
        widgets.draw_scrim(screen)
        widgets.draw_panel(screen, WINDOW, theme.CARD, border=theme.BLUE, border_width=2)

        widgets.draw_text_center(screen, self.title, (WINDOW.centerx, WINDOW.y + TITLE_Y),
                                 theme.SIZE_HEAD, theme.INK, bold=True)

        y = WINDOW.y + BODY_Y
        for line in self.lines:
            widgets.draw_text_center(screen, line, (WINDOW.centerx, y),
                                     theme.SIZE_BODY, theme.GREY)
            y += 32

        for button in self.visible_buttons():
            widgets.draw_button(screen, button)
