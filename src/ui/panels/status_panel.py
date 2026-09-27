from __future__ import annotations

import pygame

from core.game import AxisScore, FacilityView

from .. import theme, widgets

PANEL = pygame.Rect(theme.COL_LEFT_X, theme.CONTENT_TOP, theme.COL_LEFT_W, theme.COLUMN_H)

PAD = 16
INNER_X = PANEL.x + PAD
INNER_W = PANEL.width - PAD * 2

HEADING_Y = PANEL.y + 14
NOTE_Y = PANEL.y + 46

ROW_Y0 = PANEL.y + 72
ROW_GAP = 70
BAR_Y = 22
BAR_H = 14
LABEL_Y = 40
ROW_H = LABEL_Y + 16

TARGET_Y0 = PANEL.y + 72
TARGET_GAP = 148
TARGET_H = 136

LEGEND_GAP = 22
LEGEND_LINES = 4
LEGEND_TOP = PANEL.bottom - PAD - LEGEND_GAP * LEGEND_LINES

assert PANEL.bottom <= theme.SCREEN_H, "ステータス列が画面の高さを超えている"
assert NOTE_Y + 20 <= ROW_Y0, "見出しの補足と 1 行目が重なる"
assert ROW_Y0 + ROW_GAP * 6 + ROW_H <= LEGEND_TOP, "7 観点が凡例に重なる"
assert TARGET_Y0 + TARGET_GAP * 2 + TARGET_H <= PANEL.bottom, "守るもの 3 件がはみ出す"


def draw(
    screen: pygame.Surface,
    scores: list[AxisScore],
    planned: list[AxisScore] | None = None,
    targets: list[FacilityView] | None = None,
    is_school: bool = False,
) -> None:
    widgets.draw_panel(screen, PANEL, theme.CARD)

    if is_school:
        _draw_targets(screen, targets or [])
        return

    widgets.draw_text(screen, "会社のステータス", (INNER_X, HEADING_Y),
                      theme.SIZE_HEAD, theme.INK, bold=True)
    widgets.draw_wrapped(screen, "棒が短いところが手薄です", (INNER_X, NOTE_Y), INNER_W,
                         theme.SIZE_TINY, theme.GREY, max_lines=1)

    planned = planned or scores
    for index, score in enumerate(scores[:7]):
        after = planned[index] if index < len(planned) else score
        _draw_axis_row(screen, ROW_Y0 + index * ROW_GAP, score, after)

    _draw_legend(screen)




def _draw_axis_row(screen: pygame.Surface, y: int, score: AxisScore, after: AxisScore) -> None:
    color = theme.STATUS.get(score.level, (theme.GREY, ""))[0]
    difference = after.value - score.value

    widgets.draw_text(screen, score.axis.name, (INNER_X, y), theme.SIZE_NOTE, theme.INK, bold=True)
    _draw_value(screen, y, score.value, difference)

    bar = pygame.Rect(INNER_X, y + BAR_Y, INNER_W, BAR_H)
    pygame.draw.rect(screen, theme.GREY_BG, bar, border_radius=BAR_H // 2)

    if difference > 0:
        _fill(screen, bar, after.value, theme.BLUE)
    if score.value > 0:
        _fill(screen, bar, score.value, _light(color))
    if score.from_measures > 0:
        _fill(screen, bar, score.from_baseline + score.from_measures, color)
    if score.from_baseline > 0:
        _fill(screen, bar, score.from_baseline, theme.GREY)
    if difference < 0:
        _fill(screen, bar, score.value, theme.RED, start=after.value)

    widgets.draw_text(screen, score.label, (INNER_X, y + LABEL_Y), theme.SIZE_TINY, color)


def _draw_value(screen: pygame.Surface, y: int, value: int, difference: int) -> None:
    right = INNER_X + INNER_W
    if difference == 0:
        widgets.draw_text_right(screen, f"{value}", right, y, theme.SIZE_NOTE, theme.INK, bold=True)
        return

    color = theme.BLUE if difference > 0 else theme.RED
    after_rect = widgets.draw_text_right(screen, f"{value + difference}", right, y,
                                         theme.SIZE_NOTE, color, bold=True)
    widgets.draw_text_right(screen, f"{value} →", after_rect.x - 6, y,
                            theme.SIZE_TINY, theme.GREY)


def _fill(
    screen: pygame.Surface,
    bar: pygame.Rect,
    value: int,
    color: tuple[int, int, int],
    start: int = 0,
) -> None:
    left = bar.x + int(bar.width * max(0, start) / 100)
    right = bar.x + int(bar.width * min(100, value) / 100)
    width = max(bar.height, right - left) if right > left else 0
    if width <= 0:
        return
    pygame.draw.rect(screen, color, pygame.Rect(left, bar.y, width, bar.height),
                     border_radius=bar.height // 2)


def _light(color: tuple[int, int, int]) -> tuple[int, int, int]:
    return tuple(min(255, value + (255 - value) * 55 // 100) for value in color)


def _draw_legend(screen: pygame.Surface) -> None:
    y = LEGEND_TOP
    for text, color in (
        ("灰色：もとからの備え", theme.GREY),
        ("濃い色：買った対策", theme.GREEN),
        ("うすい色：今年の施策ぶん", _light(theme.GREEN)),
        ("青：いま選んでいるぶん", theme.BLUE),
    ):
        pygame.draw.rect(screen, color, pygame.Rect(INNER_X, y + 4, 10, 10), border_radius=2)
        widgets.draw_text(screen, text, (INNER_X + 18, y), theme.SIZE_TINY, theme.GREY)
        y += LEGEND_GAP




def _draw_targets(screen: pygame.Surface, views: list[FacilityView]) -> None:
    widgets.draw_text(screen, "守るもの", (INNER_X, HEADING_Y), theme.SIZE_HEAD,
                      theme.INK, bold=True)
    widgets.draw_wrapped(screen, "赤いところが守れていません", (INNER_X, NOTE_Y), INNER_W,
                         theme.SIZE_TINY, theme.GREY, max_lines=1)

    for index, view in enumerate(views[:3]):
        rect = pygame.Rect(INNER_X, TARGET_Y0 + index * TARGET_GAP, INNER_W, TARGET_H)
        _draw_target(screen, rect, view)


def _draw_target(screen: pygame.Surface, rect: pygame.Rect, view: FacilityView) -> None:
    color, _label = theme.STATUS.get(view.level, (theme.GREY, ""))
    background = theme.STATUS_BG.get(view.level, theme.GREY_BG)
    widgets.draw_panel(screen, rect, background, border=color, border_width=2)

    pad = 12
    widgets.draw_wrapped(screen, view.name, (rect.x + pad, rect.y + 10), rect.width - pad * 2,
                         theme.SIZE_NOTE, theme.INK, max_lines=1, bold=True)

    badge = pygame.Rect(rect.x + pad, rect.y + 34, 116, 24)
    widgets.draw_status_badge(screen, badge, view.level, view.label)

    widgets.draw_wrapped(screen, view.note, (rect.x + pad, rect.y + 64), rect.width - pad * 2,
                         theme.SIZE_TINY, theme.GREY, max_lines=1)

    if not view.missing:
        widgets.draw_text(screen, "必要な対策はそろっています", (rect.x + pad, rect.y + 88),
                          theme.SIZE_TINY, theme.GREEN)
        return
    widgets.draw_wrapped(screen, "／".join(view.missing) + " なし",
                         (rect.x + pad, rect.y + 88), rect.width - pad * 2,
                         theme.SIZE_TINY, theme.RED, max_lines=2, leading=3)
