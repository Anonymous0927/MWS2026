from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from .measures import MeasureCatalog
from .types import Money


def human_error_weight_rate(awareness: int, awareness_factor: float) -> float:
    return 1.0 - (1.0 - awareness_factor) * (max(0, awareness) / 100)


@dataclass(frozen=True)
class Choice:

    id: str
    label: str
    requires: str | None
    extra_cost: Money
    damage_scale: float
    downtime_days: int
    trust_delta: int
    result_text: str
    risky: bool = False

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> Choice:
        return Choice(
            id=raw["id"],
            label=raw["label"],
            requires=raw.get("requires"),
            extra_cost=raw.get("extra_cost", 0),
            damage_scale=float(raw.get("damage_scale", 1.0)),
            downtime_days=raw.get("downtime_days", 0),
            trust_delta=raw.get("trust_delta", 0),
            result_text=raw["result_text"],
            risky=bool(raw.get("risky", False)),
        )


@dataclass(frozen=True)
class NoEffectNote:

    measure_id: str
    reason: str


@dataclass(frozen=True)
class Event:

    id: str
    name: str
    base_damage: Money
    weight: int
    public: bool
    requires_facility: str | None
    situation: tuple[str, ...]
    mitigations: dict[str, int]
    human_error: bool
    axes: tuple[str, ...]
    omen: str
    learning: str
    no_effect: tuple[NoEffectNote, ...]
    glossary: tuple[str, ...]
    choices: tuple[Choice, ...]

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> Event:
        return Event(
            id=raw["id"],
            name=raw["name"],
            base_damage=raw["base_damage"],
            weight=raw.get("weight", 10),
            public=bool(raw.get("public", False)),
            requires_facility=raw.get("requires_facility"),
            situation=tuple(raw["situation"]),
            mitigations=dict(raw["mitigations"]),
            human_error=bool(raw.get("human_error", False)),
            axes=tuple(raw.get("axes", ())),
            omen=raw.get("omen", ""),
            learning=raw["learning"],
            no_effect=tuple(
                NoEffectNote(measure_id=note["measure"], reason=note["reason"])
                for note in raw.get("no_effect", ())
            ),
            glossary=tuple(raw.get("glossary", ())),
            choices=tuple(Choice.from_dict(item) for item in raw["choices"]),
        )


@dataclass(frozen=True)
class ChoiceView:

    choice: Choice
    selectable: bool
    reason: str


class EventDeck:

    def __init__(self, events: list[Event], catalog: MeasureCatalog) -> None:
        self._events = list(events)
        self._by_id = {event.id: event for event in self._events}
        self._catalog = catalog

    @staticmethod
    def from_data(raw: dict[str, Any], catalog: MeasureCatalog) -> EventDeck:
        return EventDeck([Event.from_dict(item) for item in raw["events"]], catalog)

    def all(self) -> list[Event]:
        return list(self._events)

    def get(self, event_id: str) -> Event:
        return self._by_id[event_id]

    def candidates(self, last_event_id: str | None, facilities: set[str]) -> list[Event]:
        return [
            event
            for event in self._events
            if event.id != last_event_id
            and (event.requires_facility is None or event.requires_facility in facilities)
        ]

    def weight_of(
        self,
        event: Event,
        awareness: int = 0,
        awareness_factor: float = 1.0,
        omen_event_id: str | None = None,
        omen_boost: float = 1.0,
        action_factors: dict[str, float] | None = None,
    ) -> float:
        if event.weight <= 0:
            return 0.0

        weight = float(event.weight)

        if event.human_error and awareness > 0:
            weight *= human_error_weight_rate(awareness, awareness_factor)

        if action_factors:
            weight *= action_factors.get(event.id, 1.0)

        if omen_event_id is not None and event.id == omen_event_id:
            weight *= omen_boost

        return max(0.1, weight)

    def draw(
        self,
        rng: random.Random,
        last_event_id: str | None,
        facilities: set[str],
        awareness: int = 0,
        awareness_factor: float = 1.0,
        omen_event_id: str | None = None,
        omen_boost: float = 1.0,
        action_factors: dict[str, float] | None = None,
    ) -> Event:
        candidates = self.candidates(last_event_id, facilities)
        if not candidates:
            candidates = self.candidates(None, facilities)

        weights = [
            self.weight_of(event, awareness, awareness_factor,
                           omen_event_id, omen_boost, action_factors)
            for event in candidates
        ]
        if sum(weights) <= 0:
            return rng.choice(candidates)
        return rng.choices(candidates, weights=weights, k=1)[0]

    def omen_candidates(self, facilities: set[str]) -> list[Event]:
        return [event for event in self.candidates(None, facilities) if event.omen]

    def choice_views(
        self,
        event: Event,
        owned: set[str],
        purchase_log: dict[str, int] | None = None,
        current_year: int | None = None,
    ) -> list[ChoiceView]:
        purchase_log = purchase_log or {}
        views: list[ChoiceView] = []

        for choice in event.choices:
            if choice.requires is None or choice.requires in owned:
                views.append(ChoiceView(choice=choice, selectable=True, reason=""))
                continue

            views.append(
                ChoiceView(
                    choice=choice,
                    selectable=False,
                    reason=self._unselectable_reason(choice.requires, purchase_log, current_year),
                )
            )
        return views

    def _unselectable_reason(
        self, measure_id: str, purchase_log: dict[str, int], current_year: int | None
    ) -> str:
        name = self._catalog.get(measure_id).name if self._catalog.has(measure_id) else measure_id
        skipped_year = purchase_log.get(measure_id)

        if skipped_year is None:
            return f"「{name}」をまだ買っていないからです"

        if current_year is None or current_year <= skipped_year:
            return f"{skipped_year} 年目に「{name}」を買わなかったからです"

        years_ago = current_year - skipped_year
        return f"{years_ago} 年前（{skipped_year} 年目）に「{name}」を買わなかったからです"
