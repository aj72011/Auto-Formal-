import type { FormalizeResponse } from "../types";
import { FailureReportPanel } from "./FailureReportPanel";
import { PipelineChecklist } from "./PipelineChecklist";

interface VerificationReportPanelProps {
  result: FormalizeResponse;
}

export function VerificationReportPanel({ result }: VerificationReportPanelProps) {
  const repairTriggered = result.attempts_used > 1;
  const isUnsupported = result.verification.status === "unsupported";

  return (
    <div className="space-y-3 text-sm text-textMuted">
      <div className="rounded-md border border-border bg-panelAlt p-3">
        <p className="text-xs font-semibold uppercase tracking-wider text-textMuted">
          Final Status Summary
        </p>
        <p className="mt-2 text-sm text-textMain">
          {result.verification.status === "verified"
            ? "All required stages completed and Lean accepted the proof."
            : isUnsupported
              ? "The theorem was classified outside the supported Tier 1/Tier 2 subset."
              : "Automatic repair attempts were exhausted before verification succeeded."}
        </p>
        <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
          <div className="rounded border border-border bg-panel px-2 py-1 text-xs">
            Repair loop triggered: {isUnsupported ? "No (guarded)" : repairTriggered ? "Yes" : "No"}
          </div>
          <div className="rounded border border-border bg-panel px-2 py-1 text-xs">
            Repair attempts: {result.attempts_used}
          </div>
          <div className="rounded border border-border bg-panel px-2 py-1 text-xs sm:col-span-2">
            Capability tier: {result.capability.tier} ({result.capability.tier_label})
          </div>
        </div>
      </div>

      <PipelineChecklist
        stageTraces={result.stage_traces}
        mode={result.mode === "direct" ? "direct" : "ast"}
      />

      <FailureReportPanel result={result} />
    </div>
  );
}
