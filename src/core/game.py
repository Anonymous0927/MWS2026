from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field, replace
from pathlib import Path

from . import dataloader, report, timeline as timeline_module
from .actions import Action, ActionCatalog, ActionView
from .company import Company
from .defense import AxisScore, DefenseModel
from .config import Config, Expansion
from .events import Choice, ChoiceView, Event, EventDeck, human_error_weight_rate
from .glossary import Glossary, Term
from .measures import Measure, MeasureCatalog, MeasureView
from .resolver import Contribution, Outcome, resolve
from .school import SchoolRun, SchoolSummary
from .score import CLEAR_LABELS, FinalScore, evaluate
from .timeline import Timeline
from .versions import LEVEL_NONE, Level, VersionRules
from .types import (
    FacilityView,
    Money,
    Phase,
    PhaseError,
    Result,
    TimelineEntry,
    TurnLog,
    format_money,
)

__all__ = [
    "GameSession",
    "StateView",
    "Preview",
    "ExpansionView",
    "YearReport",
    "Phase",
    "PhaseError",
    "Result",
    "Money",
    "Measure",
    "MeasureView",
    "Event",
    "Choice",
    "ChoiceView",
    "Outcome",
    "Contribution",
    "FinalScore",
    "CLEAR_LABELS",
    "Action",
    "ActionView",
    "AxisScore",
    "Level",
    "LEVEL_NONE",
    "FacilityView",
    "TimelineEntry",
    "Term",
    "SchoolSummary",
    "format_money",
]


@dataclass(frozen=True)
class StateView:

    year: int
    total_years: int
    phase: Phase
    money: Money
    employees: int
    trust: int
    morale: int
    star: int
    owned_count: int
    total_damage: Money
    profit: Money
    seed: int
    is_school: bool
    unit: str
    bankrupt: bool
    awareness: int
    awareness_notes: tuple[str, ...]
    trust_notes: tuple[str, ...]
    upkeep: Money
    slots_left: int
    slots_per_year: int
    total_levels: int


@dataclass(frozen=True)
class Preview:

    budget: Money
    selected_cost: Money
    remaining: Money
    star_now: int
    star_after: int
    ratio: float
    upkeep_now: Money
    upkeep_after: Money
    refund: Money
    slots_left: int
    slots_after: int
    slots_per_year: int


@dataclass(frozen=True)
class ExpansionView:

    expansion: Expansion
    available: bool
    reason: str
    undoable: bool = False


@dataclass(frozen=True)
class YearReport:

    year: int
    profit: Money
    damage: Money
    money_after: Money
    bankrupt: bool
    finished: bool
    bonus_text: str = ""
    upkeep: Money = 0
    omen_text: str = ""


@dataclass
class _PendingPurchase:

    selected: dict[str, int] = field(default_factory=dict)
    canceling: set[str] = field(default_factory=set)


