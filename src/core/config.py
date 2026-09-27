from __future__ import annotations

from dataclasses import dataclass

from . import dataloader
from .types import Money


@dataclass(frozen=True)
class ClearConditions:

    min_trust: int
    min_star: int
    max_total_damage: Money
    min_morale: int


@dataclass(frozen=True)
class Rules:

    mitigation_cap: int
    trust_penalty_divisor: int
    public_penalty: int
    trust_recovery_no_damage: int
    morale_damage: int
    morale_expansion: int
    morale_remote: int
    morale_no_damage: int


@dataclass(frozen=True)
class Facility:

    id: str
    name: str
    note: str
    always: bool


@dataclass(frozen=True)
class Expansion:

    id: str
    name: str
    cost: Money
    employees: int
    morale: int
    facility: str | None
    summary: str
    unlocks: str


@dataclass(frozen=True)
class Awareness:

    initial: int
    decay: int
    weight_factor: float


@dataclass(frozen=True)
class Omen:

    one_in: int
    weight_boost: float
    follow_up_one_in: int
    follow_up_start_year: int


@dataclass(frozen=True)
class InitialDefense:

    percent: int
    axis_points: int
    name: str


@dataclass(frozen=True)
class WorkLimit:

    per_year: int


@dataclass(frozen=True)
class Bonus:

    one_in: int
    money: Money
    trust: int
    text: str


@dataclass(frozen=True)
class Config:

    total_years: int
    initial_money: Money
    initial_employees: int
    initial_trust: int
    initial_morale: int
    profit_per_employee: Money
    rules: Rules
    star_thresholds: tuple[int, ...]
    max_money_score: Money
    max_damage_score: Money
    points_per_axis: int
    clear: ClearConditions
    ranks: dict[str, int]
    comments: dict[str, str]
    facilities: tuple[Facility, ...]
    expansions: tuple[Expansion, ...]
    bonus: Bonus
    axes: tuple[dict, ...]
    awareness: Awareness
    omen: Omen
    initial_defense: InitialDefense
    work_limit: WorkLimit

    @property
    def mitigation_cap(self) -> int:
        return self.rules.mitigation_cap

    @staticmethod
    def load(total_years: int | None = None) -> Config:
        raw = dataloader.load("config")
        dataloader.validate_config(raw)
        return Config.from_dict(raw, total_years)

    @staticmethod
    def from_dict(raw: dict, total_years: int | None = None) -> Config:
        initial = raw["initial"]
        score = raw["score"]
        clear = raw["clear"]
        bonus = raw["bonus"]["quiet_inspection"]

        return Config(
            total_years=total_years if total_years is not None else raw["total_years"],
            initial_money=initial["money"],
            initial_employees=initial["employees"],
            initial_trust=initial["trust"],
            initial_morale=initial["morale"],
            profit_per_employee=raw["economy"]["profit_per_employee"],
            rules=Rules(**raw["rules"]),
            star_thresholds=tuple(raw["stars"]["thresholds"]),
            max_money_score=score["max_money"],
            max_damage_score=score["max_damage"],
            points_per_axis=score["points_per_axis"],
            clear=ClearConditions(
                min_trust=clear["min_trust"],
                min_star=clear["min_star"],
                max_total_damage=clear["max_total_damage"],
                min_morale=clear["min_morale"],
            ),
            ranks=dict(raw["ranks"]),
            comments=dict(raw["comments"]),
            facilities=tuple(Facility(**item) for item in raw["facilities"]),
            expansions=tuple(Expansion(**item) for item in raw["expansions"]),
            bonus=Bonus(**bonus),
            axes=tuple(raw["axes"]),
            awareness=Awareness(**raw["awareness"]),
            omen=Omen(**raw["omen"]),
            initial_defense=InitialDefense(**raw["initial_defense"]),
            work_limit=WorkLimit(**raw["work_limit"]),
        )
