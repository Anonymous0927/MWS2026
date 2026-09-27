from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

VALID_FACILITIES = ("shop", "remote")

SCHOOL_PREFIX = "sc_"


class DataError(Exception):

    def __init__(self, file: str, key: str, reason: str) -> None:
        self.file = file
        self.key = key
        self.reason = reason
        location = f"{key} " if key else ""
        super().__init__(f"{file}: {location}{reason}")


def load(name: str) -> dict[str, Any]:
    path = DATA_DIR / f"{name}.json"
    if not path.exists():
        raise DataError(f"{name}.json", "", "ファイルが見つかりません")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise DataError(
            f"{name}.json", f"{error.lineno} 行目で", "JSON の構文が壊れています"
        ) from error




def _require_key(item: dict[str, Any], key: str, file: str, where: str) -> Any:
    if key not in item:
        raise DataError(file, where, f'"{key}" がありません')
    return item[key]


def _require_int(value: Any, file: str, where: str, key: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DataError(file, where, f'"{key}" は整数である必要があります')
    return value


def _require_str(value: Any, file: str, where: str, key: str) -> str:
    if not isinstance(value, str):
        raise DataError(file, where, f'"{key}" は文字列である必要があります')
    return value


def _require_list(value: Any, file: str, where: str, key: str) -> list[Any]:
    if not isinstance(value, list):
        raise DataError(file, where, f'"{key}" は配列である必要があります')
    return value


def _where(item_id: str) -> str:
    return f'id="{item_id}" の'




def validate_config(config: dict[str, Any]) -> None:
    file = "config.json"

    thresholds = _require_list(
        _require_key(config, "stars", file, "")["thresholds"], file, "stars.thresholds", "thresholds"
    )
    if len(thresholds) != 5:
        raise DataError(file, "stars.thresholds", "5 要素である必要があります")
    if list(thresholds) != sorted(thresholds):
        raise DataError(file, "stars.thresholds", "小さい順に並べてください")

    axes = _require_list(_require_key(config, "axes", file, ""), file, "axes", "axes")
    if not axes:
        raise DataError(file, "axes", "観点が 1 つもありません")
    for axis in axes:
        _require_str(_require_key(axis, "id", file, "axes"), file, "axes", "id")
        _require_str(_require_key(axis, "name", file, "axes"), file, "axes", "name")

    awareness = _require_key(config, "awareness", file, "")
    for key in ("initial", "decay"):
        _require_int(_require_key(awareness, key, file, "awareness"), file, "awareness", key)
    if not 0 <= awareness["initial"] <= 100:
        raise DataError(file, "awareness.initial は", "0〜100 にしてください")

    omen = _require_key(config, "omen", file, "")
    for key in ("one_in", "follow_up_one_in", "follow_up_start_year"):
        value = _require_int(_require_key(omen, key, file, "omen"), file, "omen", key)
        if value < 1:
            raise DataError(file, f"omen.{key} は", "1 以上にしてください")

    cap = _require_int(config["rules"]["mitigation_cap"], file, "rules.mitigation_cap", "mitigation_cap")
    if not 1 <= cap <= 99:
        raise DataError(file, "mitigation_cap は", "100 未満にしてください（被害が 0 になるため）")

    _validate_versions(config, file)
    _validate_initial_defense(config, file)
    _validate_work_limit(config, file)


def _validate_versions(config: dict[str, Any], file: str) -> None:
    versions = _require_key(config, "versions", file, "")
    levels = _require_list(
        _require_key(versions, "levels", file, "versions"), file, "versions", "levels"
    )
    if not levels:
        raise DataError(file, "versions.levels", "ver が 1 つもありません")

    previous_level = 0
    previous_unlock = 0
    for item in levels:
        where = "versions.levels"
        level = _require_int(_require_key(item, "level", file, where), file, where, "level")
        _require_str(_require_key(item, "name", file, where), file, where, "name")

        if level != previous_level + 1:
            raise DataError(file, where, f"ver の番号は 1 から順に並べてください（いまは {level}）")
        previous_level = level

        where = f"versions.levels[{level}]"
        unlock_year = _require_int(
            _require_key(item, "unlock_year", file, where), file, where, "unlock_year"
        )
        if unlock_year < 1:
            raise DataError(file, where, '"unlock_year" は 1 以上にしてください')
        if unlock_year < previous_unlock:
            raise DataError(file, where, '"unlock_year" は上の ver ほど遅くしてください')
        previous_unlock = unlock_year

        for key in ("effect_rate", "cost_rate", "upkeep_rate"):
            rate = _require_int(_require_key(item, key, file, where), file, where, key)
            if rate < 0:
                raise DataError(file, where, f'"{key}" は 0 以上にしてください')
        if item["effect_rate"] > 100:
            raise DataError(file, where, '"effect_rate" は 0〜100 にしてください')

    decay = _require_int(
        _require_key(versions, "decay_per_year", file, "versions"), file, "versions", "decay_per_year"
    )
    if decay < 0:
        raise DataError(file, "versions.decay_per_year は", "0 以上にしてください")

    floor = _require_int(
        _require_key(versions, "decay_floor", file, "versions"), file, "versions", "decay_floor"
    )
    if not 0 <= floor <= 100:
        raise DataError(file, "versions.decay_floor は", "0〜100 にしてください")


def _validate_initial_defense(config: dict[str, Any], file: str) -> None:
    where = "initial_defense"
    initial_defense = _require_key(config, where, file, "")

    percent = _require_int(
        _require_key(initial_defense, "percent", file, where), file, where, "percent"
    )
    if not 0 <= percent <= 99:
        raise DataError(file, "initial_defense.percent は", "0〜99 にしてください（被害が 0 になるため）")

    points = _require_int(
        _require_key(initial_defense, "axis_points", file, where), file, where, "axis_points"
    )
    if not 0 <= points <= 100:
        raise DataError(file, "initial_defense.axis_points は", "0〜100 にしてください")

    _require_str(_require_key(initial_defense, "name", file, where), file, where, "name")


def _validate_work_limit(config: dict[str, Any], file: str) -> None:
    where = "work_limit"
    work_limit = _require_key(config, where, file, "")

    per_year = _require_int(
        _require_key(work_limit, "per_year", file, where), file, where, "per_year"
    )
    if per_year < 1:
        raise DataError(file, "work_limit.per_year は", "1 以上にしてください")


def validate_measures(measures_data: dict[str, Any], version_count: int = 3) -> set[str]:
    file = "measures.json"
    measure_ids: set[str] = set()

    for item in _require_list(_require_key(measures_data, "measures", file, ""), file, "", "measures"):
        measure_id = _require_str(_require_key(item, "id", file, ""), file, "", "id")
        where = _where(measure_id)

        if measure_id in measure_ids:
            raise DataError(file, f'id="{measure_id}" が', "2 回定義されています")
        measure_ids.add(measure_id)

        for key in ("name", "formal_name", "summary", "weakness"):
            _require_str(_require_key(item, key, file, where), file, where, key)

        if not item["weakness"].strip():
            raise DataError(file, where, '"weakness" が空です')

        cost = _require_int(_require_key(item, "cost", file, where), file, where, "cost")
        if cost < 0:
            raise DataError(file, where, '"cost" は 0 以上である必要があります')

        upkeep = _require_int(item.get("upkeep", 0), file, where, "upkeep")
        if upkeep < 0:
            raise DataError(file, where, '"upkeep" は 0 以上である必要があります')

        versions = _require_list(_require_key(item, "versions", file, where), file, where, "versions")
        if len(versions) != version_count:
            raise DataError(
                file, where, f'"versions" は {version_count} 行にしてください（いまは {len(versions)} 行）'
            )
        for line in versions:
            if not _require_str(line, file, where, "versions[]").strip():
                raise DataError(file, where, '"versions" に空の行があります')

        _require_list(item.get("belongs_to", []), file, where, "belongs_to")
        _require_list(item.get("glossary", []), file, where, "glossary")

    return measure_ids


def validate_actions(actions_data: dict[str, Any]) -> set[str]:
    file = "actions.json"
    action_ids: set[str] = set()

    for item in _require_list(_require_key(actions_data, "actions", file, ""), file, "", "actions"):
        action_id = _require_str(_require_key(item, "id", file, ""), file, "", "id")
        where = _where(action_id)

        if action_id in action_ids:
            raise DataError(file, f'id="{action_id}" が', "2 回定義されています")
        action_ids.add(action_id)

        for key in ("name", "summary"):
            _require_str(_require_key(item, key, file, where), file, where, key)

        cost_base = _require_int(_require_key(item, "cost_base", file, where), file, where, "cost_base")
        if cost_base < 0:
            raise DataError(file, where, '"cost_base" は 0 以上である必要があります')

        per_employee = item.get("cost_per_employee", 0)
        if isinstance(per_employee, bool) or not isinstance(per_employee, (int, float)):
            raise DataError(file, where, '"cost_per_employee" は数値である必要があります')
        if per_employee < 0:
            raise DataError(file, where, '"cost_per_employee" は 0 以上である必要があります')

    return action_ids


def validate_events(
    events_data: dict[str, Any], measure_ids: set[str]
) -> set[str]:
    file = "events.json"
    event_ids: set[str] = set()

    for item in _require_list(_require_key(events_data, "events", file, ""), file, "", "events"):
        event_id = _require_str(_require_key(item, "id", file, ""), file, "", "id")
        where = _where(event_id)

        if event_id in event_ids:
            raise DataError(file, f'id="{event_id}" が', "2 回定義されています")
        event_ids.add(event_id)

        _require_str(_require_key(item, "name", file, where), file, where, "name")
        _require_str(_require_key(item, "learning", file, where), file, where, "learning")
        _require_int(_require_key(item, "base_damage", file, where), file, where, "base_damage")
        _require_int(_require_key(item, "weight", file, where), file, where, "weight")

        mitigations = _require_key(item, "mitigations", file, where)
        if not isinstance(mitigations, dict):
            raise DataError(file, where, '"mitigations" は辞書である必要があります')
        for measure_id, effect in mitigations.items():
            if measure_id not in measure_ids:
                raise DataError(file, f'id="{event_id}" が', f'知らない対策 "{measure_id}" を参照しています')
            _require_int(effect, file, where, f'mitigations["{measure_id}"]')
            if not 0 <= effect <= 100:
                raise DataError(file, where, f'効きめ "{measure_id}" は 0〜100 の整数にしてください')

        facility = item.get("requires_facility")
        if facility is not None and facility not in VALID_FACILITIES:
            allowed = " / ".join(VALID_FACILITIES)
            raise DataError(file, where, f'"requires_facility" は {allowed} か null にしてください')

        situation = _require_list(_require_key(item, "situation", file, where), file, where, "situation")
        if not 1 <= len(situation) <= 3:
            raise DataError(file, where, f'"situation" は 1〜3 行にしてください（いまは {len(situation)} 行）')

        choices = _require_list(_require_key(item, "choices", file, where), file, where, "choices")
        if not choices:
            raise DataError(file, where, "選択肢がありません")
        for choice in choices:
            choice_id = _require_str(_require_key(choice, "id", file, where), file, where, "choices[].id")
            choice_where = f'id="{event_id}" の選択肢 "{choice_id}" の'
            _require_str(_require_key(choice, "label", file, choice_where), file, choice_where, "label")
            _require_str(
                _require_key(choice, "result_text", file, choice_where), file, choice_where, "result_text"
            )
            requires = choice.get("requires")
            if requires is not None and requires not in measure_ids:
                raise DataError(file, choice_where, f'"requires" が知らない対策 "{requires}" を指しています')

        for note in _require_list(item.get("no_effect", []), file, where, "no_effect"):
            measure_id = _require_key(note, "measure", file, where)
            if measure_id not in measure_ids:
                raise DataError(file, where, f'no_effect が知らない対策 "{measure_id}" を参照しています')
            _require_str(_require_key(note, "reason", file, where), file, where, "no_effect[].reason")

    return event_ids


def validate_axes(
    config: dict[str, Any],
    measures_data: dict[str, Any],
    events_data: dict[str, Any],
    actions_data: dict[str, Any],
) -> None:
    axis_ids = {axis["id"] for axis in config["axes"]}

    for file, key, items in (
        ("measures.json", "measures", measures_data["measures"]),
        ("actions.json", "actions", actions_data["actions"]),
    ):
        for item in items:
            for axis_id in item.get("axes", {}):
                if axis_id not in axis_ids:
                    raise DataError(file, _where(item["id"]), f'知らない観点 "{axis_id}" を指しています')

    for item in events_data["events"]:
        for axis_id in item.get("axes", ()):
            if axis_id not in axis_ids:
                raise DataError("events.json", _where(item["id"]), f'知らない観点 "{axis_id}" を指しています')


def validate_glossary(
    glossary_data: dict[str, Any], known_ids: set[str]
) -> set[str]:
    file = "glossary.json"
    term_ids: set[str] = set()

    for item in _require_list(_require_key(glossary_data, "terms", file, ""), file, "", "terms"):
        term_id = _require_str(_require_key(item, "id", file, ""), file, "", "id")
        where = _where(term_id)

        if term_id in term_ids:
            raise DataError(file, f'id="{term_id}" が', "2 回定義されています")
        term_ids.add(term_id)

        for key in ("formal", "reading", "easy"):
            _require_str(_require_key(item, key, file, where), file, where, key)

        description = _require_list(
            _require_key(item, "description", file, where), file, where, "description"
        )
        if not 1 <= len(description) <= 2:
            raise DataError(
                file, where, f"説明が {len(description)} 行あります（2 行までにしてください）"
            )

        for ref in _require_list(item.get("appears_in", []), file, where, "appears_in"):
            if ref not in known_ids:
                raise DataError(file, where, f'appears_in の "{ref}" は対策にも事件にもありません')

    return term_ids


def validate_glossary_references(
    measures_data: dict[str, Any], events_data: dict[str, Any], term_ids: set[str]
) -> None:
    for file, key, items in (
        ("measures.json", "measures", measures_data["measures"]),
        ("events.json", "events", events_data["events"]),
    ):
        for item in items:
            for term_id in item.get("glossary", []):
                if term_id not in term_ids:
                    raise DataError(
                        file, _where(item["id"]), f'知らない用語 "{term_id}" を参照しています'
                    )


def validate_school(school_data: dict[str, Any]) -> None:
    file = "school.json"

    turns = _require_int(_require_key(school_data, "turns", file, ""), file, "", "turns")
    school_measure_ids: set[str] = set()

    for item in _require_list(_require_key(school_data, "measures", file, ""), file, "", "measures"):
        measure_id = _require_str(_require_key(item, "id", file, ""), file, "", "id")
        if not measure_id.startswith(SCHOOL_PREFIX):
            raise DataError(file, f'id="{measure_id}" は', f'"{SCHOOL_PREFIX}" で始めてください')
        if not _require_str(
            _require_key(item, "weakness", file, _where(measure_id)), file, _where(measure_id), "weakness"
        ).strip():
            raise DataError(file, _where(measure_id), '"weakness" が空です')
        school_measure_ids.add(measure_id)

    seen_turns: set[int] = set()
    for item in _require_list(_require_key(school_data, "events", file, ""), file, "", "events"):
        event_id = _require_str(_require_key(item, "id", file, ""), file, "", "id")
        where = _where(event_id)
        if not event_id.startswith(SCHOOL_PREFIX):
            raise DataError(file, f'id="{event_id}" は', f'"{SCHOOL_PREFIX}" で始めてください')

        turn = _require_int(_require_key(item, "turn", file, where), file, where, "turn")
        if not 1 <= turn <= turns:
            raise DataError(file, where, f'"turn" は 1〜{turns} にしてください（いまは {turn}）')
        if turn in seen_turns:
            raise DataError(file, f"turn={turn} が", "2 回使われています")
        seen_turns.add(turn)

        for measure_id in _require_key(item, "mitigations", file, where):
            if measure_id not in school_measure_ids:
                raise DataError(file, where, f'知らない対策 "{measure_id}" を参照しています')

        choices = _require_list(_require_key(item, "choices", file, where), file, where, "choices")
        if not choices:
            raise DataError(file, where, "選択肢がありません")


def load_all() -> dict[str, dict[str, Any]]:
    config = load("config")
    validate_config(config)

    measures_data = load("measures")
    measure_ids = validate_measures(measures_data, len(config["versions"]["levels"]))

    actions_data = load("actions")
    action_ids = validate_actions(actions_data)

    events_data = load("events")
    event_ids = validate_events(events_data, measure_ids)

    validate_axes(config, measures_data, events_data, actions_data)

    glossary_data = load("glossary")
    term_ids = validate_glossary(glossary_data, measure_ids | event_ids | action_ids)
    validate_glossary_references(measures_data, events_data, term_ids)

    school_data = load("school")
    validate_school(school_data)

    return {
        "config": config,
        "measures": measures_data,
        "actions": actions_data,
        "events": events_data,
        "glossary": glossary_data,
        "school": school_data,
    }
