from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Hashable

import pygame

from . import fonts, theme

_text_cache: dict[tuple[str, int, bool, tuple[int, int, int]], pygame.Surface] = {}

_TEXT_CACHE_LIMIT = 4000


def clear_text_cache() -> None:
    _text_cache.clear()


def render_text(
    text: str, size: int, color: tuple[int, int, int], bold: bool = False
) -> pygame.Surface:
    key = (text, size, bold, color)
    cached = _text_cache.get(key)
    if cached is None:
        if len(_text_cache) > _TEXT_CACHE_LIMIT:
            _text_cache.clear()
        cached = fonts.get(size, bold).render(text, True, color)
        _text_cache[key] = cached
    return cached




def draw_panel(
    surface: pygame.Surface,
    rect: pygame.Rect,
    color: tuple[int, int, int] = theme.CARD,
    radius: int = theme.RADIUS,
    border: tuple[int, int, int] | None = theme.LINE,
    border_width: int = 1,
) -> None:
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    if border is not None:
        pygame.draw.rect(surface, border, rect, width=border_width, border_radius=radius)


def draw_text(
    surface: pygame.Surface,
    text: str,
    pos: tuple[int, int],
    size: int = theme.SIZE_BODY,
    color: tuple[int, int, int] = theme.INK,
    bold: bool = False,
) -> pygame.Rect:
    rendered = render_text(text, size, color, bold)
    surface.blit(rendered, pos)
    return pygame.Rect(pos, rendered.get_size())


def draw_text_right(
    surface: pygame.Surface,
    text: str,
    right_x: int,
    y: int,
    size: int = theme.SIZE_BODY,
    color: tuple[int, int, int] = theme.INK,
    bold: bool = False,
) -> pygame.Rect:
    rendered = render_text(text, size, color, bold)
    pos = (right_x - rendered.get_width(), y)
    surface.blit(rendered, pos)
    return pygame.Rect(pos, rendered.get_size())


def draw_text_center(
    surface: pygame.Surface,
    text: str,
    center: tuple[int, int],
    size: int = theme.SIZE_BODY,
    color: tuple[int, int, int] = theme.INK,
    bold: bool = False,
) -> pygame.Rect:
    rendered = render_text(text, size, color, bold)
    rect = rendered.get_rect(center=center)
    surface.blit(rendered, rect)
    return rect


def wrap_text(text: str, size: int, max_width: int, max_lines: int = 99,
              bold: bool = False) -> list[str]:
    font = fonts.get(size, bold)
    lines: list[str] = []
    current = ""

    for char in text:
        if char == "\n":
            lines.append(current)
            current = ""
            continue
        if font.size(current + char)[0] <= max_width:
            current += char
            continue
        lines.append(current)
        current = char
        if len(lines) >= max_lines:
            break

    if current and len(lines) < max_lines:
        lines.append(current)

    if len(lines) > max_lines:
        lines = lines[:max_lines]

    consumed = sum(len(line) for line in lines)
    if consumed < len(text.replace("\n", "")) and lines:
        last = lines[-1]
        while last and font.size(last + "…")[0] > max_width:
            last = last[:-1]
        lines[-1] = last + "…"

    return lines


def draw_paragraph(
    surface: pygame.Surface,
    lines: list[str],
    pos: tuple[int, int],
    size: int = theme.SIZE_BODY,
    color: tuple[int, int, int] = theme.INK,
    leading: int = 8,
    bold: bool = False,
) -> int:
    x, y = pos
    line_height = fonts.get(size, bold).get_height() + leading
    for line in lines:
        draw_text(surface, line, (x, y), size, color, bold)
        y += line_height
    return y


