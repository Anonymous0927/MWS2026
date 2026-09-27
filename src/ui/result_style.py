from __future__ import annotations

from dataclasses import dataclass

from core.score import FinalScore

from . import theme


@dataclass(frozen=True)
class ResultStyle:

    key: str
    title: str
    accent: tuple[int, int, int]
    background: tuple[int, int, int]


def style_for(score: FinalScore) -> ResultStyle:
    if score.bankrupt:
        return _make_style("bankrupt", "倒産しました")
    if score.cleared:
        return _make_style("complete", "完全勝利です")

    achieved = sum(score.clear_flags.values())
    if score.clear_flags and achieved == len(score.clear_flags) - 1:
        return _make_style("near", "あと一歩でした")
    return _make_style("caution", "危ないところでした")


def _make_style(key: str, title: str) -> ResultStyle:
    accent, background = theme.RESULT_PALETTE[key]
    return ResultStyle(key, title, accent, background)
