from __future__ import annotations

import pygame

from core.game import format_money

from .. import theme, widgets
from ..widgets import Button
from .base import INNER, ContentView

STRIP_H = 64
STRIP = pygame.Rect(INNER.x, INNER.y, INNER.width, STRIP_H)
STRIP_COL_X = (STRIP.x + 14, STRIP.x + 220, STRIP.x + 380)

CARD_COLUMNS = 3
CARD_GAP = 14
CARD_TOP = STRIP.bottom + 16
CARD_W = (INNER.width - CARD_GAP * (CARD_COLUMNS - 1)) // CARD_COLUMNS
CARD_H = 300

PLACES_PANEL = pygame.Rect(INNER.x, CARD_TOP + CARD_H + 20, INNER.width,
                           INNER.bottom - (CARD_TOP + CARD_H + 20))
PLACE_COLUMNS = 4
PLACE_GAP = 12
PLACE_W = (PLACES_PANEL.width - 32 - PLACE_GAP * (PLACE_COLUMNS - 1)) // PLACE_COLUMNS
PLACE_H = 92

assert STRIP.bottom <= CARD_TOP, "上段と拡大カードが重なる"
assert CARD_TOP + CARD_H <= PLACES_PANEL.y, "拡大カードが守る場所の帯に重なる"
assert PLACES_PANEL.bottom <= INNER.bottom, "守る場所の帯が中央パネルからはみ出す"
assert PLACE_H + 46 <= PLACES_PANEL.height, "守る場所のカードが帯からはみ出す"


class ExpansionView(ContentView):

    title = "会社を大きくする"


    def buttons(self) -> list[Button]:
        return [
            Button(
                rect=self._card_rect(index),
                label="",
                on_click=lambda i=view.expansion.id: self._press(i),
                enabled=view.available or view.undoable,
                reason=view.reason,
                kind="normal",
            )
            for index, view in enumerate(self.session.expansions())
        ]

    def hint(self) -> tuple[str, str]:
        return (
            "もうけは増えますが、守る場所も増えます。押すとその場で決まります。",
            "増やした場所を守る対策を買っていないと、新しい事件で被害が出ます。",
        )

    def _press(self, expansion_id: str) -> None:
        view = next(v for v in self.session.expansions() if v.expansion.id == expansion_id)
        if view.undoable:
            self.session.undo_expansion(expansion_id)
        else:
            self.session.expand(expansion_id)

    def _card_rect(self, index: int) -> pygame.Rect:
        return pygame.Rect(INNER.x + index * (CARD_W + CARD_GAP), CARD_TOP, CARD_W, CARD_H)


    def draw(self, screen: pygame.Surface) -> None:
        state = self.session.state
        self._draw_strip(screen, state)

        for index, view in enumerate(self.session.expansions()):
            self._draw_card(screen, self._card_rect(index), view, state.unit)

        self._draw_places(screen)

    def _draw_strip(self, screen: pygame.Surface, state) -> None:
        widgets.draw_panel(screen, STRIP, theme.CARD)
        y = STRIP.y + 10

        for x, (label, value, color) in zip(STRIP_COL_X, (
            ("使えるお金", format_money(state.money, state.unit), theme.AMBER),
            ("社員", f"{state.employees} 人", theme.INK),
            ("1 年のもうけ", format_money(state.profit, state.unit), theme.GREEN),
        )):
            widgets.draw_text(screen, label, (x, y), theme.SIZE_TINY, theme.GREY)
            widgets.draw_text(screen, value, (x, y + 20), theme.SIZE_HEAD, color, bold=True)

    def _draw_places(self, screen: pygame.Surface) -> None:
        widgets.draw_panel(screen, PLACES_PANEL, theme.CARD)
        widgets.draw_text(screen, "いま守っている場所", (PLACES_PANEL.x + 16, PLACES_PANEL.y + 12),
                          theme.SIZE_NOTE, theme.INK, bold=True)
        widgets.draw_text(screen, "事業を広げると、ここに守る場所が増えます",
                          (PLACES_PANEL.x + 190, PLACES_PANEL.y + 15),
                          theme.SIZE_TINY, theme.GREY)

        for index, view in enumerate(self.session.company_view()[:PLACE_COLUMNS]):
            rect = pygame.Rect(PLACES_PANEL.x + 16 + index * (PLACE_W + PLACE_GAP),
                               PLACES_PANEL.y + 40, PLACE_W, PLACE_H)
            color, _label = theme.STATUS.get(view.level, (theme.GREY, ""))
            background = theme.STATUS_BG.get(view.level, theme.GREY_BG)
            widgets.draw_panel(screen, rect, background, border=color, border_width=2)

            widgets.draw_wrapped(screen, view.name, (rect.x + 12, rect.y + 10), rect.width - 24,
                                 theme.SIZE_NOTE, theme.INK, max_lines=1, bold=True)
            widgets.draw_wrapped(screen, view.note, (rect.x + 12, rect.y + 34), rect.width - 24,
                                 theme.SIZE_TINY, theme.GREY, max_lines=1)
            badge = pygame.Rect(rect.x + 12, rect.y + 56, 116, 24)
            widgets.draw_status_badge(screen, badge, view.level, view.label)

    def _draw_card(self, screen: pygame.Surface, rect: pygame.Rect, view, unit: str) -> None:
        expansion = view.expansion
        if view.undoable:
            border, fill, text_color = theme.GREEN, theme.GREEN_BG, theme.INK
        elif view.available:
            border, fill, text_color = theme.LINE, theme.CARD, theme.INK
        else:
            border, fill, text_color = theme.LINE, theme.GREY_BG, theme.GREY

        widgets.draw_panel(screen, rect, fill, border=border)
        left = rect.x + 16
        width = rect.width - 32

        widgets.draw_wrapped(screen, expansion.name, (left, rect.y + 16), width,
                             theme.SIZE_BODY, text_color, max_lines=2, leading=4, bold=True)
        widgets.draw_text(screen, format_money(expansion.cost, unit), (left, rect.y + 72),
                          theme.SIZE_HEAD, theme.AMBER, bold=True)
        widgets.draw_wrapped(screen, expansion.summary, (left, rect.y + 112), width,
                             theme.SIZE_NOTE, theme.GREY, max_lines=3, leading=4)

        if expansion.unlocks:
            widgets.draw_wrapped(screen, f"これから起こりえる事件：{expansion.unlocks}",
                                 (left, rect.y + 186), width,
                                 theme.SIZE_TINY, theme.AMBER, max_lines=3, leading=3)
        if view.undoable:
            widgets.draw_wrapped(screen, "もう一度押すと取り消せます（全額もどります）",
                                 (left, rect.y + 258), width,
                                 theme.SIZE_TINY, theme.BLUE, max_lines=2, leading=3)
        elif not view.available and view.reason:
            widgets.draw_wrapped(screen, view.reason, (left, rect.y + 258), width,
                                 theme.SIZE_TINY, theme.RED, max_lines=1)
