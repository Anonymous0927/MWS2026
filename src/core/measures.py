from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .types import Money, Result, format_money
from .versions import LEVEL_NONE, VersionRules

STATE_OWNED = "owned"
STATE_SELECTED = "selected"
STATE_AVAILABLE = "available"
STATE_DISABLED = "disabled"
STATE_CANCELING = "canceling"

BADGE_LABELS = {
    STATE_OWNED: "導入ずみ",
    STATE_SELECTED: "選んでいる",
    STATE_AVAILABLE: "未導入",
    STATE_DISABLED: "未導入",
    STATE_CANCELING: "もどす",
}


@dataclass(frozen=True)
class Measure:

    id: str
    name: str
    formal_name: str
    cost: Money
    upkeep: Money
    recurring: bool
    summary: str
    weakness: str
    belongs_to: tuple[str, ...]
    axes: dict[str, int]
    versions: tuple[str, ...]
    glossary: tuple[str, ...]

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> Measure:
        return Measure(
            id=raw["id"],
            name=raw["name"],
            formal_name=raw["formal_name"],
            cost=raw["cost"],
            upkeep=raw.get("upkeep", 0),
            recurring=bool(raw.get("recurring", False)),
            summary=raw["summary"],
            weakness=raw["weakness"],
            belongs_to=tuple(raw.get("belongs_to", ())),
            axes=dict(raw.get("axes", {})),
            versions=tuple(raw.get("versions", ())),
            glossary=tuple(raw.get("glossary", ())),
        )

    def version_note(self, level: int) -> str:
        if 1 <= level <= len(self.versions):
            return self.versions[level - 1]
        return ""


@dataclass(frozen=True)
class MeasureView:

    measure: Measure
    state: str
    reason: str
    badge_label: str

    level: int = LEVEL_NONE
    level_name: str = "未導入"
    max_level: int = 3
    effect_rate: int = 0
    version_note: str = ""
    next_level: int = 0
    next_level_name: str = ""
    next_cost: Money = 0
    next_upkeep: Money = 0
    next_note: str = ""
    upkeep: Money = 0
    outdated: bool = False


