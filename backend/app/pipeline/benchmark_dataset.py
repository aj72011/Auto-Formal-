from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BenchmarkTheorem:
    id: str
    statement: str
    tier: int


class BenchmarkDatasetError(Exception):
    """Raised when benchmark dataset structure is invalid."""


def load_benchmark_dataset(dataset_path: Path) -> list[BenchmarkTheorem]:
    if not dataset_path.exists():
        raise BenchmarkDatasetError(f"Dataset not found: {dataset_path}")

    raw = json.loads(dataset_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise BenchmarkDatasetError("Dataset must be a JSON array.")

    items: list[BenchmarkTheorem] = []
    seen_ids: set[str] = set()
    for index, sample in enumerate(raw, start=1):
        if not isinstance(sample, dict):
            raise BenchmarkDatasetError(f"Dataset row {index} must be a JSON object.")

        theorem_id = str(sample.get("id", "")).strip()
        statement = str(sample.get("statement", "")).strip()
        tier = sample.get("tier")

        if not theorem_id:
            raise BenchmarkDatasetError(f"Dataset row {index} is missing non-empty 'id'.")
        if theorem_id in seen_ids:
            raise BenchmarkDatasetError(f"Duplicate theorem id detected: {theorem_id!r}.")
        seen_ids.add(theorem_id)

        if not statement:
            raise BenchmarkDatasetError(
                f"Dataset row {index} ({theorem_id}) is missing non-empty 'statement'."
            )
        if not isinstance(tier, int) or tier < 1 or tier > 4:
            raise BenchmarkDatasetError(
                f"Dataset row {index} ({theorem_id}) must provide integer 'tier' in [1,4]."
            )

        items.append(BenchmarkTheorem(id=theorem_id, statement=statement, tier=tier))

    if len(items) < 50 or len(items) > 100:
        raise BenchmarkDatasetError(
            "Benchmark dataset must contain between 50 and 100 theorems."
        )

    return sorted(items, key=lambda item: item.id)
