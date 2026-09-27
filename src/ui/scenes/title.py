from __future__ import annotations

import pygame

from .. import theme, widgets
from ..scene import Scene
from ..widgets import Button

TITLE_Y = 238
SUBTITLE_Y = 300
LEAD_Y = 360
SEED_LABEL_Y = 468
SEED_BOX_W = 400
SEED_BOX = pygame.Rect((theme.SCREEN_W - SEED_BOX_W) // 2, 496, SEED_BOX_W, 56)
BUTTON_W = 320
BUTTON_H = 68
BUTTON_Y = 594
BUTTON_GAP = 24
BUTTON_X0 = (theme.SCREEN_W - BUTTON_W * 2 - BUTTON_GAP) // 2

assert SEED_LABEL_Y + 20 <= SEED_BOX.y, "シードの見出しと入力欄が重なる"
assert SEED_BOX.bottom <= BUTTON_Y, "シードの入力欄とボタンが重なる"
assert BUTTON_Y + BUTTON_H <= theme.SCREEN_H, "ボタンが画面の高さを超えている"
assert abs((TITLE_Y + BUTTON_Y + BUTTON_H) // 2 - theme.SCREEN_H // 2) <= 24, \
    "タイトル画面のかたまりが上下のまん中から外れている"


class TitleScene(Scene):

    def __init__(self, app, session) -> None:
        super().__init__(app, session)
        start_seed = getattr(app, "_start_seed", None)
        self.seed_text = str(start_seed) if start_seed is not None else ""
        self.seed_focused = False


    def buttons(self) -> list[Button]:
        return [
            Button(
                rect=pygame.Rect(BUTTON_X0, BUTTON_Y, BUTTON_W, BUTTON_H),
                label="はじめから（学校編）",
                on_click=lambda: self.app.start_game(self._seed(), skip_school=False),
                kind="primary",
            ),
            Button(
                rect=pygame.Rect(BUTTON_X0 + BUTTON_W + BUTTON_GAP, BUTTON_Y,
                                 BUTTON_W, BUTTON_H),
                label="会社編から始める",
                on_click=lambda: self.app.start_game(self._seed(), skip_school=True),
                kind="normal",
            ),
        ]

    def _seed(self) -> int | None:
        return int(self.seed_text) if self.seed_text.isdigit() else None


    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.seed_focused = SEED_BOX.collidepoint(event.pos)

        if event.type == pygame.KEYDOWN and self.seed_focused:
            if event.key == pygame.K_BACKSPACE:
                self.seed_text = self.seed_text[:-1]
                return
            if event.unicode.isdigit() and len(self.seed_text) < 6:
                self.seed_text += event.unicode
                return

        super().handle_event(event)

    def on_escape(self) -> None:
        self.app.quit()


    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(theme.BG)

        widgets.draw_text_center(screen, "Secure Company Simulator",
                                 (theme.SCREEN_W // 2, TITLE_Y), theme.SIZE_SCORE - 26,
                                 theme.INK, bold=True)
        widgets.draw_text_center(screen, "情報を守る担当になって、会社を 10 年つづけよう",
                                 (theme.SCREEN_W // 2, SUBTITLE_Y), theme.SIZE_HEAD, theme.BLUE)

        for index, line in enumerate((
            "対策を買う → 次のターンへ → 事件で選ぶ。1 年でクリックするのは 3 回だけです。",
            "ひとつの対策で全部は守れません。買わなかった判断が、あとで返ってきます。",
        )):
            widgets.draw_text_center(screen, line,
                                     (theme.SCREEN_W // 2, LEAD_Y + index * 30),
                                     theme.SIZE_BODY, theme.GREY)

        self._draw_seed_box(screen)

        for button in self.visible_buttons():
            widgets.draw_button(screen, button)

    def _draw_seed_box(self, screen: pygame.Surface) -> None:
        widgets.draw_text_center(screen, "シード（数字。空欄なら毎回ちがう展開になります）",
                                 (theme.SCREEN_W // 2, SEED_LABEL_Y),
                                 theme.SIZE_NOTE, theme.GREY)

        border = theme.BLUE if self.seed_focused else theme.LINE
        widgets.draw_panel(screen, SEED_BOX, theme.WHITE, border=border,
                           border_width=2 if self.seed_focused else 1)

        text = self.seed_text or "（空欄）"
        color = theme.INK if self.seed_text else theme.GREY
        widgets.draw_text_center(screen, text, SEED_BOX.center, theme.SIZE_HEAD, color)
