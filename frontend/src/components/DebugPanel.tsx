import { useState } from "react";
import type { StructuredError } from "../api";

interface DebugPanelProps {
  error: StructuredError | null;
}

export function DebugPanel({ error }: DebugPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!error) return null;

  return (
    <div className="rounded-lg border border-border bg-panel p-4">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex w-full items-center justify-between text-left"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-textPrimary">
            Technical Diagnostics
          </span>
          <span className="rounded px-2 py-0.5 text-xs font-medium bg-red-500/10 text-red-500">
            {error.stage}
          </span>
          <span className="rounded px-2 py-0.5 text-xs font-medium bg-orange-500/10 text-orange-500">
            {error.error_type}
          </span>
        </div>
        <svg
          className={`h-5 w-5 transition-transform ${isExpanded ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {isExpanded && (
        <div className="mt-4 space-y-3">
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-textMuted">
              Status
            </div>
            <div className="mt-1 text-sm text-textPrimary">{error.status}</div>
          </div>

          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-textMuted">
              Error Message
            </div>
            <div className="mt-1 text-sm text-textPrimary">{error.message}</div>
          </div>

          {error.diagnostics && (
            <div>
              <div className="text-xs font-semibold uppercase tracking-wide text-textMuted">
                Diagnostics
              </div>
              <pre className="mt-1 rounded bg-surface p-2 text-xs text-textSecondary overflow-x-auto">
                {error.diagnostics}
              </pre>
            </div>
          )}

          {error.lean_output && (
            <div>
              <div className="text-xs font-semibold uppercase tracking-wide text-textMuted">
                Lean Output
              </div>
              <pre className="mt-1 rounded bg-surface p-2 text-xs text-textSecondary overflow-x-auto font-mono">
                {error.lean_output}
              </pre>
            </div>
          )}

          {error.traceback && (
            <details className="group">
              <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wide text-textMuted hover:text-textPrimary">
                Full Traceback (Server-side)
              </summary>
              <pre className="mt-2 rounded bg-surface p-2 text-xs text-textSecondary overflow-x-auto font-mono max-h-64 overflow-y-auto">
                {error.traceback}
              </pre>
            </details>
          )}

          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-textMuted">
              Raw JSON
            </div>
            <pre className="mt-1 rounded bg-surface p-2 text-xs text-textSecondary overflow-x-auto max-h-48 overflow-y-auto">
              {JSON.stringify(error, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
