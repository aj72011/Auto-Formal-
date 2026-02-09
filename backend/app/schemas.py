from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class VerificationStatus(str, Enum):
    verified = "verified"
    failed = "failed"
    unsupported = "unsupported"
    capability_boundary = "capability_boundary"


class ErrorStage(str, Enum):
    parse = "parse"
    compile = "compile"
    verify = "verify"
    repair = "repair"
    model = "model"
    network = "network"
    internal = "internal"


class ErrorType(str, Enum):
    none = "none"
    timeout = "timeout"
    model_failure = "model_failure"
    invalid_output = "invalid_output"
    internal_error = "internal_error"
    parse_error = "parse_error"
    compile_error = "compile_error"
    verification_error = "verification_error"


class StructuredErrorResponse(BaseModel):
    """
    Structured error response that is always returned even on crashes,
    timeouts, or model failures. Never returns empty responses or plain text errors.
    """
    status: Literal["success", "failure"]
    stage: ErrorStage
    error_type: ErrorType
    message: str = Field(..., description="Human readable explanation")
    lean_output: str = Field(default="", description="Optional Lean code if available")
    diagnostics: str = Field(default="", description="Optional debug trace")
    traceback: str = Field(default="", description="Full server-side traceback for debugging")


class FormalizeRequest(BaseModel):
    statement: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Natural language mathematical statement.",
    )
    mode: Literal["ast", "direct"] | None = Field(
        default=None,
        description="Pipeline mode for ablation: AST compiler mode or direct generation mode.",
    )
    enable_repair_loop: bool | None = Field(
        default=None,
        description="Override backend default repair-loop behavior for this request.",
    )


class VerificationErrorPayload(BaseModel):
    message: str
    line: int | None = None
    column: int | None = None


class VerificationPayload(BaseModel):
    status: VerificationStatus
    errors: list[VerificationErrorPayload]
    latency_ms: int
    stdout: str = ""
    stderr: str = ""


class AttemptVerificationPayload(BaseModel):
    status: VerificationStatus
    errors: list[VerificationErrorPayload]
    latency_ms: int


class RepairAttemptPayload(BaseModel):
    attempt: int
    source: str
    lean_code: str
    verification: AttemptVerificationPayload
    error_class: str
    error_messages: list[str]
    targeted_fix: str
    diff_from_previous: str


class ExplanationStepPayload(BaseModel):
    line_number: int
    tactic: str
    explanation: str


class ExplanationPayload(BaseModel):
    summary: str
    steps: list[ExplanationStepPayload]


class AnnotatedLinePayload(BaseModel):
    line_number: int
    text: str
    has_info: bool
    theorem_name: str | None = None
    short_explanation: str | None = None
    concept_summary: str | None = None
    knowledge_id: str | None = None
    concept_key: str | None = None


class KnowledgeEntryPayload(BaseModel):
    id: str
    concept_key: str
    theorem_name: str
    summary: str
    detailed_explanation: str
    research_context: str
    paper_notes: str
    related_theorems: list[str]


class StageTracePayload(BaseModel):
    stage: str
    latency_ms: int
    payload: dict


class ModelResponsePayload(BaseModel):
    status: Literal["success", "failure", "unsupported"]
    lean_code: str
    explanation: str
    error_message: str
    reason: str = ""


class CapabilityBoundaryPayload(BaseModel):
    """
    Educational fallback data when a theorem exceeds automated proof capability.
    Provides structured guidance for manual proof completion.
    """
    missing_lemmas: list[str] = Field(
        default_factory=list,
        description="Lean lemmas or theorems needed but not in automated subset"
    )
    proof_depth_estimate: int = Field(
        default=0,
        description="Estimated number of proof steps or tactic applications required"
    )
    recommended_topics: list[str] = Field(
        default_factory=list,
        description="Mathematical topics/concepts user should study to complete proof"
    )
    subgoals: list[str] = Field(
        default_factory=list,
        description="Intermediate proof goals that need to be satisfied"
    )
    lean_skeleton: str = Field(
        default="",
        description="Partial Lean theorem statement with sorries for manual completion"
    )
    human_explanation: str = Field(
        default="",
        description="Why automation stopped and what patterns/reasoning are missing"
    )


class CapabilityPayload(BaseModel):
    tier: int
    tier_label: str
    status: Literal["supported", "unsupported", "capability_boundary"]
    supported: bool
    reason: str
    signals: list[str] = Field(default_factory=list)
    boundary_info: CapabilityBoundaryPayload | None = Field(
        default=None,
        description="Educational guidance when capability boundary is hit"
    )


class FormalizeResponse(BaseModel):
    request_id: str
    original_statement: str
    mode: str
    ast: dict
    capability: CapabilityPayload
    model_response: ModelResponsePayload
    lean_code: str
    verification: VerificationPayload
    attempts_used: int
    repair_history: list[RepairAttemptPayload]
    explanation: ExplanationPayload
    annotated_lines: list[AnnotatedLinePayload]
    knowledge_entries: list[KnowledgeEntryPayload]
    stage_traces: list[StageTracePayload]
    total_latency_ms: int


class HealthResponse(BaseModel):
    status: str
    huggingface_configured: bool
    pipeline_mode: str
    repair_loop_enabled: bool


class EvaluateRequest(BaseModel):
    dataset_path: str = Field(
        default="data/benchmark_tiered.json",
        description="Path to a JSON dataset relative to backend directory.",
    )
    limit: int = Field(default=0, ge=0)
    output_prefix: str = Field(default="research_eval")
    protocol: Literal["baseline", "upgraded", "both"] = Field(default="both")
    seed: int = Field(default=1729)


class EvaluateResponse(BaseModel):
    run_id: str
    dataset_path: str
    total_samples: int
    protocols: list[str]
    metrics: dict
    comparison: dict[str, float | int | str]
    output_files: dict[str, str]
