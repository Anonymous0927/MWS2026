from __future__ import annotations

import pygame

from core.game import format_money

from .. import theme, widgets
from ..scene import Scene
from ..widgets import Button

MARGIN = 40
CONTENT_W = theme.SCREEN_W - MARGIN * 2

HEADER = pygame.Rect(MARGIN, 32, CONTENT_W, 112)
SITUATION_X = MARGIN
SITUATION_Y = 164

TERMS_Y = 236
TERMS_H = 26
TERMS_LABEL_X = MARGIN

READY_PANEL = pygame.Rect(MARGIN, 280, 440, 420)
CHOICE_X = READY_PANEL.right + 30
CHOICE_W = theme.SCREEN_W - MARGIN - CHOICE_X
CHOICE_H = 76
CHOICE_GAP = 96
CHOICE_Y0 = 292

WHY_PANEL = pygame.Rect(CHOICE_X, 716, CHOICE_W, 120)
GLOSSARY_PANEL = pygame.Rect(MARGIN, 716, READY_PANEL.width, 120)

assert WHY_PANEL.bottom <= theme.SCREEN_H, "「なぜ選べないの？」欄が画面外にある"
assert HEADER.bottom <= SITUATION_Y, "見出しと状況の文が重なる"
assert CHOICE_Y0 + CHOICE_GAP * 3 <= WHY_PANEL.y, "選択肢が説明欄に重なる"
assert TERMS_Y + TERMS_H <= READY_PANEL.y, "用語の帯が「いまの備え」に重なる"
assert READY_PANEL.bottom <= WHY_PANEL.y, "「いまの備え」が下の欄に重なる"

READY_LIMIT = 5


