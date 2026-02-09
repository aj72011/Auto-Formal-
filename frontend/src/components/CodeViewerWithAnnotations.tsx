import { useState } from "react";
import type { AnnotatedLinePayload, VerificationStatus } from "../types";
import { Tooltip } from "./Tooltip";

interface CodeViewerWithAnnotationsProps {
  lines: AnnotatedLinePayload[];
  verificationStatus?: VerificationStatus;
  selectedLine?: number;
  onSelectLine: (line: AnnotatedLinePayload) => void;
}

export function CodeViewerWithAnnotations({
  lines,
  verificationStatus,
  selectedLine,
  onSelectLine,
}: CodeViewerWithAnnotationsProps) {
  const [openTooltipLine, setOpenTooltipLine] = useState<number | null>(null);

  return (
    <div
      className={`h-full overflow-y-auto rounded-md border bg-codeSurface p-4 font-mono text-sm ${
        verificationStatus === "verified" ? "border-emerald-400/40 shadow-successGlow" : "border-border"
      }`}
    >
      {lines.length === 0 ? (
        <div className="flex h-full items-center justify-center text-xs text-textMuted">
          Proof output will appear here after formalization.
        </div>
      ) : (
        <div className="space-y-1">
          {lines.map((line) => {
            const active = line.line_number === selectedLine;
            return (
              <div
                key={`${line.line_number}-${line.text}`}
                className={`group relative flex items-start gap-3 rounded px-2 py-1 transition ${
                  active ? "bg-accent/10" : "hover:bg-white/5"
                }`}
              >
                <span className="w-8 select-none text-right text-xs text-textMuted/80">
                  {line.line_number}
                </span>
                <button
                  type="button"
                  onClick={() => onSelectLine(line)}
                  className="flex-1 cursor-pointer text-left text-codeText"
                >
                  {line.text || " "}
                </button>
                {line.has_info ? (
                  <div className="relative">
                    <button
                      type="button"
                      onClick={() =>
                        setOpenTooltipLine((current) =>
                          current === line.line_number ? null : line.line_number,
                        )
                      }
                      className="mt-0.5 h-5 w-5 rounded-full border border-accent/40 text-[10px] font-bold text-accent transition hover:bg-accent/10"
                      aria-label="Show annotation"
                    >
                      i
                    </button>
                    <Tooltip
                      visible={openTooltipLine === line.line_number}
                      title={line.theorem_name ?? line.concept_key ?? "Concept"}
                      body={`${line.short_explanation ?? "No summary."}\n\n${line.concept_summary ?? ""}`}
                    />
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
