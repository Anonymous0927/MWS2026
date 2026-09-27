from __future__ import annotations

import pygame

from .. import theme, widgets
from ..panels import status_panel, timeline_panel
from ..scene import Scene
from ..views.actions_view import ActionsView
from ..views.expansion_view import ExpansionView
from ..views.shop_view import ShopView
from ..widgets import Button

TAB_GAP = 10
TAB_Y = theme.CONTENT_TOP
TAB_H = theme.TAB_H

BOTTOM_Y = theme.BOTTOM_Y
BOTTOM_H = theme.BOTTOM_H
GLOSSARY_BUTTON = pygame.Rect(theme.COL_LEFT_X, BOTTOM_Y, theme.COL_LEFT_W, BOTTOM_H)
NEXT_BUTTON = pygame.Rect(theme.COL_RIGHT_X, BOTTOM_Y, theme.COL_RIGHT_W, BOTTOM_H)
ACTION_SLOT = pygame.Rect(NEXT_BUTTON.x - 16 - 180, BOTTOM_Y, 180, BOTTOM_H)
NOTICE_RECT = pygame.Rect(theme.COL_CENTER_X, BOTTOM_Y,
                          ACTION_SLOT.x - 16 - theme.COL_CENTER_X, BOTTOM_H)

assert TAB_Y + TAB_H <= theme.PANEL_Y, "タブ帯が中央パネルに重なる"
assert NOTICE_RECT.width > 300, "警告を出す幅が足りない"
assert ACTION_SLOT.right < NEXT_BUTTON.x, "「決定」と「次のターンへ」が重なる"
assert NEXT_BUTTON.bottom <= theme.SCREEN_H, "下部バーが画面の高さを超えている"

SUMMARY_PANEL = pygame.Rect(220, 140, 1000, 520)
SUMMARY_BUTTON_W = 300
SUMMARY_BUTTON_GAP = 24
SUMMARY_BUTTON_X = (theme.SCREEN_W - SUMMARY_BUTTON_W * 2 - SUMMARY_BUTTON_GAP) // 2
SUMMARY_TITLE_BUTTON = pygame.Rect(SUMMARY_BUTTON_X, 700, SUMMARY_BUTTON_W, 68)
SUMMARY_COMPANY_BUTTON = pygame.Rect(
    SUMMARY_TITLE_BUTTON.right + SUMMARY_BUTTON_GAP, 700, SUMMARY_BUTTON_W, 68
)

assert SUMMARY_PANEL.bottom <= SUMMARY_TITLE_BUTTON.y, "まとめのパネルとボタンが重なる"
assert SUMMARY_TITLE_BUTTON.right < SUMMARY_COMPANY_BUTTON.x, "まとめ画面のボタンが重なる"
assert SUMMARY_COMPANY_BUTTON.bottom <= theme.SCREEN_H, "まとめ画面のボタンが画面外にある"

TAB_SHOP = "shop"
TAB_ACTIONS = "actions"
TAB_EXPANSIONS = "expansions"
DEFAULT_TAB = TAB_SHOP


