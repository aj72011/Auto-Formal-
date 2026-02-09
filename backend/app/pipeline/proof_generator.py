from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from huggingface_hub import InferenceClient

from app.config import BASE_DIR


GENERATOR_SYSTEM_PROMPT = """You generate Lean 4 formalizations in a strict Lean 4 core subset.
Generate Lean 4 code and explanation. Do not output JSON.

Output format:
```lean
theorem autoformal_generated (n : Nat) : proposition := by
  intro ...
  have ...
  exact ...
```
Explanation:
<short plain-English explanation>

Rules:
- Lean 4 only
- no import statements
- no sorry/admit placeholders
- use core types only: Nat, Int, Float, Bool, Prop
- normalize unicode types: \u2115 -> Nat, \u2124 -> Int, \u211d -> Float
- no unicode math symbols in Lean code
- no mathlib-only tactics/identifiers
- allowed tactics: intro, have, exact, simp, rfl, apply
"""

CORRECTION_SYSTEM_PROMPT = """Your previous response did not contain usable Lean 4 core output.
Return Lean 4 code in a fenced code block plus a short explanation.
Do not output JSON.
"""

FENCED_CODE_PATTERN = re.compile(
    r"```(?:[A-Za-z0-9_+\-]+)?\s*\n?(.*?)```",
    flags=re.DOTALL,
)
LEAN_HINT_PATTERN = re.compile(
    r"\b(theorem|lemma|example|def|axiom|inductive|structure|by|intro|simp|exact|rfl|apply)\b|:=|forall|exists|->|<=",
    flags=re.IGNORECASE,
)
LEAN3_BANNED_PATTERNS = (
    re.compile(r"\bassume\b"),
    re.compile(r"\bbegin\b"),
    re.compile(r"\bend\b"),
    re.compile(r"\bclassical\b"),
    re.compile(r"\bby_cases\b"),
    re.compile(r"\bhave\s+.+\s+from\b"),
)
MATHLIB_BANNED_PATTERNS = (
    re.compile(r"\blinarith\b"),
    re.compile(r"\bnlinarith\b"),
    re.compile(r"\bring\b"),
    re.compile(r"\bnorm_num\b"),
    re.compile(r"\baesop\b"),
    re.compile(r"\bomega\b"),
    re.compile(r"\bsimp_all\b"),
)
THEOREM_HEADER_PATTERN = re.compile(
    r"^theorem\s+[A-Za-z_][A-Za-z0-9_]*(?:\s+\([^)]*\))*\s*:\s*.+:=\s*by$"
)
ALLOWED_TACTIC_PREFIXES = ("intro ", "exact ", "simp", "rfl", "apply ", "have ")

UNICODE_REPLACEMENTS = {
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
    "\u2227": " And ",
    "\u2228": " Or ",
    "\u00d7": "*",
    "\u2212": "-",
}


class ProofGenerationError(Exception):
    """Raised when model output cannot be converted to Lean code."""


@dataclass
class GeneratedProof:
    status: str
    lean_code: str
    explanation: str
    error_message: str
    prompt_used: str
    raw_outputs: list[str] = field(default_factory=list)
    validation_failures: list[str] = field(default_factory=list)


def _replace_unicode_tokens(text: str) -> str:
    normalized = text
    for source, target in UNICODE_REPLACEMENTS.items():
        normalized = normalized.replace(source, target)
    return normalized


def _to_ascii(text: str) -> str:
    return "".join(ch if ch.isascii() else " " for ch in text)


def _sanitize_lean_code(code: str) -> str:
    lines: list[str] = []
    for raw_line in code.splitlines():
        line = _replace_unicode_tokens(raw_line)
        line = _to_ascii(line)
        line = re.sub(r":=\s*begin\b", ":= by", line, flags=re.IGNORECASE)
        line = re.sub(r"\bassume\b", "intro", line, flags=re.IGNORECASE)
        line = re.sub(r"\bhave\s+(.+?)\s+from\s+(.+)", r"have \1 := \2", line, flags=re.IGNORECASE)
        if line.strip().lower().startswith("import "):
            continue
        if line.strip().lower() in {"begin", "end"}:
            continue
        if line.strip().startswith("intro "):
            line = line.replace(",", "")
        lines.append(line.rstrip())

    sanitized = "\n".join(lines).strip()
    sanitized = re.sub(r"\n{3,}", "\n\n", sanitized)
    return sanitized


