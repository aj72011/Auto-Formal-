from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class KnowledgeEntry:
    id: str
    concept_key: str
    theorem_name: str
    summary: str
    detailed_explanation: str
    research_context: str
    paper_notes: str
    related_theorems: list[str]


class KnowledgeMappingEngine:
    def __init__(self, knowledge_file: Path) -> None:
        self.knowledge_file = knowledge_file
        self.entries = self._load_entries()

    def _load_entries(self) -> dict[str, KnowledgeEntry]:
        if not self.knowledge_file.exists():
            return {}
        payload = json.loads(self.knowledge_file.read_text(encoding="utf-8"))
        entries: dict[str, KnowledgeEntry] = {}
        for item in payload:
            entry = KnowledgeEntry(
                id=item["id"],
                concept_key=item["concept_key"],
                theorem_name=item["theorem_name"],
                summary=item["summary"],
                detailed_explanation=item["detailed_explanation"],
                research_context=item["research_context"],
                paper_notes=item["paper_notes"],
                related_theorems=item.get("related_theorems", []),
            )
            entries[entry.concept_key] = entry
        return entries

    def all_entries(self) -> list[KnowledgeEntry]:
        return list(self.entries.values())

    def map_line(self, line: str) -> KnowledgeEntry | None:
        lowered = line.lower()
        keyword_map = {
            "nat.add_zero": "Nat.add_zero",
            "nat.zero_add": "Nat.zero_add",
            "nat.mul_one": "Nat.mul_one",
            "nat.one_mul": "Nat.one_mul",
            "intro": "intro",
            "exact": "exact",
            "simpa": "simpa",
            "simp": "simp",
            "rfl": "rfl",
            "and.intro": "And.intro",
            "or.inl": "Or.inl",
            "or.inr": "Or.inr",
        }
        for token, concept_key in keyword_map.items():
            if token in lowered and concept_key in self.entries:
                return self.entries[concept_key]
        return None

    def to_dict(self, entry: KnowledgeEntry | None) -> dict | None:
        if entry is None:
            return None
        return asdict(entry)
