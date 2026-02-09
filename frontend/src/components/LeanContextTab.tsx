import { useEffect, useMemo, useState } from "react";
import type { FormalizeResponse } from "../types";
import { CopyProofButton } from "./CopyProofButton";
import { ToastNotification } from "./ToastNotification";

interface LeanContextTabProps {
  result: FormalizeResponse;
}

function uniqueTactics(result: FormalizeResponse): string[] {
  const seen = new Set<string>();
  const ordered: string[] = [];
  for (const step of result.explanation.steps) {
    const normalized = step.tactic.trim();
    if (!normalized || seen.has(normalized)) continue;
    seen.add(normalized);
    ordered.push(normalized);
  }
  return ordered;
}

export function LeanContextTab({ result }: LeanContextTabProps) {
  const [copiedVisible, setCopiedVisible] = useState(false);
  const tactics = useMemo(() => uniqueTactics(result), [result]);

  useEffect(() => {
    if (!copiedVisible) return;
    const timer = window.setTimeout(() => setCopiedVisible(false), 1800);
    return () => window.clearTimeout(timer);
  }, [copiedVisible]);

  return (
    <div className="space-y-3 text-sm text-textMuted">
      <div className="rounded-md border border-border bg-panelAlt p-3">
        <p className="text-xs font-semibold uppercase tracking-wider text-textMuted">
          Reading This Lean Proof
        </p>
        <p className="mt-2">
          Lean proofs are structured as theorem declarations, assumptions, and tactic-driven goal
          transformations. The generated script follows this pattern and is accepted only when
          each step is type-correct.
        </p>
      </div>

      <div className="rounded-md border border-border bg-panelAlt p-3">
        <p className="text-xs font-semibold uppercase tracking-wider text-textMuted">
          Tactic Mapping
        </p>
        <ul className="mt-2 space-y-1 text-xs">
          <li>
            `intro`: introduces universally quantified variables or assumptions into context.
          </li>
          <li>
            `simp`: simplifies expressions using definitional equalities and lemmas.
          </li>
          <li>
            `theorem` block: names the proposition and declares the formal statement Lean checks.
          </li>
        </ul>
        {tactics.length > 0 ? (
          <p className="mt-2 text-xs text-textMuted/85">
            Detected tactics in this proof: {tactics.join(", ")}.
          </p>
        ) : null}
      </div>

      <div className="rounded-md border border-border bg-panelAlt p-3">
        <p className="text-xs font-semibold uppercase tracking-wider text-textMuted">
          Why This Is Valid
        </p>
        <p className="mt-2 text-xs">
          Lean validates the proof by checking term typing, theorem references, and each tactic
          transformation against the current goal state. A verified result means the final goal
          was discharged under Lean's kernel rules.
        </p>
        <div className="mt-3">
          <CopyProofButton
            leanCode={result.lean_code}
            onCopied={() => setCopiedVisible(true)}
          />
        </div>
      </div>

      <ToastNotification visible={copiedVisible} message="Lean code copied." />
    </div>
  );
}