def draw_wrapped(
    surface: pygame.Surface,
    text: str,
    pos: tuple[int, int],
    max_width: int,
    size: int = theme.SIZE_BODY,
    color: tuple[int, int, int] = theme.INK,
    max_lines: int = 99,
    leading: int = 8,
    bold: bool = False,
) -> int:
    if max_lines == 1:
        if not text:
            return pos[1]
        draw_flow_line(surface, text, pos, max_width, size, color, bold)
        return pos[1] + fonts.get(size, bold).get_height() + leading

    lines = wrap_text(text, size, max_width, max_lines, bold)
    if lines and lines[-1].endswith("…"):
        return _draw_flow_paragraph(surface, text, pos, max_width, size, color,
                                    max_lines, leading, bold, lines)
    return draw_paragraph(surface, lines, pos, size, color, leading, bold)



FLOW_PAUSE_MS = 800

FLOW_SPEED_PX = 60

FLOW_SPEED_Y_PX = 26

FLOW_HOVER_PAD = 3


@dataclass
class HoverFlowTimer:

    _started_at: dict[Hashable, int] = field(default_factory=dict)

    def elapsed(self, key: Hashable, hovered: bool, ticks: int) -> int:
        if not hovered:
            self._started_at.pop(key, None)
            return 0

        started_at = self._started_at.setdefault(key, ticks)
        if ticks < started_at:
            self._started_at[key] = ticks
            return 0
        return ticks - started_at


_HOVER_FLOW_TIMER = HoverFlowTimer()


def flow_offset(overflow: int, ticks: int, speed: int = FLOW_SPEED_PX) -> int:
    if overflow <= 0:
        return 0

    travel_ms = max(1, int(overflow / speed * 1000))
    elapsed = ticks % (FLOW_PAUSE_MS * 2 + travel_ms)

    if elapsed < FLOW_PAUSE_MS:
        return 0
    elapsed -= FLOW_PAUSE_MS
    if elapsed < travel_ms:
        return int(overflow * elapsed / travel_ms)
    return overflow


def flow_position(origin: int, overflow: int, ticks: int,
                  speed: int = FLOW_SPEED_PX) -> int:
    if overflow <= 0:
        return origin
    return origin - flow_offset(overflow, ticks, speed)


def mouse_pos() -> tuple[int, int]:
    if not pygame.display.get_init():
        return (-1, -1)
    return pygame.mouse.get_pos()


def draw_flow_line(
    surface: pygame.Surface,
    text: str,
    pos: tuple[int, int],
    max_width: int,
    size: int = theme.SIZE_BODY,
    color: tuple[int, int, int] = theme.INK,
    bold: bool = False,
) -> pygame.Rect:
    line = text.replace("\n", " ")
    full = render_text(line, size, color, bold)
    height = fonts.get(size, bold).get_height()
    rect = pygame.Rect(pos[0], pos[1], min(full.get_width(), max_width), height)

    overflow = full.get_width() - max_width
    if overflow <= 0:
        surface.blit(full, pos)
        return rect

    hover_area = pygame.Rect(pos[0], pos[1] - FLOW_HOVER_PAD,
                             max_width, height + FLOW_HOVER_PAD * 2)
    hovered = hover_area.collidepoint(mouse_pos())
    ticks = pygame.time.get_ticks()
    timer_key = ("line", id(surface), text, pos, max_width, size, bold)
    hover_ticks = _HOVER_FLOW_TIMER.elapsed(timer_key, hovered, ticks)
    if not hovered:
        draw_text(surface, wrap_text(line, size, max_width, 1, bold)[0], pos, size, color, bold)
        return rect

    clip_area = pygame.Rect(pos[0], pos[1], max_width, height)
    previous = surface.get_clip()
    surface.set_clip(clip_area.clip(previous) if previous is not None else clip_area)
    x = flow_position(pos[0], overflow, hover_ticks)
    surface.blit(full, (x, pos[1]))
    surface.set_clip(previous)
    return rect


