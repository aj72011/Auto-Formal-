from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path


LEAN_PREAMBLE = """import Std
set_option autoImplicit false
"""

UNICODE_CORE_REPLACEMENTS = {
    "\u2115": "Nat",
    "\u2124": "Int",
    "\u211d": "Float",
    "\u2200": "forall",
    "\u2203": "Exists",
    "\u2192": "->",
    "\u2194": "<->",
    "\u2264": "<=",
    "\u2265": ">=",
    "\u2260": "!=",
    "\u00d7": "*",
    "\u2212": "-",
}


@dataclass
class VerificationError:
    message: str
    line: int | None = None
    column: int | None = None


@dataclass
class VerificationResult:
    status: str
    errors: list[VerificationError] = field(default_factory=list)
    latency_ms: int = 0
    stdout: str = ""
    stderr: str = ""


class LeanVerificationEngine:
    def __init__(self, lean_command: str = "lean", timeout_seconds: int = 60) -> None:
        self.lean_command = lean_command
        self.timeout_seconds = timeout_seconds

    def verify(self, lean_code: str) -> VerificationResult:
        started = time.perf_counter()
        if shutil.which(self.lean_command) is None:
            return VerificationResult(
                status="failed",
                errors=[
                    VerificationError(
                        message=(
                            f"Lean command '{self.lean_command}' was not found on PATH."
                        )
                    )
                ],
                latency_ms=self._latency_ms(started),
            )

        sanitized = self._sanitize_before_write(lean_code)
        source = f"{LEAN_PREAMBLE}\n{sanitized.strip()}\n"
        with tempfile.TemporaryDirectory(prefix="autoformalplus-") as temp_dir:
            file_path = Path(temp_dir) / "Main.lean"
            file_path.write_text(source, encoding="utf-8")
            try:
                completed = subprocess.run(
                    [self.lean_command, str(file_path)],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=self.timeout_seconds,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                return VerificationResult(
                    status="failed",
                    errors=[
                        VerificationError(
                            message=(
                                f"Lean verification timed out after {self.timeout_seconds} seconds."
                            )
                        )
                    ],
                    latency_ms=self._latency_ms(started),
                )

        stdout = (completed.stdout or "").strip()
        stderr = (completed.stderr or "").strip()
        diagnostics = "\n".join(part for part in [stderr, stdout] if part).strip()
        errors = self._parse_errors(diagnostics)

        status = "verified" if completed.returncode == 0 else "failed"
        if status == "verified":
            errors = []

        return VerificationResult(
            status=status,
            errors=errors,
            latency_ms=self._latency_ms(started),
            stdout=stdout,
            stderr=stderr,
        )

    def _parse_errors(self, diagnostics: str) -> list[VerificationError]:
        if not diagnostics:
            return []
        parsed_errors: list[VerificationError] = []
        pattern = re.compile(r":(?P<line>\d+):(?P<col>\d+): error: (?P<msg>.+)")
        for raw_line in diagnostics.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            match = pattern.search(line)
            if match:
                parsed_errors.append(
                    VerificationError(
                        message=match.group("msg").strip(),
                        line=int(match.group("line")),
                        column=int(match.group("col")),
                    )
                )
            elif "error" in line.lower():
                parsed_errors.append(VerificationError(message=line))
        if not parsed_errors:
            parsed_errors.append(VerificationError(message=diagnostics))
        return parsed_errors

    def _latency_ms(self, started: float) -> int:
        return int((time.perf_counter() - started) * 1000)

    def _sanitize_before_write(self, lean_code: str) -> str:
        normalized = lean_code
        for source, target in UNICODE_CORE_REPLACEMENTS.items():
            normalized = normalized.replace(source, target)

        lines: list[str] = []
        for raw_line in normalized.splitlines():
            if raw_line.strip().startswith("import "):
                continue
            ascii_line = "".join(ch if ch.isascii() else " " for ch in raw_line)
            lines.append(ascii_line.rstrip())
        return "\n".join(lines)
