from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field

from app.pipeline.ast_schema import LogicalAST
from app.pipeline.ast_to_lean_compiler import ASTToLeanCompiler
from app.pipeline.error_analyzer import ErrorAnalysis, LeanErrorAnalyzer
from app.pipeline.lean_verification_engine import LeanVerificationEngine, VerificationResult
from app.pipeline.proof_generator import HuggingFaceProofGenerator, ProofGenerationError


@dataclass
class RepairAttemptRecord:
    attempt: int
    source: str
    lean_code: str
    verification: VerificationResult
    error_class: str
    error_messages: list[str] = field(default_factory=list)
    targeted_fix: str = ""
    diff_from_previous: str = ""


class AutomaticRepairLoop:
    _UNICODE_TYPE_REPLACEMENTS = {
        "\u2115": "Nat",
        "\u2124": "Int",
        "\u211d": "Float",
    }
    _UNKNOWN_IDENTIFIER_PATTERNS = (
        re.compile(r"unknown identifier\s+['`]?([A-Za-z_][A-Za-z0-9_]*)['`]?"),
        re.compile(r"unknown constant\s+['`]?([A-Za-z_][A-Za-z0-9_]*)['`]?"),
    )
    _UNKNOWN_UNICODE_TYPE_PATTERNS = (
        re.compile(r"unknown identifier.*\u2115", flags=re.IGNORECASE),
        re.compile(r"unknown constant.*\u2115", flags=re.IGNORECASE),
        re.compile(r"unknown identifier.*\u2124", flags=re.IGNORECASE),
        re.compile(r"unknown constant.*\u2124", flags=re.IGNORECASE),
        re.compile(r"unknown identifier.*\u211d", flags=re.IGNORECASE),
        re.compile(r"unknown constant.*\u211d", flags=re.IGNORECASE),
    )

    def __init__(
        self,
        verifier: LeanVerificationEngine,
        analyzer: LeanErrorAnalyzer,
        generator: HuggingFaceProofGenerator,
        max_repair_attempts: int = 2,
        enabled: bool = True,
        binder_compiler: ASTToLeanCompiler | None = None,
    ) -> None:
        self.verifier = verifier
        self.analyzer = analyzer
        self.generator = generator
        self.max_repair_attempts = max_repair_attempts
        self.enabled = enabled
        self.binder_compiler = binder_compiler or ASTToLeanCompiler()

    def run(
        self,
        statement: str,
        ast: LogicalAST,
        initial_lean_code: str,
        initial_source: str = "ast_compiler",
    ) -> tuple[str, VerificationResult, list[RepairAttemptRecord]]:
        attempts: list[RepairAttemptRecord] = []
        ast_json = ast.model_dump_json()

        current_code = initial_lean_code
        verification = self.verifier.verify(current_code)
        analysis = self.analyzer.analyze(verification)
        attempts.append(
            RepairAttemptRecord(
                attempt=1,
                source=initial_source,
                lean_code=current_code,
                verification=verification,
                error_class=analysis.error_class,
                error_messages=[error.message for error in verification.errors],
                targeted_fix=analysis.suggested_fix,
                diff_from_previous="",
            )
        )

        current_code, verification, analysis = self._apply_unicode_type_repair(
            current_code=current_code,
            verification=verification,
            analysis=analysis,
            attempts=attempts,
            source="unicode_type_autorepair",
        )

        current_code, verification, analysis = self._apply_unknown_identifier_binder_repair(
            current_code=current_code,
            verification=verification,
            analysis=analysis,
            attempts=attempts,
            source="binder_autorepair",
        )

        if verification.status == "verified" or not self.enabled:
            return current_code, verification, attempts

        for repair_index in range(1, self.max_repair_attempts + 1):
            prev_code = current_code
            prev_analysis = analysis
            try:
                generated = self.generator.generate_repair(
                    statement=statement,
                    ast_json=ast_json,
                    previous_code=current_code,
                    error_class=prev_analysis.error_class,
                    error_messages=[error.message for error in verification.errors],
                    targeted_fix=prev_analysis.suggested_fix,
                )
                if generated.status != "success":
                    attempts.append(
                        RepairAttemptRecord(
                            attempt=len(attempts) + 1,
                            source="repair_structured_failure",
                            lean_code=current_code,
                            verification=verification,
                            error_class="generation_failure",
                            error_messages=(
                                [generated.error_message]
                                + generated.validation_failures
                            ),
                            targeted_fix=(
                                "Repair model returned structured failure response; "
                                "keeping previous code."
                            ),
                            diff_from_previous="",
                        )
                    )
                    break
                current_code = generated.lean_code
            except ProofGenerationError as exc:
                attempts.append(
                    RepairAttemptRecord(
                        attempt=len(attempts) + 1,
                        source="repair_generation_failed",
                        lean_code=current_code,
                        verification=verification,
                        error_class="generation_failure",
                        error_messages=[str(exc)],
                        targeted_fix="Model output could not be used; keep previous code.",
                        diff_from_previous="",
                    )
                )
                break

            verification = self.verifier.verify(current_code)
            analysis = self.analyzer.analyze(verification)
            attempts.append(
                RepairAttemptRecord(
                    attempt=len(attempts) + 1,
                    source="repair_loop",
                    lean_code=current_code,
                    verification=verification,
                    error_class=analysis.error_class,
                    error_messages=[error.message for error in verification.errors],
                    targeted_fix=analysis.suggested_fix,
                    diff_from_previous=self._build_diff(prev_code, current_code),
                )
            )

            current_code, verification, analysis = self._apply_unicode_type_repair(
                current_code=current_code,
                verification=verification,
                analysis=analysis,
                attempts=attempts,
                source=f"unicode_type_autorepair_after_repair_{repair_index}",
            )

            current_code, verification, analysis = self._apply_unknown_identifier_binder_repair(
                current_code=current_code,
                verification=verification,
                analysis=analysis,
                attempts=attempts,
                source=f"binder_autorepair_after_repair_{repair_index}",
            )

            if verification.status == "verified":
                break

        return current_code, verification, attempts

    def _apply_unicode_type_repair(
        self,
        current_code: str,
        verification: VerificationResult,
        analysis: ErrorAnalysis,
        attempts: list[RepairAttemptRecord],
        source: str,
    ) -> tuple[str, VerificationResult, ErrorAnalysis]:
        if verification.status == "verified":
            return current_code, verification, analysis

        if not self._needs_unicode_type_repair(current_code, verification):
            return current_code, verification, analysis

        patched_code = self._rewrite_unicode_types(current_code)
        if patched_code == current_code:
            return current_code, verification, analysis

        previous_code = current_code
        current_code = patched_code
        verification = self.verifier.verify(current_code)
        analysis = self.analyzer.analyze(verification)
        attempts.append(
            RepairAttemptRecord(
                attempt=len(attempts) + 1,
                source=source,
                lean_code=current_code,
                verification=verification,
                error_class="unicode_type_rewrite",
                error_messages=[error.message for error in verification.errors],
                targeted_fix="Rewrote unicode core types to Lean 4 core aliases (Nat/Int/Float).",
                diff_from_previous=self._build_diff(previous_code, current_code),
            )
        )
        return current_code, verification, analysis

    def _needs_unicode_type_repair(
        self,
        current_code: str,
        verification: VerificationResult,
    ) -> bool:
        if any(symbol in current_code for symbol in self._UNICODE_TYPE_REPLACEMENTS):
            return True
        for error in verification.errors:
            message = error.message
            if any(pattern.search(message) for pattern in self._UNKNOWN_UNICODE_TYPE_PATTERNS):
                return True
        return False

    def _rewrite_unicode_types(self, lean_code: str) -> str:
        patched = lean_code
        for source, target in self._UNICODE_TYPE_REPLACEMENTS.items():
            patched = patched.replace(source, target)
        return patched

    def _apply_unknown_identifier_binder_repair(
        self,
        current_code: str,
        verification: VerificationResult,
        analysis: ErrorAnalysis,
        attempts: list[RepairAttemptRecord],
        source: str,
    ) -> tuple[str, VerificationResult, ErrorAnalysis]:
        max_rounds = 3
        for _ in range(max_rounds):
            missing_identifiers = self._extract_unknown_identifiers(verification)
            if not missing_identifiers:
                break

            patched_code = self.binder_compiler.add_identifiers_to_theorem_binder(
                lean_code=current_code,
                identifiers=missing_identifiers,
                default_type="Nat",
            )
            if patched_code == current_code:
                break

            previous_code = current_code
            current_code = patched_code
            verification = self.verifier.verify(current_code)
            analysis = self.analyzer.analyze(verification)
            attempts.append(
                RepairAttemptRecord(
                    attempt=len(attempts) + 1,
                    source=source,
                    lean_code=current_code,
                    verification=verification,
                    error_class="missing_binder",
                    error_messages=[error.message for error in verification.errors],
                    targeted_fix=(
                        "Added missing identifiers to theorem binder: "
                        + ", ".join(missing_identifiers)
                    ),
                    diff_from_previous=self._build_diff(previous_code, current_code),
                )
            )

            if verification.status == "verified":
                break

        return current_code, verification, analysis

    def _extract_unknown_identifiers(self, verification: VerificationResult) -> list[str]:
        identifiers: list[str] = []
        seen: set[str] = set()
        for error in verification.errors:
            message = error.message
            lowered = message.lower()
            if "unknown identifier" not in lowered and "unknown constant" not in lowered:
                continue
            for pattern in self._UNKNOWN_IDENTIFIER_PATTERNS:
                for match in pattern.findall(message):
                    candidate = match.strip()
                    if not re.fullmatch(r"[a-z][A-Za-z0-9_]*", candidate):
                        continue
                    if candidate in {"by", "intro", "simp", "exact", "rfl", "trivial"}:
                        continue
                    if candidate in seen:
                        continue
                    seen.add(candidate)
                    identifiers.append(candidate)
        return identifiers

    def _build_diff(self, previous: str, current: str) -> str:
        lines = difflib.unified_diff(
            previous.splitlines(),
            current.splitlines(),
            fromfile="previous.lean",
            tofile="current.lean",
            lineterm="",
        )
        return "\n".join(lines)

