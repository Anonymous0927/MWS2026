from __future__ import annotations

import pygame

from core.game import format_money

from .. import theme, widgets
from ..scene import Scene
from ..widgets import Button

MARGIN = 40
CONTENT_W = theme.SCREEN_W - MARGIN * 2

STORY_PANEL = pygame.Rect(MARGIN, 128, 880, 282)
CHANGE_PANEL = pygame.Rect(STORY_PANEL.right + 24, 128, CONTENT_W - STORY_PANEL.width - 24, 282)
DEFENCE_PANEL = pygame.Rect(MARGIN, 430, CONTENT_W, 230)
LEARNING_PANEL = pygame.Rect(MARGIN, 680, CONTENT_W, 125)
NEXT_BUTTON = pygame.Rect(theme.SCREEN_W - MARGIN - 220, 812, 220, 64)
GLOSSARY_BUTTON = pygame.Rect(MARGIN, 812, 240, 64)

assert NEXT_BUTTON.bottom <= theme.SCREEN_H, "「次へ」が画面の高さを超えている"
assert STORY_PANEL.right < CHANGE_PANEL.x, "話のパネルと変化のパネルが重なる"
assert STORY_PANEL.bottom <= DEFENCE_PANEL.y, "話のパネルが守りの帯に重なる"
assert DEFENCE_PANEL.bottom <= LEARNING_PANEL.y, "守りの帯が学習ポイントに重なる"
assert LEARNING_PANEL.bottom <= NEXT_BUTTON.y, "学習ポイントがボタンに重なる"

CONTRIBUTION_LIMIT = 3


