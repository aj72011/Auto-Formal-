from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExplanationStep:
    line_number: int
    tactic: str
    explanation: str


@dataclass
class ExplanationBundle:
    summary: str
    steps: list[ExplanationStep] = field(default_factory=list)


TACTIC_EXPLANATIONS: dict[str, str] = {
    "intro": "Introduces universally quantified variables or assumptions into the proof context.",
    "intros": "Introduces multiple variables/assumptions into the proof context.",
    "exact": "Closes the goal by providing a term that matches the goal exactly.",
    "simpa": "Simplifies the goal using known lemmas and closes it if both sides match.",
    "simp": "Runs simplification rules to reduce the goal.",
    "rfl": "Uses reflexivity when both sides of an equality are definitionally equal.",
    "apply": "Transforms the goal by applying a theorem whose conclusion matches the target.",
    "constructor": "Splits conjunction goals into separate subgoals.",
    "cases": "Performs case analysis on an inductive hypothesis.",
}


class ExplanationGenerator:
    def generate(self, lean_code: str, verification_status: str) -> ExplanationBundle:
        lines = lean_code.splitlines()
        steps: list[ExplanationStep] = []

        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("theorem "):
                continue
            if stripped == "by":
                steps.append(
                    ExplanationStep(
                        line_number=idx,
                        tactic="by",
                        explanation="Starts tactic mode for a constructive proof.",
                    )
                )
                continue

            tactic = stripped.split()[0]
            explanation = TACTIC_EXPLANATIONS.get(
                tactic,
                "Executes a Lean tactic step contributing to the final proof.",
            )
            steps.append(
                ExplanationStep(
                    line_number=idx,
                    tactic=tactic,
                    explanation=explanation,
                )
            )

        if verification_status == "verified":
            summary = (
                "The proof type-checks in Lean 4. Each tactic step contributes to a complete formal derivation."
            )
        else:
            summary = (
                "The current proof did not verify. Steps below describe intended tactic actions before failure."
            )

        return ExplanationBundle(summary=summary, steps=steps)
