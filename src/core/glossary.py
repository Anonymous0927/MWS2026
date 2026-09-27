from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Term:

    id: str
    formal: str
    reading: str
    easy: str
    description: tuple[str, ...]
    appears_in: tuple[str, ...]

    @property
    def display_name(self) -> str:
        return f"{self.easy}（{self.formal}）"

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> Term:
        return Term(
            id=raw["id"],
            formal=raw["formal"],
            reading=raw["reading"],
            easy=raw["easy"],
            description=tuple(raw["description"]),
            appears_in=tuple(raw.get("appears_in", ())),
        )


class Glossary:

    def __init__(self, terms: list[Term]) -> None:
        self._terms = sorted(terms, key=lambda term: term.reading)
        self._by_id = {term.id: term for term in self._terms}

    @staticmethod
    def from_data(raw: dict[str, Any]) -> Glossary:
        return Glossary([Term.from_dict(item) for item in raw["terms"]])

    def all(self) -> list[Term]:
        return list(self._terms)

    def get(self, term_id: str) -> Term:
        return self._by_id[term_id]

    def has(self, term_id: str) -> bool:
        return term_id in self._by_id

    def search(self, query: str) -> list[Term]:
        query = query.strip()
        if not query:
            return self.all()
        return [
            term
            for term in self._terms
            if query in term.easy or query in term.formal or query in term.reading
        ]

    def for_measure(self, measure_id: str) -> list[Term]:
        return self._related_to(measure_id)

    def for_event(self, event_id: str) -> list[Term]:
        return self._related_to(event_id)

    def _related_to(self, target_id: str) -> list[Term]:
        return [term for term in self._terms if target_id in term.appears_in]
