from __future__ import annotations

from dataclasses import dataclass
from typing import Any

MAX_SCORE = 100


@dataclass(frozen=True)
class Axis:

    id: str
    name: str
    note: str

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> Axis:
        return Axis(id=raw["id"], name=raw["name"], note=raw.get("note", ""))


@dataclass(frozen=True)
class AxisScore:

    axis: Axis
    value: int
    from_measures: int
    from_actions: int
    level: str
    label: str
    from_baseline: int = 0

    @property
    def temporary(self) -> bool:
        return self.from_actions > 0


LEVEL_THRESHOLDS = ((60, "ok", "守れている"), (30, "warn", "手薄"), (0, "ng", "ほぼ無防備"))


def level_of(value: int) -> tuple[str, str]:
    for threshold, level, label in LEVEL_THRESHOLDS:
        if value >= threshold:
            return (level, label)
    return ("ng", "ほぼ無防備")


class DefenseModel:

    def __init__(self, axes: list[Axis]) -> None:
        self._axes = list(axes)

    @staticmethod
    def from_data(raw: dict[str, Any]) -> DefenseModel:
        return DefenseModel([Axis.from_dict(item) for item in raw["axes"]])

    def axes(self) -> list[Axis]:
        return list(self._axes)

    def scores(
        self,
        measure_axes: list[dict[str, int]],
        action_axes: list[dict[str, int]] | None = None,
        baseline: int = 0,
    ) -> list[AxisScore]:
        action_axes = action_axes or []
        scores: list[AxisScore] = []

        for axis in self._axes:
            from_baseline = min(MAX_SCORE, max(0, baseline))
            from_measures = sum(item.get(axis.id, 0) for item in measure_axes)
            from_actions = sum(item.get(axis.id, 0) for item in action_axes)
            value = min(MAX_SCORE, from_baseline + from_measures + from_actions)

            filled_measures = min(MAX_SCORE - from_baseline, from_measures)
            level, label = level_of(value)

            scores.append(
                AxisScore(
                    axis=axis,
                    value=value,
                    from_measures=filled_measures,
                    from_actions=value - from_baseline - filled_measures,
                    level=level,
                    label=label,
                    from_baseline=from_baseline,
                )
            )
        return scores

    def weakest(self, scores: list[AxisScore]) -> AxisScore | None:
        if not scores:
            return None
        return min(scores, key=lambda score: score.value)