class OutcomeScene(Scene):

    def __init__(self, app, session) -> None:
        super().__init__(app, session)
        self.outcome = session.last_outcome()


    def buttons(self) -> list[Button]:
        return [
            Button(
                rect=GLOSSARY_BUTTON,
                label="？ 用語をしらべる",
                on_click=self._open_glossary,
                kind="quiet",
            ),
            Button(rect=NEXT_BUTTON, label="次へ", on_click=self.app.finish_year, kind="next"),
        ]

    def _open_glossary(self) -> None:
        related = (
            self.session.glossary_for("event", self.outcome.event.id) if self.outcome else []
        )
        self.app.open_glossary(related=related)

    def on_escape(self) -> None:
        self.app.finish_year()


    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(theme.BG)
        if self.outcome is None:
            return

        from .. import hud

        hud.draw(screen, self.session.state)
        self._draw_story(screen)
        self._draw_changes(screen)
        self._draw_defence(screen)
        self._draw_learning(screen)

        for button in self.visible_buttons():
            widgets.draw_button(screen, button)

        hud.draw_tip(screen, self.session.state)

    def _draw_story(self, screen: pygame.Surface) -> None:
        outcome = self.outcome

        widgets.draw_panel(screen, STORY_PANEL, theme.CARD)
        x = STORY_PANEL.x + 20
        y = STORY_PANEL.y + 14

        widgets.draw_text(screen, "選んだ手", (x, y), theme.SIZE_TINY, theme.GREY)
        y = widgets.draw_wrapped(screen, outcome.choice.label, (x, y + 20),
                                 STORY_PANEL.width - 40, theme.SIZE_BODY, theme.BLUE,
                                 max_lines=1, bold=True)
        y += 8

        y = widgets.draw_wrapped(screen, outcome.choice.result_text, (x, y),
                                 STORY_PANEL.width - 40, theme.SIZE_BODY, theme.INK,
                                 max_lines=2, leading=6)

        if outcome.luck_note:
            widgets.draw_wrapped(screen, outcome.luck_note, (x, y + 6),
                                 STORY_PANEL.width - 40, theme.SIZE_NOTE, theme.AMBER,
                                 max_lines=2, leading=4)

    def _draw_changes(self, screen: pygame.Surface) -> None:
        outcome = self.outcome
        unit = self.session.state.unit

        widgets.draw_panel(screen, CHANGE_PANEL, theme.CARD)
        x = CHANGE_PANEL.x + 20
        y = CHANGE_PANEL.y + 14

        widgets.draw_text(screen, "この事件による変化", (x, y), theme.SIZE_NOTE,
                          theme.INK, bold=True)
        y += 36

        rows = [
            ("被害額", f"−{format_money(outcome.damage, unit)}" if outcome.damage
             else format_money(0, unit),
             theme.RED if outcome.damage else theme.GREEN),
            ("信用度", _signed(outcome.trust_delta),
             theme.GREEN if outcome.trust_delta >= 0 else theme.RED),
        ]
        if not self.session.state.is_school:
            rows.append(
                ("満足度", _signed(outcome.morale_delta),
                 theme.GREEN if outcome.morale_delta >= 0 else theme.RED)
            )

        for label, value, color in rows:
            widgets.draw_text(screen, label, (x, y + 8), theme.SIZE_NOTE, theme.GREY)
            widgets.draw_text_right(screen, value, CHANGE_PANEL.right - 20, y,
                                    theme.SIZE_HEAD, color, bold=True)
            y += 44

        if outcome.choice.downtime_days:
            widgets.draw_text(screen, f"業務が止まった日数：{outcome.choice.downtime_days} 日",
                              (x, y), theme.SIZE_TINY, theme.GREY)

    def _draw_defence(self, screen: pygame.Surface) -> None:
        outcome = self.outcome
        unit = self.session.state.unit

        widgets.draw_panel(screen, DEFENCE_PANEL, theme.CARD)
        x = DEFENCE_PANEL.x + 20
        y = DEFENCE_PANEL.y + 12

        widgets.draw_text(screen, "守りはどう働いたか", (x, y), theme.SIZE_HEAD,
                          theme.INK, bold=True)
        y += 36

        label_x = x
        value_x = x + 130

        widgets.draw_text(screen, "効いた対策", (label_x, y), theme.SIZE_NOTE,
                          theme.GREEN, bold=True)
        parts = []
        if outcome.baseline:
            parts.append(f"もとからの備え {outcome.baseline}")
        parts += [
            f"{item.measure_name} {item.effect}"
            for item in outcome.contributions[:CONTRIBUTION_LIMIT]
        ]
        if parts:
            tail = f" ＝ 効きめ {outcome.effect_total} %"
            if outcome.capped:
                tail += "（上限 90 まで。リスクはゼロになりません）"
            widgets.draw_wrapped(screen, " ＋ ".join(parts) + tail, (value_x, y),
                                 DEFENCE_PANEL.width - 170, theme.SIZE_NOTE,
                                 theme.INK, max_lines=1)
        else:
            widgets.draw_text(screen, "この事件に効く対策を、ひとつも持っていませんでした",
                              (value_x, y), theme.SIZE_NOTE, theme.RED)
        y += 30

        widgets.draw_text(screen, "効かなかった", (label_x, y), theme.SIZE_NOTE,
                          theme.AMBER, bold=True)
        if outcome.no_effect_notes:
            widgets.draw_wrapped(screen, outcome.no_effect_notes[0], (value_x, y),
                                 DEFENCE_PANEL.width - 170, theme.SIZE_NOTE,
                                 theme.INK, max_lines=1)
        else:
            widgets.draw_text(screen, "買ってあった対策は、どれもこの事件に関係していました",
                              (value_x, y), theme.SIZE_NOTE, theme.GREY)
        y += 30

        widgets.draw_text(screen, "被害の計算", (label_x, y), theme.SIZE_NOTE,
                          theme.BLUE, bold=True)
        widgets.draw_wrapped(screen, outcome.full_formula_text, (value_x, y),
                             DEFENCE_PANEL.width - 170, theme.SIZE_NOTE, theme.INK,
                             max_lines=1)
        y += 30

        widgets.draw_text(screen, "上げていたら", (label_x, y), theme.SIZE_NOTE,
                          theme.AMBER, bold=True)
        if outcome.upgrade_note:
            widgets.draw_wrapped(screen, outcome.upgrade_note, (value_x, y),
                                 DEFENCE_PANEL.width - 170, theme.SIZE_NOTE,
                                 theme.AMBER, max_lines=1)
        else:
            widgets.draw_text(screen, "いま出せる守りは、出しきっていました",
                              (value_x, y), theme.SIZE_NOTE, theme.GREY)

    def _draw_learning(self, screen: pygame.Surface) -> None:
        widgets.draw_panel(screen, LEARNING_PANEL, theme.AMBER_BG, border=theme.AMBER)

        x = LEARNING_PANEL.x + 20
        y = LEARNING_PANEL.y + 12

        widgets.draw_text(screen, "★ 学習ポイント", (x, y), theme.SIZE_NOTE,
                          theme.AMBER, bold=True)
        widgets.draw_wrapped(screen, self.outcome.event.learning, (x, y + 30),
                             LEARNING_PANEL.width - 40, theme.SIZE_BODY, theme.INK,
                             max_lines=2, leading=6)


def _signed(value: int) -> str:
    if value > 0:
        return f"+{value}"
    return str(value)
