from __future__ import annotations

import re
from dataclasses import dataclass

from app.pipeline.ast_schema import ASTNode, LogicalAST, QuantifierNode, VariableDecl


class SemanticParseError(Exception):
    """Raised when deterministic parsing cannot produce a valid AST."""


def _clean_text(statement: str) -> str:
    text = statement.strip()
    text = re.sub(r"\s+", " ", text)
    return text.rstrip(".")


def _derive_theorem_name(statement: str) -> str:
    tokens = re.findall(r"[A-Za-z0-9]+", statement.lower())
    slug = "_".join(tokens[:8]) if tokens else "generated_theorem"
    return f"autoformal_{slug}"


def _split_variable_list(raw: str) -> list[str]:
    normalized = raw.replace(",", " and ")
    parts = [part.strip() for part in normalized.split("and") if part.strip()]
    return [part for part in parts if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", part)]


@dataclass
class _TermCursor:
    tokens: list[str]
    index: int = 0

    def peek(self) -> str | None:
        if self.index >= len(self.tokens):
            return None
        return self.tokens[self.index]

    def pop(self) -> str:
        token = self.peek()
        if token is None:
            raise SemanticParseError("Unexpected end of expression.")
        self.index += 1
        return token


class DeterministicSemanticParser:
    def parse(self, statement: str) -> LogicalAST:
        cleaned = _clean_text(statement)
        quantifiers, variables, body, matched_pattern = self._extract_quantifiers(cleaned)

        prop_variables = {var.name for var in variables if var.type == "Prop"}
        formula = self._parse_formula(body, prop_variables=prop_variables)
        hypotheses, conclusion = self._split_hypotheses_conclusion(formula)

        theorem_references = self._collect_references(conclusion)
        for hyp in hypotheses:
            theorem_references.extend(self._collect_references(hyp))

        deduped_references = list(dict.fromkeys(theorem_references))
        return LogicalAST(
            statement=statement,
            theorem_name=_derive_theorem_name(statement),
            quantifiers=quantifiers,
            variables=variables,
            hypotheses=hypotheses,
            conclusion=conclusion,
            theorem_references=deduped_references,
            parser_metadata={
                "parser": "deterministic_rule_parser",
                "matched_pattern": matched_pattern,
            },
        )

    def _extract_quantifiers(
        self, cleaned: str
    ) -> tuple[list[QuantifierNode], list[VariableDecl], str, str]:
        nat_prefixes = [
            "for every natural number ",
            "for all natural number ",
            "for every natural numbers ",
            "for all natural numbers ",
        ]
        for prefix in nat_prefixes:
            extracted = self._extract_prefixed_segments(cleaned, prefix)
            if extracted is None:
                continue
            var_text, body = extracted
            names = _split_variable_list(var_text)
            if not names:
                raise SemanticParseError("Could not parse natural-number quantifier variables.")
            variables = [VariableDecl(name=name, type="Nat") for name in names]
            quantifiers = [QuantifierNode(kind="forall", variable=var) for var in variables]
            pattern_name = "forall_single_nat" if len(variables) == 1 else "forall_nat"
            return quantifiers, variables, body, pattern_name

        prop_prefixes = [
            "for propositions ",
            "for proposition ",
        ]
        for prefix in prop_prefixes:
            extracted = self._extract_prefixed_segments(cleaned, prefix)
            if extracted is None:
                continue
            var_text, body = extracted
            names = _split_variable_list(var_text)
            if not names:
                raise SemanticParseError("Could not parse proposition quantifier variables.")
            variables = [VariableDecl(name=name, type="Prop") for name in names]
            quantifiers = [QuantifierNode(kind="forall", variable=var) for var in variables]
            return quantifiers, variables, body, "forall_prop"

        return [], [], cleaned, "no_explicit_quantifier"

    def _extract_prefixed_segments(
        self,
        cleaned: str,
        lowercase_prefix: str,
    ) -> tuple[str, str] | None:
        lowered = cleaned.lower()
        if not lowered.startswith(lowercase_prefix):
            return None
        remainder = cleaned[len(lowercase_prefix) :].strip()
        if not remainder:
            raise SemanticParseError("Quantifier prefix found but no body detected.")
        if "," in remainder:
            var_text, body = remainder.split(",", 1)
            return var_text.strip(), body.strip()
        if " if " in remainder.lower():
            idx = remainder.lower().find(" if ")
            var_text = remainder[:idx].strip()
            body = remainder[idx + 1 :].strip()
            return var_text, body
        raise SemanticParseError(
            "Expected a comma after quantified variables to separate statement body."
        )

    def _normalize_formula_text(self, text: str) -> str:
        normalized = text.strip().rstrip(".")
        replacements = {
            " plus ": " + ",
            " times ": " * ",
            " multiplied by ": " * ",
            " equals ": " = ",
            " is equal to ": " = ",
        }
        lowered = f" {normalized} "
        for source, target in replacements.items():
            lowered = lowered.replace(source, target)
        return lowered.strip()

    def _parse_formula(self, text: str, prop_variables: set[str]) -> ASTNode:
        normalized = self._normalize_formula_text(text)

        if normalized.lower().startswith("if ") and " then " in normalized.lower():
            idx = normalized.lower().find(" then ")
            antecedent = normalized[3:idx].strip()
            consequent = normalized[idx + 6 :].strip()
            return ASTNode(
                kind="connective",
                op="implies",
                operands=[
                    self._parse_formula(antecedent, prop_variables),
                    self._parse_formula(consequent, prop_variables),
                ],
            )

        if " and " in normalized.lower():
            parts = re.split(r"\band\b", normalized, flags=re.IGNORECASE)
            parsed_parts = [
                self._parse_formula(part.strip(), prop_variables)
                for part in parts
                if part.strip()
            ]
            if len(parsed_parts) > 1:
                return ASTNode(kind="connective", op="and", operands=parsed_parts)

        if " or " in normalized.lower():
            parts = re.split(r"\bor\b", normalized, flags=re.IGNORECASE)
            parsed_parts = [
                self._parse_formula(part.strip(), prop_variables)
                for part in parts
                if part.strip()
            ]
            if len(parsed_parts) > 1:
                return ASTNode(kind="connective", op="or", operands=parsed_parts)

        if "=" in normalized:
            left_raw, right_raw = normalized.split("=", 1)
            return ASTNode(
                kind="equality",
                left=self._parse_term(left_raw.strip()),
                right=self._parse_term(right_raw.strip()),
            )

        divides_match = re.match(
            r"^(?P<a>[A-Za-z][A-Za-z0-9_]*|\d+)\s+divides\s+(?P<b>.+)$",
            normalized,
            flags=re.IGNORECASE,
        )
        if divides_match:
            return ASTNode(
                kind="predicate",
                name="dvd",
                args=[
                    self._parse_term(divides_match.group("a").strip()),
                    self._parse_term(divides_match.group("b").strip()),
                ],
            )

        even_prefix = re.match(r"^even\s+(.+)$", normalized, flags=re.IGNORECASE)
        if even_prefix:
            return ASTNode(
                kind="predicate",
                name="Even",
                args=[self._parse_term(even_prefix.group(1).strip())],
            )

        even_suffix = re.match(r"^(.+)\s+is\s+even$", normalized, flags=re.IGNORECASE)
        if even_suffix:
            return ASTNode(
                kind="predicate",
                name="Even",
                args=[self._parse_term(even_suffix.group(1).strip())],
            )

        odd_prefix = re.match(r"^odd\s+(.+)$", normalized, flags=re.IGNORECASE)
        if odd_prefix:
            return ASTNode(
                kind="predicate",
                name="Odd",
                args=[self._parse_term(odd_prefix.group(1).strip())],
            )

        odd_suffix = re.match(r"^(.+)\s+is\s+odd$", normalized, flags=re.IGNORECASE)
        if odd_suffix:
            return ASTNode(
                kind="predicate",
                name="Odd",
                args=[self._parse_term(odd_suffix.group(1).strip())],
            )

        if "<=" in normalized:
            left_raw, right_raw = normalized.split("<=", 1)
            return ASTNode(
                kind="predicate",
                name="le",
                args=[
                    self._parse_term(left_raw.strip()),
                    self._parse_term(right_raw.strip()),
                ],
            )

        if "<" in normalized:
            left_raw, right_raw = normalized.split("<", 1)
            return ASTNode(
                kind="predicate",
                name="lt",
                args=[
                    self._parse_term(left_raw.strip()),
                    self._parse_term(right_raw.strip()),
                ],
            )

        if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", normalized) and normalized in prop_variables:
            return ASTNode(kind="var", name=normalized)

        # Fallback: treat as theorem/predicate reference for inspectable AST output.
        return ASTNode(kind="reference", theorem_ref=normalized)

    def _tokenize_term(self, term: str) -> list[str]:
        tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*|\d+|[()+*]", term)
        if not tokens:
            raise SemanticParseError(f"Failed to tokenize term: {term!r}")
        return tokens

    def _parse_term(self, term: str) -> ASTNode:
        cursor = _TermCursor(tokens=self._tokenize_term(term))
        parsed = self._parse_add(cursor)
        if cursor.peek() is not None:
            raise SemanticParseError(f"Unexpected token in term: {cursor.peek()}")
        return parsed

    def _parse_add(self, cursor: _TermCursor) -> ASTNode:
        node = self._parse_mul(cursor)
        while cursor.peek() == "+":
            cursor.pop()
            rhs = self._parse_mul(cursor)
            node = ASTNode(kind="binary", op="+", left=node, right=rhs)
        return node

    def _parse_mul(self, cursor: _TermCursor) -> ASTNode:
        node = self._parse_atom(cursor)
        while cursor.peek() == "*":
            cursor.pop()
            rhs = self._parse_atom(cursor)
            node = ASTNode(kind="binary", op="*", left=node, right=rhs)
        return node

    def _parse_atom(self, cursor: _TermCursor) -> ASTNode:
        token = cursor.pop()
        if token == "(":
            node = self._parse_add(cursor)
            if cursor.pop() != ")":
                raise SemanticParseError("Missing closing parenthesis in term.")
            return node
        if token.isdigit():
            return ASTNode(kind="int", value=int(token))
        return ASTNode(kind="var", name=token)

    def _split_hypotheses_conclusion(self, formula: ASTNode) -> tuple[list[ASTNode], ASTNode]:
        if formula.kind == "connective" and formula.op == "implies" and len(formula.operands) == 2:
            hypotheses = self._explode_hypotheses(formula.operands[0])
            conclusion = formula.operands[1]
            return hypotheses, conclusion
        return [], formula

    def _explode_hypotheses(self, node: ASTNode) -> list[ASTNode]:
        if node.kind == "connective" and node.op == "and":
            flattened: list[ASTNode] = []
            for operand in node.operands:
                flattened.extend(self._explode_hypotheses(operand))
            return flattened
        return [node]

    def _collect_references(self, node: ASTNode | None) -> list[str]:
        if node is None:
            return []
        refs: list[str] = []
        if node.kind == "equality" and node.left and node.right:
            if self._is_add_zero_pattern(node.left, node.right):
                refs.append("Nat.add_zero")
            if self._is_zero_add_pattern(node.left, node.right):
                refs.append("Nat.zero_add")
        if node.kind == "reference" and node.theorem_ref:
            refs.append(node.theorem_ref)
        refs.extend(self._collect_references(node.left))
        refs.extend(self._collect_references(node.right))
        for item in node.args:
            refs.extend(self._collect_references(item))
        for item in node.operands:
            refs.extend(self._collect_references(item))
        return refs

    def _is_add_zero_pattern(self, left: ASTNode, right: ASTNode) -> bool:
        return (
            left.kind == "binary"
            and left.op == "+"
            and left.right is not None
            and left.right.kind == "int"
            and left.right.value == 0
            and right.kind == "var"
            and left.left is not None
            and left.left.kind == "var"
            and left.left.name == right.name
        )

    def _is_zero_add_pattern(self, left: ASTNode, right: ASTNode) -> bool:
        return (
            left.kind == "binary"
            and left.op == "+"
            and left.left is not None
            and left.left.kind == "int"
            and left.left.value == 0
            and right.kind == "var"
            and left.right is not None
            and left.right.kind == "var"
            and left.right.name == right.name
        )
