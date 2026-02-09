from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class VariableDecl(BaseModel):
    name: str
    type: str


class ASTNode(BaseModel):
    kind: Literal[
        "var",
        "int",
        "binary",
        "predicate",
        "equality",
        "connective",
        "reference",
    ]
    name: str | None = None
    op: str | None = None
    value: int | str | None = None
    left: ASTNode | None = None
    right: ASTNode | None = None
    args: list[ASTNode] = Field(default_factory=list)
    operands: list[ASTNode] = Field(default_factory=list)
    theorem_ref: str | None = None


class QuantifierNode(BaseModel):
    kind: Literal["forall", "exists"]
    variable: VariableDecl


class LogicalAST(BaseModel):
    statement: str
    theorem_name: str
    quantifiers: list[QuantifierNode]
    variables: list[VariableDecl]
    hypotheses: list[ASTNode]
    conclusion: ASTNode
    theorem_references: list[str] = Field(default_factory=list)
    parser_metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)


ASTNode.model_rebuild()
