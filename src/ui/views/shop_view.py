from __future__ import annotations

import pygame

from core.game import format_money

from .. import theme, widgets
from ..widgets import Button, TermLink
from .base import INNER, PANEL, ContentView

STRIP_H = 44
STRIP = pygame.Rect(INNER.x, INNER.y, INNER.width, STRIP_H)
STRIP_COLUMNS = 5
STRIP_COL_W = STRIP.width // STRIP_COLUMNS
STRIP_LABEL_Y = STRIP.y + 5
STRIP_VALUE_Y = STRIP.y + 21
STRIP_PAD_X = 14

STRIP_STAR_SIZE = theme.SIZE_TINY

COLUMNS = 3
ROWS = 4
CARD_GAP_X = 14
CARD_GAP_Y = 12
CARD_TOP = STRIP.bottom + 12
CARD_W = (INNER.width - CARD_GAP_X * (COLUMNS - 1)) // COLUMNS
CARD_H = (INNER.bottom - CARD_TOP - CARD_GAP_Y * (ROWS - 1)) // ROWS

CARDS_BOTTOM = CARD_TOP + CARD_H * ROWS + CARD_GAP_Y * (ROWS - 1)

assert STRIP.bottom <= CARD_TOP, "見こみ帯と対策カードが重なる"
assert CARDS_BOTTOM <= PANEL.bottom, "対策カードが中央パネルからはみ出す"
assert CARD_H >= widgets.CARD_MIN_H, "カードが低すぎて 5 段が収まらない"
assert CARD_W >= 240, "カードが狭すぎて対策の名前が読めない"
assert STRIP.width - STRIP_PAD_X - STRIP_COL_W * (STRIP_COLUMNS - 1) >= 149, \
    "見こみ帯のいちばん右の枠に、★の見こみが収まらない"
assert COLUMNS * ROWS >= 12, "対策 12 種が 1 画面に収まらない"


class ShopView(ContentView):

    title = "対策を買う"

    def __init__(self, session) -> None:
        super().__init__(session)
        self._term_links: list[TermLink] = []


    def buttons(self) -> list[Button]:
        return [
            Button(
                rect=self._card_rect(index),
                label="",
                on_click=lambda i=view.measure.id: self._toggle(i),
                enabled=view.state in ("available", "selected", "owned", "canceling"),
                reason=view.reason,
                kind="normal",
            )
            for index, view in enumerate(self.session.catalog_views())
        ]

    def bottom_buttons(self, slot: pygame.Rect) -> list[Button]:
        return [Button(rect=slot, label="決定", on_click=self.session.commit, kind="confirm")]

    def term_links(self) -> list[TermLink]:
        return self._term_links

    def hint(self) -> tuple[str, str]:
        return self.session.hint()

    def _card_rect(self, index: int) -> pygame.Rect:
        column = index % COLUMNS
        row = index // COLUMNS
        return pygame.Rect(
            INNER.x + column * (CARD_W + CARD_GAP_X),
            CARD_TOP + row * (CARD_H + CARD_GAP_Y),
            CARD_W,
            CARD_H,
        )

    def _toggle(self, measure_id: str) -> None:
        if measure_id in self.session.selected():
            self.session.unselect(measure_id)
            return
        if measure_id in self.session.canceling():
            self.session.uncancel(measure_id)
            return

        result = self.session.select(measure_id)
        if not result.ok and measure_id in self.session.owned:
            self.session.cancel(measure_id)


    def draw(self, screen: pygame.Surface) -> None:
        self._term_links = []

        preview = self.session.preview()
        unit = self.session.state.unit
        self._draw_strip(screen, preview, unit)

        for index, view in enumerate(self.session.catalog_views()):
            link = widgets.draw_measure_card(screen, self._card_rect(index), view, unit)
            if link is not None:
                self._term_links.append(link)

    def _draw_strip(self, screen: pygame.Surface, preview, unit: str) -> None:
        widgets.draw_panel(screen, STRIP, theme.CARD)

        remaining_color = theme.INK if preview.remaining >= 0 else theme.RED
        upkeep_color = theme.RED if preview.upkeep_after > preview.upkeep_now else theme.AMBER

        school = self.session.state.is_school
        count = STRIP_COLUMNS - (1 if school else 0)
        col_w = STRIP.width // count

        self._draw_strip_column(screen, 0, col_w, "選んでいる金額",
                                format_money(preview.selected_cost, unit), theme.BLUE)
        self._draw_strip_column(screen, 1, col_w, "決定後の残り",
                                format_money(preview.remaining, unit), remaining_color)
        self._draw_strip_column(
            screen, 2, col_w, "年間維持費（毎年）",
            f"{format_money(preview.upkeep_now, unit)} → {format_money(preview.upkeep_after, unit)}"
            if preview.upkeep_after != preview.upkeep_now
            else format_money(preview.upkeep_now, unit),
            upkeep_color,
        )
        index = 3
        if not school:
            self._draw_slot_column(screen, index, col_w, preview)
            index += 1
        self._draw_star_column(screen, index, col_w, preview)

    @staticmethod
    def _draw_strip_column(screen: pygame.Surface, index: int, col_w: int, label: str,
                           value: str, color: tuple[int, int, int]) -> None:
        x = STRIP.x + STRIP_PAD_X + index * col_w
        widgets.draw_wrapped(screen, label, (x, STRIP_LABEL_Y), col_w - 20,
                             theme.SIZE_TINY, theme.GREY, max_lines=1)
        widgets.draw_wrapped(screen, value, (x, STRIP_VALUE_Y), col_w - 20,
                             theme.SIZE_NOTE, color, max_lines=1, bold=True)

    @staticmethod
    def _draw_slot_column(screen: pygame.Surface, index: int, col_w: int, preview) -> None:
        x = STRIP.x + STRIP_PAD_X + index * col_w
        widgets.draw_wrapped(screen, "今年できる工事", (x, STRIP_LABEL_Y),
                             col_w - 20, theme.SIZE_TINY, theme.GREY, max_lines=1)

        left_after = preview.slots_after
        color = theme.RED if left_after <= 0 else theme.INK
        widgets.draw_wrapped(
            screen, f"あと {left_after} 件", (x, STRIP_VALUE_Y),
            col_w - 20, theme.SIZE_NOTE, color, max_lines=1, bold=True,
        )

    @staticmethod
    def _draw_star_column(screen: pygame.Surface, index: int, col_w: int, preview) -> None:
        x = STRIP.x + STRIP_PAD_X + index * col_w
        widgets.draw_text(screen, "安全レベル", (x, STRIP_LABEL_Y),
                          theme.SIZE_TINY, theme.GREY)

        now_rect = widgets.draw_stars(screen, (x, STRIP_VALUE_Y + 2), preview.star_now,
                                      STRIP_STAR_SIZE, theme.GREY)
        arrow = widgets.draw_text(screen, " → ", (now_rect.right, STRIP_VALUE_Y + 2),
                                  STRIP_STAR_SIZE, theme.INK, bold=True)
        after_color = theme.GREEN if preview.star_after > preview.star_now else theme.AMBER
        widgets.draw_stars(screen, (arrow.right, STRIP_VALUE_Y + 2), preview.star_after,
                           STRIP_STAR_SIZE, after_color)
