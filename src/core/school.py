from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .events import Event
from .measures import Measure, MeasureCatalog
from .types import Money
from .versions import VersionRules


@dataclass(frozen=True)
class SchoolTarget:

    id: str
    name: str
    note: str
    measures: tuple[str, ...]


@dataclass(frozen=True)
class SchoolSummary:

    spent: Money
    remaining: Money
    trust_start: int
    trust_end: int
    lessons: tuple[str, ...]
    bridge_text: str


class SchoolRun:

    def __init__(
        self,
        raw: dict[str, Any],
        star_thresholds: tuple[int, ...],
        versions: "VersionRules | None" = None,
    ) -> None:
        self._raw = raw
        self.turns: int = raw["turns"]
        self.budget_per_turn: Money = raw["budget_per_turn"]
        self.unit: str = raw.get("unit", "yen")
        self.trust_penalty_divisor: int = raw.get("rules", {}).get(
            "trust_penalty_divisor", 10
        )

        self.catalog = MeasureCatalog(
            [Measure.from_dict(item) for item in raw["measures"]],
            star_thresholds,
            unit=self.unit,
            versions=versions,
        )
        self._events_by_turn: dict[int, Event] = {
            item["turn"]: Event.from_dict(self._as_company_event(item))
            for item in raw["events"]
        }
        self.targets = tuple(
            SchoolTarget(
                id=item["id"],
                name=item["name"],
                note=item["note"],
                measures=tuple(item["measures"]),
            )
            for item in raw["targets"]
        )
        self.lessons = tuple(raw.get("lessons", ()))
        self.bridge_text = raw.get("bridge_text", "")

    @staticmethod
    def _as_company_event(raw: dict[str, Any]) -> dict[str, Any]:
        return {
            **raw,
            "weight": raw.get("weight", 10),
            "requires_facility": None,
        }

    def event_of(self, turn: int) -> Event:
        return self._events_by_turn[turn]

    def all_events(self) -> list[Event]:
        return [self._events_by_turn[turn] for turn in sorted(self._events_by_turn)]

    def target_views(self, owned: set[str]) -> list[SchoolTarget]:
        return list(self.targets)

    def summary(
        self, spent: Money, remaining: Money, trust_start: int, trust_end: int
    ) -> SchoolSummary:
        return SchoolSummary(
            spent=spent,
            remaining=remaining,
            trust_start=trust_start,
            trust_end=trust_end,
            lessons=self.lessons,
            bridge_text=self.bridge_text,
        )
