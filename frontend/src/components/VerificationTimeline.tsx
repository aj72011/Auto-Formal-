import type { FormalizeResponse, VerificationRunState } from "../types";

interface VerificationTimelineProps {
  result: FormalizeResponse | null;
  runState: VerificationRunState;
}

type TimelineState = "pending" | "completed" | "failed" | "active";

const STAGES = [
  { key: "parse", label: "Parse" },
  { key: "compile", label: "Compile" },
  { key: "verify", label: "Verify" },
  { key: "repair", label: "Repair" },
  { key: "explain", label: "Explain" },
] as const;

function hasTrace(result: FormalizeResponse, stage: string): boolean {
  return result.stage_traces.some((trace) => trace.stage === stage);
}

function stageState(
  stage: (typeof STAGES)[number]["key"],
  result: FormalizeResponse | null,
  runState: VerificationRunState,
): TimelineState {
  if (runState === "running" && !result) {
    if (stage === "parse") return "active";
    return "pending";
  }

  if (!result) {
    return runState === "failed" || runState === "unsupported" ? "failed" : "pending";
  }

  if (stage === "parse") {
    return hasTrace(result, "semantic_parser") ? "completed" : "pending";
  }

  if (stage === "compile") {
    const compileDone =
      hasTrace(result, "ast_to_lean_compiler") || hasTrace(result, "direct_generator");
    return compileDone ? "completed" : "pending";
  }

  if (stage === "verify") {
    if (!hasTrace(result, "verification_and_repair_loop")) return "pending";
    return result.verification.status === "failed" || result.verification.status === "unsupported"
      ? "failed"
      : "completed";
  }

  if (stage === "repair") {
    if (result.verification.status === "unsupported") return "pending";
    if (result.attempts_used <= 1) return "pending";
    return result.verification.status === "failed" ? "failed" : "completed";
  }

  if (stage === "explain") {
    return hasTrace(result, "explanation_generator") ? "completed" : "pending";
  }

  return "pending";
}

export function VerificationTimeline({ result, runState }: VerificationTimelineProps) {
  return (
    <div className="rounded-md border border-border bg-panelAlt p-3">
      <p className="text-[11px] font-semibold uppercase tracking-wider text-textMuted">
        Verification Timeline
      </p>
      <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-5">
        {STAGES.map((stage) => {
          const state = stageState(stage.key, result, runState);
          const tone =
            state === "completed"
              ? "border-emerald-400/40 bg-emerald-500/10 text-success"
              : state === "failed"
                ? "border-rose-400/40 bg-rose-500/10 text-danger"
                : state === "active"
                  ? "border-accent/50 bg-accent/10 text-accent"
                  : "border-border bg-panel text-textMuted";

          const icon =
            state === "completed"
              ? "OK"
              : state === "failed"
                ? "ERR"
                : state === "active"
                  ? "..."
                  : "-";

          return (
            <div key={stage.key} className={`rounded border px-2 py-2 text-center text-xs ${tone}`}>
              <div className="text-xs font-semibold">{icon}</div>
              <div className="mt-1 font-semibold">{stage.label}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
