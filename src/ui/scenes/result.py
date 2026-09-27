from __future__ import annotations

import pygame

from core.game import CLEAR_LABELS, format_money

from .. import theme, widgets
from ..result_style import style_for
from ..scene import Scene
from ..widgets import Button

MARGIN = 40
PANEL_TOP = 40
PANEL_H = 700

SCORE_PANEL = pygame.Rect(MARGIN, PANEL_TOP, 440, 300)
CLEAR_PANEL = pygame.Rect(MARGIN, SCORE_PANEL.bottom + 16, 440, PANEL_H - 316)
AXES_PANEL = pygame.Rect(SCORE_PANEL.right + 16, PANEL_TOP, 440, PANEL_H)
GOOD_PANEL = pygame.Rect(AXES_PANEL.right + 16, PANEL_TOP,
                         theme.SCREEN_W - MARGIN - AXES_PANEL.right - 16, 342)
REGRET_PANEL = pygame.Rect(GOOD_PANEL.x, GOOD_PANEL.bottom + 16,
                           GOOD_PANEL.width, PANEL_H - 358)

BUTTON_Y = 764
BUTTON_H = 68
SAVE_BUTTON = pygame.Rect(MARGIN, BUTTON_Y, 300, BUTTON_H)
REPLAY_BUTTON = pygame.Rect(360, BUTTON_Y, 300, BUTTON_H)
QUIT_BUTTON = pygame.Rect(680, BUTTON_Y, 220, BUTTON_H)
SAVED_PATH_X = MARGIN
SAVED_PATH_Y = 848

assert AXES_PANEL.bottom == PANEL_TOP + PANEL_H, "まん中の列の下端がそろっていない"
assert CLEAR_PANEL.bottom == PANEL_TOP + PANEL_H, "左の列の下端がそろっていない"
assert REGRET_PANEL.bottom == PANEL_TOP + PANEL_H, "右の列の下端がそろっていない"
assert REGRET_PANEL.bottom <= BUTTON_Y, "パネルが下部ボタンに重なる"
assert BUTTON_Y + BUTTON_H <= theme.SCREEN_H, "下部ボタンが画面の高さを超えている"
assert SAVED_PATH_Y + 24 <= theme.SCREEN_H, "保存先の表示が画面外にある"

CLEAR_ORDER = ("survived", "trust", "star", "damage", "morale")


