import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import BASE_DIR, settings
from app.pipeline.evaluator import (
    DEFAULT_EVALUATION_SEED,
    run_research_evaluation,
)
from app.pipeline.orchestrator import AutoFormalOrchestrator
from app.services.telemetry import TelemetryLogger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run AutoFormal+ research evaluation with deterministic protocol modes "
            "(baseline, upgraded, or both)."
        )
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("data/benchmark_tiered.json"),
        help="Dataset path relative to backend directory, unless absolute.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional max number of statements to evaluate.",
    )
    parser.add_argument(
        "--output-prefix",
        type=str,
        default="research_eval",
        help="Prefix for exported CSV/JSON/Markdown files.",
    )
    parser.add_argument(
        "--protocol",
        type=str,
        choices=["baseline", "upgraded", "both"],
        default="both",
        help="Evaluation protocol selection.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_EVALUATION_SEED,
        help="Deterministic seed recorded in outputs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_path = args.dataset
    if not dataset_path.is_absolute():
        dataset_path = BASE_DIR / dataset_path

    orchestrator = AutoFormalOrchestrator(
        settings=settings,
        telemetry=TelemetryLogger(settings.telemetry_file),
    )

    summary = run_research_evaluation(
        orchestrator=orchestrator,
        dataset_path=dataset_path,
        output_dir=settings.evaluation_output_dir,
        output_prefix=args.output_prefix,
        limit=args.limit,
        protocol=args.protocol,
        seed=args.seed,
    )

    print(json.dumps(summary, indent=2))
    print("\nEvaluation complete.")
    print(f"Run ID: {summary['run_id']}")
    print(f"Total samples: {summary['total_samples']}")
    print(f"Protocols: {', '.join(summary['protocols'])}")
    print("Outputs:")
    for key, value in summary["output_files"].items():
        print(f"- {key}: {value}")


if __name__ == "__main__":
    main()