def _draw_flow_paragraph(
    surface: pygame.Surface,
    text: str,
    pos: tuple[int, int],
    max_width: int,
    size: int,
    color: tuple[int, int, int],
    max_lines: int,
    leading: int,
    bold: bool,
    clipped_lines: list[str],
) -> int:
    line_height = fonts.get(size, bold).get_height() + leading
    box_height = line_height * max_lines
    bottom = pos[1] + box_height

    hover_area = pygame.Rect(pos[0], pos[1] - FLOW_HOVER_PAD,
                             max_width, box_height + FLOW_HOVER_PAD * 2)
    hovered = hover_area.collidepoint(mouse_pos())
    ticks = pygame.time.get_ticks()
    timer_key = (
        "paragraph", id(surface), text, pos, max_width, size, max_lines, leading, bold
    )
    hover_ticks = _HOVER_FLOW_TIMER.elapsed(timer_key, hovered, ticks)
    if not hovered:
        draw_paragraph(surface, clipped_lines, pos, size, color, leading, bold)
        return bottom

    full_lines = wrap_text(text, size, max_width, bold=bold)
    overflow = line_height * (len(full_lines) - max_lines)

    clip_area = pygame.Rect(pos[0], pos[1], max_width, box_height)
    previous = surface.get_clip()
    surface.set_clip(clip_area.clip(previous) if previous is not None else clip_area)
    draw_paragraph(
        surface, full_lines,
        (pos[0], flow_position(pos[1], overflow, hover_ticks, FLOW_SPEED_Y_PX)),
        size, color, leading, bold,
    )
    surface.set_clip(previous)
    return bottom



TIP_PAD = 14
TIP_LEADING = 6
TIP_GAP = 8
TIP_WIDTH = 460


def draw_tooltip(
    surface: pygame.Surface,
    anchor: pygame.Rect,
    title: str,
    lines: tuple[str, ...] | list[str],
    width: int = TIP_WIDTH,
) -> pygame.Rect:
    if not lines:
        return pygame.Rect(0, 0, 0, 0)

    inner = width - TIP_PAD * 2
    body: list[str] = []
    for line in lines:
        first, *rest = wrap_text(f"・{line}", theme.SIZE_NOTE, inner)
        body.append(first)
        body.extend(f"　{item}" for item in rest)

    line_height = fonts.get(theme.SIZE_NOTE).get_height() + TIP_LEADING
    height = line_height * (len(body) + 1) - TIP_LEADING + TIP_PAD * 2

    rect = pygame.Rect(anchor.x, anchor.bottom + TIP_GAP, width, height)
    rect.right = min(rect.right, theme.SCREEN_W - theme.MARGIN)
    rect.x = max(rect.x, theme.MARGIN)
    if rect.bottom > theme.SCREEN_H - theme.MARGIN:
        rect.bottom = anchor.y - TIP_GAP

    draw_panel(surface, rect, theme.CARD, border=theme.BLUE, border_width=2)
    y = draw_paragraph(surface, [title], (rect.x + TIP_PAD, rect.y + TIP_PAD),
                       theme.SIZE_NOTE, theme.BLUE, TIP_LEADING, bold=True)
    draw_paragraph(surface, body, (rect.x + TIP_PAD, y), theme.SIZE_NOTE,
                   theme.INK, TIP_LEADING)
    return rect




@dataclass
class Button:

    rect: pygame.Rect
    label: str
    on_click: Callable[[], None] | None = None
    enabled: bool = True
    reason: str = ""
    kind: str = "primary"
    hovered: bool = False

    def hit(self, pos: tuple[int, int]) -> bool:
        return self.rect.collidepoint(pos)

    def click(self) -> None:
        if self.enabled and self.on_click is not None:
            self.on_click()


_BUTTON_STYLE = {
    "primary": (theme.BLUE, theme.WHITE, theme.BLUE),
    "confirm": (theme.CONFIRM, theme.WHITE, theme.CONFIRM),
    "next": (theme.NEXT, theme.WHITE, theme.NEXT),
    "normal": (theme.WHITE, theme.INK, theme.LINE),
    "quiet": (theme.GREY_BG, theme.INK, theme.LINE),
    "danger": (theme.RED, theme.WHITE, theme.RED),
}


