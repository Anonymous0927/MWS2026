from __future__ import annotations

import math
from dataclasses import dataclass

from .config import Rules
from .events import Choice, Event
from .measures import MeasureCatalog
from .types import Money, format_money

DEFAULT_CAP = 90


@dataclass(frozen=True)
class Contribution:

    measure_id: str
    measure_name: str
    effect: int
    base_effect: int = 0
    rate: int = 100

    @property
    def scaled_down(self) -> bool:
        return self.rate < 100


@dataclass(frozen=True)
class Outcome:

    event: Event
    choice: Choice
    contributions: tuple[Contribution, ...]
    effect_total: int
    effect_raw: int
    base_damage: Money
    damage: Money
    extra_cost: Money
    trust_delta: int
    morale_delta: int
    no_effect_notes: tuple[str, ...]
    formula_text: str
    full_formula_text: str
    capped: bool
    luck_note: str = ""
    baseline: int = 0
    upgrade_note: str = ""

    @property
    def prevented(self) -> bool:
        return self.damage == 0


def resolve(
    event: Event,
    choice: Choice,
    active: set[str],
    catalog: MeasureCatalog,
    cap: int = DEFAULT_CAP,
    rules: Rules | None = None,
    unit: str = "man",
    baseline: int = 0,
    scales: dict[str, int] | None = None,
    upgraded_scales: dict[str, int] | None = None,
) -> Outcome:
    contributions = _contributions_of(event, active, catalog, scales)
    effect_raw = baseline + sum(item.effect for item in contributions)

    effect_total = min(effect_raw, cap)

    damage_before_choice = math.floor(event.base_damage * (100 - effect_total) / 100)
    damage_scaled = _floor_scaled(damage_before_choice, choice.damage_scale)
    damage = damage_scaled + choice.extra_cost

    no_effect_notes = tuple(
        note.reason for note in event.no_effect if note.measure_id in active
    )

    rules = rules or _default_rules(cap)
    trust_delta = -math.ceil(damage / rules.trust_penalty_divisor)
    if event.public and damage > 0:
        trust_delta -= rules.public_penalty
    if damage == 0:
        trust_delta += rules.trust_recovery_no_damage
    trust_delta += choice.trust_delta

    morale_delta = rules.morale_no_damage if damage == 0 else rules.morale_damage

    return Outcome(
        event=event,
        choice=choice,
        contributions=contributions,
        effect_total=effect_total,
        effect_raw=effect_raw,
        base_damage=event.base_damage,
        damage=damage,
        extra_cost=choice.extra_cost,
        trust_delta=trust_delta,
        morale_delta=morale_delta,
        no_effect_notes=no_effect_notes,
        formula_text=build_formula_text(event.base_damage, effect_total, damage_before_choice, unit),
        full_formula_text=build_full_formula_text(
            event.base_damage, effect_total, damage_before_choice,
            damage_scaled, damage, choice, unit,
        ),
        capped=effect_raw > cap,
        luck_note=_luck_note(choice, effect_total),
        baseline=baseline,
        upgrade_note=_upgrade_note(
            event, choice, active, catalog, cap, baseline, upgraded_scales, damage, unit
        ),
    )


def _contributions_of(
    event: Event,
    active: set[str],
    catalog: MeasureCatalog,
    scales: dict[str, int] | None,
) -> tuple[Contribution, ...]:
    scales = scales or {}
    items: list[Contribution] = []

    for measure_id in active:
        if measure_id not in event.mitigations:
            continue
        base_effect = event.mitigations[measure_id]
        rate = scales.get(measure_id, 100)
        items.append(
            Contribution(
                measure_id=measure_id,
                measure_name=(
                    catalog.get(measure_id).name if catalog.has(measure_id) else measure_id
                ),
                effect=math.floor(base_effect * rate / 100),
                base_effect=base_effect,
                rate=rate,
            )
        )

    return tuple(sorted(items, key=lambda item: (-item.effect, item.measure_id)))


def _upgrade_note(
    event: Event,
    choice: Choice,
    active: set[str],
    catalog: MeasureCatalog,
    cap: int,
    baseline: int,
    upgraded_scales: dict[str, int] | None,
    damage: Money,
    unit: str,
) -> str:
    if not upgraded_scales or damage == 0:
        return ""

    upgraded = _contributions_of(event, active, catalog, upgraded_scales)
    effect_total = min(baseline + sum(item.effect for item in upgraded), cap)

    damage_before_choice = math.floor(event.base_damage * (100 - effect_total) / 100)
    best_damage = _floor_scaled(damage_before_choice, choice.damage_scale) + choice.extra_cost

    if best_damage >= damage:
        return ""

    if best_damage == 0:
        return (
            "持っている守りを、いま選べるいちばん新しい ver にしていれば、"
            "この事件の被害は出ませんでした。"
        )
    return (
        "持っている守りを、いま選べるいちばん新しい ver にしていれば、"
        f"被害は {format_money(best_damage, unit)} ですみました"
        f"（実際は {format_money(damage, unit)}）。"
    )


def _floor_scaled(amount: Money, scale: float) -> Money:
    return math.floor(round(amount * scale, 6))


def build_formula_text(
    base_damage: Money, effect_total: int, damage: Money, unit: str = "man"
) -> str:
    return (
        f"{format_money(base_damage, unit)} × (100 − {effect_total}) ÷ 100 "
        f"＝ {format_money(damage, unit)}"
    )


def build_full_formula_text(
    base_damage: Money,
    effect_total: int,
    damage_before_choice: Money,
    damage_scaled: Money,
    damage: Money,
    choice: Choice,
    unit: str = "man",
) -> str:
    text = build_formula_text(base_damage, effect_total, damage_before_choice, unit)

    if choice.damage_scale != 1.0:
        text += (
            f"　→　{damage_before_choice} × {choice.damage_scale}"
            f" ＝ {format_money(damage_scaled, unit)}"
        )
    if choice.extra_cost:
        text += (
            f"　→　{damage_scaled} ＋ {choice.extra_cost}（追加の費用）"
            f" ＝ {format_money(damage, unit)}"
        )
    return text


def _luck_note(choice: Choice, effect_total: int) -> str:
    if choice.risky and effect_total > 0:
        return "備えがあったおかげで軽く済みましたが、これは運に頼った判断でした。"
    return ""


def _default_rules(cap: int) -> Rules:
    return Rules(
        mitigation_cap=cap,
        trust_penalty_divisor=10,
        public_penalty=5,
        trust_recovery_no_damage=5,
        morale_damage=-2,
        morale_expansion=-4,
        morale_remote=4,
        morale_no_damage=2,
    )
