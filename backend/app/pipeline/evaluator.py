from __future__ import annotations

import csv
import json
import statistics
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from random import seed as random_seed
from typing import Any, Literal

from app.pipeline.benchmark_dataset import BenchmarkTheorem, load_benchmark_dataset
from app.pipeline.orchestrator import AutoFormalOrchestrator


EvaluationProtocolName = Literal["baseline", "upgraded"]
ProtocolSelection = Literal["baseline", "upgraded", "both"]

DEFAULT_EVALUATION_SEED = 1729
SUPPORTED_TIER_MAX = 2


@dataclass(frozen=True)
class EvaluationProtocol:
    name: EvaluationProtocolName
    mode: Literal["ast", "direct"]
    repair_enabled: bool
    description: str


BASELINE_PROTOCOL = EvaluationProtocol(
    name="baseline",
    mode="direct",
    repair_enabled=False,
    description="Direct generation without repair loop.",
)
UPGRADED_PROTOCOL = EvaluationProtocol(
    name="upgraded",
    mode="ast",
    repair_enabled=True,
    description="Deterministic AST compiler with repair loop enabled.",
)


def run_research_evaluation(
    orchestrator: AutoFormalOrchestrator,
    dataset_path: Path,
    output_dir: Path,
    output_prefix: str,
    limit: int = 0,
    protocol: ProtocolSelection = "both",
    seed: int = DEFAULT_EVALUATION_SEED,
) -> dict[str, Any]:
    random_seed(seed)

    dataset = load_benchmark_dataset(dataset_path)
    selected_dataset = dataset[:limit] if limit > 0 else dataset
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    protocols = _resolve_protocols(protocol)

    rows: list[dict[str, Any]] = []
    protocol_metrics: dict[str, dict[str, Any]] = {}

    for eval_protocol in protocols:
        protocol_rows = _run_protocol(
            orchestrator=orchestrator,
            samples=selected_dataset,
            run_id=run_id,
            protocol=eval_protocol,
            deterministic_seed=seed,
        )
        rows.extend(protocol_rows)
        protocol_metrics[eval_protocol.name] = _compute_protocol_metrics(
            protocol_rows=protocol_rows,
            total_samples=len(selected_dataset),
        )

    comparison = _build_comparison(protocol_metrics)
    summary = {
        "run_id": run_id,
        "dataset_path": str(dataset_path),
        "total_samples": len(selected_dataset),
        "deterministic_seed": seed,
        "protocols": [proto.name for proto in protocols],
        "protocol_settings": {
            proto.name: {
                "mode": proto.mode,
                "repair_enabled": proto.repair_enabled,
                "description": proto.description,
            }
            for proto in protocols
        },
        "metrics": protocol_metrics,
        "comparison": comparison,
        "rows": rows,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    file_prefix = f"{output_prefix}_{run_id}"
    csv_path = output_dir / f"{file_prefix}.csv"
    json_path = output_dir / f"{file_prefix}.json"
    markdown_path = output_dir / f"{file_prefix}.md"

    _write_csv(rows=rows, destination=csv_path)
    json_path.write_text(json.dumps(summary, ensure_ascii=True, indent=2), encoding="utf-8")
    markdown_path.write_text(
        _build_markdown_summary(summary=summary),
        encoding="utf-8",
    )

    return {
        "run_id": run_id,
        "dataset_path": str(dataset_path),
        "total_samples": len(selected_dataset),
        "protocols": [proto.name for proto in protocols],
        "metrics": protocol_metrics,
        "comparison": comparison,
        "output_files": {
            "csv": str(csv_path),
            "json": str(json_path),
            "markdown": str(markdown_path),
        },
    }


def run_ablation_evaluation(
    orchestrator: AutoFormalOrchestrator,
    dataset_path: Path,
    output_dir: Path,
    output_prefix: str,
    limit: int = 0,
) -> dict[str, Any]:
    # Backward-compatible wrapper used by existing integrations.
    return run_research_evaluation(
        orchestrator=orchestrator,
        dataset_path=dataset_path,
        output_dir=output_dir,
        output_prefix=output_prefix,
        limit=limit,
        protocol="both",
        seed=DEFAULT_EVALUATION_SEED,
    )


def _resolve_protocols(selection: ProtocolSelection) -> list[EvaluationProtocol]:
    if selection == "baseline":
        return [BASELINE_PROTOCOL]
    if selection == "upgraded":
        return [UPGRADED_PROTOCOL]
    return [BASELINE_PROTOCOL, UPGRADED_PROTOCOL]


def _run_protocol(
    orchestrator: AutoFormalOrchestrator,
    samples: list[BenchmarkTheorem],
    run_id: str,
    protocol: EvaluationProtocol,
    deterministic_seed: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, sample in enumerate(samples, start=1):
        request_id = (
            f"eval-{run_id}-{protocol.name}-{index:03d}-{uuid.uuid4().hex[:6]}"
        )
        try:
            result = orchestrator.run(
                statement=sample.statement,
                request_id=request_id,
                mode=protocol.mode,
                repair_enabled=protocol.repair_enabled,
            )
            row = _result_to_row(
                sample=sample,
                protocol=protocol,
                request_id=request_id,
                result=result,
                deterministic_seed=deterministic_seed,
            )
        except Exception as exc:
            row = _exception_row(
                sample=sample,
                protocol=protocol,
                request_id=request_id,
                error_message=str(exc),
                deterministic_seed=deterministic_seed,
            )
        rows.append(row)
    return rows


def _result_to_row(
    sample: BenchmarkTheorem,
    protocol: EvaluationProtocol,
    request_id: str,
    result,
    deterministic_seed: int,
) -> dict[str, Any]:
    stage_payloads = {item["stage"]: item for item in result.stage_traces}
    parse_success = _stage_succeeded(stage_payloads.get("semantic_parser"))
    compile_stage_name = "ast_to_lean_compiler" if protocol.mode == "ast" else "direct_generator"
    compile_success = _stage_succeeded(stage_payloads.get(compile_stage_name))
    verification_status = str(result.verification.get("status", "failed"))
    verification_success = verification_status == "verified"

    capability = result.capability
    capability_tier = int(capability.get("tier", 0))
    capability_label = str(capability.get("tier_label", "unknown"))
    unsupported_prediction = bool(capability.get("status") == "unsupported")
    expected_unsupported = sample.tier > SUPPORTED_TIER_MAX
    unsupported_correct = unsupported_prediction == expected_unsupported

    repair_triggered = result.attempts_used > 1
    repair_success = repair_triggered and verification_success
    final_attempt = result.attempts[-1] if result.attempts else {}
    error_type = str(final_attempt.get("error_class", "none"))
    total_latency_ms = int(sum(item["latency_ms"] for item in result.stage_traces))

    return {
        "run_id": request_id.split("-")[1],
        "request_id": request_id,
        "protocol": protocol.name,
        "mode": protocol.mode,
        "repair_enabled": protocol.repair_enabled,
        "seed": deterministic_seed,
        "id": sample.id,
        "statement": sample.statement,
        "tier": sample.tier,
        "parse_success": parse_success,
        "compile_success": compile_success,
        "verification_success": verification_success,
        "repair_success": repair_success,
        "unsupported_classification": unsupported_prediction,
        "unsupported_expected": expected_unsupported,
        "unsupported_correct": unsupported_correct,
        "final_status": verification_status,
        "attempts": int(result.attempts_used),
        "error_type": error_type,
        "classification": capability_label,
        "capability_reason": str(capability.get("reason", "")),
        "lean_output": result.lean_code,
        "latency_ms": total_latency_ms,
    }


def _exception_row(
    sample: BenchmarkTheorem,
    protocol: EvaluationProtocol,
    request_id: str,
    error_message: str,
    deterministic_seed: int,
) -> dict[str, Any]:
    expected_unsupported = sample.tier > SUPPORTED_TIER_MAX
    return {
        "run_id": request_id.split("-")[1],
        "request_id": request_id,
        "protocol": protocol.name,
        "mode": protocol.mode,
        "repair_enabled": protocol.repair_enabled,
        "seed": deterministic_seed,
        "id": sample.id,
        "statement": sample.statement,
        "tier": sample.tier,
        "parse_success": False,
        "compile_success": False,
        "verification_success": False,
        "repair_success": False,
        "unsupported_classification": False,
        "unsupported_expected": expected_unsupported,
        "unsupported_correct": not expected_unsupported,
        "final_status": "failed",
        "attempts": 0,
        "error_type": "runtime_exception",
        "classification": "runtime_exception",
        "capability_reason": error_message,
        "lean_output": "",
        "latency_ms": 0,
    }


def _stage_succeeded(stage_trace: dict[str, Any] | None) -> bool:
    if stage_trace is None:
        return False
    payload = stage_trace.get("payload", {})
    return payload.get("status") == "ok"


def _compute_protocol_metrics(
    protocol_rows: list[dict[str, Any]],
    total_samples: int,
) -> dict[str, Any]:
    if total_samples == 0:
        return {
            "overall_success_rate_percent": 0.0,
            "success_rate_per_tier": {},
            "unsupported_detection_accuracy_percent": 0.0,
            "repair_loop_success_rate_percent": 0.0,
            "average_attempts_per_theorem": 0.0,
            "failure_distribution": {},
            "capability_boundary_stats": {},
            "status_counts": {},
        }

    verified_count = sum(1 for row in protocol_rows if row["final_status"] == "verified")
    success_rate = _percent(verified_count, total_samples)

    per_tier: dict[str, Any] = {}
    for tier in (1, 2, 3, 4):
        tier_rows = [row for row in protocol_rows if int(row["tier"]) == tier]
        if not tier_rows:
            per_tier[str(tier)] = {
                "total": 0,
                "verified": 0,
                "unsupported": 0,
                "failed": 0,
                "success_rate_percent": 0.0,
            }
            continue
        tier_verified = sum(1 for row in tier_rows if row["final_status"] == "verified")
        tier_unsupported = sum(1 for row in tier_rows if row["final_status"] == "unsupported")
        tier_failed = sum(1 for row in tier_rows if row["final_status"] == "failed")
        per_tier[str(tier)] = {
            "total": len(tier_rows),
            "verified": tier_verified,
            "unsupported": tier_unsupported,
            "failed": tier_failed,
            "success_rate_percent": _percent(tier_verified, len(tier_rows)),
        }

    unsupported_correct = sum(1 for row in protocol_rows if row["unsupported_correct"])
    unsupported_accuracy = _percent(unsupported_correct, total_samples)

    repair_trigger_rows = [row for row in protocol_rows if int(row["attempts"]) > 1]
    repair_success_rows = [row for row in repair_trigger_rows if row["repair_success"]]
    repair_success_rate = (
        _percent(len(repair_success_rows), len(repair_trigger_rows))
        if repair_trigger_rows
        else 0.0
    )

    avg_attempts = round(
        statistics.mean(int(row["attempts"]) for row in protocol_rows), 3
    )

    failure_distribution: dict[str, int] = {}
    for row in protocol_rows:
        if row["final_status"] == "verified":
            continue
        key = str(row["error_type"] or "unknown")
        failure_distribution[key] = failure_distribution.get(key, 0) + 1

    status_counts: dict[str, int] = {}
    for row in protocol_rows:
        key = str(row["final_status"])
        status_counts[key] = status_counts.get(key, 0) + 1

    tp = sum(
        1
        for row in protocol_rows
        if row["unsupported_expected"] and row["unsupported_classification"]
    )
    tn = sum(
        1
        for row in protocol_rows
        if (not row["unsupported_expected"]) and (not row["unsupported_classification"])
    )
    fp = sum(
        1
        for row in protocol_rows
        if (not row["unsupported_expected"]) and row["unsupported_classification"]
    )
    fn = sum(
        1
        for row in protocol_rows
        if row["unsupported_expected"] and (not row["unsupported_classification"])
    )
    capability_boundary_stats = {
        "expected_unsupported_total": tp + fn,
        "predicted_unsupported_total": tp + fp,
        "true_positive": tp,
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
    }

    return {
        "overall_success_rate_percent": success_rate,
        "success_rate_per_tier": per_tier,
        "unsupported_detection_accuracy_percent": unsupported_accuracy,
        "repair_loop_success_rate_percent": repair_success_rate,
        "average_attempts_per_theorem": avg_attempts,
        "failure_distribution": failure_distribution,
        "capability_boundary_stats": capability_boundary_stats,
        "status_counts": status_counts,
    }


def _build_comparison(protocol_metrics: dict[str, dict[str, Any]]) -> dict[str, Any]:
    baseline = protocol_metrics.get("baseline")
    upgraded = protocol_metrics.get("upgraded")
    if baseline is None or upgraded is None:
        return {}

    return {
        "overall_success_rate_delta_percent": round(
            upgraded["overall_success_rate_percent"]
            - baseline["overall_success_rate_percent"],
            2,
        ),
        "unsupported_detection_accuracy_delta_percent": round(
            upgraded["unsupported_detection_accuracy_percent"]
            - baseline["unsupported_detection_accuracy_percent"],
            2,
        ),
        "repair_loop_success_rate_delta_percent": round(
            upgraded["repair_loop_success_rate_percent"]
            - baseline["repair_loop_success_rate_percent"],
            2,
        ),
        "average_attempts_delta": round(
            upgraded["average_attempts_per_theorem"]
            - baseline["average_attempts_per_theorem"],
            3,
        ),
    }


def _write_csv(rows: list[dict[str, Any]], destination: Path) -> None:
    field_order = [
        "run_id",
        "request_id",
        "protocol",
        "mode",
        "repair_enabled",
        "seed",
        "id",
        "statement",
        "tier",
        "parse_success",
        "compile_success",
        "verification_success",
        "repair_success",
        "unsupported_classification",
        "unsupported_expected",
        "unsupported_correct",
        "final_status",
        "attempts",
        "error_type",
        "classification",
        "capability_reason",
        "lean_output",
        "latency_ms",
    ]
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=field_order)
        writer.writeheader()
        writer.writerows(rows)


def _build_markdown_summary(summary: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# AutoFormal+ Evaluation Summary")
    lines.append("")
    lines.append(f"- Run ID: `{summary['run_id']}`")
    lines.append(f"- Dataset: `{summary['dataset_path']}`")
    lines.append(f"- Total samples: `{summary['total_samples']}`")
    lines.append(f"- Deterministic seed: `{summary['deterministic_seed']}`")
    lines.append(f"- Protocols: `{', '.join(summary['protocols'])}`")
    lines.append("")

    lines.append("## Metrics by Protocol")
    lines.append("")
    lines.append(
        "| Protocol | Success % | Unsupported Accuracy % | Repair Success % | Avg Attempts |"
    )
    lines.append("|---|---:|---:|---:|---:|")
    for protocol_name in summary["protocols"]:
        metrics = summary["metrics"][protocol_name]
        lines.append(
            "| {name} | {success:.2f} | {unsupported:.2f} | {repair:.2f} | {attempts:.3f} |".format(
                name=protocol_name,
                success=metrics["overall_success_rate_percent"],
                unsupported=metrics["unsupported_detection_accuracy_percent"],
                repair=metrics["repair_loop_success_rate_percent"],
                attempts=metrics["average_attempts_per_theorem"],
            )
        )
    lines.append("")

    lines.append("## Tier Performance Breakdown")
    lines.append("")
    for protocol_name in summary["protocols"]:
        metrics = summary["metrics"][protocol_name]
        lines.append(f"### {protocol_name.title()}")
        lines.append("")
        lines.append("| Tier | Total | Verified | Unsupported | Failed | Success % |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        tier_metrics = metrics["success_rate_per_tier"]
        for tier in ("1", "2", "3", "4"):
            item = tier_metrics[tier]
            lines.append(
                "| {tier} | {total} | {verified} | {unsupported} | {failed} | {success:.2f} |".format(
                    tier=tier,
                    total=item["total"],
                    verified=item["verified"],
                    unsupported=item["unsupported"],
                    failed=item["failed"],
                    success=item["success_rate_percent"],
                )
            )
        lines.append("")

    lines.append("## Failure Distribution")
    lines.append("")
    for protocol_name in summary["protocols"]:
        metrics = summary["metrics"][protocol_name]
        lines.append(f"### {protocol_name.title()}")
        distribution = metrics["failure_distribution"]
        if not distribution:
            lines.append("- No failures recorded.")
        else:
            for error_type, count in sorted(distribution.items(), key=lambda item: item[0]):
                lines.append(f"- `{error_type}`: {count}")
        lines.append("")

    lines.append("## Capability Boundary Statistics")
    lines.append("")
    for protocol_name in summary["protocols"]:
        boundary = summary["metrics"][protocol_name]["capability_boundary_stats"]
        lines.append(f"### {protocol_name.title()}")
        lines.append(
            "- Expected unsupported: `{expected}` | Predicted unsupported: `{predicted}`".format(
                expected=boundary["expected_unsupported_total"],
                predicted=boundary["predicted_unsupported_total"],
            )
        )
        lines.append(
            "- TP: `{tp}` | TN: `{tn}` | FP: `{fp}` | FN: `{fn}`".format(
                tp=boundary["true_positive"],
                tn=boundary["true_negative"],
                fp=boundary["false_positive"],
                fn=boundary["false_negative"],
            )
        )
        lines.append("")

    if summary.get("comparison"):
        lines.append("## Baseline vs Upgraded Comparison")
        lines.append("")
        for key, value in summary["comparison"].items():
            lines.append(f"- `{key}`: {value}")
        lines.append("")

    lines.append("## Result Table")
    lines.append("")
    lines.append(
        "| Protocol | ID | Tier | Final Status | Parse | Compile | Verify | Repair Success | Unsupported Pred | Attempts | Error Type |"
    )
    lines.append("|---|---|---:|---|---|---|---|---|---|---:|---|")
    for row in summary["rows"]:
        lines.append(
            "| {protocol} | {id} | {tier} | {status} | {parse} | {compile} | {verify} | {repair} | {unsupported} | {attempts} | {error} |".format(
                protocol=row["protocol"],
                id=row["id"],
                tier=row["tier"],
                status=row["final_status"],
                parse="Y" if row["parse_success"] else "N",
                compile="Y" if row["compile_success"] else "N",
                verify="Y" if row["verification_success"] else "N",
                repair="Y" if row["repair_success"] else "N",
                unsupported="Y" if row["unsupported_classification"] else "N",
                attempts=row["attempts"],
                error=row["error_type"],
            )
        )
    lines.append("")

    return "\n".join(lines)


def _percent(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100.0, 2)