def draw_button(surface: pygame.Surface, button: Button) -> None:
    fill, text_color, border = _BUTTON_STYLE.get(button.kind, _BUTTON_STYLE["normal"])
    if not button.enabled:
        fill, text_color, border = theme.GREY_BG, theme.GREY, theme.LINE
    elif button.hovered:
        fill = {
            "primary": theme.BLUE_HOVER,
            "confirm": theme.CONFIRM_HOVER,
            "next": theme.NEXT_HOVER,
        }.get(button.kind, theme.BLUE_BG)

    emphasized = button.enabled and button.kind in ("confirm", "next")
    if emphasized:
        shadow = button.rect.move(0, 4)
        draw_panel(surface, shadow, theme.BUTTON_SHADOW, radius=theme.RADIUS)

    draw_panel(
        surface,
        button.rect,
        fill,
        radius=theme.RADIUS,
        border=border,
        border_width=2 if emphasized else 1,
    )

    inner_width = button.rect.width - 20
    size = theme.SIZE_BODY
    for candidate in (theme.SIZE_BODY, theme.SIZE_NOTE, theme.SIZE_TINY):
        if fonts.get(candidate, True).size(button.label)[0] <= inner_width:
            size = candidate
            break
    else:
        size = theme.SIZE_TINY

    label = button.label
    if fonts.get(size, True).size(label)[0] > inner_width:
        label = wrap_text(label, size, inner_width, max_lines=1, bold=True)[0]

    draw_text_center(surface, label, button.rect.center, size, text_color, bold=True)

    if emphasized:
        _draw_action_icon(surface, button, text_color)


def _draw_action_icon(surface: pygame.Surface, button: Button, color: tuple[int, int, int]) -> None:
    center_y = button.rect.centery
    if button.kind == "confirm":
        x = button.rect.x + 20
        pygame.draw.line(surface, color, (x - 5, center_y), (x - 1, center_y + 5), 3)
        pygame.draw.line(surface, color, (x - 1, center_y + 5), (x + 7, center_y - 5), 3)
        return

    if button.kind == "next":
        x = button.rect.right - 20
        pygame.draw.line(surface, color, (x - 8, center_y), (x + 5, center_y), 3)
        pygame.draw.line(surface, color, (x, center_y - 5), (x + 5, center_y), 3)
        pygame.draw.line(surface, color, (x, center_y + 5), (x + 5, center_y), 3)




