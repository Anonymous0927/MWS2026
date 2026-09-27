from __future__ import annotations

import pygame

from core.game import TimelineEntry

from .. import theme, widgets

PANEL = pygame.Rect(theme.COL_RIGHT_X, theme.CONTENT_TOP, theme.COL_RIGHT_W, theme.COLUMN_H)

PAD = 16
HEADING_Y = PANEL.y + 14
NOTE_Y = PANEL.y + 44

LIST_RECT = pygame.Rect(PANEL.x + PAD, PANEL.y + 70, PANEL.width - PAD * 2,
                        PANEL.height - 70 - PAD)

ITEM_H = 72
ITEM_GAP = 6
SCROLLBAR_ROOM = 12

assert PANEL.bottom <= theme.SCREEN_H, "できごと列が画面の高さを超えている"
assert LIST_RECT.bottom <= PANEL.bottom, "できごとの一覧がパネルからはみ出す"
assert NOTE_Y + 20 <= LIST_RECT.y, "見出しの補足と 1 件目が重なる"


def item_step() -> int:
    return ITEM_H + ITEM_GAP


def draw(
    screen: pygame.Surface,
    entries: list[TimelineEntry],
    scroll: widgets.ScrollList,
    is_school: bool = False,
) -> None:
    widgets.draw_panel(screen, PANEL, theme.CARD)
    widgets.draw_text(screen, "これまでのできごと", (PANEL.x + PAD, HEADING_Y),
                      theme.SIZE_HEAD, theme.INK, bold=True)

    if not entries:
        widgets.draw_text(screen, "まだ何も起きていません", (PANEL.x + PAD, LIST_RECT.y),
                          theme.SIZE_NOTE, theme.GREY)
        return

    note = f"全 {len(entries)} 件"
    if scroll.max_offset > 0:
        note += "　ホイールで過去へ"
    widgets.draw_text(screen, note, (PANEL.x + PAD, NOTE_Y), theme.SIZE_TINY, theme.GREY)

    previous_clip = screen.get_clip()
    screen.set_clip(LIST_RECT)
    for index in scroll.visible_range():
        rect = scroll.item_rect(index)
        rect.height = ITEM_H
        rect.width -= SCROLLBAR_ROOM
        _draw_entry(screen, rect, entries[index], is_school)
    screen.set_clip(previous_clip)

    widgets.draw_scrollbar(screen, scroll)


def _draw_entry(
    screen: pygame.Surface,
    rect: pygame.Rect,
    entry: TimelineEntry,
    is_school: bool,
) -> None:
    color, background = theme.TIMELINE_STYLE.get(entry.kind, (theme.GREY, theme.GREY_BG))
    widgets.draw_panel(screen, rect, background, border=None)

    pygame.draw.rect(screen, color, pygame.Rect(rect.x, rect.y, 4, rect.height), border_radius=2)

    unit = "学期" if is_school else "年目"
    widgets.draw_text(screen, f"{entry.year} {unit}", (rect.x + 12, rect.y + 6),
                      theme.SIZE_TINY, theme.GREY, bold=True)

    widgets.draw_text_right(screen, f"【{entry.kind}】", rect.right - 10, rect.y + 6,
                            theme.SIZE_TINY, color, bold=True)

    widgets.draw_wrapped(screen, entry.text, (rect.x + 12, rect.y + 26), rect.width - 24,
                         theme.SIZE_TINY, theme.INK, max_lines=2, leading=4)
