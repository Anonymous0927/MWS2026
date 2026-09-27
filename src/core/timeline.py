from __future__ import annotations

from .types import TimelineEntry

KIND_BOUGHT = "買った"
KIND_INSTALL = "導入"
KIND_UPGRADE = "強化"
KIND_CANCEL = "解除"
KIND_UNDO = "取消"
KIND_ACTION = "施策"
KIND_UPKEEP = "維持費"
KIND_OMEN = "前兆"
KIND_EXPAND = "拡大"
KIND_PREVENTED = "防げた"
KIND_WARN = "注意"
KIND_DANGER = "あぶない"
KIND_DAMAGE = "被害"
KIND_SETTLE = "決算"

ALL_KINDS = (
    KIND_BOUGHT,
    KIND_INSTALL,
    KIND_UPGRADE,
    KIND_CANCEL,
    KIND_UNDO,
    KIND_ACTION,
    KIND_UPKEEP,
    KIND_OMEN,
    KIND_EXPAND,
    KIND_PREVENTED,
    KIND_WARN,
    KIND_DANGER,
    KIND_DAMAGE,
    KIND_SETTLE,
)


class Timeline:

    def __init__(self) -> None:
        self._entries: list[TimelineEntry] = []

    def add(self, year: int, kind: str, text: str) -> None:
        self._entries.append(TimelineEntry(year=year, kind=kind, text=text))

    def recent(self, limit: int | None = None) -> list[TimelineEntry]:
        if limit is None:
            return list(reversed(self._entries))
        return list(reversed(self._entries[-limit:]))

    def of_year(self, year: int) -> list[TimelineEntry]:
        return [entry for entry in reversed(self._entries) if entry.year == year]

    def all(self) -> list[TimelineEntry]:
        return list(self._entries)

    def __len__(self) -> int:
        return len(self._entries)