def draw_status_badge(
    surface: pygame.Surface,
    rect: pygame.Rect,
    level: str,
    label: str,
) -> None:
    color, default_label = theme.STATUS.get(level, (theme.GREY, ""))
    background = theme.STATUS_BG.get(level, theme.GREY_BG)

    draw_panel(surface, rect, background, radius=rect.height // 2, border=color)
    draw_text_center(surface, label or default_label, rect.center, theme.SIZE_NOTE, color, bold=True)


def draw_gauge(
    surface: pygame.Surface,
    rect: pygame.Rect,
    value: int,
    color: tuple[int, int, int] = theme.BLUE,
    background: tuple[int, int, int] = theme.GREY_BG,
) -> None:
    radius = rect.height // 2
    pygame.draw.rect(surface, background, rect, border_radius=radius)

    filled = max(0, min(100, value))
    if filled <= 0:
        return
    width = max(rect.height, int(rect.width * filled / 100))
    pygame.draw.rect(surface, color, pygame.Rect(rect.x, rect.y, width, rect.height),
                     border_radius=radius)


@dataclass
class TermLink:

    rect: pygame.Rect
    term_id: str
    label: str

    def hit(self, pos: tuple[int, int]) -> bool:
        return self.rect.collidepoint(pos)


def draw_term_link(surface: pygame.Surface, link: TermLink,
                   size: int = theme.SIZE_NOTE) -> None:
    rendered = render_text(link.label, size, theme.BLUE)
    surface.blit(rendered, link.rect.topleft)
    underline_y = link.rect.y + rendered.get_height() - 1
    pygame.draw.line(
        surface, theme.BLUE,
        (link.rect.x, underline_y),
        (link.rect.x + rendered.get_width(), underline_y), 1,
    )


def make_term_link(term_id: str, label: str, pos: tuple[int, int],
                   size: int = theme.SIZE_NOTE) -> TermLink:
    width, height = fonts.get(size).size(label)
    rect = pygame.Rect(pos[0], pos[1], max(width, theme.MIN_TAP), max(height, LINK_H))
    return TermLink(rect=rect, term_id=term_id, label=label)




@dataclass
class ScrollList:

    rect: pygame.Rect
    item_height: int
    count: int = 0
    offset: int = 0

    @property
    def max_offset(self) -> int:
        total = self.item_height * self.count
        return max(0, total - self.rect.height)

    def scroll(self, wheel_y: int) -> None:
        self.offset = max(0, min(self.max_offset, self.offset - wheel_y * self.item_height))

    def visible_range(self) -> range:
        first = self.offset // self.item_height
        last = (self.offset + self.rect.height) // self.item_height + 1
        return range(max(0, first), min(self.count, last))

    def item_rect(self, index: int) -> pygame.Rect:
        return pygame.Rect(
            self.rect.x,
            self.rect.y + index * self.item_height - self.offset,
            self.rect.width,
            self.item_height,
        )


def scrollbar_rects(
    scroll: ScrollList, vertical_inset: int = 0
) -> tuple[pygame.Rect, pygame.Rect]:
    inset = max(0, min(vertical_inset, (scroll.rect.height - 1) // 2))
    track = pygame.Rect(
        scroll.rect.right - 6,
        scroll.rect.y + inset,
        4,
        scroll.rect.height - inset * 2,
    )

    ratio = scroll.rect.height / (scroll.item_height * scroll.count)
    knob_height = min(track.height, max(24, int(track.height * ratio)))
    travel = track.height - knob_height
    knob_y = track.y + int(travel * scroll.offset / scroll.max_offset)
    knob = pygame.Rect(track.x, knob_y, 4, knob_height)
    return track, knob


def draw_scrollbar(
    surface: pygame.Surface, scroll: ScrollList, vertical_inset: int = 0
) -> None:
    if scroll.max_offset <= 0:
        return

    track, knob = scrollbar_rects(scroll, vertical_inset)
    pygame.draw.rect(surface, theme.GREY_BG, track, border_radius=2)
    pygame.draw.rect(surface, theme.LINE, knob, border_radius=2)



CARD_PAD = 12
CARD_ROW_BADGE = 4
CARD_ROW_NAME = 26
CARD_ROW_FORMAL = 46
CARD_ROW_COST = 62
CARD_ROW_SUMMARY = 84
CARD_ROW_LINK = 102
BADGE_W = 84
BADGE_H = 20

PIP_R = 5
PIP_GAP = 14

LEVEL_NONE = 0
LINK_H = 24

CARD_MIN_H = CARD_ROW_LINK + LINK_H


def draw_measure_card(
    surface: pygame.Surface,
    rect: pygame.Rect,
    view,
    unit: str = "man",
) -> TermLink | None:
    from core.game import format_money

    border, fill, text_color = theme.MEASURE_STYLE.get(
        view.state, theme.MEASURE_STYLE["available"]
    )
    draw_panel(surface, rect, fill, border=border,
               border_width=2 if view.state in ("owned", "selected") else 1)

    measure = view.measure
    left = rect.x + CARD_PAD
    inner_width = rect.width - CARD_PAD * 2

    badge_rect = pygame.Rect(rect.right - CARD_PAD - BADGE_W, rect.y + CARD_ROW_BADGE,
                             BADGE_W, BADGE_H)
    _draw_measure_badge(surface, badge_rect, view.state, view.badge_label)

    draw_flow_line(surface, measure.name, (left, rect.y + CARD_ROW_NAME),
                   inner_width, theme.SIZE_BODY, text_color, bold=True)

    formal_width = inner_width
    if view.max_level > 1:
        formal_width -= PIP_GAP * view.max_level + 6
    draw_flow_line(surface, f"（{measure.formal_name}）", (left, rect.y + CARD_ROW_FORMAL),
                   formal_width, theme.SIZE_TINY, theme.GREY)

    _draw_version_pips(surface, rect, view)

    _draw_next_step(surface, rect, view, unit, format_money)

    if view.reason:
        color = theme.RED if view.state == "disabled" else theme.AMBER
        line = view.reason
    elif view.level <= 0:
        color, line = theme.GREY, measure.summary
    elif view.next_note:
        color, line = theme.INK, f"次：{view.next_note}"
    else:
        color, line = theme.GREY, view.version_note or measure.summary
    draw_wrapped(surface, line, (left, rect.y + CARD_ROW_SUMMARY),
                 rect.width - CARD_PAD * 2, theme.SIZE_NOTE, color, max_lines=1)

    if measure.glossary:
        link = make_term_link(measure.glossary[0], "くわしく >",
                              (rect.right - CARD_PAD - 78, rect.y + CARD_ROW_LINK),
                              theme.SIZE_TINY)
        draw_term_link(surface, link, theme.SIZE_TINY)
        return link
    return None


def _draw_version_pips(surface: pygame.Surface, rect: pygame.Rect, view) -> None:
    if view.max_level <= 1:
        return

    color = theme.AMBER if view.outdated else theme.GREEN
    right = rect.right - CARD_PAD
    center_y = rect.y + CARD_ROW_FORMAL + 8

    for index in range(view.max_level):
        center_x = right - PIP_R - (view.max_level - 1 - index) * PIP_GAP
        filled = index < view.level
        pygame.draw.circle(surface, color if filled else theme.WHITE,
                           (center_x, center_y), PIP_R)
        pygame.draw.circle(surface, color if filled else theme.GREY,
                           (center_x, center_y), PIP_R, 1)


def _draw_next_step(surface: pygame.Surface, rect: pygame.Rect, view,
                    unit: str, format_money) -> None:
    left = rect.x + CARD_PAD
    baseline_y = rect.y + CARD_ROW_COST

    if view.next_level <= 0:
        draw_text(surface, "いちばん上の ver です", (left, baseline_y),
                  theme.SIZE_NOTE, theme.GREEN, bold=True)
        if view.upkeep:
            draw_text_right(surface, f"毎年 {format_money(view.upkeep, unit)}",
                            rect.right - CARD_PAD, baseline_y + 4,
                            theme.SIZE_TINY, theme.GREY)
        return

    if view.level <= LEVEL_NONE:
        cost_text = f"導入 {format_money(view.next_cost, unit)}"
    else:
        cost_text = f"次：{view.next_level_name} に {format_money(view.next_cost, unit)}"
    draw_text(surface, cost_text, (left, baseline_y),
              theme.SIZE_NOTE, theme.AMBER, bold=True)

    if view.next_upkeep:
        draw_text_right(surface, f"毎年 {format_money(view.next_upkeep, unit)}",
                        rect.right - CARD_PAD, baseline_y + 4,
                        theme.SIZE_TINY, theme.GREY)


def _draw_measure_badge(surface: pygame.Surface, rect: pygame.Rect,
                        state: str, label: str) -> None:
    colors = {
        "owned": (theme.GREEN, theme.GREEN_BG),
        "selected": (theme.BLUE, theme.BLUE_BG),
        "available": (theme.GREY, theme.WHITE),
        "disabled": (theme.GREY, theme.GREY_BG),
        "canceling": (theme.RED, theme.RED_BG),
    }
    color, background = colors.get(state, (theme.GREY, theme.WHITE))
    draw_panel(surface, rect, background, radius=rect.height // 2, border=color)
    draw_text_center(surface, label, rect.center, theme.SIZE_TINY, color, bold=True)


def draw_stars(
    surface: pygame.Surface,
    pos: tuple[int, int],
    star: int,
    size: int = theme.SIZE_HEAD,
    color: tuple[int, int, int] = theme.AMBER,
) -> pygame.Rect:
    return draw_text(surface, "★" * star + "☆" * (5 - star), pos, size, color, bold=True)


def draw_scrim(surface: pygame.Surface) -> None:
    scrim = pygame.Surface((theme.SCREEN_W, theme.SCREEN_H), pygame.SRCALPHA)
    scrim.fill((0, 0, 0, theme.SCRIM_ALPHA))
    surface.blit(scrim, (0, 0))
