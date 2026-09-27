from __future__ import annotations

import math
from dataclasses import dataclass

from .company import Company
from .config import Config
from .types import Money, TurnLog, format_money

AXIS_LABELS = (
    ("money", "もうけ"),
    ("star", "安全レベル"),
    ("trust", "信用度"),
    ("damage", "被害の少なさ"),
    ("morale", "社員の満足度"),
)

CLEAR_LABELS = (
    ("survived", "全年を、資金 0 未満にせず終える"),
    ("trust", "最終の信用度が 80 以上"),
    ("star", "最終の安全レベルが ★4 以上"),
    ("damage", "被害の合計が 300 万円未満"),
    ("morale", "最終の満足度が 70 以上"),
)


@dataclass(frozen=True)
class Axis:

    key: str
    label: str
    value: int
    points: float
    detail: str = ""


@dataclass(frozen=True)
class Highlight:

    kind: str
    year: int
    measure_name: str
    amount: Money
    text: str


@dataclass(frozen=True)
class FinalScore:

    total: int
    rank: str
    axes: tuple[Axis, ...]
    clear_flags: dict[str, bool]
    highlights: tuple[Highlight, ...]
    comment: str
    cleared: bool
    bankrupt: bool

    @property
    def good_highlights(self) -> tuple[Highlight, ...]:
        return tuple(item for item in self.highlights if item.kind == "good")

    @property
    def regret_highlights(self) -> tuple[Highlight, ...]:
        return tuple(item for item in self.highlights if item.kind == "regret")


def evaluate(
    company: Company,
    star: int,
    logs: list[TurnLog],
    config: Config,
    bankrupt: bool = False,
    years_played: int | None = None,
    unit: str = "man",
    measure_names: dict[str, str] | None = None,
) -> FinalScore:
    axes = _build_axes(company, star, config, unit)
    total = round(sum(axis.points for axis in axes))

    clear_flags = _build_clear_flags(company, star, config, bankrupt, years_played)
    cleared = all(clear_flags.values())

    rank = "D" if bankrupt else _rank_of(total, config.ranks)

    return FinalScore(
        total=total,
        rank=rank,
        axes=axes,
        clear_flags=clear_flags,
        highlights=build_highlights(logs, unit, measure_names),
        comment=config.comments.get(rank, ""),
        cleared=cleared,
        bankrupt=bankrupt,
    )


def _build_axes(company: Company, star: int, config: Config, unit: str) -> tuple[Axis, ...]:
    full = config.points_per_axis

    ratios = {
        "money": min(1.0, max(0.0, company.money / config.max_money_score)),
        "star": star / 5,
        "trust": company.trust / 100,
        "damage": max(0.0, 1 - company.total_damage / config.max_damage_score),
        "morale": company.morale / 100,
    }
    details = {
        "money": f"年末の残り {format_money(company.money, unit)}",
        "star": "★" * star + "☆" * (5 - star),
        "trust": f"{company.trust} / 100",
        "damage": f"被害の合計 {format_money(company.total_damage, unit)}",
        "morale": f"{company.morale} / 100",
    }

    return tuple(
        Axis(
            key=key,
            label=label,
            value=round(ratios[key] * 100),
            points=ratios[key] * full,
            detail=details[key],
        )
        for key, label in AXIS_LABELS
    )


def _build_clear_flags(
    company: Company,
    star: int,
    config: Config,
    bankrupt: bool,
    years_played: int | None,
) -> dict[str, bool]:
    survived = not bankrupt
    if years_played is not None:
        survived = survived and years_played >= config.total_years

    return {
        "survived": survived,
        "trust": company.trust >= config.clear.min_trust,
        "star": star >= config.clear.min_star,
        "damage": company.total_damage < config.clear.max_total_damage,
        "morale": company.morale >= config.clear.min_morale,
    }


def _rank_of(total: int, ranks: dict[str, int]) -> str:
    for rank in ("S", "A", "B", "C"):
        if total >= ranks[rank]:
            return rank
    return "D"


def build_highlights(
    logs: list[TurnLog],
    unit: str = "man",
    measure_names: dict[str, str] | None = None,
) -> tuple[Highlight, ...]:
    good: dict[str, dict] = {}
    regret: dict[str, dict] = {}

    for log in logs:
        for outcome in (log.outcome, *log.additional_outcomes):
            event = outcome.event
            for measure_id, effect in event.mitigations.items():
                rate = (
                    _rate_of(outcome, measure_id)
                    if measure_id in log.owned
                    else log.best_rate
                )
                reduced = event.base_damage * math.floor(effect * rate / 100) // 100
                if reduced <= 0:
                    continue

                bucket = good if measure_id in log.owned else regret
                name = _measure_name(outcome, measure_id, measure_names)
                entry = bucket.setdefault(
                    measure_id, {"amount": 0, "year": log.year, "name": name, "years": []}
                )
                entry["amount"] += reduced
                entry["year"] = min(entry["year"], log.year)
                entry["years"].append(log.year)

    highlights: list[Highlight] = []
    highlights.extend(_top_two(good, "good", unit))
    highlights.extend(_top_two(regret, "regret", unit))
    return tuple(highlights)


def _rate_of(outcome, measure_id: str) -> int:
    for contribution in outcome.contributions:
        if contribution.measure_id == measure_id:
            return contribution.rate
    return 0


def _measure_name(
    outcome, measure_id: str, measure_names: dict[str, str] | None = None
) -> str:
    for contribution in outcome.contributions:
        if contribution.measure_id == measure_id:
            return contribution.measure_name
    if measure_names and measure_id in measure_names:
        return measure_names[measure_id]
    return measure_id


def _top_two(bucket: dict[str, dict], kind: str, unit: str) -> list[Highlight]:
    ranked = sorted(bucket.items(), key=lambda item: (-item[1]["amount"], item[1]["year"]))[:2]

    highlights: list[Highlight] = []
    for measure_id, entry in ranked:
        years = "・".join(f"{year} 年目" for year in entry["years"][:3])
        amount_text = format_money(entry["amount"], unit)
        if kind == "good":
            text = f"{entry['name']} を持っていたので、{years} の被害を {amount_text} 減らせました"
        else:
            text = f"{entry['name']} を見送ったため、{years} に {amount_text} を余分に失いました"
        highlights.append(
            Highlight(
                kind=kind,
                year=entry["year"],
                measure_name=entry["name"],
                amount=entry["amount"],
                text=text,
            )
        )
    return highlights