class GameSession:

    def __init__(
        self,
        seed: int | None = None,
        total_years: int | None = None,
        school: bool = False,
    ) -> None:
        self.seed = seed if seed is not None else int(time.time()) % 1_000_000
        self._rng = random.Random(self.seed)

        data = dataloader.load_all()
        self.config = Config.from_dict(data["config"], total_years)
        self.is_school = school

        self.versions = (
            VersionRules.single_level() if school else VersionRules.from_data(data["config"])
        )

        if school:
            self._school = SchoolRun(data["school"], (0, 1, 2, 3, 3), self.versions)
            self.catalog = self._school.catalog
            self.deck = EventDeck(self._school.all_events(), self.catalog)
            self.unit = self._school.unit
            self.total_years = self._school.turns
            self.config = replace(
                self.config,
                rules=replace(
                    self.config.rules,
                    trust_penalty_divisor=self._school.trust_penalty_divisor,
                ),
            )
            self.company = Company(
                money=self._school.budget_per_turn,
                employees=0,
                trust=self.config.initial_trust,
                morale=self.config.initial_morale,
                awareness=self.config.awareness.initial,
            )
        else:
            self._school = None
            self.catalog = MeasureCatalog.from_data(
                data["measures"], self.config.star_thresholds, unit="man",
                versions=self.versions,
            )
            self.deck = EventDeck.from_data(data["events"], self.catalog)
            self.unit = "man"
            self.total_years = self.config.total_years
            self.company = Company(
                money=self.config.initial_money,
                employees=self.config.initial_employees,
                trust=self.config.initial_trust,
                morale=self.config.initial_morale,
                awareness=self.config.awareness.initial,
            )

        self.actions = ActionCatalog.from_data(data["actions"], unit=self.unit)
        self.defense = DefenseModel.from_data(data["config"])

        self.glossary = Glossary.from_data(data["glossary"])
        self.timeline = Timeline()

        self.year = 1
        self.phase = Phase.MANAGE
        self.bankrupt = False

        self.levels: dict[str, int] = {}
        self.training_years: set[int] = set()
        self.facilities: set[str] = set()
        self.done_expansions: set[str] = set()
        self.purchase_log: dict[str, int] = {}
        self.skipped_log: dict[str, int] = {}
        self.logs: list[TurnLog] = []
        self.history: list[str] = []
        self.incident_history: list[str] = []

        self.slots_per_year = 999 if school else self.config.work_limit.per_year
        self._level_at_year_start: dict[str, int] = {}

        self.baseline = 0 if school else self.config.initial_defense.percent
        self.baseline_axis_points = 0 if school else self.config.initial_defense.axis_points
        self.baseline_name = self.config.initial_defense.name

        self.actions_done: set[str] = set()
        self._year_action_ids: list[str] = []
        self._year_expansion_ids: list[str] = []
        self.omen_event_id: str | None = None
        self.omen_text = ""
        self.omen_year: int | None = None

        self._pending = _PendingPurchase()
        self._current_event: Event | None = None
        self._choice_order: tuple[str, ...] = ()
        self._last_outcome: Outcome | None = None
        self._year_outcomes: list[Outcome] = []
        self._follow_up_checked = False
        self._last_message = ""
        self._trust_at_start = self.company.trust
        self._spent_total: Money = 0

        self._year_budget: Money = self.company.money
        self._year_bought: list[str] = []
        self._year_spent: Money = 0
        self._year_expansions: list[str] = []
        self._year_actions: list[str] = []

        self._begin_year(first=True)

        self._draw_omen()


    @property
    def is_over(self) -> bool:
        return self.phase is Phase.FINISHED

    @property
    def owned(self) -> set[str]:
        return {measure_id for measure_id, level in self.levels.items() if level > LEVEL_NONE}

    @property
    def total_levels(self) -> int:
        return sum(max(0, level) for level in self.levels.values())

    @property
    def star(self) -> int:
        return self.catalog.star_for(self.active_levels())

    @property
    def last_message(self) -> str:
        return self._last_message

    def active_levels(self) -> dict[str, int]:
        active: dict[str, int] = {}
        for measure_id, level in self.levels.items():
            if level <= LEVEL_NONE:
                continue
            measure = self.catalog.get(measure_id)
            if measure.recurring and self.year not in self.training_years:
                continue
            active[measure_id] = level
        return active

    def active_measures(self) -> set[str]:
        return set(self.active_levels())

    def effect_rates(self) -> dict[str, int]:
        return self.catalog.effect_rates(self.active_levels(), self.year)

    def best_effect_rates(self) -> dict[str, int]:
        return self.catalog.best_effect_rates(self.active_levels(), self.year)

    def level_of(self, measure_id: str) -> int:
        return self.levels.get(measure_id, LEVEL_NONE)

    def outdated_count(self) -> int:
        unlocked = self.versions.unlocked_level(self.year)
        return sum(1 for level in self.levels.values() if LEVEL_NONE < level < unlocked)

    def slots_used(self, levels: dict[str, int] | None = None) -> int:
        levels = self.levels if levels is None else levels
        return sum(
            max(0, level - self._level_at_year_start.get(measure_id, LEVEL_NONE))
            for measure_id, level in levels.items()
        )

    def slots_left(self) -> int:
        return max(0, self._slots_before_pending() - len(self._pending.selected))

    def _slots_before_pending(self) -> int:
        planned = dict(self.levels)
        for measure_id in self._pending.canceling:
            planned[measure_id] = max(LEVEL_NONE, planned.get(measure_id, LEVEL_NONE) - 1)
        return max(0, self.slots_per_year - self.slots_used(planned))

    @property
    def state(self) -> StateView:
        return StateView(
            year=self.year,
            total_years=self.total_years,
            phase=self.phase,
            money=self.company.money,
            employees=self.company.employees,
            trust=self.company.trust,
            morale=self.company.morale,
            star=self.star,
            owned_count=len(self.active_measures()),
            total_damage=self.company.total_damage,
            profit=self.company.profit(self.config.profit_per_employee),
            seed=self.seed,
            is_school=self.is_school,
            unit=self.unit,
            bankrupt=self.bankrupt,
            awareness=self.company.awareness,
            awareness_notes=self.awareness_notes(),
            trust_notes=self.trust_notes(),
            upkeep=self.total_upkeep(),
            slots_left=self.slots_left(),
            slots_per_year=self.slots_per_year,
            total_levels=self.total_levels,
        )

    def total_upkeep(self) -> Money:
        return self.catalog.total_upkeep(self.levels)

    def defense_scores(self) -> list[AxisScore]:
        return self.defense.scores(
            measure_axes=self.catalog.axes_of(self.levels),
            action_axes=self.actions.combined_axes(self.actions_done),
            baseline=self.baseline_axis_points,
        )

    def planned_defense_scores(self) -> list[AxisScore]:
        return self.defense.scores(
            measure_axes=self.catalog.axes_of(self.planned_levels()),
            action_axes=self.actions.combined_axes(self.actions_done),
            baseline=self.baseline_axis_points,
        )

    def planned_levels(self) -> dict[str, int]:
        planned = dict(self.levels)
        planned.update(self._pending.selected)
        for measure_id in self._pending.canceling:
            planned[measure_id] = max(LEVEL_NONE, planned.get(measure_id, LEVEL_NONE) - 1)
        return {mid: level for mid, level in planned.items() if level > LEVEL_NONE}

    def timeline_entries(self, limit: int | None = None) -> list[TimelineEntry]:
        return self.timeline.recent(limit)

    def company_view(self) -> list[FacilityView]:
        active = self.active_measures()
        views: list[FacilityView] = []

        if self.is_school and self._school is not None:
            for target in self._school.targets:
                missing = tuple(
                    self.catalog.get(measure_id).name
                    for measure_id in target.measures
                    if measure_id not in active
                )
                views.append(self._facility_view(target.id, target.name, target.note, missing))
            return views

        for facility in self.config.facilities:
            if not facility.always and facility.id not in self.facilities:
                continue
            missing = tuple(
                measure.name
                for measure in self.catalog.all()
                if facility.id in measure.belongs_to and measure.id not in active
            )
            views.append(self._facility_view(facility.id, facility.name, facility.note, missing))
        return views

    @staticmethod
    def _facility_view(
        facility_id: str, name: str, note: str, missing: tuple[str, ...]
    ) -> FacilityView:
        if not missing:
            return FacilityView(facility_id, name, note, "ok", "守れている", ())
        if len(missing) == 1:
            return FacilityView(facility_id, name, note, "warn", "注意", missing)
        return FacilityView(facility_id, name, note, "ng", "守れていない", missing)


    def catalog_views(self) -> list[MeasureView]:
        return self.catalog.views(
            self.levels,
            self._pending.selected,
            self.company.money,
            self._pending.canceling,
            year=self.year,
            slots_left=self._slots_before_pending(),
        )

    def select(self, measure_id: str) -> Result:
        if self.phase is not Phase.MANAGE:
            return Result.failure("いまは対策を買えません")

        result = self.catalog.can_upgrade(
            measure_id,
            self.levels,
            self._pending.selected,
            self.company.money,
            year=self.year,
            slots_left=self._slots_before_pending(),
        )
        if not result.ok:
            self._last_message = result.message
            return result

        target = self.catalog.next_level_of(measure_id, self.levels)
        self._pending.selected[measure_id] = target
        name = self.catalog.get(measure_id).name
        self._last_message = f"「{name}」を {self.versions.name_of(target)} にします"
        return Result.success(self._last_message)

    def unselect(self, measure_id: str) -> Result:
        if self.phase is not Phase.MANAGE:
            return Result.failure("いまは対策を買えません")
        if measure_id not in self._pending.selected:
            return Result.failure("選んでいません")

        self._pending.selected.pop(measure_id)
        self._last_message = f"「{self.catalog.get(measure_id).name}」の選択をやめました"
        return Result.success(self._last_message)

    def selected(self) -> dict[str, int]:
        return dict(self._pending.selected)

    def canceling(self) -> set[str]:
        return set(self._pending.canceling)

    def has_bought_measure_this_turn(self) -> bool:
        return bool(self._year_bought)

    def cancel(self, measure_id: str) -> Result:
        if self.phase is not Phase.MANAGE:
            return Result.failure("いまは対策を解除できません")
        if self.levels.get(measure_id, LEVEL_NONE) <= LEVEL_NONE:
            return Result.failure("導入していません")
        if measure_id in self._pending.canceling:
            return Result.failure("すでにもどそうとしています")

        self._pending.canceling.add(measure_id)
        name = self.catalog.get(measure_id).name
        after = self.versions.name_of(self.levels[measure_id] - 1)
        self._last_message = f"「{name}」を {after} にもどします（決定を押すと確定します）"
        return Result.success(self._last_message)

    def uncancel(self, measure_id: str) -> Result:
        if measure_id not in self._pending.canceling:
            return Result.failure("もどそうとしていません")
        self._pending.canceling.discard(measure_id)
        return Result.success()

    def refund_for(self, measure_id: str) -> Money:
        current = self.levels.get(measure_id, LEVEL_NONE)
        if current <= LEVEL_NONE:
            return 0
        if current > self._level_at_year_start.get(measure_id, LEVEL_NONE):
            return self.catalog.cost_of(measure_id, current)
        return 0

    def preview(self) -> Preview:
        selected_cost = self.catalog.total_cost(self._pending.selected)
        refund = sum(self.refund_for(measure_id) for measure_id in self._pending.canceling)
        net_cost = selected_cost - refund

        planned = self.planned_levels()
        active_after = dict(self.active_levels())
        active_after.update(self._pending.selected)
        for measure_id in self._pending.canceling:
            active_after[measure_id] = max(LEVEL_NONE, active_after.get(measure_id, 0) - 1)

        budget = self.company.money
        slots_left = self._slots_before_pending()

        return Preview(
            budget=budget,
            selected_cost=selected_cost,
            remaining=budget - net_cost,
            star_now=self.star,
            star_after=self.catalog.star_for(active_after),
            ratio=(net_cost / budget) if budget > 0 else 0.0,
            upkeep_now=self.total_upkeep(),
            upkeep_after=self.catalog.total_upkeep(planned),
            refund=refund,
            slots_left=slots_left,
            slots_after=max(0, slots_left - len(self._pending.selected)),
            slots_per_year=self.slots_per_year,
        )

    def commit(self) -> Result:
        if self.phase is not Phase.MANAGE:
            return Result.failure("いまは対策を買えません")

        selected = dict(self._pending.selected)
        canceling = set(self._pending.canceling)

        if not selected and not canceling:
            self._last_message = "今回は何も買いませんでした"
            return Result.success(self._last_message)

        cancelled_names = self._apply_cancellations(canceling)

        bought_names: list[str] = []
        if selected:
            cost = self.catalog.total_cost(selected)
            self.company.spend(cost)
            self._year_spent += cost
            self._spent_total += cost

            for measure_id, target in sorted(selected.items()):
                measure = self.catalog.get(measure_id)
                was_new = self.levels.get(measure_id, LEVEL_NONE) <= LEVEL_NONE
                self.levels[measure_id] = target
                if was_new:
                    self.purchase_log.setdefault(measure_id, self.year)
                self.skipped_log.pop(measure_id, None)
                if measure.recurring:
                    self.training_years.add(self.year)

                label = f"{measure.name}（{self.versions.name_of(target)}）"
                bought_names.append(label)
                self._year_bought.append(label)

                self.timeline.add(
                    self.year,
                    timeline_module.KIND_INSTALL if was_new else timeline_module.KIND_UPGRADE,
                    f"{measure.name} を {self.versions.name_of(target)} にしました"
                    f"（{format_money(self.catalog.cost_of(measure_id, target), self.unit)}"
                    f"／年間維持費 "
                    f"{format_money(self.catalog.upkeep_of(measure_id, target), self.unit)}）"
                    + (f" ― {measure.version_note(target)}" if measure.version_note(target) else ""),
                )

        self._pending.selected.clear()
        self._pending.canceling.clear()

        parts = []
        if bought_names:
            parts.append(f"{'／'.join(bought_names)}にしました")
        if cancelled_names:
            parts.append(f"{'／'.join(cancelled_names)}にもどしました")
        self._last_message = "。".join(parts)
        return Result.success(self._last_message)

    def _apply_cancellations(self, canceling: set[str]) -> list[str]:
        names: list[str] = []
        for measure_id in sorted(canceling):
            current = self.levels.get(measure_id, LEVEL_NONE)
            if current <= LEVEL_NONE:
                continue
            measure = self.catalog.get(measure_id)
            refund = self.refund_for(measure_id)
            after = current - 1

            if after <= LEVEL_NONE:
                self.levels.pop(measure_id, None)
                self.purchase_log.pop(measure_id, None)
            else:
                self.levels[measure_id] = after

            if refund:
                self.company.earn(refund)
                self._year_spent -= refund
                self._spent_total -= refund
                label = f"{measure.name}（{self.versions.name_of(current)}）"
                if label in self._year_bought:
                    self._year_bought.remove(label)

            names.append(f"{measure.name}（{self.versions.name_of(after)}）")
            refund_text = (
                f"{format_money(refund, self.unit)} が戻りました"
                if refund else "返金はありません（維持費だけ下がります）"
            )
            self.timeline.add(
                self.year,
                timeline_module.KIND_CANCEL,
                f"{measure.name} を {self.versions.name_of(after)} にもどしました。{refund_text}",
            )
        return names


    def action_views(self) -> list[ActionView]:
        return self.actions.views(
            self.actions_done, self.company.money, self.company.employees
        )

    def do_action(self, action_id: str) -> Result:
        if self.phase is not Phase.MANAGE:
            return Result.failure("いまは施策を実施できません")
        if self.is_school:
            return Result.failure("学校編では施策を実施できません")

        result = self.actions.can_do(
            action_id, self.actions_done, self.company.money, self.company.employees
        )
        if not result.ok:
            self._last_message = result.message
            return result

        action = self.actions.get(action_id)
        cost = action.cost_for(self.company.employees)

        self.company.spend(cost)
        self.company.add_awareness(action.awareness)
        self.actions_done.add(action_id)
        self._year_spent += cost
        self._spent_total += cost
        self._year_actions.append(action.name)
        self._year_action_ids.append(action_id)

        self.timeline.add(
            self.year,
            timeline_module.KIND_ACTION,
            f"{action.name} を実施しました（{format_money(cost, self.unit)}／"
            f"意識 +{action.awareness}）",
        )
        self._last_message = f"{action.name} を実施しました"
        return Result.success(self._last_message)

    def undo_action(self, action_id: str) -> Result:
        if self.phase is not Phase.MANAGE:
            return Result.failure("いまは施策を取り消せません")
        if action_id not in self._year_action_ids:
            return Result.failure("今年実施した施策ではありません")

        action = self.actions.get(action_id)
        cost = action.cost_for(self.company.employees)

        self.company.earn(cost)
        self.company.add_awareness(-action.awareness)
        self.actions_done.discard(action_id)
        self._year_action_ids.remove(action_id)
        self._year_spent -= cost
        self._spent_total -= cost
        if action.name in self._year_actions:
            self._year_actions.remove(action.name)

        self.timeline.add(
            self.year,
            timeline_module.KIND_UNDO,
            f"{action.name} を取り消しました（{format_money(cost, self.unit)} が戻りました）",
        )
        self._last_message = f"{action.name} を取り消しました"
        return Result.success(self._last_message)


    def expansions(self) -> list[ExpansionView]:
        views: list[ExpansionView] = []
        for expansion in self.config.expansions:
            if expansion.id in self._year_expansion_ids:
                views.append(
                    ExpansionView(expansion, False, "今年実行しました（押すと取り消せます）",
                                  undoable=True)
                )
            elif expansion.id in self.done_expansions:
                views.append(ExpansionView(expansion, False, "もう実行しました"))
            elif self.company.money < expansion.cost:
                shortage = expansion.cost - self.company.money
                views.append(
                    ExpansionView(
                        expansion, False, f"お金が足りません（あと {format_money(shortage, self.unit)}）"
                    )
                )
            else:
                views.append(ExpansionView(expansion, True, ""))
        return views

    def expand(self, expansion_id: str) -> Result:
        if self.phase is not Phase.MANAGE:
            return Result.failure("いまは会社を大きくできません")
        if self.is_school:
            return Result.failure("学校編では会社を大きくできません")

        for view in self.expansions():
            if view.expansion.id != expansion_id:
                continue
            if not view.available:
                self._last_message = view.reason
                return Result.failure(view.reason)

            expansion = view.expansion
            self.company.spend(expansion.cost)
            self.company.add_employees(expansion.employees)
            self.company.add_morale(expansion.morale)
            self.done_expansions.add(expansion.id)
            self._year_spent += expansion.cost
            self._spent_total += expansion.cost
            self._year_expansions.append(expansion.name)
            self._year_expansion_ids.append(expansion.id)

            if expansion.facility:
                self.facilities.add(expansion.facility)

            text = f"{expansion.name}（{format_money(expansion.cost, self.unit)}）"
            if expansion.unlocks:
                text += f" ― これから「{expansion.unlocks}」が起こりえます"
            self.timeline.add(self.year, timeline_module.KIND_EXPAND, text)
            self._last_message = f"{expansion.name}を実行しました"
            return Result.success(self._last_message)

        return Result.failure("その行動はありません")

    def undo_expansion(self, expansion_id: str) -> Result:
        if self.phase is not Phase.MANAGE:
            return Result.failure("いまは取り消せません")
        if expansion_id not in self._year_expansion_ids:
            return Result.failure("今年実行した行動ではありません")

        expansion = next(
            item for item in self.config.expansions if item.id == expansion_id
        )

        self.company.earn(expansion.cost)
        self.company.add_employees(-expansion.employees)
        self.company.add_morale(-expansion.morale)
        self.done_expansions.discard(expansion_id)
        self._year_expansion_ids.remove(expansion_id)
        self._year_spent -= expansion.cost
        self._spent_total -= expansion.cost
        if expansion.name in self._year_expansions:
            self._year_expansions.remove(expansion.name)
        if expansion.facility:
            self.facilities.discard(expansion.facility)

        self.timeline.add(
            self.year,
            timeline_module.KIND_UNDO,
            f"{expansion.name} を取り消しました"
            f"（{format_money(expansion.cost, self.unit)} が戻りました）",
        )
        self._last_message = f"{expansion.name}を取り消しました"
        return Result.success(self._last_message)


    def draw_event(self) -> Event:
        if self.phase is not Phase.MANAGE:
            raise PhaseError(f"経営フェーズではありません（いまは {self.phase.value}）")

        self._record_skipped()

        if self.is_school and self._school is not None:
            event = self._school.event_of(self.year)
        else:
            if self.omen_event_id is not None:
                event = self.deck.get(self.omen_event_id)
            else:
                last_event_id = self.incident_history[-1] if self.incident_history else None
                event = self._draw_random_event(last_event_id)

        self._year_outcomes.clear()
        self._follow_up_checked = False
        self._set_current_event(event)
        return event

    def _draw_random_event(self, last_event_id: str | None) -> Event:
        return self.deck.draw(
            self._rng,
            last_event_id,
            self.facilities,
            awareness=self.company.awareness,
            awareness_factor=self.config.awareness.weight_factor,
            action_factors={
                event_id: self.actions.event_weight_factor(self.actions_done, event_id)
                for event_id in (item.id for item in self.deck.all())
            },
        )

    def _set_current_event(self, event: Event) -> None:
        self._current_event = event
        choice_ids = [choice.id for choice in event.choices]
        self._rng.shuffle(choice_ids)
        self._choice_order = tuple(choice_ids)
        self.phase = Phase.INCIDENT

    def draw_follow_up_event(self) -> Event | None:
        if self.phase is not Phase.OUTCOME or self._last_outcome is None:
            raise PhaseError("結果表示中ではありません")
        if (
            self.is_school
            or self.year < self.config.omen.follow_up_start_year
            or self._follow_up_checked
            or len(self._year_outcomes) != 1
        ):
            return None

        self._follow_up_checked = True
        one_in = self.config.omen.follow_up_one_in
        if one_in < 1 or self._rng.randint(1, one_in) != 1:
            return None

        event = self._draw_random_event(self._last_outcome.event.id)
        self._set_current_event(event)
        return event

    def _record_skipped(self) -> None:
        for measure in self.catalog.all():
            if measure.id in self.owned:
                continue
            if self.catalog.cost_of(measure.id, 1) <= self.company.money:
                self.skipped_log.setdefault(measure.id, self.year)

    def current_event(self) -> Event | None:
        return self._current_event

    def available_options(self) -> list[ChoiceView]:
        if self.phase is not Phase.INCIDENT or self._current_event is None:
            raise PhaseError("いまは選択肢を出せません")
        views = self.deck.choice_views(
            self._current_event, self.active_measures(), self.skipped_log, self.year
        )
        by_id = {view.choice.id: view for view in views}
        return [by_id[choice_id] for choice_id in self._choice_order]

    def choose(self, choice_id: str) -> Outcome:
        if self.phase is not Phase.INCIDENT or self._current_event is None:
            raise PhaseError("いまは選択肢を選べません")

        for view in self.available_options():
            if view.choice.id != choice_id:
                continue
            if not view.selectable:
                raise PhaseError(f"選べない選択肢です: {view.reason}")

            outcome = resolve(
                event=self._current_event,
                choice=view.choice,
                active=self.active_measures(),
                catalog=self.catalog,
                cap=self.config.mitigation_cap,
                rules=self.config.rules,
                unit=self.unit,
                baseline=self.baseline,
                scales=self.effect_rates(),
                upgraded_scales=self.best_effect_rates(),
            )
            self._last_outcome = outcome
            self._year_outcomes.append(outcome)
            self.phase = Phase.OUTCOME
            return outcome

        raise PhaseError(f"その選択肢はありません: {choice_id}")

    def last_outcome(self) -> Outcome | None:
        return self._last_outcome


    def close_year(self) -> YearReport:
        if self.phase is not Phase.OUTCOME or self._last_outcome is None:
            raise PhaseError("いまは決算できません")

        outcomes = tuple(self._year_outcomes) or (self._last_outcome,)
        outcome = outcomes[0]
        event = outcome.event

        trust_before = self.company.trust
        morale_before = self.company.morale
        star_before = self.star

        for item in outcomes:
            self.company.take_damage(item.damage)
            self.company.add_trust(item.trust_delta)
            if not self.is_school:
                self.company.add_morale(item.morale_delta)

        bonus_text = ""
        if not self.is_school and outcome.damage == 0 and event.base_damage == 0:
            if self._rng.randint(1, self.config.bonus.one_in) == 1:
                self.company.earn(self.config.bonus.money)
                self.company.add_trust(self.config.bonus.trust)
                bonus_text = self.config.bonus.text
                self.timeline.add(self.year, timeline_module.KIND_PREVENTED, bonus_text)

        for item in outcomes:
            self._record_event_in_timeline(item)

        self.history.append(event.id)
        self.incident_history.extend(item.event.id for item in outcomes)
        self.logs.append(
            TurnLog(
                year=self.year,
                event=event,
                choice=outcome.choice,
                outcome=outcome,
                owned=frozenset(self.active_measures()),
                levels=dict(self.active_levels()),
                best_rate=self.versions.effect_rate(
                    self.versions.unlocked_level(self.year), self.year
                ),
                bought=tuple(self._year_bought),
                spent=self._year_spent,
                budget=self._year_budget,
                money_after=self.company.money,
                trust_before=trust_before,
                trust_after=self.company.trust,
                morale_before=morale_before,
                morale_after=self.company.morale,
                star_before=star_before,
                star_after=self.star,
                expansions=tuple(self._year_expansions),
                bonus_text=bonus_text,
                additional_outcomes=outcomes[1:],
            )
        )

        self.timeline.add(
            self.year,
            timeline_module.KIND_SETTLE,
            f"{self.year} 年目の決算：年末の残り {format_money(self.company.money, self.unit)}",
        )

        if not self.is_school and self.company.money < 0:
            self.bankrupt = True

        omen_text = self._draw_omen()

        finished = self.bankrupt or self.year >= self.total_years
        report_ = YearReport(
            year=self.year,
            profit=self.company.profit(self.config.profit_per_employee),
            damage=sum(item.damage for item in outcomes),
            money_after=self.company.money,
            bankrupt=self.bankrupt,
            finished=finished,
            bonus_text=bonus_text,
            upkeep=self.total_upkeep(),
            omen_text=omen_text,
        )

        if finished:
            self.phase = Phase.FINISHED
        else:
            self.year += 1
            self.phase = Phase.MANAGE
            self._begin_year()

        self._current_event = None
        self._choice_order = ()
        self._year_outcomes.clear()
        return report_

    def _draw_omen(self) -> str:
        self.omen_event_id = None
        self.omen_text = ""
        self.omen_year = None

        if self.is_school:
            return ""

        candidates = self.deck.omen_candidates(self.facilities)
        if not candidates or self._rng.randint(1, self.config.omen.one_in) != 1:
            return ""

        event = self._rng.choice(candidates)
        self.omen_event_id = event.id
        self.omen_text = event.omen
        self.omen_year = self.year
        self.timeline.add(self.year, timeline_module.KIND_OMEN, f"前兆：{event.omen}")
        return event.omen

    def omen_notice(self) -> str:
        event = self._current_event
        if event is not None and len(self._year_outcomes) == 1:
            return "予告のない別の事件も続けて起きました"
        if event is None or self.omen_event_id != event.id:
            return ""
        if self.omen_year is not None and self.omen_year < self.year:
            return "前の年に前兆が出ていました"
        return "今年のはじめに前兆が出ていました"

    def _record_event_in_timeline(self, outcome: Outcome) -> None:
        event = outcome.event
        if outcome.damage == 0:
            kind = timeline_module.KIND_PREVENTED
            text = f"{event.name}：被害はありませんでした"
        elif outcome.effect_total >= 50:
            kind = timeline_module.KIND_WARN
            text = (
                f"{event.name}：効きめ {outcome.effect_total}% で "
                f"{format_money(outcome.damage, self.unit)} におさえました"
            )
        else:
            kind = timeline_module.KIND_DANGER
            text = f"{event.name}：{format_money(outcome.damage, self.unit)} の被害"

        self.timeline.add(self.year, kind, text)

        if outcome.damage > 0:
            self.timeline.add(
                self.year,
                timeline_module.KIND_DAMAGE,
                f"被害額 {format_money(outcome.damage, self.unit)}（{outcome.formula_text}）",
            )

        if outcome.upgrade_note:
            self.timeline.add(self.year, timeline_module.KIND_UPGRADE, outcome.upgrade_note)

    def _begin_year(self, first: bool = False) -> None:
        self._year_bought = []
        self._year_spent = 0
        self._year_expansions = []
        self._year_actions = []
        self._year_action_ids = []
        self._year_expansion_ids = []
        self._level_at_year_start = dict(self.levels)

        if not first and not self.is_school:
            self.actions_done.clear()
            self.company.add_awareness(-self.config.awareness.decay)

        if self.is_school:
            if not first and self._school is not None:
                self.company.earn(self._school.budget_per_turn)
        else:
            self.company.earn(self.company.profit(self.config.profit_per_employee))

            upkeep = self.total_upkeep()
            if upkeep:
                self.company.spend(upkeep)
                self.timeline.add(
                    self.year,
                    timeline_module.KIND_UPKEEP,
                    f"年間維持費 {format_money(upkeep, self.unit)} を払いました",
                )

        self._year_budget = self.company.money


    def final_score(self) -> FinalScore:
        if self.phase is not Phase.FINISHED:
            raise PhaseError("まだ終わっていません")
        return evaluate(
            company=self.company,
            star=self.star,
            logs=self.logs,
            config=self.config,
            bankrupt=self.bankrupt,
            years_played=len(self.logs),
            unit=self.unit,
            measure_names={m.id: m.name for m in self.catalog.all()},
        )

    def school_summary(self) -> SchoolSummary:
        if self._school is None:
            raise PhaseError("学校編ではありません")
        return self._school.summary(
            spent=self._spent_total,
            remaining=self.company.money,
            trust_start=self._trust_at_start,
            trust_end=self.company.trust,
        )

    def save_report(self, out_dir: Path | str = "output") -> tuple[Path, Path]:
        return report.write(self, Path(out_dir))


    def glossary_terms(self) -> list[Term]:
        return self.glossary.all()

    def glossary_for(self, kind: str, target_id: str) -> list[Term]:
        if kind == "measure":
            return self.glossary.for_measure(target_id)
        return self.glossary.for_event(target_id)

    def glossary_search(self, query: str) -> list[Term]:
        return self.glossary.search(query)

    def term_label(self, term_id: str) -> str:
        if not self.glossary.has(term_id):
            return ""
        return self.glossary.get(term_id).easy

    def name_of(self, target_id: str) -> str:
        if self.catalog.has(target_id):
            return self.catalog.get(target_id).name
        try:
            return self.deck.get(target_id).name
        except KeyError:
            return ""


    def warning(self) -> tuple[str, str]:
        if self.company.money < 0:
            return ("ng", "⚠ お金がマイナスです。このままでは決算で倒産します。")

        if self.omen_text:
            return ("warn", f"⚠ 前兆：{self.omen_text}")

        if not self.is_school:
            upkeep = self.total_upkeep()
            profit = self.company.profit(self.config.profit_per_employee)
            if upkeep > profit:
                return (
                    "warn",
                    f"⚠ 年間維持費 {format_money(upkeep, self.unit)} が、"
                    f"1 年のもうけ {format_money(profit, self.unit)} を超えています。",
                )

            outdated = self.outdated_count()
            if outdated:
                return (
                    "warn",
                    f"⚠ 古い ver のままの守りが {outdated} つあります。"
                    "年が進むほど効きめは落ちます。",
                )


        return ("info", self._last_message)

    def awareness_notes(self) -> tuple[str, ...]:
        if self.is_school:
            return ()

        awareness = self.company.awareness
        factor = self.config.awareness.weight_factor
        now = round(human_error_weight_rate(awareness, factor) * 100)
        best = round(human_error_weight_rate(100, factor) * 100)

        return (
            "社員のミスから始まる事件（偽メール・拾った USB・設定ミスなど）が、"
            "起きにくくなります。",
            f"いまの意識 {awareness} だと、その起きやすさは {now} %です"
            f"（意識 0 のときを 100 %として）。",
            f"意識 100 まで上げると {best} %まで下がります。ただし 0 にはなりません。",
            f"意識は毎年 {self.config.awareness.decay} 下がります。"
            "研修や監査を続けないと、効きめは薄れていきます。",
        )

    def trust_notes(self) -> tuple[str, ...]:
        if self.is_school:
            return ()

        rules = self.config.rules
        per_employee = self.config.profit_per_employee

        full_trust = self.company.snapshot()
        full_trust.trust = 100
        profit_now = format_money(self.company.profit(per_employee), self.unit)
        profit_full = format_money(full_trust.profit(per_employee), self.unit)

        formula = "1 年のもうけは 社員数 × 単価 × 信用度 ÷ 100 です。"
        if self.company.trust < 100:
            profit_line = (
                f"{formula}いまの信用度 {self.company.trust} でのもうけは {profit_now}。"
                f"信用度が 100 まで戻れば {profit_full} になります。"
            )
        else:
            profit_line = f"{formula}信用度 100 のいまは、もうけも上限の {profit_now} です。"

        return (
            "お客さんや取引先からの評判です。事件を起こすと下がり、"
            "きちんと対応した年に少しずつ戻ります。",
            profit_line,
            f"被害が {format_money(rules.trust_penalty_divisor, self.unit)} 出るごとに 1 下がります。"
            f"世間に知られる事件では、さらに {rules.public_penalty} 下がります。",
            f"上げるには、被害を 0 でしのぐことです（その年は +{rules.trust_recovery_no_damage}）。"
            "事件のときに、手順どおり・正直に対応する選び方でも上がります。"
            "隠す、後回しにする選び方は大きく下げます。",
            f"クリアには、最後に {self.config.clear.min_trust} 以上が必要です。",
        )

    def hint(self) -> tuple[str, str]:
        second_line = "どの対策で埋めるかは、いくつも道があります。正解は 1 つではありません。"

        if self.is_school:
            return ("ヒント：0 円でできる対策から試してみましょう。", second_line)

        weakest = self.defense.weakest(self.defense_scores())
        if weakest is None:
            return ("ヒント：予算と相談しながら選びましょう。", second_line)

        if self.outdated_count():
            return (
                "ヒント：古い ver の守りは、年が進むほど効きめが落ちていきます。",
                "新しく導入するか、いまあるものを上げるか。正解は 1 つではありません。",
            )

        upkeep = self.total_upkeep()
        if upkeep > self.company.profit(self.config.profit_per_employee):
            return (
                f"ヒント：年間維持費 {format_money(upkeep, self.unit)} が、"
                f"1 年のもうけを超えています。",
                "使っていない対策をやめるのも、立派な判断です。正解は 1 つではありません。",
            )

        return (
            f"ヒント：いま手薄なのは「{weakest.axis.name}」です"
            f"（{weakest.value} / 100）。",
            second_line,
        )
