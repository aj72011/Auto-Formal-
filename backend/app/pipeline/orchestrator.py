from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from app.config import Settings
from app.pipeline.annotator import LeanCodeAnnotator
from app.pipeline.ast_schema import ASTNode, LogicalAST
from app.pipeline.ast_to_lean_compiler import ASTToLeanCompiler, LeanCompilationError
from app.pipeline.capability_classifier import (
    CapabilityClassification,
    TheoremCapabilityClassifier,
)
from app.pipeline.error_analyzer import LeanErrorAnalyzer
from app.pipeline.explanation_generator import ExplanationGenerator
from app.pipeline.knowledge_mapping import KnowledgeMappingEngine
from app.pipeline.lean_verification_engine import (
    LeanVerificationEngine,
    VerificationError,
    VerificationResult,
)
from app.pipeline.proof_generator import HuggingFaceProofGenerator, ProofGenerationError
from app.pipeline.repair_loop import AutomaticRepairLoop, RepairAttemptRecord
from app.pipeline.semantic_parser import DeterministicSemanticParser, SemanticParseError
from app.services.telemetry import TelemetryLogger


@dataclass
class StageTrace:
    stage: str
    latency_ms: int
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    ast: LogicalAST
    capability: dict[str, Any]
    lean_code: str
    verification: dict[str, Any]
    model_response: dict[str, Any]
    attempts: list[dict[str, Any]]
    attempts_used: int
    explanation: dict[str, Any]
    annotated_lines: list[dict[str, Any]]
    knowledge_entries: list[dict[str, Any]]
    stage_traces: list[dict[str, Any]]
    mode: str


