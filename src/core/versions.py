from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .types import Money

LEVEL_NONE = 0


@dataclass(frozen=True)
class Level:

    level: int
    name: str
    unlock_year: int
    effect_rate: int
    cost_rate: int
    upkeep_rate: int

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> Level:
        return Level(
            level=raw["level"],
            name=raw["name"],
            unlock_year=raw["unlock_year"],
            effect_rate=raw["effect_rate"],
            cost_rate=raw.get("cost_rate", 100),
            upkeep_rate=raw.get("upkeep_rate", 100),
        )


class VersionRules:

    def __init__(self, levels: list[Level], decay_per_year: int, decay_floor: int) -> None:
        self._levels = sorted(levels, key=lambda item: item.level)
        self._by_level = {item.level: item for item in self._levels}
        self._decay_per_year = decay_per_year
        self._decay_floor = decay_floor


    @staticmethod
    def from_data(raw: dict[str, Any]) -> VersionRules:
        versions = raw["versions"]
        return VersionRules(
            levels=[Level.from_dict(item) for item in versions["levels"]],
            decay_per_year=versions["decay_per_year"],
            decay_floor=versions["decay_floor"],
        )

    @staticmethod
    def single_level() -> VersionRules:
        return VersionRules(
            levels=[Level(1, "導入ずみ", unlock_year=1, effect_rate=100,
                          cost_rate=100, upkeep_rate=100)],
            decay_per_year=0,
            decay_floor=100,
        )


    def all(self) -> list[Level]:
        return list(self._levels)

    def get(self, level: int) -> Level:
        return self._by_level[level]

    def max_level(self) -> int:
        return self._levels[-1].level

    def name_of(self, level: int) -> str:
        if level <= LEVEL_NONE:
            return "未導入"
        return self._by_level[level].name

    def unlocked_level(self, year: int) -> int:
        unlocked = LEVEL_NONE
        for item in self._levels:
            if year >= item.unlock_year:
                unlocked = item.level
        return unlocked

    def is_unlocked(self, level: int, year: int) -> bool:
        if level not in self._by_level:
            return False
        return year >= self._by_level[level].unlock_year

    def lock_reason(self, level: int, year: int) -> str:
        if level not in self._by_level:
            return ""
        item = self._by_level[level]
        if year >= item.unlock_year:
            return ""
        return f"「{item.name}」はまだありません（{item.unlock_year} 年目から）"


    def effect_rate(self, level: int, year: int) -> int:
        if level <= LEVEL_NONE or level not in self._by_level:
            return 0

        item = self._by_level[level]
        years_passed = max(0, year - item.unlock_year)
        rate = item.effect_rate - self._decay_per_year * years_passed
        return max(self._decay_floor, rate)

    def scaled_effect(self, base_effect: int, level: int, year: int) -> int:
        return math.floor(base_effect * self.effect_rate(level, year) / 100)


    def cost_of(self, base_cost: Money, level: int) -> Money:
        if level <= LEVEL_NONE or level not in self._by_level:
            return 0
        return math.ceil(base_cost * self._by_level[level].cost_rate / 100)

    def upkeep_of(self, base_upkeep: Money, level: int) -> Money:
        if level <= LEVEL_NONE or level not in self._by_level:
            return 0
        return math.ceil(base_upkeep * self._by_level[level].upkeep_rate / 100)
