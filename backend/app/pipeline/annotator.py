from __future__ import annotations

from dataclasses import dataclass

from app.pipeline.knowledge_mapping import KnowledgeMappingEngine


@dataclass
class LineAnnotation:
    line_number: int
    text: str
    has_info: bool
    theorem_name: str | None
    short_explanation: str | None
    concept_summary: str | None
    knowledge_id: str | None
    concept_key: str | None


class LeanCodeAnnotator:
    def __init__(self, knowledge_engine: KnowledgeMappingEngine) -> None:
        self.knowledge_engine = knowledge_engine

    def annotate(self, lean_code: str) -> list[LineAnnotation]:
        annotations: list[LineAnnotation] = []
        for line_number, line in enumerate(lean_code.splitlines(), start=1):
            stripped = line.rstrip()
            if not stripped:
                annotations.append(
                    LineAnnotation(
                        line_number=line_number,
                        text=line,
                        has_info=False,
                        theorem_name=None,
                        short_explanation=None,
                        concept_summary=None,
                        knowledge_id=None,
                        concept_key=None,
                    )
                )
                continue

            knowledge = self.knowledge_engine.map_line(stripped)
            annotations.append(
                LineAnnotation(
                    line_number=line_number,
                    text=line,
                    has_info=knowledge is not None,
                    theorem_name=knowledge.theorem_name if knowledge else None,
                    short_explanation=knowledge.summary if knowledge else None,
                    concept_summary=knowledge.detailed_explanation if knowledge else None,
                    knowledge_id=knowledge.id if knowledge else None,
                    concept_key=knowledge.concept_key if knowledge else None,
                )
            )
        return annotations