class AutoFormalOrchestrator:
    def __init__(self, settings: Settings, telemetry: TelemetryLogger) -> None:
        self.settings = settings
        self.telemetry = telemetry

        self.parser = DeterministicSemanticParser()
        self.capability_classifier = TheoremCapabilityClassifier()
        self.compiler = ASTToLeanCompiler()
        self.verifier = LeanVerificationEngine(
            lean_command=settings.lean_command,
            timeout_seconds=settings.lean_timeout_seconds,
        )
        self.analyzer = LeanErrorAnalyzer()
        self.generator = HuggingFaceProofGenerator(
            api_key=settings.hf_api_key,
            model=settings.hf_model,
            timeout_seconds=settings.hf_timeout_seconds,
            structured_retries=settings.hf_structured_retries,
        )
        self.repair_loop = AutomaticRepairLoop(
            verifier=self.verifier,
            analyzer=self.analyzer,
            generator=self.generator,
            max_repair_attempts=settings.max_repair_attempts,
            enabled=settings.enable_repair_loop,
            binder_compiler=self.compiler,
        )
        self.explainer = ExplanationGenerator()
        self.knowledge_engine = KnowledgeMappingEngine(settings.knowledge_base_file)
        self.annotator = LeanCodeAnnotator(self.knowledge_engine)

    def run(
        self,
        statement: str,
        request_id: str,
        mode: str | None = None,
        repair_enabled: bool | None = None,
    ) -> PipelineResult:
        selected_mode = mode or self.settings.pipeline_mode
        do_repair = self.settings.enable_repair_loop if repair_enabled is None else repair_enabled

        traces: list[StageTrace] = []

        ast = self._run_stage(
            traces,
            stage_name="semantic_parser",
            fn=lambda: self._parse_or_fallback(statement),
            request_id=request_id,
        )

        capability = self._run_stage(
            traces,
            stage_name="capability_classifier",
            fn=lambda: self.capability_classifier.classify(statement=statement, ast=ast),
            request_id=request_id,
        )
        self.telemetry.append(
            event_type="capability_classification",
            request_id=request_id,
            payload=capability.to_dict(),
        )

        if not capability.supported:
            return self._build_unsupported_result(
                request_id=request_id,
                statement=statement,
                mode=selected_mode,
                ast=ast,
                capability=capability,
                traces=traces,
            )

        model_response = {
            "status": "success",
            "lean_code": "",
            "explanation": "",
            "error_message": "",
            "reason": "",
        }

        if selected_mode == "direct":
            direct_output = self._run_stage(
                traces,
                stage_name="direct_generator",
                fn=lambda: self.generator.generate_direct(statement),
                request_id=request_id,
            )
            self._log_model_generation(request_id, "direct_generator", direct_output)
            model_response = {
                "status": direct_output.status,
                "lean_code": direct_output.lean_code,
                "explanation": direct_output.explanation,
                "error_message": direct_output.error_message,
                "reason": "",
            }
            initial_code = direct_output.lean_code
            initial_source = "direct_generator"
        else:
            compile_bundle = self._run_stage(
                traces,
                stage_name="ast_to_lean_compiler",
                fn=lambda: self._compile_or_fallback(ast, statement, request_id),
                request_id=request_id,
            )
            initial_code = compile_bundle["lean_code"]
            initial_source = str(compile_bundle["source"])
            model_response = compile_bundle["model_response"]

        if do_repair != self.repair_loop.enabled:
            self.repair_loop.enabled = do_repair

        if model_response.get("status") in {"failure", "unsupported"}:
            failure_message = str(
                model_response.get("error_message")
                or model_response.get("reason")
                or "Model did not produce usable Lean output."
            )
            final_verification = VerificationResult(
                status="failed",
                errors=[VerificationError(message=failure_message)],
                latency_ms=0,
                stdout="",
                stderr=failure_message,
            )
            attempts = [
                RepairAttemptRecord(
                    attempt=1,
                    source=f"{initial_source}_model_failure",
                    lean_code="",
                    verification=final_verification,
                    error_class="model_failure",
                    error_messages=[failure_message],
                    targeted_fix="Structured model response indicated failure.",
                    diff_from_previous="",
                )
            ]
            repaired_code = ""
            traces.append(
                StageTrace(
                    stage="verification_and_repair_loop",
                    latency_ms=0,
                    payload={
                        "status": "skipped",
                        "reason": "model_failure",
                        "error_message": failure_message,
                    },
                )
            )
            self.telemetry.append(
                event_type="pipeline_stage",
                request_id=request_id,
                payload={
                    "stage": "verification_and_repair_loop",
                    "latency_ms": 0,
                    "status": "skipped",
                    "reason": "model_failure",
                    "error_message": failure_message,
                },
            )
        else:
            repaired_code, final_verification, attempts = self._run_stage(
                traces,
                stage_name="verification_and_repair_loop",
                fn=lambda: self.repair_loop.run(
                    statement=statement,
                    ast=ast,
                    initial_lean_code=initial_code,
                    initial_source=initial_source,
                ),
                request_id=request_id,
            )

        explanation_bundle = self._run_stage(
            traces,
            stage_name="explanation_generator",
            fn=lambda: self.explainer.generate(
                lean_code=repaired_code,
                verification_status=final_verification.status,
            ),
            request_id=request_id,
        )

        annotations = self._run_stage(
            traces,
            stage_name="knowledge_mapping_and_annotation",
            fn=lambda: self.annotator.annotate(repaired_code),
            request_id=request_id,
        )

        knowledge_entries = self._collect_knowledge_entries(annotations)

        verification_payload = {
            "status": final_verification.status,
            "errors": [
                {"message": error.message, "line": error.line, "column": error.column}
                for error in final_verification.errors
            ],
            "latency_ms": final_verification.latency_ms,
            "stdout": final_verification.stdout,
            "stderr": final_verification.stderr,
        }

        attempt_payloads = [self._attempt_to_dict(item) for item in attempts]
        explanation_payload = {
            "summary": explanation_bundle.summary,
            "steps": [
                {
                    "line_number": step.line_number,
                    "tactic": step.tactic,
                    "explanation": step.explanation,
                }
                for step in explanation_bundle.steps
            ],
        }
        annotation_payloads = [
            {
                "line_number": item.line_number,
                "text": item.text,
                "has_info": item.has_info,
                "theorem_name": item.theorem_name,
                "short_explanation": item.short_explanation,
                "concept_summary": item.concept_summary,
                "knowledge_id": item.knowledge_id,
                "concept_key": item.concept_key,
            }
            for item in annotations
        ]

        trace_payloads = [
            {"stage": trace.stage, "latency_ms": trace.latency_ms, "payload": trace.payload}
            for trace in traces
        ]

        self.telemetry.append(
            event_type="pipeline_completed",
            request_id=request_id,
            payload={
                "statement": statement,
                "mode": selected_mode,
                "capability": capability.to_dict(),
                "verification_status": final_verification.status,
                "attempts_used": len(attempt_payloads),
                "stage_traces": trace_payloads,
            },
        )

        return PipelineResult(
            ast=ast,
            capability=capability.to_dict(),
            lean_code=repaired_code,
            verification=verification_payload,
            model_response=model_response,
            attempts=attempt_payloads,
            attempts_used=len(attempt_payloads),
            explanation=explanation_payload,
            annotated_lines=annotation_payloads,
            knowledge_entries=knowledge_entries,
            stage_traces=trace_payloads,
            mode=selected_mode,
        )

    def _build_unsupported_result(
        self,
        request_id: str,
        statement: str,
        mode: str,
        ast: LogicalAST,
        capability: CapabilityClassification,
        traces: list[StageTrace],
    ) -> PipelineResult:
        reason = capability.reason
        self._append_skipped_stage(
            traces=traces,
            request_id=request_id,
            stage_name="verification_and_repair_loop",
            reason="unsupported_capability",
            message=reason,
        )
        self._append_skipped_stage(
            traces=traces,
            request_id=request_id,
            stage_name="explanation_generator",
            reason="unsupported_capability",
            message=reason,
        )
        self._append_skipped_stage(
            traces=traces,
            request_id=request_id,
            stage_name="knowledge_mapping_and_annotation",
            reason="unsupported_capability",
            message=reason,
        )
        self.telemetry.append(
            event_type="unsupported_statement",
            request_id=request_id,
            payload={
                "statement": statement,
                "mode": mode,
                "capability": capability.to_dict(),
            },
        )

        verification_result = VerificationResult(
            status="unsupported",
            errors=[VerificationError(message=reason)],
            latency_ms=0,
            stdout="",
            stderr=reason,
        )
        unsupported_attempt = RepairAttemptRecord(
            attempt=1,
            source="capability_classifier",
            lean_code="",
            verification=verification_result,
            error_class="unsupported_subset",
            error_messages=[reason],
            targeted_fix=(
                "Statement is outside Tier 1/Tier 2 subset. Logged for future capability upgrades."
            ),
            diff_from_previous="",
        )

        trace_payloads = [
            {"stage": trace.stage, "latency_ms": trace.latency_ms, "payload": trace.payload}
            for trace in traces
        ]
        attempts = [self._attempt_to_dict(unsupported_attempt)]
        verification_payload = {
            "status": "unsupported",
            "errors": [{"message": reason, "line": None, "column": None}],
            "latency_ms": 0,
            "stdout": "",
            "stderr": reason,
        }
        explanation_payload = {
            "summary": reason,
            "steps": [],
        }
        model_response = {
            "status": "unsupported",
            "lean_code": "",
            "explanation": "",
            "error_message": reason,
            "reason": reason,
        }

        self.telemetry.append(
            event_type="pipeline_completed",
            request_id=request_id,
            payload={
                "statement": statement,
                "mode": mode,
                "verification_status": "unsupported",
                "attempts_used": 1,
                "stage_traces": trace_payloads,
            },
        )

        return PipelineResult(
            ast=ast,
            capability=capability.to_dict(),
            lean_code="",
            verification=verification_payload,
            model_response=model_response,
            attempts=attempts,
            attempts_used=1,
            explanation=explanation_payload,
            annotated_lines=[],
            knowledge_entries=[],
            stage_traces=trace_payloads,
            mode=mode,
        )

    def _run_stage(
        self,
        traces: list[StageTrace],
        stage_name: str,
        fn,
        request_id: str,
    ):
        started = time.perf_counter()
        try:
            result = fn()
            payload = {"status": "ok"}
            return result
        except Exception as exc:
            payload = {"status": "error", "message": str(exc)}
            raise
        finally:
            latency_ms = int((time.perf_counter() - started) * 1000)
            trace = StageTrace(stage=stage_name, latency_ms=latency_ms, payload=payload)
            traces.append(trace)
            self.telemetry.append(
                event_type="pipeline_stage",
                request_id=request_id,
                payload={
                    "stage": stage_name,
                    "latency_ms": latency_ms,
                    **payload,
                },
            )

    def _parse_or_fallback(self, statement: str) -> LogicalAST:
        try:
            ast = self.parser.parse(statement)
            self.telemetry.append("ast_snapshot", payload=ast.model_dump())
            return ast
        except SemanticParseError:
            fallback = LogicalAST(
                statement=statement,
                theorem_name="autoformal_fallback_statement",
                quantifiers=[],
                variables=[],
                hypotheses=[],
                conclusion=ASTNode(kind="reference", theorem_ref=statement),
                theorem_references=[],
                parser_metadata={"parser": "fallback_reference_parser", "matched_pattern": "fallback"},
            )
            self.telemetry.append("ast_snapshot", payload=fallback.model_dump())
            return fallback

    def _compile_or_fallback(
        self,
        ast: LogicalAST,
        statement: str,
        request_id: str,
    ) -> dict[str, Any]:
        try:
            lean_code, metadata = self.compiler.compile_with_metadata(ast)
            self.telemetry.append(
                event_type="compiler_binding_inference",
                request_id=request_id,
                payload=metadata,
            )
            return {
                "lean_code": lean_code,
                "source": "ast_compiler",
                "model_response": {
                    "status": "success",
                    "lean_code": lean_code,
                    "explanation": "Deterministic AST compiler output.",
                    "error_message": "",
                    "reason": "",
                },
            }
        except LeanCompilationError:
            self.telemetry.append(
                event_type="compiler_binding_inference",
                request_id=request_id,
                payload={
                    "status": "failed",
                    "message": "Compiler binder validation failed; falling back to direct generation.",
                },
            )
            generated = self.generator.generate_direct(statement)
            self._log_model_generation(request_id, "direct_generator_fallback", generated)
            return {
                "lean_code": generated.lean_code,
                "source": (
                    "direct_generator_fallback"
                    if generated.status == "success"
                    else "direct_generator_fallback_failure"
                ),
                "model_response": {
                    "status": generated.status,
                    "lean_code": generated.lean_code,
                    "explanation": generated.explanation,
                    "error_message": generated.error_message,
                    "reason": "",
                },
            }
        except ProofGenerationError:
            return {
                "lean_code": "",
                "source": "direct_generator_fallback_failure",
                "model_response": {
                    "status": "failure",
                    "lean_code": "",
                    "explanation": "",
                    "error_message": "Model did not produce usable Lean output.",
                    "reason": "",
                },
            }

    def _log_model_generation(self, request_id: str, stage: str, generated) -> None:
        self.telemetry.append(
            event_type="model_structured_output",
            request_id=request_id,
            payload={
                "stage": stage,
                "status": generated.status,
                "error_message": generated.error_message,
                "validation_failures": generated.validation_failures,
                "raw_outputs": generated.raw_outputs,
            },
        )

    def _attempt_to_dict(self, record: RepairAttemptRecord) -> dict[str, Any]:
        return {
            "attempt": record.attempt,
            "source": record.source,
            "lean_code": record.lean_code,
            "verification": {
                "status": record.verification.status,
                "errors": [
                    {"message": err.message, "line": err.line, "column": err.column}
                    for err in record.verification.errors
                ],
                "latency_ms": record.verification.latency_ms,
            },
            "error_class": record.error_class,
            "error_messages": record.error_messages,
            "targeted_fix": record.targeted_fix,
            "diff_from_previous": record.diff_from_previous,
        }

    def _append_skipped_stage(
        self,
        traces: list[StageTrace],
        request_id: str,
        stage_name: str,
        reason: str,
        message: str,
    ) -> None:
        payload = {
            "status": "skipped",
            "reason": reason,
            "message": message,
        }
        traces.append(StageTrace(stage=stage_name, latency_ms=0, payload=payload))
        self.telemetry.append(
            event_type="pipeline_stage",
            request_id=request_id,
            payload={
                "stage": stage_name,
                "latency_ms": 0,
                **payload,
            },
        )

    def _collect_knowledge_entries(self, annotations: list) -> list[dict[str, Any]]:
        by_id: dict[str, dict[str, Any]] = {}
        for annotation in annotations:
            if not annotation.knowledge_id:
                continue
            entry = self.knowledge_engine.entries.get(annotation.concept_key or "")
            if entry is None:
                continue
            by_id[entry.id] = self.knowledge_engine.to_dict(entry) or {}
        return list(by_id.values())