class IncidentScene(Scene):

    def __init__(self, app, session) -> None:
        super().__init__(app, session)
        self.event = session.current_event()
        self.options = session.available_options()
        self._term_links: list[widgets.TermLink] = []
        self.omen_notice = session.omen_notice()


    def buttons(self) -> list[Button]:
        items: list[Button] = []
        for index, view in enumerate(self.options):
            items.append(
                Button(
                    rect=pygame.Rect(CHOICE_X, CHOICE_Y0 + index * CHOICE_GAP,
                                     CHOICE_W, CHOICE_H),
                    label="",
                    on_click=lambda i=view.choice.id: self._choose(i),
                    enabled=view.selectable,
                    reason=view.reason,
                )
            )
        items.append(
            Button(
                rect=pygame.Rect(GLOSSARY_PANEL.x + 16, GLOSSARY_PANEL.y + 24,
                                 GLOSSARY_PANEL.width - 32, 72),
                label="？ 用語をしらべる",
                on_click=self._open_glossary,
                kind="quiet",
            )
        )
        return items

    def _choose(self, choice_id: str) -> None:
        self.session.choose(choice_id)
        self.app.show_outcome()

    def term_links(self) -> list[widgets.TermLink]:
        return self._term_links

    def _open_glossary(self) -> None:
        related = self.session.glossary_for("event", self.event.id) if self.event else []
        self.app.open_glossary(related=related)

    def on_escape(self) -> None:
        pass


    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(theme.BG)
        if self.event is None:
            return

        self._draw_header(screen)
        self._draw_situation(screen)
        self._draw_terms(screen)
        self._draw_readiness(screen)
        self._draw_choices(screen)
        self._draw_why(screen)
        self._draw_glossary_panel(screen)

    def _draw_header(self, screen: pygame.Surface) -> None:
        state = self.session.state
        widgets.draw_panel(screen, HEADER, theme.RED_BG, border=theme.RED, border_width=2)

        widgets.draw_text(screen, f"事件が起きました　{state.year} 年目",
                          (HEADER.x + 20, HEADER.y + 12), theme.SIZE_NOTE, theme.RED, bold=True)
        widgets.draw_wrapped(screen, self.event.name, (HEADER.x + 20, HEADER.y + 40),
                             HEADER.width - 220, theme.SIZE_TITLE, theme.INK, max_lines=1, bold=True)

        level, label = self._severity()
        badge = pygame.Rect(HEADER.right - 190, HEADER.y + 40, 170, 36)
        widgets.draw_status_badge(screen, badge, level, label)

        if self.omen_notice:
            widgets.draw_text_right(screen, self.omen_notice,
                                    HEADER.right - 20, HEADER.y + 84,
                                    theme.SIZE_TINY, theme.RED, bold=True)

    def _severity(self) -> tuple[str, str]:
        base = self.event.base_damage
        if base == 0:
            return ("ok", "おだやか")
        if base >= 70:
            return ("ng", "深刻度：大")
        if base >= 50:
            return ("warn", "深刻度：中")
        return ("warn", "深刻度：小")

    def _draw_situation(self, screen: pygame.Surface) -> None:
        y = SITUATION_Y
        for line in self.event.situation:
            y = widgets.draw_wrapped(screen, line, (SITUATION_X, y), CONTENT_W,
                                     theme.SIZE_BODY, theme.INK, max_lines=1, leading=6)

    def _draw_terms(self, screen: pygame.Surface) -> None:
        self._term_links = []
        if not self.event.glossary:
            return

        label = "この事件に出てくる言葉："
        label_rect = widgets.draw_text(screen, label, (TERMS_LABEL_X, TERMS_Y),
                                       theme.SIZE_NOTE, theme.GREY)
        x = label_rect.right + 12

        for term_id in self.event.glossary:
            name = self.session.term_label(term_id)
            if not name:
                continue
            link = widgets.make_term_link(term_id, name, (x, TERMS_Y), theme.SIZE_NOTE)
            if link.rect.right > theme.SCREEN_W - MARGIN:
                break
            widgets.draw_term_link(screen, link, theme.SIZE_NOTE)
            self._term_links.append(link)
            x = link.rect.right + 20

    def _draw_readiness(self, screen: pygame.Surface) -> None:
        widgets.draw_panel(screen, READY_PANEL, theme.CARD)
        x = READY_PANEL.x + 20
        y = READY_PANEL.y + 16

        widgets.draw_text(screen, "いまの備え", (x, y), theme.SIZE_HEAD, theme.INK, bold=True)
        y += 38

        active = self.session.active_measures()
        rates = self.session.effect_rates()
        related = sorted(self.event.mitigations.items(), key=lambda item: -item[1])[:READY_LIMIT]

        if not related:
            widgets.draw_text(screen, "この事件に効く対策はありません", (x, y),
                              theme.SIZE_NOTE, theme.GREY)
            return

        for measure_id, effect in related:
            owned = measure_id in active
            mark = "○" if owned else "×"
            color = theme.GREEN if owned else theme.RED
            name = self.session.name_of(measure_id) or measure_id

            widgets.draw_text(screen, mark, (x, y), theme.SIZE_BODY, color, bold=True)
            widgets.draw_flow_line(screen, name, (x + 28, y + 2), 240, theme.SIZE_NOTE,
                                   theme.INK if owned else theme.GREY)
            if owned:
                level = self.session.level_of(measure_id)
                actual = effect * rates.get(measure_id, 100) // 100
                effect_text = f"効きめ {actual}（{self.session.versions.name_of(level)}）"
            else:
                effect_text = f"効きめ {effect}"
            widgets.draw_text_right(screen, effect_text, READY_PANEL.right - 20, y + 2,
                                    theme.SIZE_NOTE, color, bold=True)
            y += 34

        y += 6
        widgets.draw_wrapped(screen, "× のところが、この事件に対する弱点です。",
                             (x, y), READY_PANEL.width - 40, theme.SIZE_TINY,
                             theme.GREY, max_lines=2, leading=4)

    def _draw_choices(self, screen: pygame.Surface) -> None:
        for index, view in enumerate(self.options):
            rect = pygame.Rect(CHOICE_X, CHOICE_Y0 + index * CHOICE_GAP, CHOICE_W, CHOICE_H)
            self._draw_choice(screen, rect, view)

    def _draw_choice(self, screen: pygame.Surface, rect: pygame.Rect, view) -> None:
        choice = view.choice
        unit = self.session.state.unit

        if view.selectable:
            widgets.draw_panel(screen, rect, theme.CARD, border=theme.BLUE, border_width=2)
            label_color, note_color = theme.INK, theme.GREY
        else:
            widgets.draw_panel(screen, rect, theme.GREY_BG, border=theme.LINE)
            label_color, note_color = theme.GREY, theme.GREY

        widgets.draw_flow_line(screen, choice.label, (rect.x + 20, rect.y + 10),
                               rect.width - 40, theme.SIZE_BODY, label_color, bold=True)

        parts = []
        if choice.extra_cost:
            parts.append(f"追加の費用 {format_money(choice.extra_cost, unit)}")
        parts.append(f"業務が止まる日数 {choice.downtime_days} 日")
        if choice.trust_delta:
            sign = "+" if choice.trust_delta > 0 else ""
            parts.append(f"信用度 {sign}{choice.trust_delta}")
        else:
            parts.append("信用度の増減なし")

        widgets.draw_text(screen, "　／　".join(parts), (rect.x + 20, rect.y + 40),
                          theme.SIZE_TINY, note_color)

        if not view.selectable:
            widgets.draw_text_right(screen, "選べません", rect.right - 20, rect.y + 40,
                                    theme.SIZE_TINY, theme.RED, bold=True)

    def _draw_why(self, screen: pygame.Surface) -> None:
        blocked = [view for view in self.options if not view.selectable]
        widgets.draw_panel(screen, WHY_PANEL, theme.AMBER_BG if blocked else theme.CARD,
                           border=theme.AMBER if blocked else theme.LINE)

        x = WHY_PANEL.x + 20
        y = WHY_PANEL.y + 12

        if not blocked:
            widgets.draw_text(screen, "いまはすべての手が選べます。", (x, y),
                              theme.SIZE_NOTE, theme.GREEN, bold=True)
            widgets.draw_text(screen, "どれを選んでも、その場では正解も不正解も出ません。"
                                      "ふりかえりは最後にまとめて出します。",
                              (x, y + 28), theme.SIZE_TINY, theme.GREY)
            return

        widgets.draw_text(screen, "なぜ選べないの？", (x, y), theme.SIZE_NOTE,
                          theme.AMBER, bold=True)
        y += 26
        for view in blocked[:2]:
            y = widgets.draw_wrapped(screen, f"・{view.reason}", (x, y), WHY_PANEL.width - 40,
                                     theme.SIZE_TINY, theme.INK, max_lines=1, leading=4)

    def _draw_glossary_panel(self, screen: pygame.Surface) -> None:
        widgets.draw_panel(screen, GLOSSARY_PANEL, theme.CARD)
        widgets.draw_text(screen, "分からない言葉がありますか？",
                          (GLOSSARY_PANEL.x + 16, GLOSSARY_PANEL.y + 2),
                          theme.SIZE_TINY, theme.GREY)
        for button in self.visible_buttons():
            if button.label:
                widgets.draw_button(screen, button)