class MainViewScene(Scene):

    def __init__(self, app, session, summary: bool = False, tab: str = DEFAULT_TAB) -> None:
        super().__init__(app, session)
        self.show_summary = summary

        self.views = {TAB_SHOP: ShopView(session)}
        if not session.state.is_school:
            self.views[TAB_ACTIONS] = ActionsView(session)
            self.views[TAB_EXPANSIONS] = ExpansionView(session)
        self.tab = tab if tab in self.views else DEFAULT_TAB
        self.school_section_title = self.views[TAB_SHOP].title if session.state.is_school else ""

        self.timeline_scroll = widgets.ScrollList(
            rect=timeline_panel.LIST_RECT, item_height=timeline_panel.item_step()
        )


    @property
    def view(self):
        return self.views[self.tab]

    def set_tab(self, tab: str) -> None:
        if tab in self.views:
            self.tab = tab

    def _tab_rect(self, index: int) -> pygame.Rect:
        count = len(self.views)
        width = (theme.COL_CENTER_W - TAB_GAP * (count - 1)) // count
        return pygame.Rect(theme.COL_CENTER_X + index * (width + TAB_GAP), TAB_Y, width, TAB_H)


    def buttons(self) -> list[Button]:
        if self.show_summary:
            return [
                Button(
                    rect=SUMMARY_TITLE_BUTTON,
                    label="トップページに戻る",
                    on_click=self.app.show_title,
                    kind="normal",
                ),
                Button(
                    rect=SUMMARY_COMPANY_BUTTON,
                    label="会社編へ進む",
                    on_click=self.app.start_company_stage,
                    kind="next",
                )
            ]

        items: list[Button] = [
            Button(
                rect=self._tab_rect(index),
                label=view.title,
                on_click=lambda key=key: self.set_tab(key),
                kind="primary" if key == self.tab else "quiet",
            )
            for index, (key, view) in enumerate(self.views.items())
            if not self.school_section_title
        ]

        items.extend(self.view.buttons())
        items.extend(self.view.bottom_buttons(ACTION_SLOT))
        items.append(
            Button(
                rect=GLOSSARY_BUTTON,
                label="？ 用語をしらべる",
                on_click=lambda: self.app.open_glossary(),
                kind="quiet",
            )
        )

        items.append(
            Button(
                rect=NEXT_BUTTON,
                label="次のターンへ",
                on_click=self.app.confirm_next_turn,
                kind="next",
            )
        )
        return items

    def term_links(self) -> list[widgets.TermLink]:
        return [] if self.show_summary else self.view.term_links()

    def on_wheel(self, wheel_y: int) -> None:
        if not self.show_summary:
            self.timeline_scroll.scroll(wheel_y)

    def on_escape(self) -> None:
        self.set_tab(DEFAULT_TAB)


    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(theme.BG)

        if self.show_summary:
            self._draw_summary(screen)
            return

        from .. import hud

        state = self.session.state
        hud.draw(screen, state)

        self._draw_status_column(screen, state)
        widgets.draw_panel(screen, _center_panel(), theme.CARD)
        self.view.draw(screen)
        self._draw_timeline_column(screen, state)

        if self.school_section_title:
            self._draw_school_section_title(screen)

        for button in self.visible_buttons():
            if button.label:
                widgets.draw_button(screen, button)

        self._draw_notice(screen)

        hud.draw_tip(screen, state)

    def _draw_school_section_title(self, screen: pygame.Surface) -> None:
        rect = self._tab_rect(0)
        widgets.draw_panel(screen, rect, theme.BLUE_BG, border=theme.LINE)
        widgets.draw_text_center(
            screen,
            self.school_section_title,
            rect.center,
            theme.SIZE_BODY,
            theme.INK,
            bold=True,
        )

    def _draw_status_column(self, screen: pygame.Surface, state) -> None:
        if state.is_school:
            status_panel.draw(screen, [], targets=self.session.company_view(), is_school=True)
            return
        status_panel.draw(
            screen,
            self.session.defense_scores(),
            planned=self.session.planned_defense_scores(),
        )

    def _draw_timeline_column(self, screen: pygame.Surface, state) -> None:
        entries = self.session.timeline_entries()
        self.timeline_scroll.count = len(entries)
        self.timeline_scroll.scroll(0)
        timeline_panel.draw(screen, entries, self.timeline_scroll, is_school=state.is_school)

    def _draw_notice(self, screen: pygame.Surface) -> None:
        level, warning = self.session.warning()
        if warning:
            color = {"ng": theme.RED, "warn": theme.AMBER}.get(level, theme.GREY)
            widgets.draw_wrapped(screen, warning, (NOTICE_RECT.x, NOTICE_RECT.y + 20),
                                 NOTICE_RECT.width, theme.SIZE_NOTE, color,
                                 max_lines=1, bold=True)


    def _draw_summary(self, screen: pygame.Surface) -> None:
        from core.game import format_money

        screen.fill(theme.BG)
        summary = self.session.school_summary()

        widgets.draw_panel(screen, SUMMARY_PANEL, theme.CARD)

        x = SUMMARY_PANEL.x + 40
        y = SUMMARY_PANEL.y + 32

        widgets.draw_text(screen, "学校編のまとめ", (x, y), theme.SIZE_TITLE, theme.INK, bold=True)
        y += 56

        widgets.draw_text(
            screen,
            f"使ったお金 {format_money(summary.spent, 'yen')}　"
            f"／　残ったお金 {format_money(summary.remaining, 'yen')}",
            (x, y), theme.SIZE_BODY, theme.AMBER, bold=True,
        )
        y += 30
        widgets.draw_text(
            screen,
            f"みんなの信頼　{summary.trust_start} → {summary.trust_end}",
            (x, y), theme.SIZE_BODY, theme.GREEN if summary.trust_end >= 80 else theme.AMBER,
            bold=True,
        )
        y += 46

        widgets.draw_text(screen, "この 3 学期で分かったこと", (x, y), theme.SIZE_HEAD,
                          theme.INK, bold=True)
        y += 38

        for index, lesson in enumerate(summary.lessons, start=1):
            widgets.draw_text(screen, f"{index}.", (x, y), theme.SIZE_BODY, theme.BLUE, bold=True)
            y = widgets.draw_wrapped(screen, lesson, (x + 32, y), SUMMARY_PANEL.width - 120,
                                     theme.SIZE_BODY, theme.INK, max_lines=2, leading=6)
            y += 10

        y += 12
        widgets.draw_wrapped(screen, summary.bridge_text, (x, y), SUMMARY_PANEL.width - 80,
                             theme.SIZE_BODY, theme.GREY, max_lines=2, leading=6)

        for button in self.visible_buttons():
            widgets.draw_button(screen, button)


def _center_panel() -> pygame.Rect:
    return pygame.Rect(theme.COL_CENTER_X, theme.PANEL_Y, theme.COL_CENTER_W, theme.PANEL_H)
