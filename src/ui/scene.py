from __future__ import annotations

import pygame

from .widgets import Button, TermLink

NO_MOUSE_POS = (-1, -1)

ButtonKey = tuple[tuple[int, int, int, int], str, str]


class Scene:

    def __init__(self, app, session) -> None:
        self.app = app
        self.session = session
        self.mouse_pos: tuple[int, int] = NO_MOUSE_POS
        self._press_key: ButtonKey | None = None
        self._press_term_id: str | None = None
        self._pressed_outside_button = False


    def update(self, dt: float) -> None:
        pass

    def draw(self, screen: pygame.Surface) -> None:
        raise NotImplementedError

    def buttons(self) -> list[Button]:
        return []

    def on_escape(self) -> None:
        self.app.go_back()

    def term_links(self) -> list[TermLink]:
        return []

    def on_click(self, pos: tuple[int, int]) -> None:
        pass

    def on_wheel(self, wheel_y: int) -> None:
        pass


    def visible_buttons(self) -> list[Button]:
        items = self.buttons()
        for button in items:
            button.hovered = button.enabled and button.hit(self.mouse_pos)
        return items


    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.mouse_pos = event.pos

            link = self._term_link_at(event.pos)
            self._press_term_id = link.term_id if link is not None else None
            if link is not None:
                self._press_key = None
                self._pressed_outside_button = False
                return

            pressed = self._button_at(event.pos)
            self._press_key = self._key_of(pressed) if pressed is not None else None
            self._pressed_outside_button = pressed is None
            return

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.mouse_pos = event.pos

            released_link = self._term_link_at(event.pos)
            if released_link is not None and released_link.term_id == self._press_term_id:
                self.app.open_glossary(released_link.term_id)
            else:
                released = self._button_at(event.pos)
                if released is not None and self._key_of(released) == self._press_key:
                    released.click()
                elif released is None and self._pressed_outside_button:
                    self.on_click(event.pos)

            self._press_key = None
            self._press_term_id = None
            self._pressed_outside_button = False
            return

        if event.type == pygame.MOUSEMOTION:
            self.mouse_pos = event.pos
            return

        if event.type == pygame.MOUSEWHEEL:
            self.on_wheel(event.y)
            return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.on_escape()

    @staticmethod
    def _key_of(button: Button) -> ButtonKey:
        return (tuple(button.rect), button.label, button.kind)

    def _term_link_at(self, pos: tuple[int, int]) -> TermLink | None:
        for link in self.term_links():
            if link.hit(pos):
                return link
        return None

    def _button_at(self, pos: tuple[int, int]) -> Button | None:
        for button in self.buttons():
            if button.enabled and button.hit(pos):
                return button
        return None
