from __future__ import annotations

import pygame

from core.game import StateView, format_money

from . import theme, widgets

HUD_X = theme.MARGIN
HUD_Y = 20
HUD_W = theme.SCREEN_W - theme.MARGIN * 2
HUD_H = theme.HUD_H
LABEL_Y = 48
VALUE_Y = 78
COLUMN_GAP = 220
COLUMN_X = tuple(56 + index * COLUMN_GAP for index in range(6))

COLUMN_W = COLUMN_GAP - 16

TRUST_COLUMN = 3
AWARENESS_COLUMN = 4

assert HUD_Y + HUD_H <= theme.SCREEN_H, "HUD が画面の高さを超えている"
assert HUD_Y + HUD_H < theme.CONTENT_TOP, "HUD が本文の領域に重なる"
assert COLUMN_X[-1] + COLUMN_W <= HUD_X + HUD_W, "いちばん右の指標が HUD からはみ出す"


def draw(screen: pygame.Surface, state: StateView) -> None:
    rect = pygame.Rect(HUD_X, HUD_Y, HUD_W, HUD_H)
    widgets.draw_panel(screen, rect, theme.CARD)

    columns = _columns(state)
    assert state.is_school or columns[TRUST_COLUMN][0] == "信用度", \
        "TRUST_COLUMN が「信用度」の枠を指していない"
    assert state.is_school or columns[AWARENESS_COLUMN][0] == "意識", \
        "AWARENESS_COLUMN が「意識」の枠を指していない"

    for index, (label, value, color) in enumerate(columns):
        x = COLUMN_X[index]
        widgets.draw_text(screen, label, (x, LABEL_Y - 14), theme.SIZE_NOTE, theme.GREY)
        widgets.draw_text(screen, value, (x, VALUE_Y - 22), theme.SIZE_HEAD, color, bold=True)

    widgets.draw_text_right(screen, f"シード {state.seed}", HUD_X + HUD_W - 16, 30,
                            theme.SIZE_TINY, theme.GREY)


def draw_tip(screen: pygame.Surface, state: StateView) -> None:
    if state.is_school:
        return

    mouse = widgets.mouse_pos()
    for column, title, lines in _tips(state):
        rect = _column_rect(column)
        if lines and rect.collidepoint(mouse):
            widgets.draw_tooltip(screen, rect, title, lines)
            return


def _tips(state: StateView) -> list[tuple[int, str, tuple[str, ...]]]:
    return [
        (TRUST_COLUMN, "信用度とは", state.trust_notes),
        (AWARENESS_COLUMN, "意識が高いと、こうなります", state.awareness_notes),
    ]


def _column_rect(column: int) -> pygame.Rect:
    x = COLUMN_X[column]
    top = LABEL_Y - 16
    return pygame.Rect(x, top, COLUMN_W, VALUE_Y + 10 - top)


def _columns(state: StateView) -> list[tuple[str, str, tuple[int, int, int]]]:
    star_text = "★" * state.star + "☆" * (5 - state.star)

    if state.is_school:
        return [
            ("学期", f"{state.year} / {state.total_years}", theme.INK),
            ("使えるお金", format_money(state.money, state.unit), theme.AMBER),
            ("みんなの信頼", f"{state.trust} / 100", _trust_color(state.trust)),
            ("安全レベル", star_text, theme.AMBER),
            ("いまの章", "第 1 部：学校編", theme.BLUE),
        ]

    return [
        ("経営年度", f"{state.year} 年目 / {state.total_years}", theme.INK),
        ("会社のお金", format_money(state.money, state.unit), _money_color(state.money)),
        ("年間維持費", format_money(state.upkeep, state.unit), _upkeep_color(state, state.upkeep)),
        ("信用度", f"{state.trust} / 100", _trust_color(state.trust)),
        ("意識", f"{state.awareness} / 100", _awareness_color(state.awareness)),
        ("安全レベル", star_text, theme.AMBER),
    ]


def _trust_color(trust: int) -> tuple[int, int, int]:
    if trust >= 80:
        return theme.GREEN
    if trust >= 50:
        return theme.AMBER
    return theme.RED


def _money_color(money: int) -> tuple[int, int, int]:
    return theme.RED if money < 0 else theme.AMBER


def _awareness_color(awareness: int) -> tuple[int, int, int]:
    if awareness >= 60:
        return theme.GREEN
    if awareness >= 30:
        return theme.AMBER
    return theme.RED


def _upkeep_color(state, upkeep: int) -> tuple[int, int, int]:
    return theme.RED if upkeep > state.profit else theme.AMBER
