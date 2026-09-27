from __future__ import annotations

import pygame

from .. import theme, widgets
from ..scene import Scene
from ..widgets import Button

WINDOW_W = 1240
WINDOW_H = 800
WINDOW_X = (theme.SCREEN_W - WINDOW_W) // 2
WINDOW_Y = (theme.SCREEN_H - WINDOW_H) // 2

PAD = 32
HEAD_H = 72

LIST_X = WINDOW_X + PAD
LIST_Y = WINDOW_Y + HEAD_H
LIST_W = 380
LIST_H = WINDOW_H - HEAD_H - PAD
LIST_ITEM_H = 56

DETAIL_X = LIST_X + LIST_W + 28
DETAIL_Y = LIST_Y
DETAIL_W = WINDOW_X + WINDOW_W - PAD - DETAIL_X
DETAIL_H = LIST_H

CLOSE_SIZE = 40
CLOSE_X = WINDOW_X + WINDOW_W - PAD - CLOSE_SIZE
CLOSE_Y = WINDOW_Y + 14

SELECTION_INSET_X = 8
SELECTION_INSET_Y = 5
SELECTION_SCROLLBAR_GAP = 16
SCROLLBAR_VERTICAL_INSET = 10

assert WINDOW_Y + WINDOW_H <= theme.SCREEN_H, "用語ウィンドウが画面の高さを超えている"
assert LIST_Y + LIST_H <= WINDOW_Y + WINDOW_H, "用語の一覧がウィンドウからはみ出す"
assert DETAIL_X + DETAIL_W <= WINDOW_X + WINDOW_W, "用語の説明がウィンドウからはみ出す"
assert CLOSE_Y + CLOSE_SIZE <= LIST_Y, "閉じるボタンが一覧に重なる"


def selection_rect(item_rect: pygame.Rect) -> pygame.Rect:
    return pygame.Rect(
        item_rect.x + SELECTION_INSET_X,
        item_rect.y + SELECTION_INSET_Y,
        item_rect.width - SELECTION_INSET_X * 2 - SELECTION_SCROLLBAR_GAP,
        item_rect.height - SELECTION_INSET_Y * 2,
    )


