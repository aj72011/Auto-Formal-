import { motion } from "framer-motion";
import type { AnnotatedLinePayload, FormalizeResponse, VerificationRunState } from "../types";
import { CodeViewerWithAnnotations } from "./CodeViewerWithAnnotations";

interface ProofViewerProps {
  result: FormalizeResponse | null;
  runState: VerificationRunState;
  selectedLine?: number;
  onSelectLine: (line: AnnotatedLinePayload) => void;
  focusMode: boolean;
}

function fallbackAnnotatedLines(leanCode: string): AnnotatedLinePayload[] {
  return leanCode.split("\n").map((text, index) => ({
    line_number: index + 1,
    text,
    has_info: false,
    theorem_name: null,
    short_explanation: null,
    concept_summary: null,
    knowledge_id: null,
    concept_key: null,
  }));
}

export function ProofViewer({
  result,
  runState,
  selectedLine,
  onSelectLine,
  focusMode,
}: ProofViewerProps) {
  const lines =
    result?.annotated_lines && result.annotated_lines.length > 0
      ? result.annotated_lines
      : result?.lean_code
        ? fallbackAnnotatedLines(result.lean_code)
        : [];

  return (
    <motion.section
      layout
      transition={{ duration: 0.32, ease: [0.22, 1, 0.36, 1] }}
      className="flex h-full min-h-0 flex-col rounded-md border border-border bg-panel p-4"
    >
      {!focusMode && result ? (
        <div className="rounded-md border border-border bg-panelAlt px-3 py-2">
          <p className="text-[11px] uppercase tracking-wider text-textMuted">Statement</p>
          <p className="mt-1 text-sm text-textMain">{result.original_statement}</p>
        </div>
      ) : null}

      <div className={`min-h-0 flex-1 ${focusMode ? "mt-0" : "mt-3"}`}>
        <div className="mb-2 flex items-center justify-between">
          <p className="text-xs font-semibold uppercase tracking-wider text-textMuted">
            Lean Proof Output
          </p>
          <p className="text-[11px] text-textMuted">
            {runState === "running" && !result ? "Awaiting generated proof..." : "Annotated formalization"}
          </p>
        </div>
        <div
          className={`h-full min-h-0 rounded-md border p-2 ${
            result?.verification.status === "verified"
              ? "border-emerald-400/45 bg-panelAlt shadow-successGlow"
              : "border-border bg-panelAlt"
          }`}
        >
          <CodeViewerWithAnnotations
            lines={lines}
            verificationStatus={result?.verification.status}
            selectedLine={selectedLine}
            onSelectLine={onSelectLine}
          />
        </div>
      </div>
    </motion.section>
  );
}
