from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .types import Money, Result, format_money


@dataclass(frozen=True)
class Action:

    id: str
    name: str
    formal_name: str
    cost_base: Money
    cost_per_employee: float
    summary: str
    weakness: str
    awareness: int
    axes: dict[str, int]
    event_weight: dict[str, float]
    glossary: tuple[str, ...]

    def cost_for(self, employees: int) -> Money:
        return math.ceil(self.cost_base + self.cost_per_employee * employees)

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> Action:
        return Action(
            id=raw["id"],
            name=raw["name"],
            formal_name=raw.get("formal_name", raw["name"]),
            cost_base=raw["cost_base"],
            cost_per_employee=float(raw.get("cost_per_employee", 0)),
            summary=raw["summary"],
            weakness=raw.get("weakness", ""),
            awareness=raw.get("awareness", 0),
            axes=dict(raw.get("axes", {})),
            event_weight={key: float(value) for key, value in raw.get("event_weight", {}).items()},
            glossary=tuple(raw.get("glossary", ())),
        )


@dataclass(frozen=True)
class ActionView:

    action: Action
    cost: Money
    done: bool
    available: bool
    reason: str


class ActionCatalog:

    def __init__(self, actions: list[Action], unit: str = "man") -> None:
        self._actions = list(actions)
        self._by_id = {action.id: action for action in self._actions}
        self._unit = unit

    @staticmethod
    def from_data(raw: dict[str, Any], unit: str = "man") -> ActionCatalog:
        return ActionCatalog([Action.from_dict(item) for item in raw["actions"]], unit)

    def all(self) -> list[Action]:
        return list(self._actions)

    def get(self, action_id: str) -> Action:
        return self._by_id[action_id]

    def has(self, action_id: str) -> bool:
        return action_id in self._by_id

    def can_do(
        self, action_id: str, done_this_year: set[str], budget: Money, employees: int
    ) -> Result:
        action = self._by_id[action_id]

        if action_id in done_this_year:
            return Result.failure("今年はもう実施しました")

        cost = action.cost_for(employees)
        if budget < cost:
            shortage = cost - budget
            return Result.failure(f"お金が足りません（あと {format_money(shortage, self._unit)}）")

        return Result.success()

    def views(
        self, done_this_year: set[str], budget: Money, employees: int
    ) -> list[ActionView]:
        views: list[ActionView] = []
        for action in self._actions:
            result = self.can_do(action.id, done_this_year, budget, employees)
            views.append(
                ActionView(
                    action=action,
                    cost=action.cost_for(employees),
                    done=action.id in done_this_year,
                    available=result.ok,
                    reason=result.message,
                )
            )
        return views

    def combined_axes(self, done_this_year: set[str]) -> list[dict[str, int]]:
        return [self._by_id[action_id].axes for action_id in done_this_year if action_id in self._by_id]

    def event_weight_factor(self, done_this_year: set[str], event_id: str) -> float:
        factor = 1.0
        for action_id in done_this_year:
            action = self._by_id.get(action_id)
            if action is not None:
                factor *= action.event_weight.get(event_id, 1.0)
        return factor