class GlossaryModal(Scene):

    def __init__(self, app, session, term_id: str | None = None,
                 related: list | None = None) -> None:
        super().__init__(app, session)

        all_terms = session.glossary_terms()
        if related:
            related_ids = [term.id for term in related]
            self.terms = related + [t for t in all_terms if t.id not in related_ids]
        else:
            self.terms = all_terms

        self.selected_index = 0
        if term_id:
            for index, term in enumerate(self.terms):
                if term.id == term_id:
                    self.selected_index = index
                    break

        self.scroll = widgets.ScrollList(
            rect=pygame.Rect(LIST_X, LIST_Y, LIST_W, LIST_H),
            item_height=LIST_ITEM_H,
            count=len(self.terms),
        )
        self._ensure_visible(self.selected_index)


    def buttons(self) -> list[Button]:
        items: list[Button] = [
            Button(
                rect=pygame.Rect(CLOSE_X, CLOSE_Y, CLOSE_SIZE, CLOSE_SIZE),
                label="×",
                on_click=self.app.close_modal,
                kind="quiet",
            )
        ]
        for index in self.scroll.visible_range():
            rect = self.scroll.item_rect(index)
            if not self.scroll.rect.contains(rect.clip(self.scroll.rect)) and rect.height == 0:
                continue
            items.append(
                Button(
                    rect=rect.clip(self.scroll.rect),
                    label="",
                    on_click=lambda i=index: self._select(i),
                    kind="quiet",
                )
            )
        return items

    def _select(self, index: int) -> None:
        self.selected_index = index

    def _ensure_visible(self, index: int) -> None:
        top = index * LIST_ITEM_H
        if top < self.scroll.offset:
            self.scroll.offset = top
        elif top + LIST_ITEM_H > self.scroll.offset + LIST_H:
            self.scroll.offset = min(self.scroll.max_offset, top + LIST_ITEM_H - LIST_H)

    def on_wheel(self, wheel_y: int) -> None:
        self.scroll.scroll(wheel_y)

    def on_escape(self) -> None:
        self.app.close_modal()

    def on_click(self, pos: tuple[int, int]) -> None:
        window = pygame.Rect(WINDOW_X, WINDOW_Y, WINDOW_W, WINDOW_H)
        if not window.collidepoint(pos):
            self.app.close_modal()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.app.close_modal()
            return
        super().handle_event(event)


    def draw(self, screen: pygame.Surface) -> None:
        widgets.draw_scrim(screen)

        window = pygame.Rect(WINDOW_X, WINDOW_Y, WINDOW_W, WINDOW_H)
        widgets.draw_panel(screen, window, theme.CARD)

        widgets.draw_text(screen, "用語をしらべる", (LIST_X, WINDOW_Y + 18), theme.SIZE_HEAD,
                          theme.INK, bold=True)
        widgets.draw_text(screen, "やさしい言い方（正式な用語）の順にならんでいます",
                          (LIST_X + 190, WINDOW_Y + 26), theme.SIZE_TINY, theme.GREY)

        self._draw_list(screen)
        self._draw_detail(screen)

        for button in self.visible_buttons():
            if button.label:
                widgets.draw_button(screen, button)

    def _draw_list(self, screen: pygame.Surface) -> None:
        list_rect = pygame.Rect(LIST_X, LIST_Y, LIST_W, LIST_H)
        widgets.draw_panel(screen, list_rect, theme.BG, border=theme.LINE)

        previous_clip = screen.get_clip()
        screen.set_clip(list_rect)

        for index in self.scroll.visible_range():
            term = self.terms[index]
            rect = self.scroll.item_rect(index)
            if index == self.selected_index:
                widgets.draw_panel(screen, selection_rect(rect), theme.BLUE_BG,
                                   border=theme.BLUE)
            widgets.draw_flow_line(screen, term.easy, (rect.x + 20, rect.y + 8),
                                   LIST_W - 56, theme.SIZE_NOTE, theme.INK,
                                   bold=index == self.selected_index)
            widgets.draw_flow_line(screen, term.formal, (rect.x + 20, rect.y + 32),
                                   LIST_W - 56, theme.SIZE_TINY, theme.GREY)

        screen.set_clip(previous_clip)
        widgets.draw_scrollbar(
            screen, self.scroll, vertical_inset=SCROLLBAR_VERTICAL_INSET
        )

    def _draw_detail(self, screen: pygame.Surface) -> None:
        detail_rect = pygame.Rect(DETAIL_X, DETAIL_Y, DETAIL_W, DETAIL_H)
        widgets.draw_panel(screen, detail_rect, theme.BG, border=theme.LINE)

        if not self.terms:
            return
        term = self.terms[self.selected_index]

        padding = 32
        x = DETAIL_X + padding
        y = DETAIL_Y + padding

        y = widgets.draw_wrapped(screen, term.easy, (x, y), DETAIL_W - padding * 2,
                                 theme.SIZE_HEAD, theme.INK, max_lines=2, bold=True)
        y += 4
        widgets.draw_text(screen, term.formal, (x, y), theme.SIZE_NOTE, theme.BLUE)
        y += 40

        pygame.draw.line(screen, theme.LINE, (x, y), (DETAIL_X + DETAIL_W - padding, y))
        y += 20

        for line in term.description:
            y = widgets.draw_wrapped(screen, line, (x, y), DETAIL_W - padding * 2,
                                     theme.SIZE_BODY, theme.INK, max_lines=2, leading=8)

        y += 24
        widgets.draw_text(screen, "このゲームでの登場場所", (x, y), theme.SIZE_NOTE,
                          theme.GREY, bold=True)
        y += 28
        appears = self._appears_text(term)
        widgets.draw_wrapped(screen, appears, (x, y), DETAIL_W - padding * 2,
                             theme.SIZE_NOTE, theme.GREY, max_lines=4, leading=6)

    def _appears_text(self, term) -> str:
        names = [name for name in (self.session.name_of(t) for t in term.appears_in) if name]
        return "／".join(names) if names else "（このゲームでは、まだ出てきていません）"