def _is_lean3_syntax(code: str) -> bool:
    lowered = code.lower()
    markers = (" proof", "\nbegin", "\nend", "\nproof", "assume ")
    has_lean4 = ":= by" in lowered or " by\n" in lowered
    return any(marker in lowered for marker in markers) and not has_lean4


def _looks_like_lean(code: str) -> bool:
    compact = code.strip()
    if not compact:
        return False
    return bool(LEAN_HINT_PATTERN.search(compact))


def _normalize_statement(statement: str) -> str:
    lowered = statement.lower()
    replacements = {
        ",": " ",
        ".": " ",
        "plus": "+",
        "equals": "=",
        "is equal to": "=",
    }
    for source, target in replacements.items():
        lowered = lowered.replace(source, target)
    return " ".join(lowered.split())


def _rule_based_proof(statement: str) -> GeneratedProof | None:
    # Try inequality-based reasoning first (lazy import to avoid circular dependency)
    try:
        from app.pipeline.inequality_reasoner import inequality_based_proof
        inequality_proof = inequality_based_proof(statement)
        if inequality_proof is not None:
            return inequality_proof
    except ImportError:
        pass  # Fall through to pattern matching if module not available
    
    # Then try simple pattern matching
    normalized = _normalize_statement(statement)
    if "n + 0 = n" in normalized:
        return GeneratedProof(
            status="success",
            lean_code=(
                "theorem autoformal_add_zero (n : Nat) : n + 0 = n := by\n"
                "  exact Nat.add_zero n"
            ),
            explanation="Applies Nat.add_zero directly.",
            error_message="",
            prompt_used="rule_based",
        )
    if "0 + n = n" in normalized:
        return GeneratedProof(
            status="success",
            lean_code=(
                "theorem autoformal_zero_add (n : Nat) : 0 + n = n := by\n"
                "  exact Nat.zero_add n"
            ),
            explanation="Applies Nat.zero_add directly.",
            error_message="",
            prompt_used="rule_based",
        )
    if "if p and q then p" in normalized:
        return GeneratedProof(
            status="success",
            lean_code=(
                "theorem autoformal_and_left (P Q : Prop) : And P Q -> P := by\n"
                "  intro h\n"
                "  exact h.left"
            ),
            explanation="Introduces the conjunction hypothesis and projects the left proof.",
            error_message="",
            prompt_used="rule_based",
        )
    return None