class MeasureCatalog:

    def __init__(
        self,
        measures: list[Measure],
        star_thresholds: tuple[int, ...],
        unit: str = "man",
        versions: VersionRules | None = None,
    ) -> None:
        self._measures = list(measures)
        self._by_id = {measure.id: measure for measure in self._measures}
        self._star_thresholds = star_thresholds
        self._unit = unit
        self.versions = versions or VersionRules.single_level()

    @staticmethod
    def from_data(
        raw: dict[str, Any],
        star_thresholds: tuple[int, ...],
        unit: str = "man",
        versions: VersionRules | None = None,
    ) -> MeasureCatalog:
        measures = [Measure.from_dict(item) for item in raw["measures"]]
        return MeasureCatalog(measures, star_thresholds, unit, versions)

    def all(self) -> list[Measure]:
        return list(self._measures)

    def get(self, measure_id: str) -> Measure:
        return self._by_id[measure_id]

    def has(self, measure_id: str) -> bool:
        return measure_id in self._by_id


    def cost_of(self, measure_id: str, level: int) -> Money:
        return self.versions.cost_of(self._by_id[measure_id].cost, level)

    def upkeep_of(self, measure_id: str, level: int) -> Money:
        return self.versions.upkeep_of(self._by_id[measure_id].upkeep, level)

    def total_cost(self, plan: dict[str, int]) -> Money:
        return sum(self.cost_of(measure_id, level) for measure_id, level in plan.items())

    def total_upkeep(self, levels: dict[str, int]) -> Money:
        return sum(
            self.upkeep_of(measure_id, level)
            for measure_id, level in levels.items()
            if measure_id in self._by_id and level > LEVEL_NONE
        )


    def effect_rates(self, levels: dict[str, int], year: int) -> dict[str, int]:
        return {
            measure_id: self.versions.effect_rate(level, year)
            for measure_id, level in levels.items()
            if measure_id in self._by_id and level > LEVEL_NONE
        }

    def best_effect_rates(self, levels: dict[str, int], year: int) -> dict[str, int]:
        best = self.versions.unlocked_level(year)
        return {
            measure_id: self.versions.effect_rate(max(level, best), year)
            for measure_id, level in levels.items()
            if measure_id in self._by_id and level > LEVEL_NONE
        }

    def axes_of(self, levels: dict[str, int]) -> list[dict[str, int]]:
        result: list[dict[str, int]] = []
        for measure_id, level in levels.items():
            if measure_id not in self._by_id or level <= LEVEL_NONE:
                continue
            rate = self.versions.get(level).effect_rate
            measure = self._by_id[measure_id]
            result.append(
                {axis: value * rate // 100 for axis, value in measure.axes.items()}
            )
        return result


    def next_level_of(self, measure_id: str, levels: dict[str, int]) -> int:
        current = levels.get(measure_id, LEVEL_NONE)
        if current >= self.versions.max_level():
            return 0
        return current + 1

    def can_upgrade(
        self,
        measure_id: str,
        levels: dict[str, int],
        selected: dict[str, int],
        budget: Money,
        year: int = 1,
        slots_left: int = 99,
    ) -> Result:
        current = levels.get(measure_id, LEVEL_NONE)

        if measure_id in selected:
            return Result.failure("すでに選んでいます")

        target = current + 1
        if target > self.versions.max_level():
            return Result.failure("もういちばん上の ver です")

        lock_reason = self.versions.lock_reason(target, year)
        if lock_reason:
            return Result.failure(lock_reason)

        if len(selected) >= slots_left:
            return Result.failure("今年の工事はここまでです（来年またできます）")

        cost = self.cost_of(measure_id, target)
        remaining = budget - self.total_cost(selected)
        if remaining < cost:
            shortage = cost - remaining
            return Result.failure(f"お金が足りません（あと {format_money(shortage, self._unit)}）")

        return Result.success()

    def views(
        self,
        levels: dict[str, int],
        selected: dict[str, int],
        budget: Money,
        canceling: set[str] | None = None,
        year: int = 1,
        slots_left: int = 99,
    ) -> list[MeasureView]:
        canceling = canceling or set()
        views: list[MeasureView] = []

        for measure in self._measures:
            current = levels.get(measure.id, LEVEL_NONE)
            target = selected.get(measure.id) or self.next_level_of(measure.id, levels)

            if measure.id in canceling:
                state, reason = STATE_CANCELING, ""
            elif measure.id in selected:
                state, reason = STATE_SELECTED, ""
            else:
                result = self.can_upgrade(
                    measure.id, levels, selected, budget, year, slots_left
                )
                if result.ok:
                    state, reason = STATE_AVAILABLE, ""
                elif current > LEVEL_NONE:
                    state, reason = STATE_OWNED, result.message
                else:
                    state, reason = STATE_DISABLED, result.message

            next_level = self.next_level_of(measure.id, levels)
            views.append(
                MeasureView(
                    measure=measure,
                    state=state,
                    reason=reason,
                    badge_label=self._badge_label(state, current),
                    level=current,
                    level_name=self.versions.name_of(current),
                    max_level=self.versions.max_level(),
                    effect_rate=self.versions.effect_rate(current, year),
                    version_note=measure.version_note(current),
                    next_level=next_level,
                    next_level_name=self.versions.name_of(next_level) if next_level else "",
                    next_cost=self.cost_of(measure.id, next_level) if next_level else 0,
                    next_upkeep=self.upkeep_of(measure.id, next_level) if next_level else 0,
                    next_note=measure.version_note(next_level) if next_level else "",
                    upkeep=self.upkeep_of(measure.id, current),
                    outdated=self._is_outdated(current, year),
                )
            )
        return views

    def _badge_label(self, state: str, level: int) -> str:
        if state in (STATE_OWNED, STATE_SELECTED, STATE_CANCELING):
            return BADGE_LABELS[state] if level <= LEVEL_NONE else self.versions.name_of(level)
        if level > LEVEL_NONE:
            return self.versions.name_of(level)
        return BADGE_LABELS[state]

    def _is_outdated(self, level: int, year: int) -> bool:
        if level <= LEVEL_NONE:
            return False
        return level < self.versions.unlocked_level(year)


    def star(self, total_levels: int) -> int:
        star = 1
        for index, threshold in enumerate(self._star_thresholds):
            if total_levels >= threshold:
                star = index + 1
        return star

    def star_for(self, levels: dict[str, int]) -> int:
        return self.star(sum(max(0, level) for level in levels.values()))
