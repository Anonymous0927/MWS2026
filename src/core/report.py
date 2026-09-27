from __future__ import annotations

import csv
import io
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from .score import CLEAR_LABELS
from .types import format_money

if TYPE_CHECKING:
    from .game import GameSession

ENCODING = "utf-8-sig"

CSV_HEADER = [
    "年", "使えるお金", "買ったもの", "投資額", "事件", "基本の被害",
    "効きめ合計", "被害額", "選んだ手", "信用度", "満足度", "安全レベル",
    "合計 ver", "対策の ver", "年末の残り",
]


def _levels_text(session: GameSession, levels: dict[str, int]) -> str:
    if not levels:
        return "（なし）"

    parts: list[str] = []
    for measure_id in sorted(levels):
        name = (
            session.catalog.get(measure_id).name
            if session.catalog.has(measure_id)
            else measure_id
        )
        parts.append(f"{name} {session.versions.name_of(levels[measure_id])}")
    return "／".join(parts)


def build_text(session: GameSession) -> str:
    unit = session.unit
    lines: list[str] = []

    mode = "学校編 3 ターン" if session.is_school else f"会社編 {session.total_years} 年"
    lines.append("Secure Company Simulator 判断の記録")
    lines.append(
        f"プレイ日時: {datetime.now():%Y-%m-%d %H:%M:%S}   "
        f"シード: {session.seed}   モード: {mode}"
    )
    lines.append("")
    lines.append("※ 金額・効きめ・被害額は、教材としての分かりやすさを優先した設定値です。")
    lines.append("　 実在の統計値ではありません。")
    lines.append("")

    for log in session.logs:
        outcome = log.outcome
        lines.append(f"[{log.year} 年目] 使えるお金 {format_money(log.budget, unit)}")
        lines.append(f"  買ったもの : {'／'.join(log.bought) if log.bought else '（なし）'}")
        lines.append(f"  対策の ver : {_levels_text(session, log.levels)}")
        if log.expansions:
            lines.append(f"  会社の動き : {'／'.join(log.expansions)}")
        lines.append(
            f"  起きた事件 : {log.event.name}  "
            f"基本の被害 {format_money(log.event.base_damage, unit)}"
        )

        parts = []
        if outcome.baseline:
            parts.append(f"もとからの備え {outcome.baseline}")
        parts += [f"{item.measure_name} {item.effect}" for item in outcome.contributions]
        if parts:
            capped = "（上限 90 を適用）" if outcome.capped else ""
            lines.append(
                f"  効きめ     : {' ＋ '.join(parts)} → 合計 {outcome.effect_total} %{capped}"
            )
        else:
            lines.append("  効きめ     : 効く対策を持っていませんでした → 合計 0 %")
        if outcome.upgrade_note:
            lines.append(f"  ver        : {outcome.upgrade_note}")

        lines.append(f"  被害       : {outcome.full_formula_text}")
        lines.append(f"  選んだ手   : {log.choice.label}")
        for note in outcome.no_effect_notes:
            lines.append(f"  効かなかった: {note}")
        if log.bonus_text:
            lines.append(f"  よいこと   : {log.bonus_text}")

        star_text = f"★{log.star_before} → ★{log.star_after}"
        lines.append(
            f"  信用度     : {log.trust_before} → {log.trust_after}    "
            f"安全レベル: {star_text}    年末の残り: {format_money(log.money_after, unit)}"
        )
        lines.append(f"  学習ポイント: {log.event.learning}")
        for index, extra in enumerate(log.additional_outcomes, start=2):
            lines.append(f"  続けて起きた第{index}事件 : {extra.event.name}")
            lines.append(f"    被害     : {extra.full_formula_text}")
            lines.append(f"    選んだ手 : {extra.choice.label}")
            lines.append(f"    学習ポイント: {extra.event.learning}")
        lines.append("")

    lines.extend(_build_final_section(session, unit))
    return "\n".join(lines)


def _build_final_section(session: GameSession, unit: str) -> list[str]:
    from .types import Phase

    if session.phase is not Phase.FINISHED:
        return ["[結果] まだプレイの途中です。"]

    score = session.final_score()
    lines: list[str] = []

    lines.append(f"[結果] 総合点 {score.total} / 1000  評価 {score.rank}")
    lines.append("  " + " / ".join(f"{axis.label} {axis.value}" for axis in score.axes))

    achieved = sum(1 for ok in score.clear_flags.values() if ok)
    lines.append(f"  クリア条件: {achieved} / {len(score.clear_flags)} 達成")
    for key, label in CLEAR_LABELS:
        mark = "○" if score.clear_flags.get(key) else "×"
        lines.append(f"    {mark} {label}")

    if score.bankrupt:
        lines.append("  ※ 倒産したため、評価は点数によらず D です。")

    good = score.good_highlights
    regret = score.regret_highlights
    lines.append(f"  よかった判断     : {good[0].text if good else '（該当なし）'}")
    for item in good[1:]:
        lines.append(f"                     {item.text}")
    lines.append(f"  もったいなかった : {regret[0].text if regret else '（該当なし）'}")
    for item in regret[1:]:
        lines.append(f"                     {item.text}")

    lines.append(f"  講評: {score.comment}")
    return lines


def build_csv(session: GameSession) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(CSV_HEADER)

    for log in session.logs:
        outcome = log.outcome
        outcomes = (outcome, *log.additional_outcomes)
        writer.writerow(
            [
                log.year,
                log.budget,
                "／".join(log.bought),
                log.spent,
                "／".join(item.event.name for item in outcomes),
                sum(item.event.base_damage for item in outcomes),
                outcome.effect_total,
                sum(item.damage for item in outcomes),
                "／".join(item.choice.label for item in outcomes),
                log.trust_after,
                log.morale_after,
                log.star_after,
                sum(log.levels.values()),
                _levels_text(session, log.levels),
                log.money_after,
            ]
        )
    return buffer.getvalue()


def write(session: GameSession, out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = f"{datetime.now():%Y%m%d_%H%M%S}"

    text_path = out_dir / f"report_{stamp}.txt"
    csv_path = out_dir / f"report_{stamp}.csv"

    text_path.write_text(build_text(session), encoding=ENCODING)
    csv_path.write_text(build_csv(session), encoding=ENCODING)

    return text_path, csv_path
