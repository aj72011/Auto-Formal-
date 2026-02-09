from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any


class TelemetryLogger:
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        if not self.file_path.exists():
            self.file_path.write_text("", encoding="utf-8")

    def append(self, event_type: str, payload: dict[str, Any], request_id: str | None = None) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "request_id": request_id,
            "payload": payload,
        }
        line = json.dumps(record, ensure_ascii=True)
        with self._lock:
            with self.file_path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")

    def read_all(self, limit: int = 2000) -> list[dict[str, Any]]:
        if not self.file_path.exists():
            return []
        lines = self.file_path.read_text(encoding="utf-8").splitlines()
        records: list[dict[str, Any]] = []
        for line in lines[-limit:]:
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return records