class HuggingFaceProofGenerator:
    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_seconds: int = 60,
        structured_retries: int = 1,
        debug_log_file: Path | None = None,
    ) -> None:
        # Flow is fixed: initial generation + one correction pass for unusable text.
        _ = structured_retries

        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.debug_log_file = debug_log_file or (BASE_DIR / "data" / "model_output_debug.jsonl")
        self.debug_log_file.parent.mkdir(parents=True, exist_ok=True)

        if api_key:
            self.client = InferenceClient(api_key=api_key, timeout=timeout_seconds)
        else:
            self.client = None

    def generate_direct(self, statement: str) -> GeneratedProof:
        fallback = _rule_based_proof(statement)
        if fallback is not None:
            return fallback

        payload = self._build_direct_payload(statement)
        return self._generate(request_payload=payload, prompt_label="direct_generation")

    def generate_repair(
        self,
        statement: str,
        ast_json: str,
        previous_code: str,
        error_class: str,
        error_messages: list[str],
        targeted_fix: str,
    ) -> GeneratedProof:
        payload = self._build_repair_payload(
            statement=statement,
            ast_json=ast_json,
            previous_code=previous_code,
            error_class=error_class,
            error_messages=error_messages,
            targeted_fix=targeted_fix,
        )
        return self._generate(request_payload=payload, prompt_label="repair_generation")

    def _build_direct_payload(self, statement: str) -> str:
        return (
            "TASK: formalize\n"
            "STATEMENT:\n"
            f"{statement.strip()}\n"
        )

    def _build_repair_payload(
        self,
        statement: str,
        ast_json: str,
        previous_code: str,
        error_class: str,
        error_messages: list[str],
        targeted_fix: str,
    ) -> str:
        errors_text = "\n".join(f"- {message}" for message in error_messages if message.strip())
        if not errors_text:
            errors_text = "- (no explicit Lean error message captured)"
        return (
            "TASK: repair\n"
            "STATEMENT:\n"
            f"{statement.strip()}\n\n"
            "LOGICAL_AST_JSON:\n"
            f"{ast_json}\n\n"
            "PREVIOUS_LEAN_CODE:\n"
            f"{previous_code.strip()}\n\n"
            f"ERROR_CLASS: {error_class}\n"
            "LEAN_ERRORS:\n"
            f"{errors_text}\n\n"
            "TARGETED_FIX:\n"
            f"{targeted_fix.strip()}\n"
        )

    def _generate(self, request_payload: str, prompt_label: str) -> GeneratedProof:
        if self.client is None:
            return self._synthetic_failure(
                prompt=prompt_label,
                error_message="HF_API_KEY is missing. Model call skipped.",
            )

        raw_outputs: list[str] = []
        validation_failures: list[str] = []
        previous_output = ""

        for phase_name, is_correction in [("initial", False), ("correction", True)]:
            if is_correction and not previous_output:
                break

            output_text = self._call_model(
                request_payload=request_payload,
                correction=is_correction,
                previous_output=previous_output,
            )
            raw_outputs.append(output_text)
            self._append_debug_record(
                event_type="model_raw_output",
                payload={
                    "phase": phase_name,
                    "prompt": prompt_label,
                    "raw_output": output_text,
                },
            )

            lean_code, explanation, failure_reason = self._extract_lean_and_explanation(output_text)
            if failure_reason is None:
                return GeneratedProof(
                    status="success",
                    lean_code=lean_code,
                    explanation=explanation,
                    error_message="",
                    prompt_used=(
                        prompt_label if not is_correction else f"{prompt_label}_correction"
                    ),
                    raw_outputs=raw_outputs,
                    validation_failures=validation_failures,
                )

            validation_failures.append(failure_reason)
            self._append_debug_record(
                event_type="lean_extraction_failure",
                payload={
                    "phase": phase_name,
                    "prompt": prompt_label,
                    "reason": failure_reason,
                },
            )
            previous_output = output_text

        return self._synthetic_failure(
            prompt=prompt_label,
            error_message="Model did not produce usable Lean output.",
            raw_outputs=raw_outputs,
            validation_failures=validation_failures,
        )

    def _build_messages(
        self,
        request_payload: str,
        correction: bool,
        previous_output: str,
    ) -> list[dict[str, str]]:
        if correction:
            return [
                {"role": "system", "content": GENERATOR_SYSTEM_PROMPT},
                {"role": "system", "content": CORRECTION_SYSTEM_PROMPT},
                {"role": "assistant", "content": previous_output[:8000]},
                {"role": "user", "content": request_payload},
            ]
        return [
            {"role": "system", "content": GENERATOR_SYSTEM_PROMPT},
            {"role": "user", "content": request_payload},
        ]

    def _call_model(
        self,
        request_payload: str,
        correction: bool,
        previous_output: str,
    ) -> str:
        assert self.client is not None
        messages = self._build_messages(
            request_payload=request_payload,
            correction=correction,
            previous_output=previous_output,
        )

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,
                max_tokens=1200,
            )
            return self._extract_content_text(completion.choices[0].message.content)
        except Exception as model_error:
            self._append_debug_record(
                event_type="model_call_failed",
                payload={"error": str(model_error), "correction": correction},
            )
            return ""

    def _extract_content_text(self, content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            chunks: list[str] = []
            for item in content:
                if isinstance(item, str):
                    chunks.append(item)
                    continue
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    chunks.append(item["text"])
            if chunks:
                return "\n".join(chunks)
        return str(content)

    def _extract_lean_and_explanation(self, payload_text: str) -> tuple[str, str, str | None]:
        text = payload_text.strip()
        if not text:
            return "", "", "Model returned empty output."

        code_blocks = self._extract_fenced_code_blocks(text)
        if not code_blocks:
            return "", text, "No fenced Lean code block found."

        validation_reasons: list[str] = []
        valid_code = ""
        for block in code_blocks:
            candidate = _sanitize_lean_code(block)
            if not candidate:
                validation_reasons.append("Lean code block was empty after sanitization.")
                continue
            if not _looks_like_lean(candidate):
                validation_reasons.append("No Lean-like theorem/tactic markers in code block.")
                continue
            reason = self._validate_lean_core_subset(candidate)
            if reason is None:
                valid_code = candidate
                break
            validation_reasons.append(reason)

        explanation = self._normalize_explanation(self._strip_fenced_code_blocks(text))

        if not valid_code:
            if not explanation:
                explanation = ""
            reason = validation_reasons[0] if validation_reasons else "No usable Lean code found."
            return "", explanation, reason

        if not explanation:
            explanation = "Generated Lean 4 proof."
        return valid_code, explanation, None

    def _validate_lean_core_subset(self, lean_code: str) -> str | None:
        lines = lean_code.splitlines()
        non_empty = [line.strip() for line in lines if line.strip()]
        if not non_empty:
            return "Lean code is empty."

        header = non_empty[0]
        if not THEOREM_HEADER_PATTERN.fullmatch(header):
            return "Theorem header must follow: theorem name (vars : Type) : proposition := by"

        for idx, raw_line in enumerate(lines):
            line = raw_line.strip()
            if not line:
                continue
            if not line.isascii():
                return "Lean code must be ASCII-only after normalization."
            lowered = line.lower()
            for pattern in LEAN3_BANNED_PATTERNS:
                if pattern.search(lowered):
                    return f"Banned Lean 3 syntax detected: {line!r}"
            for pattern in MATHLIB_BANNED_PATTERNS:
                if pattern.search(lowered):
                    return f"Banned mathlib-only tactic/identifier detected: {line!r}"
            if line.startswith("intro ") and "," in line:
                return "Intro lines must not contain commas."
            if idx == 0:
                continue
            if line.startswith("--"):
                continue
            if line.startswith("theorem "):
                return "Only one theorem per generated block is allowed."
            if not any(line.startswith(prefix) for prefix in ALLOWED_TACTIC_PREFIXES):
                return "Proof must use only intro/exact/simp/rfl/apply tactics."

        if _is_lean3_syntax(lean_code):
            return "Lean code appears to use Lean 3 block syntax."
        return None

    def _extract_fenced_code_blocks(self, text: str) -> list[str]:
        blocks = [match.group(1).strip() for match in FENCED_CODE_PATTERN.finditer(text)]
        return [block for block in blocks if block]

    def _strip_fenced_code_blocks(self, text: str) -> str:
        return FENCED_CODE_PATTERN.sub("", text)

    def _normalize_explanation(self, text: str) -> str:
        normalized = _replace_unicode_tokens(text)
        normalized = _to_ascii(normalized)
        normalized = re.sub(r"\bexplanation\s*:\s*", "", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    def _synthetic_failure(
        self,
        prompt: str,
        error_message: str,
        raw_outputs: list[str] | None = None,
        validation_failures: list[str] | None = None,
    ) -> GeneratedProof:
        result = GeneratedProof(
            status="failure",
            lean_code="",
            explanation="",
            error_message=error_message,
            prompt_used=prompt,
            raw_outputs=raw_outputs or [],
            validation_failures=validation_failures or [],
        )
        self._append_debug_record(
            event_type="generator_failure",
            payload={
                "error_message": error_message,
                "prompt": prompt,
                "validation_failures": result.validation_failures,
            },
        )
        return result

    def _append_debug_record(self, event_type: str, payload: dict[str, Any]) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "payload": payload,
        }
        try:
            with self.debug_log_file.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=True) + "\n")
        except OSError:
            # Debug logging should never break formalization flow.
            pass
