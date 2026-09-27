from __future__ import annotations

import pygame

from core.game import format_money

from .. import theme, widgets
from ..widgets import Button
from .base import INNER, ContentView

STRIP_H = 64
STRIP = pygame.Rect(INNER.x, INNER.y, INNER.width, STRIP_H)
STRIP_MONEY_X = STRIP.x + 14
STRIP_STAFF_X = STRIP.x + 220
STRIP_AWARE_X = STRIP.x + 380
GAUGE = pygame.Rect(STRIP_AWARE_X + 130, STRIP.y + 36, 200, 14)

CARD_H = 190
CARD_GAP = 16
CARD_TOP = STRIP.bottom + 16
CARD_W = INNER.width

NOTE_H = 96
NOTE_PANEL = pygame.Rect(INNER.x, INNER.bottom - NOTE_H, INNER.width, NOTE_H)

assert STRIP.bottom <= CARD_TOP, "上段と施策カードが重なる"
assert CARD_TOP + CARD_H * 2 + CARD_GAP <= NOTE_PANEL.y, "施策カードが説明帯に重なる"
assert NOTE_PANEL.bottom <= INNER.bottom, "説明帯が中央パネルからはみ出す"
assert GAUGE.right <= STRIP.right - 14, "意識のゲージが帯からはみ出す"


class ActionsView(ContentView):

    title = "今年やること"


    def buttons(self) -> list[Button]:
        return [
            Button(
                rect=self._card_rect(index),
                label="",
                on_click=lambda i=view.action.id: self._press(i),
                enabled=view.available or view.done,
                reason=view.reason,
                kind="normal",
            )
            for index, view in enumerate(self.session.action_views())
        ]

    def hint(self) -> tuple[str, str]:
        return (
            "施策は、その年かぎりの取り組みです。翌年にはもう一度やり直します。",
            "社員が多いほど高くつきます。会社を大きくすると、人への投資も重くなります。",
        )

    def _press(self, action_id: str) -> None:
        view = next(v for v in self.session.action_views() if v.action.id == action_id)
        if view.done:
            self.session.undo_action(action_id)
        else:
            self.session.do_action(action_id)

    def _card_rect(self, index: int) -> pygame.Rect:
        return pygame.Rect(INNER.x, CARD_TOP + index * (CARD_H + CARD_GAP), CARD_W, CARD_H)


    def draw(self, screen: pygame.Surface) -> None:
        state = self.session.state
        self._draw_strip(screen, state)

        for index, view in enumerate(self.session.action_views()):
            self._draw_card(screen, self._card_rect(index), view, state)

        self._draw_note(screen)

    def _draw_strip(self, screen: pygame.Surface, state) -> None:
        widgets.draw_panel(screen, STRIP, theme.CARD)
        y = STRIP.y + 10

        widgets.draw_text(screen, "使えるお金", (STRIP_MONEY_X, y), theme.SIZE_TINY, theme.GREY)
        widgets.draw_text(screen, format_money(state.money, state.unit), (STRIP_MONEY_X, y + 20),
                          theme.SIZE_HEAD, theme.AMBER, bold=True)

        widgets.draw_text(screen, "社員", (STRIP_STAFF_X, y), theme.SIZE_TINY, theme.GREY)
        widgets.draw_text(screen, f"{state.employees} 人", (STRIP_STAFF_X, y + 20),
                          theme.SIZE_HEAD, theme.INK, bold=True)

        widgets.draw_text(screen, "社員のセキュリティ意識", (STRIP_AWARE_X, y),
                          theme.SIZE_TINY, theme.GREY)
        color = _awareness_color(state.awareness)
        widgets.draw_text(screen, f"{state.awareness} / 100", (STRIP_AWARE_X, y + 20),
                          theme.SIZE_HEAD, color, bold=True)
        widgets.draw_gauge(screen, GAUGE, state.awareness, color)

    def _draw_card(self, screen: pygame.Surface, rect: pygame.Rect, view, state) -> None:
        action = view.action
        if view.done:
            border, fill, text_color = theme.GREEN, theme.GREEN_BG, theme.INK
        elif view.available:
            border, fill, text_color = theme.LINE, theme.CARD, theme.INK
        else:
            border, fill, text_color = theme.LINE, theme.GREY_BG, theme.GREY

        widgets.draw_panel(screen, rect, fill, border=border, border_width=2 if view.done else 1)
        left = rect.x + 16

        widgets.draw_text(screen, action.name, (left, rect.y + 12), theme.SIZE_HEAD,
                          text_color, bold=True)
        badge = pygame.Rect(rect.right - 16 - 116, rect.y + 14, 116, 26)
        widgets.draw_status_badge(screen, badge, "ok" if view.done else "warn",
                                  "実施ずみ" if view.done else "まだ")

        widgets.draw_text(screen, f"（{action.formal_name}）", (left, rect.y + 44),
                          theme.SIZE_NOTE, theme.GREY)

        widgets.draw_text(screen, format_money(view.cost, state.unit), (left, rect.y + 68),
                          theme.SIZE_HEAD, theme.AMBER, bold=True)
        widgets.draw_text(screen, f"（社員 {state.employees} 人ぶん）",
                          (left + 130, rect.y + 76), theme.SIZE_TINY, theme.GREY)

        widgets.draw_wrapped(screen, action.summary, (left, rect.y + 100), rect.width - 32,
                             theme.SIZE_NOTE, theme.GREY, max_lines=1)

        effect = f"意識 +{action.awareness}"
        if action.axes:
            effect += "　" + "／".join(self._axis_name(axis) for axis in action.axes) + " が上がる"
        widgets.draw_wrapped(screen, effect, (left, rect.y + 124), rect.width - 32,
                             theme.SIZE_TINY, theme.BLUE, max_lines=1)

        if view.done:
            widgets.draw_text(screen, "もう一度押すと取り消せます（全額もどります）",
                              (left, rect.y + 146), theme.SIZE_TINY, theme.BLUE)
        elif not view.available and view.reason:
            widgets.draw_text(screen, view.reason, (left, rect.y + 146), theme.SIZE_TINY, theme.RED)
        elif action.weakness:
            widgets.draw_wrapped(screen, f"できないこと：{action.weakness}",
                                 (left, rect.y + 146), rect.width - 32,
                                 theme.SIZE_TINY, theme.GREY, max_lines=1)

    def _axis_name(self, axis_id: str) -> str:
        for score in self.session.defense_scores():
            if score.axis.id == axis_id:
                return score.axis.name
        return axis_id

    def _draw_note(self, screen: pygame.Surface) -> None:
        widgets.draw_panel(screen, NOTE_PANEL, theme.BLUE_BG, border=theme.LINE)

        widgets.draw_text(screen, "施策は「続けないと効かない」取り組みです。",
                          (NOTE_PANEL.x + 16, NOTE_PANEL.y + 14), theme.SIZE_NOTE,
                          theme.INK, bold=True)
        widgets.draw_wrapped(
            screen,
            "買い切りの対策とちがい、効果はその年だけ。"
            "やめれば意識は下がり、人のミスが起点の事件が増えます。",
            (NOTE_PANEL.x + 16, NOTE_PANEL.y + 42), NOTE_PANEL.width - 32,
            theme.SIZE_NOTE, theme.GREY, max_lines=2, leading=4,
        )


def _awareness_color(value: int) -> tuple[int, int, int]:
    if value >= 60:
        return theme.GREEN
    if value >= 30:
        return theme.AMBER
    return theme.RED
