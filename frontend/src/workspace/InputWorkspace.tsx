import { FormEvent } from "react";
import { StructuredError } from "../api";
import { DebugPanel } from "../components/DebugPanel";
import { EditorContainer } from "../components/EditorContainer";
import { InputHelperPanel } from "../components/InputHelperPanel";
import { LeanInfoStrip } from "../components/LeanInfoStrip";
import { StatusBanner } from "../components/StatusBanner";
import { ThemeMode, ThemeToggle } from "../components/ThemeToggle";
import { WorkspaceHeader } from "../components/WorkspaceHeader";
import type { VerificationRunState } from "../types";
import { NavigationButtons } from "./NavigationButtons";

interface InputWorkspaceProps {
  statement: string;
  mode: "ast" | "direct";
  repairEnabled: boolean;
  loading: boolean;
  error: string;
  structuredError: StructuredError | null;
  runState: VerificationRunState;
  runDetail: string;
  canViewResults: boolean;
  viewLabel: string;
  examples: string[];
  theme: ThemeMode;
  backendOnline: boolean | null;
  checkingConnection: boolean;
  onRetryConnection: () => void;
  onThemeToggle: () => void;
  onStatementChange: (value: string) => void;
  onModeChange: (value: "ast" | "direct") => void;
  onRepairEnabledChange: (value: boolean) => void;
  onSubmit: (event: FormEvent) => void;
  onViewResults: () => void;
}

export function InputWorkspace({
  statement,
  mode,
  repairEnabled,
  loading,
  error,
  structuredError,
  runState,
  runDetail,
  canViewResults,
  viewLabel,
  examples,
  theme,
  backendOnline,
  checkingConnection,
  onRetryConnection,
  onThemeToggle,
  onStatementChange,
  onModeChange,
  onRepairEnabledChange,
  onSubmit,
  onViewResults,
}: InputWorkspaceProps) {
  const controlsDisabled = loading || runState === "running" || backendOnline === false;
  const hasCustomInput =
    statement.trim().length > 0 &&
    !examples.some((example) => example.toLowerCase() === statement.trim().toLowerCase());

  return (
    <div className="h-full w-full overflow-y-auto overflow-x-hidden bg-surface">
      <div className="mx-auto flex min-h-full w-full max-w-[1220px] flex-col gap-4 px-4 py-4 lg:px-6">
        <div className="shrink-0 flex items-center justify-end">
          <ThemeToggle theme={theme} onToggle={onThemeToggle} />
        </div>

        <div className="shrink-0">
          <WorkspaceHeader
            title="Input Workspace"
            subtitle="Describe a mathematical statement in natural language. AutoFormal+ will translate it to Lean 4, verify it, repair failed attempts, and generate a structured proof report."
          />
        </div>

        <div className="shrink-0">
          <LeanInfoStrip />
        </div>

        <div className="shrink-0">
          <StatusBanner context="input" runState={runState} detail={runDetail} />
        </div>

        {backendOnline === false && (
          <div className="shrink-0 rounded-lg border border-rose-400/50 bg-rose-500/10 px-4 py-3">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                <span className="mt-0.5 inline-flex h-2.5 w-2.5 rounded-full bg-rose-400" />
                <div>
                  <p className="text-sm font-semibold text-rose-300">
                    Backend Offline
                  </p>
                  <p className="mt-1 text-xs text-rose-300/85">
                    Cannot reach verification server. Make sure the backend is running on the configured port.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={onRetryConnection}
                disabled={checkingConnection}
                className="rounded-md border border-rose-400/45 bg-rose-500/20 px-3 py-1.5 text-xs font-semibold text-rose-200 transition hover:bg-rose-500/30 disabled:opacity-60"
              >
                {checkingConnection ? "Checking..." : "Retry Connection"}
              </button>
            </div>
          </div>
        )}

        <section className="rounded-xl border border-border/90 bg-panel p-4 shadow-sm">
          <form onSubmit={onSubmit} className="space-y-4">
            <div className="rounded-lg border border-border bg-surface/60 p-3">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-textMuted">
                Natural Language Statement
              </p>
              <p className="mt-1 text-xs text-textMuted">
                Best results come from quantified arithmetic or logic statements with explicit assumptions.
              </p>
              <div className="mt-3">
                <EditorContainer
                  value={statement}
                  disabled={controlsDisabled}
                  examples={examples}
                  onChange={onStatementChange}
                />
              </div>
              <p className="mt-2 text-[11px] text-textMuted/85">
                This statement will be compiled into a Lean 4 proof.
              </p>
              <div className="mt-3">
                <InputHelperPanel minimized={hasCustomInput} />
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-md border border-border bg-panelAlt p-3">
                <p className="text-xs font-semibold uppercase tracking-wider text-textMuted">
                  Pipeline Mode
                </p>
                <select
                  value={mode}
                  disabled={controlsDisabled}
                  onChange={(event) => onModeChange(event.target.value as "ast" | "direct")}
                  className="mt-2 w-full rounded border border-border bg-surface px-2 py-1 text-sm text-textMain"
                >
                  <option value="ast">AST Pipeline</option>
                  <option value="direct">Direct Generation</option>
                </select>
              </div>

              <div className="rounded-md border border-border bg-panelAlt p-3">
                <p className="text-xs font-semibold uppercase tracking-wider text-textMuted">
                  Repair Loop
                </p>
                <label className="mt-2 flex items-center gap-2 text-sm text-textMain">
                  <input
                    type="checkbox"
                    checked={repairEnabled}
                    disabled={controlsDisabled}
                    onChange={(event) => onRepairEnabledChange(event.target.checked)}
                  />
                  Enable automatic proof repair
                </label>
              </div>
            </div>

            {error ? (
              <div className="space-y-3">
                <div className="rounded border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
                  {error}
                </div>
                {structuredError && <DebugPanel error={structuredError} />}
              </div>
            ) : null}

            <div className="sticky bottom-0 z-20 -mx-4 border-t border-border/80 bg-surface/95 px-4 py-3 backdrop-blur">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <button
                  type="submit"
                  disabled={controlsDisabled}
                  className="rounded-md border border-accent/45 bg-accent/12 px-5 py-2.5 text-sm font-semibold text-accent transition hover:bg-accent/22 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {controlsDisabled ? "Running pipeline..." : "Formalize / Validate"}
                </button>

                <NavigationButtons
                  page="input"
                  canViewResults={canViewResults}
                  disableView={false}
                  viewLabel={viewLabel}
                  onViewResults={onViewResults}
                  onBackToInput={() => {}}
                />
              </div>
            </div>
          </form>
        </section>
      </div>
    </div>
  );
}
