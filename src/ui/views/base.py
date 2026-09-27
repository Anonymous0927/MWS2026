from __future__ import annotations

import pygame

from .. import theme
from ..widgets import Button, TermLink

PANEL = pygame.Rect(theme.COL_CENTER_X, theme.PANEL_Y, theme.COL_CENTER_W, theme.PANEL_H)

PAD = 16
INNER = PANEL.inflate(-PAD * 2, -PAD * 2)

assert PANEL.bottom <= theme.SCREEN_H, "中央の切り替えエリアが画面の高さを超えている"
assert INNER.width > 0 and INNER.height > 0, "中央の内側に描く余地がない"


class ContentView:

    title = ""

    def __init__(self, session) -> None:
        self.session = session


    def draw(self, screen: pygame.Surface) -> None:
        raise NotImplementedError

    def buttons(self) -> list[Button]:
        return []

    def bottom_buttons(self, slot: pygame.Rect) -> list[Button]:
        return []

    def term_links(self) -> list[TermLink]:
        return []

    def hint(self) -> tuple[str, str]:
        return ("", "")
