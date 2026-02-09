from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.pipeline.ast_schema import ASTNode, LogicalAST
from app.pipeline.inequality_reasoner import _detect_inequality_cycle
from app.schemas import CapabilityBoundaryPayload


@dataclass
class CapabilityClassification:
    tier: int
    tier_label: str
    status: str
    supported: bool
    reason: str
    signals: list[str] = field(default_factory=list)
    boundary_info: CapabilityBoundaryPayload | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {
            "tier": self.tier,
            "tier_label": self.tier_label,
            "status": self.status,
            "supported": self.supported,
            "reason": self.reason,
            "signals": self.signals,
        }
        if self.boundary_info:
            result["boundary_info"] = self.boundary_info.model_dump()
        return result


class TheoremCapabilityClassifier:
    _UNSUPPORTED_REASON = (
        "The statement requires multi-lemma reasoning outside the current proof subset."
    )

    _TIER4_KEYWORDS = (
        "induction",
        "inductive",
        "recursion",
        "recursive",
        "well-founded",
        "well founded",
        "for all n >= 0",
        "for every n >= 0",
        "fibonacci",
        "factorial",
    )
    _TIER3_KEYWORDS = (
        "transitive",
        "transitivity",
        "antisymmetric",
        "anti-symmetric",
        "chain",
        "therefore",
        "hence",
        "combine",
    )

    def classify(self, statement: str, ast: LogicalAST) -> CapabilityClassification:
        lowered = statement.strip().lower()
        signals: list[str] = []

        # Check if inequality cycle can be handled
        inequality_pattern = _detect_inequality_cycle(statement)
        if inequality_pattern is not None:
            signals.append("Inequality cycle detected; automated proof available.")
            return CapabilityClassification(
                tier=2,
                tier_label="inequality_cycle",
                status="supported",
                supported=True,
                reason="Inequality cycle with transitivity and antisymmetry (automated).",
                signals=signals,
                boundary_info=None,
            )

        if self._is_tier4(lowered, ast, signals):
            boundary_info = self._generate_boundary_guidance(4, statement, ast, signals)
            return CapabilityClassification(
                tier=4,
                tier_label="structured_proof",
                status="capability_boundary",
                supported=False,
                reason="Requires inductive reasoning beyond current automation capability",
                signals=signals,
                boundary_info=boundary_info,
            )

        if self._is_tier3(lowered, ast, signals):
            boundary_info = self._generate_boundary_guidance(3, statement, ast, signals)
            return CapabilityClassification(
                tier=3,
                tier_label="multi_lemma_reasoning",
                status="capability_boundary",
                supported=False,
                reason="Requires multi-step reasoning beyond current automation capability",
                signals=signals,
                boundary_info=boundary_info,
            )

        if self._is_tier1(ast, signals):
            return CapabilityClassification(
                tier=1,
                tier_label="trivial_rewrite",
                status="supported",
                supported=True,
                reason="Tier 1 theorem is inside the supported automated subset.",
                signals=signals,
                boundary_info=None,
            )

        signals.append("Classified as single-step direct lemma/rule application.")
        return CapabilityClassification(
            tier=2,
            tier_label="direct_lemma_application",
            status="supported",
            supported=True,
            reason="Tier 2 theorem is inside the supported automated subset.",
            signals=signals,
            boundary_info=None,
        )

    def _is_tier4(self, lowered: str, ast: LogicalAST, signals: list[str]) -> bool:
        for keyword in self._TIER4_KEYWORDS:
            if keyword in lowered:
                signals.append(f"Tier 4 keyword matched: {keyword!r}.")
                return True

        if self._has_exists_quantifier(ast):
            signals.append("Exists quantifier detected; classified as structured proof.")
            return True

        if self._node_depth(ast.conclusion) >= 7:
            signals.append("Conclusion depth is high; likely structured proof.")
            return True

        return False

    def _is_tier3(self, lowered: str, ast: LogicalAST, signals: list[str]) -> bool:
        for keyword in self._TIER3_KEYWORDS:
            if keyword in lowered:
                signals.append(f"Tier 3 keyword matched: {keyword!r}.")
                return True

        raw_chain = self._extract_if_and_then_chain(lowered)
        if raw_chain is not None:
            left, right, conclusion = raw_chain
            if conclusion not in {left, right}:
                signals.append(
                    "Conditional chain 'if A and B then C' detected where C differs from A/B."
                )
                return True

        if len(ast.hypotheses) >= 2:
            if any(hyp.model_dump() == ast.conclusion.model_dump() for hyp in ast.hypotheses):
                signals.append(
                    "Multiple hypotheses detected but conclusion directly matches a hypothesis."
                )
                return False
            signals.append("Multiple hypotheses detected; likely chaining/multi-lemma reasoning.")
            return True

        connective_count = self._connective_count(ast.conclusion)
        connective_count += sum(self._connective_count(node) for node in ast.hypotheses)
        if connective_count >= 2:
            signals.append("Multiple connectives detected in theorem structure.")
            return True

        return False

    def _is_tier1(self, ast: LogicalAST, signals: list[str]) -> bool:
        if ast.hypotheses:
            return False

        conclusion = ast.conclusion
        if conclusion.kind == "equality" and conclusion.left and conclusion.right:
            if conclusion.left.model_dump() == conclusion.right.model_dump():
                signals.append("Reflexive equality detected.")
                return True
            if self._is_identity_pattern(conclusion.left, conclusion.right):
                signals.append("Identity rewrite equality detected.")
                return True

        return False

    def _is_identity_pattern(self, left: ASTNode, right: ASTNode) -> bool:
        if left.kind == "binary" and left.op in {"+", "*"} and left.left and left.right:
            if left.op == "+" and left.right.kind == "int" and left.right.value == 0:
                return right.kind == "var" and left.left.kind == "var" and left.left.name == right.name
            if left.op == "+" and left.left.kind == "int" and left.left.value == 0:
                return right.kind == "var" and left.right.kind == "var" and left.right.name == right.name
            if left.op == "*" and left.right.kind == "int" and left.right.value == 1:
                return right.kind == "var" and left.left.kind == "var" and left.left.name == right.name
            if left.op == "*" and left.left.kind == "int" and left.left.value == 1:
                return right.kind == "var" and left.right.kind == "var" and left.right.name == right.name
        return False

    def _has_exists_quantifier(self, ast: LogicalAST) -> bool:
        return any(node.kind == "exists" for node in ast.quantifiers)

    def _node_depth(self, node: ASTNode | None) -> int:
        if node is None:
            return 0
        depths = [
            self._node_depth(node.left),
            self._node_depth(node.right),
            *(self._node_depth(item) for item in node.args),
            *(self._node_depth(item) for item in node.operands),
        ]
        return 1 + (max(depths) if depths else 0)

    def _connective_count(self, node: ASTNode | None) -> int:
        if node is None:
            return 0
        count = 1 if node.kind == "connective" else 0
        count += self._connective_count(node.left)
        count += self._connective_count(node.right)
        count += sum(self._connective_count(item) for item in node.args)
        count += sum(self._connective_count(item) for item in node.operands)
        return count

    def _extract_if_and_then_chain(self, lowered: str) -> tuple[str, str, str] | None:
        normalized = re.sub(r"[.,]", " ", lowered)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        match = re.search(r"\bif\s+(.+?)\s+and\s+(.+?)\s+then\s+(.+)$", normalized)
        if match is None:
            return None
        left = match.group(1).strip()
        right = match.group(2).strip()
        conclusion = match.group(3).strip()
        if not left or not right or not conclusion:
            return None
        return left, right, conclusion

    def _generate_boundary_guidance(
        self,
        tier: int,
        statement: str,
        ast: LogicalAST,
        signals: list[str]
    ) -> CapabilityBoundaryPayload:
        """
        Generate educational guidance for capability boundary cases.
        Provides specific lemmas, topics, and skeleton for manual proof completion.
        """
        missing_lemmas = []
        recommended_topics = []
        subgoals = []
        proof_depth = 0
        human_explanation = ""

        if tier == 4:  # Structured proof / induction
            missing_lemmas = [
                "Nat.add_zero",
                "Nat.zero_add",
                "Nat.succ_add",
                "Nat.add_succ",
                "Nat.add_comm",
                "Nat.add_assoc"
            ]
            recommended_topics = [
                "Mathematical induction on natural numbers",
                "Well-founded recursion and termination",
                "Inductive types and constructors in Lean",
                "The 'induction' tactic in Lean 4"
            ]
            subgoals = [
                "Identify the base case (typically n = 0)",
                "State the inductive hypothesis",
                "Prove the inductive step (n → n+1)",
                "Apply the induction tactic with appropriate motive"
            ]
            proof_depth = 8
            human_explanation = (
                "This theorem requires mathematical induction or recursive reasoning over natural numbers. "
                "The current automated system handles direct rewrites and single-step lemma applications, "
                "but inductive proofs require manual tactic orchestration. "
                "To complete this proof manually, you'll need to structure it as a base case and inductive step, "
                "then apply the 'induction' tactic. Study Lean's induction tactic syntax and natural number lemmas."
            )

        elif tier == 3: # Multi-lemma reasoning
            missing_lemmas = [
                "Eq.trans",
                "Eq.symm",
                "Eq.refl",
                "And.intro",
                "And.left",
                "And.right"
            ]
            recommended_topics = [
                "Transitivity and symmetry of equality",
                "Logical connectives (and, or, implies)",
                "Proof composition and chaining",
                "Forward and backward reasoning"
            ]
            subgoals = [
                "Identify intermediate equalities or propositions",
                "Apply transitivity to chain equalities",
                "Decompose compound hypotheses with And.left/And.right",
                "Combine results with logical connectives"
            ]
            proof_depth = 4
            human_explanation = (
                "This theorem requires chaining multiple lemmas together through intermediate steps. "
                "The automated system handles single-step proofs, but multi-step reasoning with "
                "intermediate goals requires explicit guidance. "
                "To complete this proof, identify the chain of reasoning: what intermediate facts "
                "can you derive from the hypotheses, and how do they combine to prove the conclusion? "
                "Study transitivity (Eq.trans) and how to decompose compound hypotheses."
            )

        # Generate Lean skeleton
        lean_skeleton = self._generate_lean_skeleton(statement, ast, tier)

        return CapabilityBoundaryPayload(
            missing_lemmas=missing_lemmas,
            proof_depth_estimate=proof_depth,
            recommended_topics=recommended_topics,
            subgoals=subgoals,
            lean_skeleton=lean_skeleton,
            human_explanation=human_explanation
        )

    def _generate_lean_skeleton(
        self,
        statement: str,
        ast: LogicalAST,
        tier: int
    ) -> str:
        """
        Generate a partial Lean theorem with sorry placeholders for manual completion.
        """
        # Extract theorem name (simplified - sanitize statement)
        theorem_name = "manual_proof_theorem"
        
        # Build quantifier string
        quantifiers_str = " ".join(
            f"({q.var} : {q.var_type})" for q in ast.quantifiers
        )
        
        # Build conclusion hint (simplified)
        conclusion_hint = "-- Prove the conclusion using the tactics and lemmas listed above"
        
        if tier == 4:
            # Induction skeleton
            tactics_hint = """  -- Suggested approach:
  -- 1. Use 'induction n' to split into base and inductive cases
  -- 2. Base case: Prove for n = 0 (often by 'rfl' or lemma application)
  -- 3. Inductive case: Assume true for n, prove for n+1
  -- 4. In inductive step, use hypothesis and relevant Nat lemmas"""
        elif tier == 3:
            # Multi-step skeleton
            tactics_hint = """  -- Suggested approach:
  -- 1. Introduce hypotheses with 'intro'
  -- 2. Decompose 'and' hypotheses with 'have h1 := hypothesis.left'
  -- 3. Apply transitivity as needed: 'trans intermediate_value'
  -- 4. Close goals with 'exact' or lemma application"""
        else:
            tactics_hint = """  -- Suggested approach:
  -- 1. Introduce variables and hypotheses
  -- 2. Apply relevant lemmas
  -- 3. Use 'exact' or 'rfl' to close the goal"""

        skeleton_code = f"""-- Original statement: {statement}
-- This proof requires manual completion

theorem {theorem_name} {quantifiers_str} :
  sorry
  /{tactics_hint}
  {conclusion_hint}
  sorry
-/
"""
        return skeleton_code