class ResultScene(Scene):

    def __init__(self, app, session) -> None:
        super().__init__(app, session)
        self.score = session.final_score()
        self.style = style_for(self.score)
        self.saved_paths: tuple = ()
        self.save_error = ""


    def buttons(self) -> list[Button]:
        return [
            Button(rect=SAVE_BUTTON, label="記録を保存する", on_click=self._save, kind="normal"),
            Button(rect=REPLAY_BUTTON, label="もう一度あそぶ",
                   on_click=self.app.show_title, kind="primary"),
            Button(rect=QUIT_BUTTON, label="終わる", on_click=self.app.quit, kind="quiet"),
        ]

    def _save(self) -> None:
        try:
            self.saved_paths = self.session.save_report()
            self.save_error = ""
        except OSError as error:
            self.saved_paths = ()
            self.save_error = f"保存できませんでした：{error}"

    def on_escape(self) -> None:
        self.app.show_title()


    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(self.style.background)

        self._draw_score(screen)
        self._draw_clear_conditions(screen)
        self._draw_axes(screen)
        self._draw_highlights(screen)

        for button in self.visible_buttons():
            widgets.draw_button(screen, button)

        self._draw_saved_path(screen)

    def _draw_score(self, screen: pygame.Surface) -> None:
        widgets.draw_panel(screen, SCORE_PANEL, self.style.background,
                           border=self.style.accent, border_width=3)
        x = SCORE_PANEL.x + 24
        y = SCORE_PANEL.y + 16

        widgets.draw_text(screen, self.style.title, (x, y), theme.SIZE_HEAD,
                          self.style.accent, bold=True)
        y += 40

        widgets.draw_text(screen, str(self.score.total), (x, y), theme.SIZE_SCORE,
                          theme.INK, bold=True)
        widgets.draw_text(screen, "/ 1000", (x + 170, y + 44), theme.SIZE_BODY, theme.GREY)
        y += 92

        widgets.draw_text(screen, f"評価 {self.score.rank}", (x, y), theme.SIZE_TITLE,
                          self.style.accent, bold=True)

        star = self.session.state.star
        widgets.draw_stars(screen, (x + 140, y + 6), star, theme.SIZE_HEAD)

        widgets.draw_wrapped(screen, self.score.comment, (x, y + 48),
                             SCORE_PANEL.width - 48, theme.SIZE_NOTE, theme.GREY,
                             max_lines=2, leading=4)

    def _draw_clear_conditions(self, screen: pygame.Surface) -> None:
        widgets.draw_panel(screen, CLEAR_PANEL, theme.CARD,
                           border=self.style.accent, border_width=2)
        x = CLEAR_PANEL.x + 20
        y = CLEAR_PANEL.y + 14

        achieved = sum(1 for ok in self.score.clear_flags.values() if ok)
        widgets.draw_text(screen, f"クリア条件　{achieved} / 5 達成", (x, y),
                          theme.SIZE_NOTE, theme.INK, bold=True)
        y += 34

        labels = dict(CLEAR_LABELS)
        for key in CLEAR_ORDER:
            ok = self.score.clear_flags.get(key, False)
            mark = "○" if ok else "×"
            color = theme.GREEN if ok else theme.RED
            widgets.draw_text(screen, mark, (x, y), theme.SIZE_BODY, color, bold=True)
            widgets.draw_wrapped(screen, labels.get(key, key), (x + 26, y + 2),
                                 CLEAR_PANEL.width - 60, theme.SIZE_TINY,
                                 theme.INK if ok else theme.GREY, max_lines=2, leading=2)
            y += 46

    def _draw_axes(self, screen: pygame.Surface) -> None:
        widgets.draw_panel(screen, AXES_PANEL, theme.CARD,
                           border=self.style.accent, border_width=2)
        x = AXES_PANEL.x + 20
        y = AXES_PANEL.y + 16

        widgets.draw_text(screen, "5 つのめやす", (x, y), theme.SIZE_HEAD, theme.INK, bold=True)
        y += 32
        widgets.draw_text(screen, "どれも同じ配点です。片方だけ伸ばしても点は伸びません。",
                          (x, y), theme.SIZE_TINY, theme.GREY)
        y += 32

        bar_width = AXES_PANEL.width - 40
        for axis in self.score.axes:
            widgets.draw_text(screen, axis.label, (x, y), theme.SIZE_NOTE, theme.INK, bold=True)
            widgets.draw_text_right(screen, f"{axis.value}", AXES_PANEL.right - 20, y,
                                    theme.SIZE_NOTE, theme.BLUE, bold=True)
            y += 26
            widgets.draw_gauge(screen, pygame.Rect(x, y, bar_width, 14), axis.value,
                               _axis_color(axis.value))
            y += 22
            widgets.draw_text(screen, axis.detail, (x, y), theme.SIZE_TINY, theme.GREY)
            y += 26

    def _draw_highlights(self, screen: pygame.Surface) -> None:
        self._draw_highlight_panel(
            screen, GOOD_PANEL, "よかった判断", self.score.good_highlights,
            theme.GREEN, theme.GREEN_BG,
            "この年の投資が、あとの年で効きました。",
        )
        self._draw_highlight_panel(
            screen, REGRET_PANEL, "もったいなかった判断", self.score.regret_highlights,
            theme.RED, theme.RED_BG,
            "買っていれば、この額を減らせました。",
        )

    def _draw_highlight_panel(
        self, screen: pygame.Surface, rect: pygame.Rect, title: str,
        items: tuple, color: tuple, background: tuple, note: str,
    ) -> None:
        widgets.draw_panel(screen, rect, theme.CARD,
                           border=self.style.accent, border_width=2)
        x = rect.x + 20
        y = rect.y + 14

        widgets.draw_text(screen, title, (x, y), theme.SIZE_NOTE, color, bold=True)
        y += 28
        widgets.draw_text(screen, note, (x, y), theme.SIZE_TINY, theme.GREY)
        y += 26

        if not items:
            widgets.draw_text(screen, "（該当はありませんでした）", (x, y),
                              theme.SIZE_TINY, theme.GREY)
            return

        for item in items[:2]:
            item_rect = pygame.Rect(x, y, rect.width - 40, 78)
            widgets.draw_panel(screen, item_rect, background, border=None)
            widgets.draw_wrapped(screen, item.text, (item_rect.x + 12, item_rect.y + 10),
                                 item_rect.width - 24, theme.SIZE_TINY, theme.INK,
                                 max_lines=4, leading=3)
            y += 88

    def _draw_saved_path(self, screen: pygame.Surface) -> None:
        if self.save_error:
            widgets.draw_text(screen, self.save_error, (SAVED_PATH_X, SAVED_PATH_Y),
                              theme.SIZE_TINY, theme.RED)
            return
        if not self.saved_paths:
            widgets.draw_text(screen,
                              "「記録を保存する」を押すと、output/ に判断の記録を書き出します。",
                              (SAVED_PATH_X, SAVED_PATH_Y), theme.SIZE_TINY, theme.GREY)
            return

        text = f"保存しました：{self.saved_paths[0]}　／　{self.saved_paths[1].name}"
        widgets.draw_wrapped(screen, text, (SAVED_PATH_X, SAVED_PATH_Y), 1200,
                             theme.SIZE_TINY, theme.GREEN, max_lines=1)


def _axis_color(value: int) -> tuple[int, int, int]:
    if value >= 70:
        return theme.GREEN
    if value >= 40:
        return theme.AMBER
    return theme.RED
