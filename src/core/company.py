from __future__ import annotations

import math
from dataclasses import dataclass

from .types import Money, clamp_percent


@dataclass
class Company:

    money: Money
    employees: int
    trust: int
    morale: int
    awareness: int = 50
    total_damage: Money = 0

    def spend(self, amount: Money) -> None:
        self.money -= amount

    def earn(self, amount: Money) -> None:
        self.money += amount

    def take_damage(self, amount: Money) -> None:
        self.money -= amount
        self.total_damage += amount

    def add_trust(self, delta: int) -> None:
        self.trust = clamp_percent(self.trust + delta)

    def add_morale(self, delta: int) -> None:
        self.morale = clamp_percent(self.morale + delta)

    def add_awareness(self, delta: int) -> None:
        self.awareness = clamp_percent(self.awareness + delta)

    def add_employees(self, count: int) -> None:
        self.employees += count

    def profit(self, per_employee: Money) -> Money:
        return math.floor(self.employees * per_employee * self.trust / 100)

    def snapshot(self) -> Company:
        return Company(
            money=self.money,
            employees=self.employees,
            trust=self.trust,
            morale=self.morale,
            awareness=self.awareness,
            total_damage=self.total_damage,
        )
