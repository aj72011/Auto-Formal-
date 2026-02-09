import type { FormalizeResponse } from "../types";

interface FailureReportPanelProps {
  result: FormalizeResponse;
}

export function FailureReportPanel({ result }: FailureReportPanelProps) {
  if (result.verification.status !== "failed" && result.verification.status !== "unsupported") {
    return null;
  }

  const isUnsupported = result.verification.status === "unsupported";
  const lastAttempt = result.repair_history[result.repair_history.length - 1] ?? null;
  const firstError = isUnsupported
    ? result.capability.reason
    : result.verification.errors[0]?.message ?? "No Lean error excerpt available.";

  return (
    <div
      className={`rounded-md border p-3 ${
        isUnsupported
          ? "border-amber-400/35 bg-amber-500/10"
          : "border-rose-400/35 bg-rose-500/10"
      }`}
    >
      <p
        className={`text-xs font-semibold uppercase tracking-wider ${
          isUnsupported ? "text-amber-200" : "text-danger"
        }`}
      >
        {isUnsupported ? "Capability Report" : "Failure Report"}
      </p>
      <p className={`mt-2 text-xs ${isUnsupported ? "text-amber-100" : "text-danger"}`}>{firstError}</p>

      {isUnsupported ? (
        <p className="mt-2 text-xs text-amber-100/90">
          This theorem is logically valid but exceeds the current automated proof capability.
        </p>
      ) : null}

      <div className={`mt-3 space-y-2 text-xs ${isUnsupported ? "text-amber-100/90" : "text-rose-200/90"}`}>
        {result.repair_history.slice(-3).map((attempt) => (
          <div
            key={attempt.attempt}
            className={`rounded border p-2 ${
              isUnsupported
                ? "border-amber-300/30 bg-amber-950/20"
                : "border-rose-400/30 bg-rose-950/20"
            }`}
          >
            <p>
              Attempt {attempt.attempt}: {attempt.verification.status} ({attempt.error_class})
            </p>
            {attempt.error_messages[0] ? <p className="mt-1">{attempt.error_messages[0]}</p> : null}
            {attempt.targeted_fix ? <p className="mt-1">Suggestion: {attempt.targeted_fix}</p> : null}
          </div>
        ))}
      </div>

      {lastAttempt ? (
        <p className={`mt-3 text-xs ${isUnsupported ? "text-amber-100/90" : "text-rose-200/90"}`}>
          Final reason classification: {lastAttempt.error_class}.{" "}
          {isUnsupported
            ? `Repair loop skipped due to unsupported capability tier.`
            : `Repair attempts exhausted after ${result.attempts_used} attempt(s).`}
        </p>
      ) : null}
    </div>
  );
}
