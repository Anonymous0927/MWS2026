from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .events import Choice, Event
    from .resolver import Outcome


class Phase(Enum):

    MANAGE = "manage"
    INCIDENT = "incident"
    OUTCOME = "outcome"
    FINISHED = "finished"


@dataclass(frozen=True)
class Result:

    ok: bool
    message: str = ""

    @staticmethod
    def success(message: str = "") -> Result:
        return Result(True, message)

    @staticmethod
    def failure(message: str) -> Result:
        return Result(False, message)


class PhaseError(RuntimeError):
    pass


Money = int
"""金額。会社編は万円単位、学校編だけ円単位の整数（school.json の unit で切り替える）。

float を使わない。割り算は必ず // か math.floor を明示する（要件定義書 C-8）。
"""


def clamp_percent(value: int) -> int:
    return max(0, min(100, value))


def format_money(amount: Money, unit: str = "man") -> str:
    if unit == "yen":
        return f"{amount:,} 円"
    return f"{amount} 万円"


@dataclass(frozen=True)
class TurnLog:

    year: int
    event: Event
    choice: Choice
    outcome: Outcome
    owned: frozenset[str]
    levels: dict[str, int] = field(default_factory=dict)
    best_rate: int = 100
    bought: tuple[str, ...] = ()
    spent: Money = 0
    budget: Money = 0
    money_after: Money = 0
    trust_before: int = 0
    trust_after: int = 0
    morale_before: int = 0
    morale_after: int = 0
    star_before: int = 1
    star_after: int = 1
    expansions: tuple[str, ...] = ()
    bonus_text: str = ""
    additional_outcomes: tuple[Outcome, ...] = ()


@dataclass(frozen=True)
class TimelineEntry:

    year: int
    kind: str
    text: str


@dataclass(frozen=True)
class FacilityView:

    id: str
    name: str
    note: str
    level: str
    label: str
    missing: tuple[str, ...] = field(default_factory=tuple)
