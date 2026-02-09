from __future__ import annotations

from dataclasses import dataclass, field

from app.pipeline.lean_verification_engine import VerificationResult


@dataclass
class ErrorAnalysis:
    error_class: str
    reasons: list[str] = field(default_factory=list)
    suggested_fix: str = ""


class LeanErrorAnalyzer:
    def analyze(self, verification: VerificationResult) -> ErrorAnalysis:
        if verification.status == "verified":
            return ErrorAnalysis(
                error_class="none",
                reasons=[],
                suggested_fix="No repair needed.",
            )

        combined = "\n".join(error.message for error in verification.errors).lower()

        if any(marker in combined for marker in ["invalid syntax", "unexpected token", "expected"]):
            return ErrorAnalysis(
                error_class="syntax",
                reasons=[error.message for error in verification.errors],
                suggested_fix="Rewrite theorem declaration and proof using strict Lean 4 syntax.",
            )
        if any(
            marker in combined
            for marker in ["unknown constant", "unknown identifier", "failed to synthesize inst"]
        ):
            return ErrorAnalysis(
                error_class="missing_theorem",
                reasons=[error.message for error in verification.errors],
                suggested_fix="Replace unknown theorem names with Std/Nat lemmas or explicit proof steps.",
            )
        if any(marker in combined for marker in ["tactic", "failed", "unsolved goals"]):
            return ErrorAnalysis(
                error_class="tactic_misuse",
                reasons=[error.message for error in verification.errors],
                suggested_fix="Adjust tactics and introduce intermediate steps before final exact/simp.",
            )
        if any(marker in combined for marker in ["type mismatch", "application type mismatch"]):
            return ErrorAnalysis(
                error_class="type_mismatch",
                reasons=[error.message for error in verification.errors],
                suggested_fix="Align term types and variable binders to the proposition structure.",
            )

        return ErrorAnalysis(
            error_class="unknown",
            reasons=[error.message for error in verification.errors],
            suggested_fix="Produce a simpler Lean 4 proof with explicit intros and exact/simpa steps.",
        )
