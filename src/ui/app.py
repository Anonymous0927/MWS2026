from __future__ import annotations

import random

import pygame

from core.game import GameSession, Phase

from . import theme, widgets
from .panels.confirm_modal import ConfirmModal
from .panels.glossary_modal import GlossaryModal
from .scene import Scene
from .scenes.incident import IncidentScene
from .scenes.main_view import MainViewScene
from .scenes.outcome import OutcomeScene
from .scenes.result import ResultScene
from .scenes.title import TitleScene

AUTO_CLICK_INTERVAL = 6

AUTO_FIRST_BUTTON_RATE = 0.3


class App:

    def __init__(
        self,
        session: GameSession,
        auto_play: bool = False,
        seed: int | None = None,
        total_years: int | None = None,
        class_mode: bool = False,
        max_frames: int = 60000,
        skip_school: bool = False,
    ) -> None:
        pygame.display.init()
        pygame.font.init()

        self.screen = pygame.display.set_mode((theme.SCREEN_W, theme.SCREEN_H))
        pygame.display.set_caption("Secure Company Simulator")
        self.clock = pygame.time.Clock()

        self.session = session
        self.total_years = total_years
        self.class_mode = class_mode
        self._start_seed = seed

        self.running = True
        self.exit_code = 0
        self.reached_result = False

        self.auto_play = auto_play
        self.max_frames = max_frames
        self.frames = 0
        self._auto_rng = random.Random(seed if seed is not None else 0)

        self.scene: Scene = (
            MainViewScene(self, session) if skip_school else TitleScene(self, session)
        )
        self.modal: Scene | None = None


    def run(self) -> int:
        while self.running:
            dt = self.clock.tick(0 if self.auto_play else theme.FPS) / 1000
            self.frames += 1

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit()
                    break
                target = self.modal or self.scene
                target.handle_event(event)

            if self.auto_play:
                self._auto_step()

            self.scene.update(dt)

            self.scene.draw(self.screen)
            if self.modal is not None:
                self.modal.draw(self.screen)
            pygame.display.flip()

        pygame.display.quit()
        return self.exit_code

    def quit(self) -> None:
        self.running = False


    def show_title(self) -> None:
        self.session = GameSession(seed=self._start_seed, total_years=self.total_years)
        self.scene = TitleScene(self, self.session)
        self.modal = None

    def start_game(self, seed: int | None, skip_school: bool) -> None:
        self._start_seed = seed
        if skip_school:
            self.session = GameSession(seed=seed, total_years=self.total_years)
        else:
            self.session = GameSession(seed=seed, school=True)
        self.scene = MainViewScene(self, self.session)
        self.modal = None

    def start_company_stage(self) -> None:
        seed = getattr(self, "_start_seed", None)
        self.session = GameSession(seed=seed, total_years=self.total_years)
        self.scene = MainViewScene(self, self.session)
        self.modal = None

    def show_main(self) -> None:
        self.scene = MainViewScene(self, self.session)

    def confirm_next_turn(self) -> None:
        state = self.session.state
        unit_label = "学期" if state.is_school else "年目"
        period_label = "この学期" if state.is_school else "この年"

        if self.session.selected() or self.session.canceling():
            lines = (
                "選んだ対策がまだ決定されていません。",
                "決定ボタンの押し忘れなどありませんか？",
            )
        elif not self.session.has_bought_measure_this_turn():
            lines = (
                f"{period_label}は、対策を1つも買っていません。",
                "決定ボタンの押し忘れなどありませんか？",
            )
        else:
            lines = (
                f"進むと事件が起きます。{period_label}の買い物は、もう変えられません。",
                "買い残しがないか、もう一度たしかめてください。",
            )

        self.modal = ConfirmModal(
            self,
            self.session,
            title=f"{state.year} {unit_label}を終えて、次に進みます",
            lines=lines,
            on_confirm=self.go_to_incident,
            confirm_label="進む",
            cancel_label="まだ買う",
        )

    def go_to_incident(self) -> None:
        self.session.draw_event()
        self.scene = IncidentScene(self, self.session)

    def show_outcome(self) -> None:
        self.scene = OutcomeScene(self, self.session)

    def finish_year(self) -> None:
        follow_up = self.session.draw_follow_up_event()
        if follow_up is not None:
            self.scene = IncidentScene(self, self.session)
            return

        report = self.session.close_year()

        if not report.finished:
            self.show_main()
            return

        if self.session.is_school:
            self.scene = MainViewScene(self, self.session, summary=True)
            return

        self.show_result()

    def show_result(self) -> None:
        self.reached_result = True
        self.scene = ResultScene(self, self.session)

    def go_back(self) -> None:
        if self.modal is not None:
            self.close_modal()
            return
        if self.session.phase is Phase.MANAGE:
            self.show_main()


    def open_glossary(self, term_id: str | None = None, related: list | None = None) -> None:
        self.modal = GlossaryModal(self, self.session, term_id=term_id, related=related)

    def close_modal(self) -> None:
        self.modal = None


    def _auto_step(self) -> None:
        if self.frames > self.max_frames:
            self.exit_code = 1
            self.running = False
            return

        if self.reached_result:
            if isinstance(self.scene, ResultScene) and not self.scene.saved_paths:
                self.scene._save()
            self.running = False
            return

        if self.frames % AUTO_CLICK_INTERVAL != 0:
            return

        if self.modal is not None:
            if isinstance(self.modal, ConfirmModal):
                clickable = [b for b in self.modal.buttons() if b.enabled]
                if clickable:
                    self._pick(clickable).click()
                return
            self.close_modal()
            return

        clickable = [button for button in self.scene.buttons() if button.enabled]
        if not clickable:
            return

        self._pick(clickable).click()

    def _pick(self, clickable: list) -> object:
        if isinstance(self.scene, IncidentScene):
            return clickable[0]

        if len(clickable) > 1 and self._auto_rng.random() < AUTO_FIRST_BUTTON_RATE:
            return self._auto_rng.choice(clickable[:-1])
        return clickable[-1]
