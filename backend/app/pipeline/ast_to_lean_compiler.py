from __future__ import annotations

import hashlib
import json
import re
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

from app.pipeline.ast_schema import ASTNode, LogicalAST


class LeanCompilationError(Exception):
    """Raised when AST cannot be compiled into Lean code."""


@dataclass
class BinderInferenceResult:
    theorem_name: str
    binder_names: list[str]
    binder_types: dict[str, str]
    binder_clause: str
    free_variables: list[str]
    validation_ok: bool
    undeclared_variables: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "theorem_name": self.theorem_name,
            "binder_names": self.binder_names,
            "binder_types": self.binder_types,
            "binder_clause": self.binder_clause.strip(),
            "free_variables": self.free_variables,
            "validation_ok": self.validation_ok,
            "undeclared_variables": self.undeclared_variables,
        }


class ASTToLeanCompiler:
    _CORE_TYPE_MAP = {
        "\u2115": "Nat",
        "nat": "Nat",
        "natural": "Nat",
        "naturalnumber": "Nat",
        "naturalnumbers": "Nat",
        "\u2124": "Int",
        "int": "Int",
        "integer": "Int",
        "integers": "Int",
        "\u211d": "Float",
        "real": "Float",
        "reals": "Float",
        "float": "Float",
        "bool": "Bool",
        "prop": "Prop",
    }
    _ALLOWED_TYPES = {"Nat", "Int", "Float", "Bool", "Prop"}
    _LEAN3_BANNED_PATTERNS = (
        re.compile(r"\bassume\b"),
        re.compile(r"\bbegin\b"),
        re.compile(r"\bend\b"),
        re.compile(r"\bclassical\b"),
        re.compile(r"\bby_cases\b"),
        re.compile(r"\bhave\s+.+\s+from\b"),
    )
    _MATHLIB_BANNED_PATTERNS = (
        re.compile(r"\blinarith\b"),
        re.compile(r"\bnlinarith\b"),
        re.compile(r"\bring\b"),
        re.compile(r"\bnorm_num\b"),
        re.compile(r"\baesop\b"),
        re.compile(r"\bomega\b"),
    )
    _THEOREM_HEADER_PATTERN = re.compile(
        r"^theorem\s+[A-Za-z_][A-Za-z0-9_]*(?:\s+\([^)]*\))*\s*:\s*.+:=\s*by$"
    )
    _ALLOWED_TACTIC_PREFIXES = ("intro ", "exact ", "simp", "rfl", "apply ")
    _ASCII_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

    _THEOREM_LINE_PATTERN = re.compile(
        r"^(?P<prefix>\s*theorem\s+\S+)(?P<binders>(?:\s*\([^)]*\))*)\s*:\s*(?P<prop>.+)$"
    )

    def compile(self, ast: LogicalAST) -> str:
        code, _ = self.compile_with_metadata(ast)
        return code

    def compile_with_metadata(self, ast: LogicalAST) -> tuple[str, dict[str, Any]]:
        theorem_name = self._deterministic_theorem_name(ast)
        binder = self._infer_and_validate_binders(ast, theorem_name=theorem_name)
        proposition = self._build_proposition(ast)
        proof_lines = self._build_proof(ast, binder_names=binder.binder_names)

        hypothesis_names = [f"h{i+1}" for i in range(len(ast.hypotheses))]
        intro_targets_in_code = len(hypothesis_names)
        expected_intro_targets = len(ast.hypotheses)
        intro_validation_ok = intro_targets_in_code == expected_intro_targets
        if not intro_validation_ok:
            raise LeanCompilationError(
                "Proof intro targets are inconsistent with implication hypotheses."
            )

        header = f"theorem {theorem_name}{binder.binder_clause} : {proposition} := by"
        code_lines = [header, *proof_lines]
        code = "\n".join(code_lines)
        self._validate_lean4_subset_or_raise(code)
        metadata = {
            "binder_inference": binder.to_dict(),
            "intro_targets": hypothesis_names,
            "intro_validation_ok": intro_validation_ok,
        }
        return code, metadata

    @classmethod
    def add_identifiers_to_theorem_binder(
        cls,
        lean_code: str,
        identifiers: list[str],
        default_type: str = "Nat",
    ) -> str:
        lines = lean_code.splitlines()
        if not lines:
            return lean_code

        theorem_idx = -1
        theorem_match: re.Match[str] | None = None
        for idx, line in enumerate(lines):
            match = cls._THEOREM_LINE_PATTERN.match(line.strip())
            if match:
                theorem_idx = idx
                theorem_match = match
                break
        if theorem_idx < 0 or theorem_match is None:
            return lean_code

        prefix = theorem_match.group("prefix")
        binders_raw = theorem_match.group("binders") or ""
        proposition = theorem_match.group("prop")
        existing_names = cls._extract_binder_names(binders_raw)

        normalized_new: list[str] = []
        for candidate in identifiers:
            cleaned = candidate.strip()
            if not re.fullmatch(r"[a-z][A-Za-z0-9_]*", cleaned):
                continue
            if cleaned in existing_names or cleaned in normalized_new:
                continue
            normalized_new.append(cleaned)

        if not normalized_new:
            return lean_code

        normalized_type = cls._normalize_core_type(default_type)
        appended = "".join(f" ({name} : {normalized_type})" for name in normalized_new)
        lines[theorem_idx] = f"{prefix}{binders_raw}{appended} : {proposition}"
        return "\n".join(lines)

    def _deterministic_theorem_name(self, ast: LogicalAST) -> str:
        canonical = json.dumps(
            {
                "statement": ast.statement,
                "quantifiers": [q.model_dump() for q in ast.quantifiers],
                "variables": [v.model_dump() for v in ast.variables],
                "hypotheses": [h.model_dump() for h in ast.hypotheses],
                "conclusion": ast.conclusion.model_dump(),
            },
            sort_keys=True,
        )
        digest = hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:12]
        return f"autoformal_{digest}"

    def _infer_and_validate_binders(
        self,
        ast: LogicalAST,
        theorem_name: str,
    ) -> BinderInferenceResult:
        ordered_free_vars = self._collect_free_variables(ast)
        inferred_types = self._infer_variable_types(ast, ordered_free_vars)
        for var_name in ordered_free_vars:
            self._assert_ascii_identifier(var_name, "free variable")

        ordered_binder_names: list[str] = []
        for quantifier in ast.quantifiers:
            self._assert_ascii_identifier(quantifier.variable.name, "quantifier variable")
            self._append_unique(ordered_binder_names, quantifier.variable.name)
        for var_name in ordered_free_vars:
            self._append_unique(ordered_binder_names, var_name)

        while True:
            undeclared = [
                name for name in ordered_free_vars if name not in ordered_binder_names
            ]
            if not undeclared:
                break
            for name in undeclared:
                inferred_types.setdefault(name, "Nat")
                self._append_unique(ordered_binder_names, name)

        final_undeclared = [
            name for name in ordered_free_vars if name not in ordered_binder_names
        ]
        validation_ok = len(final_undeclared) == 0
        if not validation_ok:
            raise LeanCompilationError(
                f"Binder synthesis failed for theorem {theorem_name}: undeclared variables {final_undeclared}."
            )

        binder_clause = self._render_binder_clause(ordered_binder_names, inferred_types)
        return BinderInferenceResult(
            theorem_name=theorem_name,
            binder_names=ordered_binder_names,
            binder_types={name: inferred_types[name] for name in ordered_binder_names},
            binder_clause=binder_clause,
            free_variables=ordered_free_vars,
            validation_ok=validation_ok,
            undeclared_variables=final_undeclared,
        )

    def _build_proposition(self, ast: LogicalAST) -> str:
        hypotheses = [self._compile_formula(node) for node in ast.hypotheses]
        conclusion = self._compile_formula(ast.conclusion)
        chain = hypotheses + [conclusion]
        if not chain:
            raise LeanCompilationError("AST has no conclusion.")
        return " -> ".join(chain)

    def _build_proof(self, ast: LogicalAST, binder_names: list[str]) -> list[str]:
        lines: list[str] = []
        hypothesis_names = [f"h{i+1}" for i in range(len(ast.hypotheses))]
        if hypothesis_names:
            lines.append(f"  intro {' '.join(hypothesis_names)}")

        conclusion = ast.conclusion

        add_zero_var = self._match_add_zero(conclusion)
        if add_zero_var is not None and add_zero_var in binder_names:
            lines.append(f"  exact Nat.add_zero {add_zero_var}")
            return lines

        zero_add_var = self._match_zero_add(conclusion)
        if zero_add_var is not None and zero_add_var in binder_names:
            lines.append(f"  exact Nat.zero_add {zero_add_var}")
            return lines

        mul_one_var = self._match_mul_one(conclusion)
        if mul_one_var is not None and mul_one_var in binder_names:
            lines.append(f"  exact Nat.mul_one {mul_one_var}")
            return lines

        one_mul_var = self._match_one_mul(conclusion)
        if one_mul_var is not None and one_mul_var in binder_names:
            lines.append(f"  exact Nat.one_mul {one_mul_var}")
            return lines

        matching_hypothesis = self._find_matching_hypothesis(conclusion, ast.hypotheses)
        if matching_hypothesis is not None:
            lines.append(f"  exact {matching_hypothesis}")
            return lines

        if (
            conclusion.kind == "connective"
            and conclusion.op == "and"
            and len(conclusion.operands) == 2
        ):
            left_name = self._find_matching_hypothesis(conclusion.operands[0], ast.hypotheses)
            right_name = self._find_matching_hypothesis(conclusion.operands[1], ast.hypotheses)
            if left_name and right_name:
                lines.append(f"  exact And.intro {left_name} {right_name}")
                return lines

        if (
            conclusion.kind == "connective"
            and conclusion.op == "or"
            and len(conclusion.operands) == 2
        ):
            left_name = self._find_matching_hypothesis(conclusion.operands[0], ast.hypotheses)
            if left_name:
                lines.append(f"  exact Or.inl {left_name}")
                return lines
            right_name = self._find_matching_hypothesis(conclusion.operands[1], ast.hypotheses)
            if right_name:
                lines.append(f"  exact Or.inr {right_name}")
                return lines

        if conclusion.kind == "equality" and conclusion.left and conclusion.right:
            if self._node_equal(conclusion.left, conclusion.right):
                lines.append("  rfl")
                return lines

        lines.append("  simp")
        return lines

    def _compile_formula(self, node: ASTNode) -> str:
        if node.kind == "equality":
            if not node.left or not node.right:
                raise LeanCompilationError("Malformed equality node.")
            return f"{self._compile_term(node.left)} = {self._compile_term(node.right)}"
        if node.kind == "predicate":
            return self._compile_predicate(node)
        if node.kind == "connective":
            compiled = [self._compile_formula(item) for item in node.operands]
            if node.op == "and":
                return self._fold_connective("And", compiled)
            if node.op == "or":
                return self._fold_connective("Or", compiled)
            if node.op == "implies" and len(compiled) == 2:
                return f"({compiled[0]} -> {compiled[1]})"
            raise LeanCompilationError(f"Unsupported connective operation: {node.op}")
        if node.kind == "var" and node.name:
            self._assert_ascii_identifier(node.name, "formula variable")
            return node.name
        if node.kind == "reference" and node.theorem_ref:
            if " " in node.theorem_ref.strip():
                raise LeanCompilationError(
                    f"Reference expression is not Lean-safe: {node.theorem_ref!r}"
                )
            if not node.theorem_ref.isascii():
                raise LeanCompilationError(
                    f"Reference expression must be ASCII-safe: {node.theorem_ref!r}"
                )
            return node.theorem_ref
        raise LeanCompilationError(f"Unsupported formula node: {node.kind}")

    def _compile_predicate(self, node: ASTNode) -> str:
        name = node.name or "UnknownPredicate"
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", name):
            raise LeanCompilationError(f"Predicate name must be ASCII-safe, got {name!r}.")
        args = [self._compile_term(arg) for arg in node.args]
        if name == "le" and len(args) == 2:
            return f"{args[0]} <= {args[1]}"
        if name == "lt" and len(args) == 2:
            return f"{args[0]} < {args[1]}"
        if name == "dvd" and len(args) == 2:
            return f"Dvd.dvd {args[0]} {args[1]}"
        if name == "Even" and len(args) == 1:
            return f"Nat.Even {args[0]}"
        if name == "Odd" and len(args) == 1:
            return f"Nat.Odd {args[0]}"
        if args:
            return f"{name} {' '.join(args)}"
        return name

    def _compile_term(self, node: ASTNode) -> str:
        if node.kind == "var" and node.name:
            self._assert_ascii_identifier(node.name, "term variable")
            return node.name
        if node.kind == "int":
            return str(node.value)
        if node.kind == "binary":
            if not node.left or not node.right or not node.op:
                raise LeanCompilationError("Malformed binary term node.")
            return f"({self._compile_term(node.left)} {node.op} {self._compile_term(node.right)})"
        raise LeanCompilationError(f"Unsupported term node kind: {node.kind}")

    def _collect_free_variables(self, ast: LogicalAST) -> list[str]:
        ordered: list[str] = []
        seen: set[str] = set()
        for node in [*ast.hypotheses, ast.conclusion]:
            self._collect_node_variables(node, seen, ordered)
        return ordered

    def _collect_node_variables(
        self,
        node: ASTNode | None,
        seen: set[str],
        ordered: list[str],
    ) -> None:
        if node is None:
            return
        if node.kind == "var" and node.name:
            if node.name not in seen:
                seen.add(node.name)
                ordered.append(node.name)
        self._collect_node_variables(node.left, seen, ordered)
        self._collect_node_variables(node.right, seen, ordered)
        for arg in node.args:
            self._collect_node_variables(arg, seen, ordered)
        for operand in node.operands:
            self._collect_node_variables(operand, seen, ordered)

    def _infer_variable_types(
        self,
        ast: LogicalAST,
        free_variables: list[str],
    ) -> dict[str, str]:
        inferred: "OrderedDict[str, str]" = OrderedDict()
        for var in ast.variables:
            self._assert_ascii_identifier(var.name, "declared variable")
            inferred[var.name] = self._normalize_core_type(var.type)
        for quantifier in ast.quantifiers:
            self._assert_ascii_identifier(quantifier.variable.name, "quantifier variable")
            inferred[quantifier.variable.name] = self._normalize_core_type(
                quantifier.variable.type
            )
        for name in free_variables:
            inferred.setdefault(name, "Nat")
        return dict(inferred)

    def _render_binder_clause(
        self,
        ordered_names: list[str],
        inferred_types: dict[str, str],
    ) -> str:
        if not ordered_names:
            return ""
        groups: list[tuple[list[str], str]] = []
        current_names: list[str] = []
        current_type: str | None = None
        for name in ordered_names:
            name_type = self._normalize_core_type(inferred_types.get(name, "Nat"))
            if current_type is None or name_type == current_type:
                current_names.append(name)
                current_type = name_type
                continue
            groups.append((current_names, current_type))
            current_names = [name]
            current_type = name_type
        if current_names and current_type is not None:
            groups.append((current_names, current_type))

        segments = [f"({' '.join(names)} : {type_name})" for names, type_name in groups]
        return " " + " ".join(segments)

    @classmethod
    def _extract_binder_names(cls, binders_raw: str) -> set[str]:
        names: set[str] = set()
        for binder_content in re.findall(r"\(([^)]*)\)", binders_raw):
            if ":" not in binder_content:
                continue
            lhs, _ = binder_content.split(":", 1)
            for token in lhs.strip().split():
                if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", token):
                    names.add(token)
        return names

    @classmethod
    def _normalize_core_type(cls, type_name: str) -> str:
        raw = (type_name or "").strip()
        if not raw:
            return "Nat"
        normalized = (
            raw.replace("\u2115", "Nat")
            .replace("\u2124", "Int")
            .replace("\u211d", "Float")
        )
        lookup = normalized.replace(" ", "").lower()
        mapped = cls._CORE_TYPE_MAP.get(lookup)
        if mapped is not None:
            return mapped
        if normalized in cls._ALLOWED_TYPES:
            return normalized
        return "Nat"

    @classmethod
    def _fold_connective(cls, connective: str, parts: list[str]) -> str:
        if not parts:
            raise LeanCompilationError(f"Connective {connective} has no operands.")
        current = parts[0]
        for part in parts[1:]:
            current = f"({connective} {current} {part})"
        return current

    @classmethod
    def _assert_ascii_identifier(cls, value: str, context: str) -> None:
        if not cls._ASCII_IDENTIFIER_PATTERN.fullmatch(value):
            raise LeanCompilationError(
                f"{context} must be ASCII-safe Lean identifier, got {value!r}."
            )

    def _validate_lean4_subset_or_raise(self, lean_code: str) -> None:
        lines = lean_code.splitlines()
        non_empty = [line.strip() for line in lines if line.strip()]
        if not non_empty:
            raise LeanCompilationError("Compiler produced empty Lean code.")

        header = non_empty[0]
        if not self._THEOREM_HEADER_PATTERN.fullmatch(header):
            raise LeanCompilationError(
                "Lean theorem header must follow: theorem name (vars : Type) : proposition := by"
            )

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("import "):
                raise LeanCompilationError("Generated Lean code cannot include imports.")
            if not line.isascii():
                raise LeanCompilationError("Generated Lean code must be ASCII-safe.")

            lowered = line.lower()
            for pattern in self._LEAN3_BANNED_PATTERNS:
                if pattern.search(lowered):
                    raise LeanCompilationError(
                        f"Generated Lean code contains banned Lean 3 syntax: {line!r}"
                    )
            for pattern in self._MATHLIB_BANNED_PATTERNS:
                if pattern.search(lowered):
                    raise LeanCompilationError(
                        f"Generated Lean code uses banned mathlib-only tactic: {line!r}"
                    )

            if line.startswith("intro ") and "," in line:
                raise LeanCompilationError("Intro lines must not contain commas.")

            if line == header:
                continue
            if line.startswith("--"):
                continue

            if not any(line.startswith(prefix) for prefix in self._ALLOWED_TACTIC_PREFIXES):
                raise LeanCompilationError(
                    "Proof lines must use minimal tactics: intro/exact/simp/rfl/apply."
                )

    def _append_unique(self, items: list[str], value: str) -> None:
        if value not in items:
            items.append(value)

    def _find_matching_hypothesis(
        self, conclusion: ASTNode, hypotheses: list[ASTNode]
    ) -> str | None:
        for idx, hypothesis in enumerate(hypotheses, start=1):
            if self._node_equal(conclusion, hypothesis):
                return f"h{idx}"
        return None

    def _node_equal(self, left: ASTNode, right: ASTNode) -> bool:
        return left.model_dump() == right.model_dump()

    def _match_add_zero(self, conclusion: ASTNode) -> str | None:
        if conclusion.kind != "equality" or not conclusion.left or not conclusion.right:
            return None
        left = conclusion.left
        right = conclusion.right
        if (
            left.kind == "binary"
            and left.op == "+"
            and left.left
            and left.right
            and left.left.kind == "var"
            and left.right.kind == "int"
            and left.right.value == 0
            and right.kind == "var"
            and left.left.name == right.name
        ):
            return right.name
        return None

    def _match_zero_add(self, conclusion: ASTNode) -> str | None:
        if conclusion.kind != "equality" or not conclusion.left or not conclusion.right:
            return None
        left = conclusion.left
        right = conclusion.right
        if (
            left.kind == "binary"
            and left.op == "+"
            and left.left
            and left.right
            and left.left.kind == "int"
            and left.left.value == 0
            and left.right.kind == "var"
            and right.kind == "var"
            and left.right.name == right.name
        ):
            return right.name
        return None

    def _match_mul_one(self, conclusion: ASTNode) -> str | None:
        if conclusion.kind != "equality" or not conclusion.left or not conclusion.right:
            return None
        left = conclusion.left
        right = conclusion.right
        if (
            left.kind == "binary"
            and left.op == "*"
            and left.left
            and left.right
            and left.left.kind == "var"
            and left.right.kind == "int"
            and left.right.value == 1
            and right.kind == "var"
            and left.left.name == right.name
        ):
            return right.name
        return None

    def _match_one_mul(self, conclusion: ASTNode) -> str | None:
        if conclusion.kind != "equality" or not conclusion.left or not conclusion.right:
            return None
        left = conclusion.left
        right = conclusion.right
        if (
            left.kind == "binary"
            and left.op == "*"
            and left.left
            and left.right
            and left.left.kind == "int"
            and left.left.value == 1
            and left.right.kind == "var"
            and right.kind == "var"
            and left.right.name == right.name
        ):
            return right.name
        return None
